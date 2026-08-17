"""
週期採購 — 請購單 API Router
Prefix: /api/v1/cycle-purchase

2026-07-11：拿掉「批次」後，請購單改掛 cycle_id + period_label（期別標籤）。
「產生本期請購單」（POST /requests/generate）取代原本批次開放時的自動觸發，
隨時可呼叫，同一週期＋期別冪等（不會重複建立）。

2026-07-17（第三次調整，請購單流程大改版，詳見 models/cycle_purchase_request.py
與 services/cycle_purchase_request_service.py 開頭說明）：
  - 拿掉送出／簽核／退回三個端點，改成「關閉／重新開啟」。
  - period_label 不再是呼叫端傳入的欄位，一律由後端在建立當下蓋章。
  - Dashboard 待辦提醒的「待簽核」改成「本月待關閉」，改看 cycle_purchase_close 權限。

2026-07-19（與 Samuel 確認，開放「只有 cycle_purchase_request 權限」的一般填單人
能實際使用請購單功能——原本清單/詳情/待辦三個讀取端點寫死要求 cycle_purchase_view，
只勾 cycle_purchase_request 的人連清單都叫不出來，選單也因此不會展開）：
  - GET /requests、GET /requests/todos、GET /requests/{id} 改成
    require_any_permission("cycle_purchase_view", "cycle_purchase_request")，
    查看範圍是「全公司所有部門」，不分部門（與 Samuel 確認，先求簡單）。
  - 編輯類端點（PUT /requests/{id}、可選料號、新增/更新/刪除明細）維持要求
    cycle_purchase_request，但新增 _ensure_own_department() 檢查：若使用者
    只有 cycle_purchase_request（沒有 cycle_purchase_view 或 system_admin），
    只能編輯自己承辦部門（CyclePurchaseDepartment.owner_user_id，2026-07-11
    既有欄位，原本只用在 Dashboard 待辦提醒）的請購單，避免改到別部門的單。

2026-08-07（第四次調整，與 Samuel 確認）：
  - **已關閉的請購單需要權限才看得到**：沒有 cycle_purchase_close（也沒有
    cycle_purchase_view / system_admin）的人，GET /requests 不回傳已關閉的單、
    GET /requests/{id} 打已關閉的單直接 403。採**後端硬過濾**而非前端預設篩選
    ——前端篩選只是畫面乾淨，切個下拉就看得到，不算權限控制。
  - 判斷用 _can_see_closed()，與 get_todos 既有的 is_closer 判斷共用同一組權限。

2026-08-09（第五次調整，部門範圍 + 品類接線，見 models/cycle_purchase_cycle.py）：
  - **POST /requests/generate 的回傳型別改變**：原本 `List[RequestOut]`，改成
    `GenerateRequestsResult`（`{requests, skipped}`）。skipped 是「某些部門為什麼
    沒產生」的原因清單，必須顯示給使用者——否則買家只會看到「怎麼少了一張單」。
    這是回傳型別變更，不是端點移除；呼叫端只有前端 Requests 頁一處，已同步調整。
  - 新增 GET /requests/generate-preview：按下產生之前先看會產生哪些部門。
  - **新增 close_state 篩選**（open／closed_manual／closed_auto）。刻意不沿用既有的
    status 參數——那是改版前的殘留欄位（新資料一律 draft），拿它當「狀態」會篩出
    使用者無法理解的結果。status 參數保留未動（CLAUDE.md §5）。
    無權限者就算硬送 close_state=closed_auto 也不會外洩：可見性過濾是另一個
    AND 條件，結果必然是空集合。

2026-08-17（新增 DELETE /requests/{id}，與 Samuel 確認）：
  - 手動新增在同日放寬成「同週期＋期別＋部門已有單也不擋，只提醒」（見
    create_request()），代表使用者可能選錯週期/部門建出一張沒用的空白單，
    原本沒有「自己刪掉重建」的入口，只能等系統在週期範圍縮小時順便清孤兒單。
  - 判準沿用既有 find_orphan_blank_requests()／delete_orphan_blank_requests()
    的三條件（明細 0 筆＋未關閉＋未彙整），不另外發明一套標準；權限與
    _ensure_own_department() 都比照 PUT /requests/{id} 同一套規則。

GET    /requests                              請購單清單（依週期／期別／部門／close_state 篩選；已關閉的單需權限）
GET    /requests/todos                        Dashboard 待辦提醒（我的待填 + 本月待關閉）
GET    /requests/{id}                          請購單詳情（含明細；已關閉的單需權限，否則 403）
GET    /requests/generate-preview               產生前預覽：這個週期會產生哪些部門的單、哪些不會與原因
POST   /requests/generate                      產生本期請購單（依週期設定的適用範圍，一次幫所有適用部門建空白單）
POST   /requests                               手動新增單一部門的請購單（備用路徑）
GET    /requests/copy-candidates               複製上期請購單：列出同週期＋同部門過去有填過品項的請購單供選擇
POST   /requests/{id}/copy                     複製上期請購單：以某張過去的單為範本建立新單（2026-08-13 新增）
PUT    /requests/{id}                          更新請購單（成本中心／備註，僅「開放中」可編輯；2026-08-07 起不再限當月）
DELETE /requests/{id}                          刪除請購單（僅限明細 0 筆＋未關閉＋未彙整的空白單；2026-08-17 新增）
GET    /requests/{id}/available-items          可選料號清單（該公司＋部門＋該週期品類下有對照的啟用中料號）
POST   /requests/{id}/items                    新增請購明細
PUT    /requests/{id}/items/{item_row_id}      更新請購明細（數量／會計科目／備註）
DELETE /requests/{id}/items/{item_row_id}      刪除請購明細
GET    /requests/open-for-close                列出某週期（可選：公司／月份）目前開放中的請購單，供勾選關閉
POST   /requests/close                         關閉勾選的請購單
POST   /requests/close-all                     全部關閉（某週期＋公司＋月份目前開放中的全部請購單）
POST   /requests/reopen                        重新開啟已關閉的請購單
"""
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.cycle_purchase_database import get_cycle_purchase_db
from app.core.database import get_db
from app.dependencies import require_permission, require_any_permission, get_user_permissions
from app.models.cycle_purchase_reference import CyclePurchaseDepartment
from app.models.cycle_purchase_request import CyclePurchaseRequest
from app.models.user import User
from app.schemas.cycle_purchase_request import (
    AvailableItemOut, CloseAllRequestsPayload, CloseRequestsPayload,
    CopyRequestResult, CopySkippedItemOut, CopySourceCandidateOut,
    GeneratePreviewResult, GenerateRequestsPayload, GenerateRequestsResult,
    ReopenRequestsPayload, RequestCreate, RequestDetail,
    RequestItemCreate, RequestItemOut, RequestItemUpdate, RequestOut,
    RequestUpdate, TodoSummary,
)
from app.services import cycle_purchase_request_service as svc
from app.services.cycle_purchase_request_service import RequestForbiddenError, RequestServiceError

router = APIRouter()


def _handle(fn, *args, **kwargs):
    """共用：把 RequestServiceError 轉成 422，統一錯誤訊息格式。"""
    try:
        return fn(*args, **kwargs)
    except RequestServiceError as e:
        raise HTTPException(status_code=422, detail=str(e))


def _ensure_own_department(
    request_id: int,
    current_user: User,
    db: Session,
    portal_db: Session,
) -> None:
    """
    2026-07-19 新增：只有 cycle_purchase_request（沒有 cycle_purchase_view／
    system_admin）的一般填單人，只能編輯「自己承辦部門」的請購單。
    承辦部門依 CyclePurchaseDepartment.owner_user_id 判斷（2026-07-11 既有欄位，
    原本只用在 Dashboard 待辦提醒，這裡是第二個使用場景）。
    找不到請購單時直接放行，讓呼叫端接續的查詢/更新邏輯回 404，不在這裡搶著處理。
    """
    perms = get_user_permissions(current_user.id, portal_db)
    if "*" in perms or "cycle_purchase_view" in perms:
        return
    req = db.query(CyclePurchaseRequest).filter(CyclePurchaseRequest.id == request_id).first()
    if not req:
        return
    dept = (
        db.query(CyclePurchaseDepartment)
        .filter(CyclePurchaseDepartment.id == req.department_id)
        .first()
    )
    if not dept or dept.owner_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能編輯自己承辦部門的請購單")


@router.get("/requests", response_model=List[RequestOut], summary="週期採購請購單清單")
def list_requests(
    cycle_id: Optional[int] = Query(None),
    period_label: Optional[str] = Query(None),
    department_id: Optional[int] = Query(None),
    status_: Optional[str] = Query(None, alias="status"),
    close_state: Optional[str] = Query(
        None,
        description="狀態篩選：open（開放中）｜closed_manual（人工關閉）｜closed_auto（系統自動關閉）；不給＝全部",
    ),
    current_user: User = Depends(require_any_permission("cycle_purchase_view", "cycle_purchase_request")),
    db: Session = Depends(get_cycle_purchase_db),
    portal_db: Session = Depends(get_db),
):
    try:
        return svc.list_requests(
            db, cycle_id=cycle_id, period_label=period_label,
            department_id=department_id, status=status_,
            can_see_closed=_can_see_closed(current_user, portal_db),
            close_state=close_state,
        )
    except RequestServiceError as e:
        raise HTTPException(status_code=422, detail=str(e))


def _can_see_closed(current_user: User, portal_db: Session) -> bool:
    """能不能看到已關閉（含系統自動關閉）的請購單。

    2026-08-07 與 Samuel 確認採 cycle_purchase_close：能關閉／重新開啟的人才看得到
    關閉後的結果，語意最一致。cycle_purchase_view（全模組可見）與 system_admin
    一併放行，它們本來就是更大的範圍。
    """
    perms = get_user_permissions(current_user.id, portal_db)
    return (
        "*" in perms
        or "cycle_purchase_close" in perms
        or "cycle_purchase_view" in perms
    )


@router.get("/requests/todos", response_model=TodoSummary, summary="Dashboard 待辦提醒")
def get_todos(
    current_user: User = Depends(require_any_permission("cycle_purchase_view", "cycle_purchase_request")),
    db: Session = Depends(get_cycle_purchase_db),
    portal_db: Session = Depends(get_db),
):
    perms = get_user_permissions(current_user.id, portal_db)
    is_closer = "*" in perms or "cycle_purchase_close" in perms
    return svc.get_dashboard_todos(db, current_user, is_closer)


@router.get(
    "/requests/open-for-close",
    response_model=List[RequestOut],
    summary="列出某週期（可選：公司／月份）目前開放中的請購單，供勾選關閉",
)
def list_open_for_close(
    cycle_id: int = Query(...),
    company: Optional[str] = Query(None),
    year_month: Optional[str] = Query(None),
    _: User = Depends(require_permission("cycle_purchase_close")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return svc.list_open_requests_for_close(db, cycle_id, company, year_month)


@router.get(
    "/requests/generate-preview",
    response_model=GeneratePreviewResult,
    summary="產生前預覽：這個週期會產生哪些部門的單、哪些不會與原因",
)
def preview_generate_requests(
    cycle_id: int = Query(..., description="週期設定 id"),
    _: User = Depends(require_permission("cycle_purchase_buyer")),
    db: Session = Depends(get_cycle_purchase_db),
):
    """⚠️ 路由順序：這支必須宣告在 /requests/{request_id} 之前，
    否則 "generate-preview" 會被當成 request_id。"""
    return _handle(svc.preview_applicable_departments, db, cycle_id)


@router.get(
    "/requests/copy-candidates",
    response_model=List[CopySourceCandidateOut],
    summary="複製上期請購單：列出同週期＋同部門過去有填過品項的請購單供選擇",
)
def list_copy_source_candidates(
    cycle_id: int = Query(...),
    department_id: int = Query(...),
    _: User = Depends(require_permission("cycle_purchase_buyer")),
    db: Session = Depends(get_cycle_purchase_db),
):
    """⚠️ 路由順序：這支必須宣告在 /requests/{request_id} 之前，
    否則 "copy-candidates" 會被當成 request_id。"""
    return svc.list_copy_source_candidates(db, cycle_id, department_id)


@router.get("/requests/{request_id}", response_model=RequestDetail, summary="請購單詳情（含明細）")
def get_request(
    request_id: int,
    current_user: User = Depends(require_any_permission("cycle_purchase_view", "cycle_purchase_request")),
    db: Session = Depends(get_cycle_purchase_db),
    portal_db: Session = Depends(get_db),
):
    try:
        req = svc.get_request(
            db, request_id, can_see_closed=_can_see_closed(current_user, portal_db)
        )
    except RequestForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))
    if not req:
        raise HTTPException(status_code=404, detail="請購單不存在")
    return req


@router.post(
    "/requests/generate",
    response_model=GenerateRequestsResult,
    summary="產生本期請購單（一次幫所有適用部門建空白單，隨時可觸發、冪等）",
)
def generate_requests(
    payload: GenerateRequestsPayload,
    _: User = Depends(require_permission("cycle_purchase_buyer")),
    db: Session = Depends(get_cycle_purchase_db),
):
    requests, skipped = _handle(svc.generate_requests_for_period, db, payload.cycle_id)
    return GenerateRequestsResult(requests=requests, skipped=skipped)


@router.post("/requests", response_model=RequestOut, status_code=status.HTTP_201_CREATED, summary="手動新增單一部門的請購單")
def create_request(
    payload: RequestCreate,
    _: User = Depends(require_permission("cycle_purchase_buyer")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return _handle(svc.create_request, db, payload)


@router.post(
    "/requests/{source_request_id}/copy",
    response_model=CopyRequestResult,
    status_code=status.HTTP_201_CREATED,
    summary="複製上期請購單：以某張過去的單為範本建立新單",
)
def copy_request(
    source_request_id: int,
    current_user: User = Depends(require_permission("cycle_purchase_buyer")),
    db: Session = Depends(get_cycle_purchase_db),
):
    new_req, skipped = _handle(svc.copy_request, db, source_request_id, current_user)
    return CopyRequestResult(
        request=new_req,
        skipped_items=[CopySkippedItemOut(**s) for s in skipped],
    )


@router.put("/requests/{request_id}", response_model=RequestOut, summary="更新請購單")
def update_request(
    request_id: int,
    payload: RequestUpdate,
    current_user: User = Depends(require_permission("cycle_purchase_request")),
    db: Session = Depends(get_cycle_purchase_db),
    portal_db: Session = Depends(get_db),
):
    _ensure_own_department(request_id, current_user, db, portal_db)
    req = _handle(svc.update_request, db, request_id, payload)
    if not req:
        raise HTTPException(status_code=404, detail="請購單不存在")
    return req


@router.delete(
    "/requests/{request_id}",
    summary="刪除請購單（僅限明細 0 筆＋未關閉＋未彙整的空白單）",
)
def delete_request(
    request_id: int,
    current_user: User = Depends(require_permission("cycle_purchase_request")),
    db: Session = Depends(get_cycle_purchase_db),
    portal_db: Session = Depends(get_db),
):
    """2026-08-17 新增：判準跟既有「週期範圍縮小時自動清孤兒單」
    （find_orphan_blank_requests／delete_orphan_blank_requests）完全一樣，
    只是這裡是使用者主動刪單一張——手動新增放寬擋重後，選錯週期／部門、
    或手滑重複建立的空白單需要有辦法清掉。"""
    _ensure_own_department(request_id, current_user, db, portal_db)
    ok = _handle(svc.delete_request, db, request_id)
    if ok is None:
        raise HTTPException(status_code=404, detail="請購單不存在")
    return {"ok": True}


@router.get(
    "/requests/{request_id}/available-items",
    response_model=List[AvailableItemOut],
    summary="可選料號清單（依請購單所屬公司過濾）",
)
def get_available_items(
    request_id: int,
    current_user: User = Depends(require_permission("cycle_purchase_request")),
    db: Session = Depends(get_cycle_purchase_db),
    portal_db: Session = Depends(get_db),
):
    _ensure_own_department(request_id, current_user, db, portal_db)
    return _handle(svc.get_available_items, db, request_id)


@router.post(
    "/requests/{request_id}/items",
    response_model=RequestItemOut,
    status_code=status.HTTP_201_CREATED,
    summary="新增請購明細",
)
def add_request_item(
    request_id: int,
    payload: RequestItemCreate,
    current_user: User = Depends(require_permission("cycle_purchase_request")),
    db: Session = Depends(get_cycle_purchase_db),
    portal_db: Session = Depends(get_db),
):
    _ensure_own_department(request_id, current_user, db, portal_db)
    return _handle(svc.add_request_item, db, request_id, payload)


@router.put(
    "/requests/{request_id}/items/{item_row_id}",
    response_model=RequestItemOut,
    summary="更新請購明細",
)
def update_request_item(
    request_id: int,
    item_row_id: int,
    payload: RequestItemUpdate,
    current_user: User = Depends(require_permission("cycle_purchase_request")),
    db: Session = Depends(get_cycle_purchase_db),
    portal_db: Session = Depends(get_db),
):
    _ensure_own_department(request_id, current_user, db, portal_db)
    row = _handle(svc.update_request_item, db, request_id, item_row_id, payload)
    if not row:
        raise HTTPException(status_code=404, detail="請購明細不存在")
    return row


@router.delete("/requests/{request_id}/items/{item_row_id}", summary="刪除請購明細")
def delete_request_item(
    request_id: int,
    item_row_id: int,
    current_user: User = Depends(require_permission("cycle_purchase_request")),
    db: Session = Depends(get_cycle_purchase_db),
    portal_db: Session = Depends(get_db),
):
    _ensure_own_department(request_id, current_user, db, portal_db)
    ok = _handle(svc.delete_request_item, db, request_id, item_row_id)
    if not ok:
        raise HTTPException(status_code=404, detail="請購明細不存在")
    return {"ok": True}


@router.post("/requests/close", response_model=List[RequestOut], summary="關閉勾選的請購單")
def close_requests(
    payload: CloseRequestsPayload,
    current_user: User = Depends(require_permission("cycle_purchase_close")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return _handle(svc.close_requests, db, payload.request_ids, current_user)


@router.post("/requests/close-all", response_model=List[RequestOut], summary="全部關閉")
def close_all_requests(
    payload: CloseAllRequestsPayload,
    current_user: User = Depends(require_permission("cycle_purchase_close")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return _handle(
        svc.close_all_requests, db, payload.cycle_id, payload.company, payload.year_month, current_user,
    )


@router.post("/requests/reopen", response_model=List[RequestOut], summary="重新開啟已關閉的請購單")
def reopen_requests(
    payload: ReopenRequestsPayload,
    current_user: User = Depends(require_permission("cycle_purchase_close")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return _handle(svc.reopen_requests, db, payload.request_ids, current_user)
