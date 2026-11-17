"""
系統設定 › Ragic 表單關聯 API（/api/v1/settings/ragic-forms）— docs/SPEC_stock_management.md §4.3

2026-11-17 Phase 1 建立於 /api/v1/stock，同日依 Samuel 裁示搬到「系統設定」（請購／採購／請款
三種單據的表單設定不只庫存模組使用）並開放有權限者編輯 ragic_sheet_config。

  GET  ""                          表單關聯表（公司 × 部門 × 三種表單＋連結＋同步筆數）
  POST /configs                    新增表單設定（補「未設定」的格）
  PUT  /configs/{id}               修改路徑／暫停同步（標 manual_override，啟動 seed 不覆寫）
  POST /configs/{id}/reset         還原為程式預設值（取消 manual_override）
  GET  /purchase-orders            Ragic 採購單清單
  GET  /purchase-orders/{id}       採購單明細（含品項）
權限：查看 settings_ragic_forms_view（或 _manage）；編輯 settings_ragic_forms_manage
"""
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import require_any_permission, require_permission
from app.models.claim_request import ApprovedClaimRequest
from app.models.nichiyo_claim_request import NichiyoClaimRequest
from app.models.nichiyo_purchase_request import NichiyoPurchaseRequest
from app.models.purchase_request import ApprovedPurchaseRequest
from app.models.ragic_purchase_order import RagicPurchaseOrder, RagicPurchaseOrderItem
from app.models.ragic_sheet_config import RagicSheetConfig
from app.models.taichung_claim_request import TaichungClaimRequest
from app.models.taichung_purchase_request import TaichungPurchaseRequest

router = APIRouter()
VIEW = "settings_ragic_forms_view"
MANAGE = "settings_ragic_forms_manage"
_can_view = require_any_permission(VIEW, MANAGE)
RAGIC_BASE = "https://ap12.ragic.com/soutlet001"

COMPANIES = ["樂群", "日曜", "台中"]
COMPANY_ALIAS = {"樂群": "春大直", "日曜": "日曜天地", "台中": "智選"}
FORM_TYPES = [("purchase", "請購單"), ("po", "採購單"), ("claim", "請款單")]

# (公司, 表單類型) → (ragic_sheet_config.module, 同步資料表 Model)
MODULE_MAP = {
    ("樂群", "purchase"): ("purchase", ApprovedPurchaseRequest),
    ("樂群", "po"):       ("purchase_po", RagicPurchaseOrder),
    ("樂群", "claim"):    ("claim", ApprovedClaimRequest),
    ("日曜", "purchase"): ("nichiyo_purchase", NichiyoPurchaseRequest),
    ("日曜", "po"):       ("nichiyo_po", RagicPurchaseOrder),
    ("日曜", "claim"):    ("nichiyo_claim", NichiyoClaimRequest),
    ("台中", "purchase"): ("taichung_purchase", TaichungPurchaseRequest),
    ("台中", "po"):       ("taichung_po", RagicPurchaseOrder),
    ("台中", "claim"):    ("taichung_claim", TaichungClaimRequest),
}


def _dt(v) -> Optional[str]:
    return v.strftime("%Y-%m-%d %H:%M") if v else None


def _sheet_stats(db: Session, model) -> dict[str, tuple[int, Optional[str]]]:
    q = db.query(model.ragic_sheet_path, func.count(model.id), func.max(model.sync_at))
    if model is RagicPurchaseOrder:
        q = q.filter(RagicPurchaseOrder.is_ragic_deleted.is_(False))
    return {p: (n, _dt(t)) for p, n, t in q.group_by(model.ragic_sheet_path).all()}


@router.get("", summary="Ragic 請購／採購／請款 表單關聯表")
def get_ragic_forms(db: Session = Depends(get_db), _=Depends(_can_view)):
    stats_cache: dict = {}
    rows: dict[tuple[str, str], dict] = {}
    order: dict[tuple[str, str], tuple] = {}
    for (company, ftype), (module, model) in MODULE_MAP.items():
        if model not in stats_cache:
            stats_cache[model] = _sheet_stats(db, model)
        stats = stats_cache[model]
        cfgs = (db.query(RagicSheetConfig).filter(RagicSheetConfig.module == module)
                .order_by(RagicSheetConfig.sort_order).all())
        for c in cfgs:
            key = (company, c.display_name)
            row = rows.setdefault(key, {"company": company, "company_alias": COMPANY_ALIAS.get(company, ""),
                                        "department": c.display_name,
                                        "purchase": None, "po": None, "claim": None})
            order[key] = min(order.get(key, (99, 999)), (FORM_TYPES.index(next(f for f in FORM_TYPES if f[0] == ftype)), c.sort_order or 0))
            n, last = stats.get(c.list_path, (0, None))
            row[ftype] = {
                "config_id": c.id,
                "manual_override": bool(getattr(c, "manual_override", False)),
                "module": module,
                "form_name": dict(FORM_TYPES)[ftype],
                "path": c.list_path,
                "detail_path": c.detail_path,
                "url": f"{RAGIC_BASE}/{c.list_path}",
                "is_active": bool(c.is_active),
                "records": n,
                "last_sync_at": last,
            }
    out = sorted(rows.values(), key=lambda r: (COMPANIES.index(r["company"]), order[(r["company"], r["department"])][1], r["department"]))
    modules = [{"company": c, "form_type": f, "form_name": dict(FORM_TYPES)[f], "module": m}
               for (c, f), (m, _) in MODULE_MAP.items()]
    return {"companies": COMPANIES, "company_alias": COMPANY_ALIAS, "modules": modules, "rows": out}


# ── 編輯 ragic_sheet_config ───────────────────────────────────────────────────

_PATH_RE = re.compile(r"^[a-z0-9][a-z0-9\-]*/\d+$")


def _clean_path(v: str) -> str:
    """接受完整網址或 slug/數字；回傳 slug/數字。"""
    t = (v or "").strip()
    t = re.sub(r"^https?://[^/]+/soutlet001/", "", t).split("?")[0].strip("/")
    if not _PATH_RE.match(t):
        raise HTTPException(status_code=422, detail=f"表單路徑格式錯誤：{v}（應為 slug/數字，例如 new-tab/11）")
    return t


def _valid_modules() -> set[str]:
    return {m for (m, _) in MODULE_MAP.values()}


class ConfigCreate(BaseModel):
    module: str
    display_name: str = Field(..., min_length=1, max_length=50)
    list_path: str
    detail_path: Optional[str] = None
    is_active: bool = True


class ConfigUpdate(BaseModel):
    list_path: Optional[str] = None
    detail_path: Optional[str] = None
    is_active: Optional[bool] = None


def _cfg_out(c: RagicSheetConfig) -> dict:
    return {"id": c.id, "module": c.module, "display_name": c.display_name, "list_path": c.list_path,
            "detail_path": c.detail_path, "is_active": bool(c.is_active),
            "manual_override": bool(c.manual_override)}


@router.post("/configs", summary="新增表單設定")
def create_config(payload: ConfigCreate, db: Session = Depends(get_db), _=Depends(require_permission(MANAGE))):
    if payload.module not in _valid_modules():
        raise HTTPException(status_code=422, detail=f"不支援的 module：{payload.module}")
    name = payload.display_name.strip()
    if db.query(RagicSheetConfig).filter(RagicSheetConfig.module == payload.module,
                                         RagicSheetConfig.display_name == name).first():
        raise HTTPException(status_code=409, detail="此公司、部門已有這種表單的設定，請改用編輯")
    lp = _clean_path(payload.list_path)
    if db.query(RagicSheetConfig).filter(RagicSheetConfig.module == payload.module,
                                         RagicSheetConfig.list_path == lp).first():
        raise HTTPException(status_code=409, detail=f"表單 {lp} 已設定在同一類表單的其他部門")
    max_order = db.query(func.max(RagicSheetConfig.sort_order)).filter(RagicSheetConfig.module == payload.module).scalar() or 0
    c = RagicSheetConfig(module=payload.module, display_name=name, ragic_dept=name, list_path=lp,
                         detail_path=_clean_path(payload.detail_path) if payload.detail_path else lp,
                         extra_json="{}", sort_order=max_order + 1, is_active=payload.is_active,
                         manual_override=True)
    db.add(c)
    db.commit()
    db.refresh(c)
    return _cfg_out(c)


@router.put("/configs/{config_id}", summary="修改表單設定（路徑／暫停同步）")
def update_config(config_id: int, payload: ConfigUpdate, db: Session = Depends(get_db),
                  _=Depends(require_permission(MANAGE))):
    c = db.query(RagicSheetConfig).get(config_id)
    if not c or c.module not in _valid_modules():
        raise HTTPException(status_code=404, detail="找不到設定")
    if payload.list_path is not None:
        lp = _clean_path(payload.list_path)
        dup = db.query(RagicSheetConfig).filter(RagicSheetConfig.module == c.module, RagicSheetConfig.list_path == lp,
                                                RagicSheetConfig.id != c.id).first()
        if dup:
            raise HTTPException(status_code=409, detail=f"表單 {lp} 已設定在「{dup.display_name}」")
        if lp != c.list_path:
            c.list_path = lp
            c.manual_override = True
    if payload.detail_path is not None:
        dp = _clean_path(payload.detail_path)
        if dp != c.detail_path:
            c.detail_path = dp
            c.manual_override = True
    if payload.is_active is not None:
        c.is_active = payload.is_active
    db.commit()
    db.refresh(c)
    return _cfg_out(c)


@router.post("/configs/{config_id}/reset", summary="還原為程式預設路徑")
def reset_config(config_id: int, db: Session = Depends(get_db), _=Depends(require_permission(MANAGE))):
    from app.services.ragic_sheet_config_service import _SEED_DATA
    c = db.query(RagicSheetConfig).get(config_id)
    if not c or c.module not in _valid_modules():
        raise HTTPException(status_code=404, detail="找不到設定")
    seed = next((r for r in _SEED_DATA if r["module"] == c.module and r["display_name"] == c.display_name), None)
    if not seed:
        raise HTTPException(status_code=409, detail="這筆是手動新增的設定，沒有程式預設值可還原")
    c.list_path, c.detail_path, c.manual_override = seed["list_path"], seed["detail_path"], False
    db.commit()
    db.refresh(c)
    return _cfg_out(c)


@router.get("/purchase-orders", summary="Ragic 採購單清單")
def list_purchase_orders(
    company: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None, max_length=100),
    include_deleted: bool = Query(False),
    limit: int = Query(500, ge=1, le=2000),
    db: Session = Depends(get_db),
    _=Depends(_can_view),
):
    q = db.query(RagicPurchaseOrder)
    if company:
        q = q.filter(RagicPurchaseOrder.company == company)
    if department:
        q = q.filter(RagicPurchaseOrder.department_display == department)
    if not include_deleted:
        q = q.filter(RagicPurchaseOrder.is_ragic_deleted.is_(False))
    if keyword:
        like = f"%{keyword.strip()}%"
        q = q.filter(or_(RagicPurchaseOrder.po_no.ilike(like), RagicPurchaseOrder.purpose.ilike(like),
                         RagicPurchaseOrder.vendor_name.ilike(like), RagicPurchaseOrder.requester.ilike(like)))
    total = q.count()
    orders = (q.order_by(func.coalesce(RagicPurchaseOrder.apply_date, RagicPurchaseOrder.arrival_date).desc().nullslast(),
                         RagicPurchaseOrder.id.desc()).limit(limit).all())
    counts = dict(db.query(RagicPurchaseOrderItem.order_id, func.count(RagicPurchaseOrderItem.id))
                  .filter(RagicPurchaseOrderItem.order_id.in_([o.id for o in orders] or [0]))
                  .group_by(RagicPurchaseOrderItem.order_id).all())
    return {"total": total, "rows": [_po_row(o, counts.get(o.id, 0)) for o in orders]}


@router.get("/purchase-orders/{order_id}", summary="Ragic 採購單明細（含品項）")
def get_purchase_order(order_id: int, db: Session = Depends(get_db), _=Depends(_can_view)):
    o = db.query(RagicPurchaseOrder).get(order_id)
    if not o:
        raise HTTPException(status_code=404, detail="找不到採購單")
    items = (db.query(RagicPurchaseOrderItem).filter(RagicPurchaseOrderItem.order_id == o.id)
             .order_by(RagicPurchaseOrderItem.seq.nullslast(), RagicPurchaseOrderItem.id).all())
    row = _po_row(o, len(items))
    row["items"] = [{
        "id": i.id, "seq": i.seq, "item_code": i.item_code, "product_name": i.product_name,
        "qty": float(i.qty) if i.qty is not None else None, "qty_raw": i.qty_raw, "unit": i.unit,
        "unit_price": float(i.unit_price) if i.unit_price is not None else None,
        "amount": float(i.amount) if i.amount is not None else None,
        "remark": i.remark, "item_dept": i.item_dept,
    } for i in items]
    return row


def _f(v):
    return float(v) if v is not None else None


def _po_row(o: RagicPurchaseOrder, item_count: int) -> dict:
    detail = {
        "採購編號": o.po_no or "",
        "公司別": o.company,
        "部門": o.department_display,
        "請購部門（Ragic）": o.department_raw or "",
        "來源請購單號": o.source_pr_no or "",
        "申請人": o.requester or "",
        "申請日期": o.apply_date.isoformat() if o.apply_date else "",
        "到貨日期": o.arrival_date.isoformat() if o.arrival_date else "",
        "用途說明": o.purpose or "",
        "擬定廠商": o.vendor_name or "",
        "擬定廠商編號": o.vendor_code or "",
        "小計": "" if o.subtotal is None else f"{o.subtotal:,.0f}",
        "營業稅": "" if o.tax is None else f"{o.tax:,.2f}".rstrip("0").rstrip("."),
        "總計": "" if o.total is None else f"{o.total:,.2f}".rstrip("0").rstrip("."),
        "付款條件": o.payment_terms or "",
        "收貨人": o.receiver or "",
        "Ragic 狀態": "Ragic 已刪除" if o.is_ragic_deleted else "正常",
    }
    return {
        "id": o.id, "company": o.company, "department": o.department_display,
        "po_no": o.po_no, "source_pr_no": o.source_pr_no, "requester": o.requester,
        "apply_date": o.apply_date.isoformat() if o.apply_date else None,
        "arrival_date": o.arrival_date.isoformat() if o.arrival_date else None,
        "purpose": o.purpose, "vendor_name": o.vendor_name,
        "subtotal": _f(o.subtotal), "tax": _f(o.tax), "total": _f(o.total),
        "item_count": item_count, "is_ragic_deleted": bool(o.is_ragic_deleted),
        "last_sync_at": _dt(o.sync_at),
        "ragic_id": o.ragic_record_id,
        "ragic_url": f"{RAGIC_BASE}/{o.ragic_sheet_path}/{o.ragic_record_id}",
        "detail": detail,
    }
