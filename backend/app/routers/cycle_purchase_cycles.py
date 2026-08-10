"""
週期採購 — 週期設定 API Router
Prefix: /api/v1/cycle-purchase

GET  /cycles                              週期設定清單
GET  /cycles/options                      表單下拉選項（適用公司／適用品類，取自主檔 distinct）
GET  /cycles/{id}                         週期設定詳情
POST /cycles                              新增週期設定
POST /cycles/{id}/preview-orphan-requests 預覽：套用這份設定後會刪掉哪幾張孤兒空白請購單
PUT  /cycles/{id}                         更新週期設定（可帶 delete_orphans=true 一併清理）

2026-08-09（部門範圍改版，見 models/cycle_purchase_cycle.py 開頭說明）：
  - 新增 /cycles/options：適用公司／適用品類改成從主檔 distinct 值選，不讓手打。
  - 新增兩段式確認：前端先打 preview-orphan-requests 拿到「會被刪掉的空白單」
    清單給使用者確認，確認後才送 PUT /cycles/{id}?delete_orphans=true。
    刻意不做成「儲存時自動靜默刪除」——刪資料一定要讓人先看到刪什麼。
  - preview 端點用 POST 而非 GET，因為要帶「還沒儲存的那份設定」當 body。
"""
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.cycle_purchase_database import get_cycle_purchase_db
from app.dependencies import require_permission
from app.models.cycle_purchase_cycle import CyclePurchaseCycle
from app.models.user import User
from app.schemas.cycle_purchase_cycle import (
    CycleCreate, CycleOptionsOut, CycleOut, CycleUpdate,
    OrphanPreviewResult, OrphanRequestOut,
)
from app.services import cycle_purchase_service as svc
from app.services import cycle_purchase_request_service as req_svc

router = APIRouter()


@router.get("/cycles", response_model=List[CycleOut], summary="週期採購週期設定清單")
def list_cycles(
    status_: Optional[str] = Query(None, alias="status"),
    _: User = Depends(require_permission("cycle_purchase_view")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return svc.list_cycles(db, status=status_)


@router.get("/cycles/options", response_model=CycleOptionsOut, summary="週期設定表單下拉選項")
def get_cycle_options(
    _: User = Depends(require_permission("cycle_purchase_view")),
    db: Session = Depends(get_cycle_purchase_db),
):
    """⚠️ 路由順序：這支必須宣告在 /cycles/{cycle_id} 之前，
    否則 "options" 會被 FastAPI 當成 cycle_id 去 match 到詳情端點。"""
    return svc.get_cycle_options(db)


@router.get("/cycles/{cycle_id}", response_model=CycleOut, summary="週期設定詳情")
def get_cycle(
    cycle_id: int,
    _: User = Depends(require_permission("cycle_purchase_view")),
    db: Session = Depends(get_cycle_purchase_db),
):
    cycle = svc.get_cycle(db, cycle_id)
    if not cycle:
        raise HTTPException(status_code=404, detail="週期設定不存在")
    return cycle


@router.post("/cycles", response_model=CycleOut, status_code=status.HTTP_201_CREATED, summary="新增週期設定")
def create_cycle(
    payload: CycleCreate,
    _: User = Depends(require_permission("cycle_purchase_admin")),
    db: Session = Depends(get_cycle_purchase_db),
):
    try:
        return svc.create_cycle(db, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="週期代碼已存在")


@router.post(
    "/cycles/{cycle_id}/preview-orphan-requests",
    response_model=OrphanPreviewResult,
    summary="預覽：套用這份設定後，會刪掉哪幾張孤兒空白請購單",
)
def preview_orphan_requests(
    cycle_id: int,
    payload: CycleUpdate,
    _: User = Depends(require_permission("cycle_purchase_admin")),
    db: Session = Depends(get_cycle_purchase_db),
):
    """
    把「使用者剛改好但還沒儲存」的那份設定套到記憶體中的 cycle 物件上算一次，
    算完 rollback，**不留下任何寫入**。這樣預覽看到的結果就是真正儲存後的結果，
    不會出現「預覽說要刪 3 張、實際刪了 5 張」這種落差。
    """
    cycle = db.query(CyclePurchaseCycle).filter(CyclePurchaseCycle.id == cycle_id).first()
    if not cycle:
        raise HTTPException(status_code=404, detail="週期設定不存在")

    try:
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(cycle, k, v)
        orphans, protected = req_svc.find_orphan_blank_requests(db, cycle)
    finally:
        # 一定要還原，否則這個 session 後續（或 autoflush）可能把試算值寫進去
        db.rollback()

    return OrphanPreviewResult(
        orphans=[OrphanRequestOut(**o) for o in orphans],
        protected_count=protected,
    )


@router.put("/cycles/{cycle_id}", response_model=CycleOut, summary="更新週期設定")
def update_cycle(
    cycle_id: int,
    payload: CycleUpdate,
    delete_orphans: bool = Query(
        False,
        description="是否一併刪除「部門已不再適用」的孤兒空白請購單"
                    "（僅刪明細 0 筆＋未關閉＋未彙整者）。前端應先打 "
                    "preview-orphan-requests 讓使用者確認後再帶 true。",
    ),
    _: User = Depends(require_permission("cycle_purchase_admin")),
    db: Session = Depends(get_cycle_purchase_db),
):
    try:
        cycle = svc.update_cycle(db, cycle_id, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="週期代碼已存在")
    if not cycle:
        raise HTTPException(status_code=404, detail="週期設定不存在")

    if delete_orphans:
        # 刻意在 update 之後、同一個 transaction 內重算一次孤兒清單
        # （不吃前端傳來的 id），避免預覽與執行之間有人填了明細而誤刪。
        deleted = req_svc.delete_orphan_blank_requests(db, cycle)
        cycle.deleted_orphan_count = deleted  # 衍生欄位，供前端提示；不落地
    return cycle
