"""
退件統計：來源登錄、同步（規格 §3、§5）

- module_table：直接讀取既有同步表（approved_* / nichiyo_* / taichung_*）的 raw_data_json，不呼叫 Ragic。
- ragic_api  ：用用印等沒有同步表的表單，呼叫 Ragic API（RagicAdapter.fetch_all）。
"""
import json
import logging
from datetime import datetime

from app.core.database import SessionLocal
from app.core.time import twnow
from app.models.purchase_request import ApprovedPurchaseRequest
from app.models.claim_request import ApprovedClaimRequest
from app.models.nichiyo_purchase_request import NichiyoPurchaseRequest
from app.models.nichiyo_claim_request import NichiyoClaimRequest
from app.models.taichung_purchase_request import TaichungPurchaseRequest
from app.models.taichung_claim_request import TaichungClaimRequest
from app.models.return_stats import ReturnStatsSource, ReturnStatsRecord, ReturnStatsStep
from app.services.return_stats_parser import as_text, parse_record, rejection_note
from app.services.ragic_adapter import RagicAdapter

logger = logging.getLogger(__name__)

RAGIC_SERVER = "ap12.ragic.com"
RAGIC_ACCOUNT = "soutlet001"

# (公司, 表單類型) → (既有同步表 model, 表名)
MODULE_TABLES = {
    ("樂群", "purchase"): (ApprovedPurchaseRequest, "approved_purchase_requests"),
    ("樂群", "claim"): (ApprovedClaimRequest, "approved_claim_requests"),
    ("日曜", "purchase"): (NichiyoPurchaseRequest, "nichiyo_purchase_requests"),
    ("日曜", "claim"): (NichiyoClaimRequest, "nichiyo_claim_requests"),
    ("台中", "purchase"): (TaichungPurchaseRequest, "taichung_purchase_requests"),
    ("台中", "claim"): (TaichungClaimRequest, "taichung_claim_requests"),
}

# 53 張掃描範圍表（與 docs/SPEC_return_reject_stats.md 附錄 B.1 一致）
SCOPE_SHEETS = [
    ("樂群", "purchase", "執董室", "請購單", "lequn-executive-office/10"),
    ("樂群", "purchase", "營業部", "請購單", "new-tab/10"),
    ("樂群", "purchase", "行銷部", "請購單", "lequn-marketing-department/12"),
    ("樂群", "purchase", "財務部", "請購單", "lequn-finance-department/9"),
    ("樂群", "purchase", "停管部", "請購單", "lequn-traffic-management/6"),
    ("樂群", "purchase", "管理部", "請購單", "community-management-department/22"),
    ("樂群", "purchase", "資訊部", "請購單", "joy-group-it-department/11"),
    ("樂群", "purchase", "工務部", "請購單", "lequn-public-works-department/1"),
    ("樂群", "purchase", "專案部", "請購單", "happy-group-project/2"),
    ("樂群", "claim", "執董室", "請款單", "lequn-executive-office/9"),
    ("樂群", "claim", "營業部", "請款單", "new-tab/8"),
    ("樂群", "claim", "行銷部", "請款單", "lequn-marketing-department/13"),
    ("樂群", "claim", "財務部", "請款單", "lequn-finance-department/6"),
    ("樂群", "claim", "停管部", "請款單", "lequn-traffic-management/5"),
    ("樂群", "claim", "管理部", "請款單", "community-management-department/24"),
    ("樂群", "claim", "資訊部", "請款單", "joy-group-it-department/14"),
    ("樂群", "claim", "工務部", "請款單", "lequn-public-works-department/2"),
    ("樂群", "claim", "專案部", "請款單", "happy-group-project/1"),
    ("日曜", "purchase", "執董室", "請購單", "free-executive-office/9"),
    ("日曜", "purchase", "營業部", "請購單", "free-business-division/21"),
    ("日曜", "purchase", "行銷部", "請購單", "marketing/40"),
    ("日曜", "purchase", "管理部", "請購單", "freed-management-division/19"),
    ("日曜", "purchase", "資訊部", "請購單", "department-of-free-information/23"),
    ("日曜", "purchase", "客服部", "請購單", "free-management-department/10"),
    ("日曜", "purchase", "設計部", "請購單", "free-design-department/2"),
    ("日曜", "claim", "執董室", "請款單", "free-executive-office/8"),
    ("日曜", "claim", "營業部", "請款單", "free-business-division/12"),
    ("日曜", "claim", "行銷部", "請款單", "marketing/32"),
    ("日曜", "claim", "管理部", "請款單", "freed-management-division/8"),
    ("日曜", "claim", "資訊部", "請款單", "department-of-free-information/22"),
    ("日曜", "claim", "客服部", "請款單", "free-management-department/8"),
    ("日曜", "claim", "財務部", "請款單", "free-finance-department/15"),
    ("日曜", "claim", "設計部", "請款單", "free-design-department/1"),
    ("台中", "purchase", "公用表單", "請購單", "taichung-public-form/7"),
    ("台中", "purchase", "客務部", "請購單", "customer-service/9"),
    ("台中", "purchase", "業務部", "請購單", "business/3"),
    ("台中", "purchase", "工程部", "請購單", "construction/3"),
    ("台中", "purchase", "財務部", "請購單", "finance/9"),
    ("台中", "purchase", "資訊部", "請購單", "info/43"),
    ("台中", "purchase", "行政辦公室", "請購單", "hr/5"),
    ("台中", "purchase", "廚房", "請購單", "kitchen/2"),
    ("台中", "purchase", "餐飲", "請購單", "food-drink/2"),
    ("台中", "purchase", "房務部", "請購單", "housekeeping/2"),
    ("台中", "claim", "公用表單", "請款單", "taichung-public-form/6"),
    ("台中", "claim", "客務部", "請款單", "customer-service/14"),
    ("台中", "claim", "業務部", "請款單", "business/5"),
    ("台中", "claim", "工程部", "請款單", "construction/5"),
    ("台中", "claim", "財務部", "請款單", "finance/12"),
    ("台中", "claim", "資訊部", "請款單", "info/50"),
    ("台中", "claim", "行政辦公室", "請款單", "hr/7"),
    ("台中", "claim", "廚房", "請款單", "kitchen/4"),
    ("台中", "claim", "餐飲", "請款單", "food-drink/5"),
    ("台中", "claim", "房務部", "請款單", "housekeeping/4"),
]

# 2026-11-12 裁示新增（應付憑單；維春樂群簽呈待確認）：沒有既有同步表，一律走 Ragic API。
# 原澄、上澄相關表單不納入。wise-mountain/2、public-form-for-group-use/8 另為獨立公司，公司名稱待確認，暫不登錄。
NEW_SHEETS = [
    ("樂群", "payable", "財務部", "應付憑單", "lequn-finance-department/7"),
    ("日曜", "payable", "財務部", "應付憑單", "free-finance-department/6"),
    # 維春樂群簽呈 6 張暫不登錄：探測顯示 6 個路徑回傳完全相同的資料（筆數、狀態分布、欄位皆相同），疑為同一張表的不同頁籤路徑，待確認後再加入
]

# 用印（規格附錄 B.2）：沒有既有同步表，改用 Ragic API
SEAL_SHEETS = [
    ("樂群", "執董室", "用印申請表", "lequn-executive-office/2"),
    ("樂群", "營業部", "用印申請單", "new-tab/9"),
    ("樂群", "行銷部", "用印申請單", "lequn-marketing-department/11"),
    ("樂群", "財務部", "用印申請單", "lequn-finance-department/5"),
    ("樂群", "停管部", "用印申請單", "lequn-traffic-management/7"),
    ("樂群", "管理部", "用印申請單", "community-management-department/27"),
    ("樂群", "管理部", "用印申請單 (統購案)", "community-management-department/53"),
    ("樂群", "資訊部", "用印申請單", "joy-group-it-department/15"),
    ("樂群", "工務部", "用印申請單", "lequn-public-works-department/5"),
    ("樂群", "專案部", "用印申請單", "happy-group-project/4"),
    ("日曜", "執董室", "用印申請單", "free-executive-office/10"),
    ("日曜", "營業部", "用印申請表", "free-business-division/22"),
    ("日曜", "行銷部", "用印申請表", "marketing/38"),
    ("日曜", "管理部", "用印申請表", "freed-management-division/7"),
    ("日曜", "客服部", "用印申請單", "free-management-department/12"),
    ("日曜", "財務部", "用印申請單", "free-finance-department/27"),
    ("日曜", "資訊部", "用印申請單", "department-of-free-information/28"),
]


def source_key(company: str, form_type: str, ragic_path: str) -> str:
    return f"{company}|{form_type}|{ragic_path}"


def seed_sources(db) -> int:
    """冪等植入來源登錄。已存在的 source_key 不覆寫（保留使用者後續修改）。回傳新增筆數。"""
    added = 0
    order = 0
    for company, ftype, dept, fname, path in SCOPE_SHEETS:
        order += 1
        key = source_key(company, ftype, path)
        if db.query(ReturnStatsSource).filter_by(source_key=key).first():
            continue
        model, table = MODULE_TABLES[(company, ftype)]
        db.add(ReturnStatsSource(
            source_key=key, company=company, form_type=ftype, dept_display=dept,
            form_name=fname, ragic_path=path, origin="ragic_api", origin_table=table,
            parser_profile="standard_v1", is_active=True, sort_order=order))
        added += 1
    for company, ftype, dept, fname, path in NEW_SHEETS:
        order += 1
        key = source_key(company, ftype, path)
        if db.query(ReturnStatsSource).filter_by(source_key=key).first():
            continue
        db.add(ReturnStatsSource(
            source_key=key, company=company, form_type=ftype, dept_display=dept,
            form_name=fname, ragic_path=path, origin="ragic_api", origin_table=None,
            parser_profile="standard_v1", is_active=True, sort_order=order))
        added += 1
    for company, dept, fname, path in SEAL_SHEETS:
        order += 1
        key = source_key(company, "seal", path)
        existing = db.query(ReturnStatsSource).filter_by(source_key=key).first()
        if existing:
            # 用印來源的解析設定由程式決定（2026-11-02 改為 seal_v1），修正先前植入的舊值
            if existing.parser_profile != "seal_v1":
                existing.parser_profile = "seal_v1"
            existing.origin = "ragic_api"
            continue
        db.add(ReturnStatsSource(
            source_key=key, company=company, form_type="seal", dept_display=dept,
            form_name=fname, ragic_path=path, origin="ragic_api", origin_table=None,
            parser_profile="seal_v1", is_active=True, sort_order=order))
        added += 1
    db.commit()
    return added


def _module_rows(db, src: ReturnStatsSource) -> dict:
    model, _ = MODULE_TABLES[(src.company, src.form_type)]
    out = {}
    for row in db.query(model).filter(model.ragic_sheet_path == src.ragic_path).all():
        try:
            raw = json.loads(row.raw_data_json or "{}")
        except (TypeError, ValueError):
            raw = {}
        out[str(row.ragic_record_id)] = raw
    return out


async def _attach_approval(src: ReturnStatsSource, out: dict, stats: dict | None = None) -> None:
    """
    module_table 來源（請購／請款／用印）原本只有 REJ 紀錄會補抓簽核步驟，
    其餘紀錄沒有步驟，「流程含某簽核人」會大量漏算（2026-11-03：2026 送件 205 vs Ragic 636）。
    這裡以清單 approval=true 一次補上全部紀錄的簽核步驟。
    """
    adapter = RagicAdapter(sheet_path=src.ragic_path, server_url=RAGIC_SERVER, account=RAGIC_ACCOUNT)
    appr = await adapter.fetch_all(extra_params={"approval": "true"})
    attached = 0
    for rid, rec in out.items():
        a = appr.get(rid) or {}
        if a.get("_approval_steps"):
            rec["_approval_steps"] = a["_approval_steps"]
            rec["_approval_id"] = a.get("_approval_id")
            attached += 1
    if stats is not None:
        stats["approval_attached"] = attached
    logger.info("[ReturnStats] %s 清單 approval 補上 %d 筆步驟", src.source_key, attached)


async def _backfill_rejected(src: ReturnStatsSource, out: dict, stats: dict | None = None) -> None:
    """
    簽核狀態=REJ 但沒有 approval 步驟者，逐筆以單筆 approval=true 補抓（單筆最多試兩次）。
    適用於 Ragic 直接來源與 module_table 來源（2026-11-03：請購／請款來源原本不經過補抓）。
    """
    if stats is not None:
        stats.update({"backfill_tried": 0, "backfill_ok": 0, "backfill_empty": 0,
                      "backfill_failed": 0, "backfill_error": ""})
    missing = [rid for rid, rec in out.items()
               if not rec.get("_approval_steps")
               and as_text(rec.get("簽核狀態")).strip().upper() == "REJ"]
    if not missing:
        return
    adapter = RagicAdapter(sheet_path=src.ragic_path, server_url=RAGIC_SERVER, account=RAGIC_ACCOUNT)
    for rid in missing:
        if stats is not None:
            stats["backfill_tried"] += 1
        last_exc = None
        for _attempt in range(2):
            try:
                one = await adapter.fetch_one(rid, extra_params={"approval": "true"})
                single = (one.get(rid) or {}) if isinstance(one, dict) else {}
                out[rid]["_approval_steps"] = single.get("_approval_steps") or []
                out[rid]["_approval_id"] = single.get("_approval_id")
                last_exc = None
                break
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
        if last_exc is not None:
            logger.warning("[ReturnStats] 補抓 approval 失敗 %s/%s：%r", src.source_key, rid, last_exc)
            if stats is not None:
                stats["backfill_failed"] += 1
                stats["backfill_error"] = stats["backfill_error"] or f"{rid}: {type(last_exc).__name__} {str(last_exc)[:140]}"
        elif stats is not None:
            stats["backfill_ok" if out[rid]["_approval_steps"] else "backfill_empty"] += 1
    logger.info("[ReturnStats] %s 補抓 REJ 簽核步驟 %d 筆", src.source_key, len(missing))


async def _ragic_rows(src: ReturnStatsSource, stats: dict | None = None) -> dict:
    """
    兩次清單請求，合併為一份：
    - 一般清單：欄位顯示名稱（申請人為姓名）。
    - approval=true：只取 _approval_steps／_approval_id。注意此模式下「申請人」會變成登入信箱，不能採用。
    """
    adapter = RagicAdapter(sheet_path=src.ragic_path, server_url=RAGIC_SERVER, account=RAGIC_ACCOUNT)
    plain = await adapter.fetch_all()
    appr = await adapter.fetch_all(extra_params={"approval": "true"})
    out = {}
    for k, v in plain.items():
        rid = str(k)
        rec = dict(v)
        a = appr.get(k) or appr.get(rid) or {}
        rec["_approval_steps"] = a.get("_approval_steps") or []
        rec["_approval_id"] = a.get("_approval_id")
        out[rid] = rec
    await _backfill_rejected(src, out, stats)
    return out


def _upsert(db, src: ReturnStatsSource, rows: dict, now: datetime) -> dict:
    seen = set()
    inserted = updated = 0
    for rid, raw in rows.items():
        seen.add(rid)
        p = parse_record(raw, src.parser_profile)
        rec = db.query(ReturnStatsRecord).filter_by(source_key=src.source_key, ragic_record_id=rid).first()
        if rec is None:
            rec = ReturnStatsRecord(source_key=src.source_key, ragic_record_id=rid)
            db.add(rec)
            inserted += 1
        else:
            updated += 1
            db.query(ReturnStatsStep).filter_by(record_id=rec.id).delete()
        rec.company, rec.form_type = src.company, src.form_type
        rec.dept_display, rec.form_name = src.dept_display, src.form_name
        rec.applicant, rec.apply_date, rec.amount = p["applicant"], p["apply_date"], p["amount"]
        rec.purpose, rec.ragic_status = p["purpose"], p["ragic_status"]
        rec.submitter, rec.next_approver = p["submitter"], p["next_approver"]
        rec.outcome, rec.outcome_reason = p["outcome"], p["outcome_reason"]
        rec.inferred_last_step, rec.last_sign_date = p["inferred_last_step"], p["last_sign_date"]
        rec.is_deleted = False
        rec.synced_at = now
        rec.raw_json = json.dumps(raw, ensure_ascii=False, default=str)
        db.flush()
        for st in p["steps"]:
            db.add(ReturnStatsStep(
                record_id=rec.id, step_no=st["step_no"], role_field=st["role_field"],
                approver_text=st["approver_text"], sign_date=st["sign_date"],
                remark=st["remark"], is_inferred_last=st["is_inferred_last"],
                response_code=st.get("code") or None))
    # 同步時已不存在於來源的紀錄：標記刪除，不實體刪除
    q = (db.query(ReturnStatsRecord)
         .filter(ReturnStatsRecord.source_key == src.source_key,
                 ReturnStatsRecord.is_deleted == False))  # noqa: E712
    if seen:
        q = q.filter(~ReturnStatsRecord.ragic_record_id.in_(seen))
    gone = q.all()
    for rec in gone:
        rec.is_deleted = True
    return {"inserted": inserted, "updated": updated, "deleted_marked": len(gone)}


async def sync_return_stats() -> dict:
    """同步所有啟用中的來源。單一來源失敗不影響其他來源。"""
    db = SessionLocal()
    try:
        seed_sources(db)
        results = []
        sources = (db.query(ReturnStatsSource)
                   .filter(ReturnStatsSource.is_active == True)  # noqa: E712
                   .order_by(ReturnStatsSource.sort_order).all())
        for src in sources:
            try:
                backfill: dict = {}
                if src.origin == "module_table":
                    rows = _module_rows(db, src)
                    await _attach_approval(src, rows, backfill)
                    await _backfill_rejected(src, rows, backfill)
                else:
                    rows = await _ragic_rows(src, backfill)
                stat = _upsert(db, src, rows, twnow())
                db.commit()
                results.append({"source_key": src.source_key, "fetched": len(rows), **stat, **backfill})
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                logger.error("[ReturnStats] %s 失敗：%s", src.source_key, exc)
                results.append({"source_key": src.source_key, "error": str(exc)[:200]})
        return {
            "fetched": sum(r.get("fetched", 0) for r in results),
            "upserted": sum(r.get("inserted", 0) + r.get("updated", 0) for r in results),
            "errors": [r["error"] for r in results if "error" in r],
            "sources": results,
            "finished_at": twnow().isoformat(),
        }
    finally:
        db.close()


def rejection_approver_of(db, record) -> str:
    """退件簽核人：被判定那一步的簽核人姓名（簽名圖不算姓名）。無對應步驟回傳空字串。"""
    if record.outcome not in ("withdrawn", "rejected"):
        return ""
    steps = (db.query(ReturnStatsStep).filter_by(record_id=record.id)
             .order_by(ReturnStatsStep.step_no).all())
    target = None
    for s in steps:
        if s.response_code == "REJ":
            target = s
            break
    if target is None and not any(s.response_code for s in steps):
        for s in steps:  # 舊資料（無 approval 步驟）：以備註關鍵字對應
            if s.remark and any(w in s.remark for w in ("退簽", "退件", "退回", "駁回")):
                target = s
                break
    if target is None and record.outcome == "rejected":
        # 與 rejection_note 相同：無代碼時取最後一個有備註的步驟
        for s in reversed(steps):
            if (s.remark or "").strip():
                target = s
                break
    if target is None or not target.approver_text or target.approver_text == "（簽名圖）":
        return ""
    return target.approver_text


def rejection_note_of(db, record) -> str:
    steps = (db.query(ReturnStatsStep).filter_by(record_id=record.id)
             .order_by(ReturnStatsStep.step_no).all())
    return rejection_note(record.outcome, [{"remark": s.remark, "code": s.response_code} for s in steps])
