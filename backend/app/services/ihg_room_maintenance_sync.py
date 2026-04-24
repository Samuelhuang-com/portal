"""
IHG 客房保養同步服務：Ragic → SQLite

資料來源：
  Sheet 4：https://ap12.ragic.com/soutlet001/periodic-maintenance/4
  Detail  ：同 Sheet 4 每筆記錄 fetch_one() 取得子表格（若有）

【欄位 mapping 策略】
  由於無法在 sandbox 直接存取 Ragic，本服務：
  1. 先嘗試常見中文欄位 key（依 IHG 保養表慣例設計）
  2. 若欄位不存在則 fallback 為空字串
  3. 完整原始 JSON 存入 raw_json，供日後補正

【同步時避免重複寫入】
  以 ragic_id 為 Primary Key，upsert 策略：
  - 存在 → 更新所有欄位（raw_json 亦更新）
  - 不存在 → INSERT

【常見 Ragic 中文欄位 key（IHG 客房保養）】
  主表：
    房號 / 客房號 → room_no
    保養日期 / 日期 → maint_date
    保養月份 / 月份 → maint_month
    年度 / 年份 → maint_year
    保養人員 / 執行人員 → assignee_name
    複核人員 → checker_name
    完成日期 → completion_date
    保養類型 / 類型 → maint_type
    備註 → notes
    完成狀態 / 狀態 → status (原始)

  子表格：
    項次 → seq_no
    保養項目 / 項目 → task_name
    執行結果 / 結果 → result
    備註 → notes
"""
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.time import twnow
from app.models.ihg_room_maintenance import IHGRoomMaintenanceMaster, IHGRoomMaintenanceDetail
from app.services.ragic_adapter import RagicAdapter

logger = logging.getLogger(__name__)

# ── Ragic 連線設定 ────────────────────────────────────────────────────────────
IHG_SERVER_URL  = getattr(settings, "RAGIC_IHG_RM_SERVER_URL",  "ap12.ragic.com")
IHG_ACCOUNT     = getattr(settings, "RAGIC_IHG_RM_ACCOUNT",     "soutlet001")
IHG_SHEET_PATH  = getattr(settings, "RAGIC_IHG_RM_SHEET_PATH",  "periodic-maintenance/4")

# ── 常見欄位 key 候選清單（按優先序，取第一個有值的）───────────────────────
FIELD_CANDIDATES = {
    "room_no":       ["房號", "客房號", "房間號", "客房"],
    "maint_date":    ["保養日期", "日期", "執行日期", "完成日期_date", "作業日期"],
    "maint_year":    ["年度", "年份", "保養年度"],
    "maint_month":   ["月份", "保養月份", "執行月份"],
    "assignee_name": ["保養人員", "執行人員", "作業人員", "人員"],
    "checker_name":  ["複核人員", "確認人員", "核簽人員", "督導"],
    "completion_date": ["完成日期", "結案日期", "完工日期"],
    "maint_type":    ["保養類型", "類型", "保養種類", "種類"],
    "notes":         ["備註", "說明", "補充說明"],
    "status_raw":    ["完成狀態", "狀態", "保養狀態", "執行狀態"],
}

# 子表格欄位候選
DETAIL_FIELD_CANDIDATES = {
    "seq_no":    ["項次", "序號"],
    "task_name": ["保養項目", "項目", "作業項目", "檢查項目"],
    "result":    ["執行結果", "結果", "檢查結果", "判定"],
    "notes":     ["備註", "說明"],
}


# ── 輔助函式 ──────────────────────────────────────────────────────────────────

def _stringify(value: Any) -> str:
    """將各種 Ragic 值型別轉成字串"""
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(_stringify(x) for x in value)
    if isinstance(value, dict):
        return _stringify(value.get("value") or value.get("label") or "")
    return str(value).strip()


def _to_int(val: Any) -> int:
    try:
        return int(float(str(val))) if val not in (None, "", "None") else 0
    except (ValueError, TypeError):
        return 0


def _pick(raw: dict, candidates: list[str], fallback: str = "") -> str:
    """從候選 key 清單中取第一個有值的欄位"""
    for key in candidates:
        if key in raw:
            val = _stringify(raw[key])
            if val:
                return val
    return fallback


def _derive_floor(room_no: str) -> str:
    """
    由房號推導樓層：
    "501" → "5F", "1001" → "10F", "B101" → "B1F"
    """
    if not room_no:
        return ""
    rn = room_no.strip()
    # 地下室格式 B101 → B1F
    m = re.match(r"^B(\d+)", rn, re.IGNORECASE)
    if m:
        return f"B{m.group(1)[0]}F"
    # 一般格式：取前 N-2 位（房間號通常末兩位是房間序號）
    digits = re.sub(r"[^0-9]", "", rn)
    if len(digits) >= 3:
        floor_digit = digits[:-2] if len(digits) > 2 else digits[0]
        try:
            return f"{int(floor_digit)}F"
        except ValueError:
            pass
    return rn


def _derive_year_month(raw: dict, maint_date: str) -> tuple[str, str]:
    """
    從 raw dict 或 maint_date 推導年份與月份。
    優先使用獨立欄位，fallback 由日期字串解析。
    """
    year  = _pick(raw, FIELD_CANDIDATES["maint_year"])
    month = _pick(raw, FIELD_CANDIDATES["maint_month"])

    if not year and maint_date:
        parts = re.split(r"[/\-.]", maint_date)
        if len(parts) >= 1 and len(parts[0]) == 4:
            year = parts[0]
        if len(parts) >= 2:
            month = parts[1].zfill(2)

    return year, month


def _parse_status(raw_status: str, is_completed: bool) -> str:
    """
    將 Ragic 原始狀態文字轉換為 Portal 標準狀態值。
    pending / completed / overdue / scheduled
    """
    if is_completed:
        return "completed"
    s = (raw_status or "").strip()
    mapping = {
        "已完成": "completed",
        "完成":   "completed",
        "完成✓":  "completed",
        "逾期":   "overdue",
        "超期":   "overdue",
        "排定":   "scheduled",
        "已排定": "scheduled",
        "待排程": "pending",
        "未排定": "pending",
        "未完成": "pending",
    }
    return mapping.get(s, "pending")


def _extract_subtable_rows(full_record: dict, batch_id_str: str) -> dict[str, dict]:
    """
    從完整 Ragic 記錄中提取子表格列。
    支援方式 A（數字 key）、B（命名 dict）、C（命名 list）、D（_subtable_ key）。
    回傳 {row_key: row_dict}。
    """
    sub_rows: dict[str, dict] = {}

    # 方式 A：頂層數字 key
    direct_numeric = {
        k: v for k, v in full_record.items()
        if k.lstrip("-").isdigit() and isinstance(v, dict)
    }
    if direct_numeric:
        if len(direct_numeric) == 1:
            container_key = next(iter(direct_numeric))
            container_val = direct_numeric[container_key]
            inner_numeric = {
                k: v for k, v in container_val.items()
                if k.lstrip("-").isdigit() and isinstance(v, dict)
            }
            sub_rows = inner_numeric if inner_numeric else direct_numeric
        else:
            sub_rows = direct_numeric

    # 方式 B：命名 key → dict（key 為數字）
    if not sub_rows:
        for k, v in full_record.items():
            if k.startswith("_"):
                continue
            if isinstance(v, dict) and v:
                first_sub = next(iter(v.keys()), "")
                if first_sub.lstrip("-").isdigit():
                    sub_rows = {rk: rv for rk, rv in v.items() if isinstance(rv, dict)}
                    break

    # 方式 C：命名 key → list of dicts
    if not sub_rows:
        for k, v in full_record.items():
            if k.startswith("_"):
                continue
            if isinstance(v, list) and v and isinstance(v[0], dict):
                sub_rows = {str(i + 1): row for i, row in enumerate(v)}
                break

    # 方式 D：_subtable_{id} key
    if not sub_rows:
        for k, v in full_record.items():
            if not k.startswith("_subtable_"):
                continue
            if not isinstance(v, dict) or not v:
                continue
            inner_numeric = {
                rk: rv for rk, rv in v.items()
                if rk.lstrip("-").isdigit() and isinstance(rv, dict)
            }
            if inner_numeric:
                sub_rows = inner_numeric
                break

    if sub_rows:
        logger.info(f"[IHGSync] 記錄 {batch_id_str} → 子表格 {len(sub_rows)} 列")
    else:
        logger.debug(f"[IHGSync] 記錄 {batch_id_str} → 無子表格")

    return sub_rows


def _master_to_model(ragic_id: str, raw: dict) -> IHGRoomMaintenanceMaster:
    """Ragic 原始 dict → ORM 主表物件"""
    rec = IHGRoomMaintenanceMaster(ragic_id=ragic_id)

    rec.room_no         = _pick(raw, FIELD_CANDIDATES["room_no"])
    rec.floor           = _derive_floor(rec.room_no)
    rec.maint_date      = _pick(raw, FIELD_CANDIDATES["maint_date"])
    rec.assignee_name   = _pick(raw, FIELD_CANDIDATES["assignee_name"])
    rec.checker_name    = _pick(raw, FIELD_CANDIDATES["checker_name"])
    rec.completion_date = _pick(raw, FIELD_CANDIDATES["completion_date"])
    rec.maint_type      = _pick(raw, FIELD_CANDIDATES["maint_type"])
    rec.notes           = _pick(raw, FIELD_CANDIDATES["notes"])

    # 年度、月份
    year, month = _derive_year_month(raw, rec.maint_date)
    rec.maint_year  = year
    rec.maint_month = month

    # 狀態
    status_raw    = _pick(raw, FIELD_CANDIDATES["status_raw"])
    # 完成判斷：completion_date 有值 OR status_raw 為「已完成」
    rec.is_completed = bool(rec.completion_date) or status_raw in ("已完成", "完成", "完成✓")
    rec.status    = _parse_status(status_raw, rec.is_completed)

    # 時間戳
    ts = raw.get("_dataTimestamp")
    if ts:
        try:
            dt_str = datetime.fromtimestamp(int(ts) / 1000, tz=timezone.utc).strftime(
                "%Y/%m/%d %H:%M:%S"
            )
            rec.ragic_created_at = dt_str
            rec.ragic_updated_at = dt_str
        except Exception:
            pass

    # 保存完整原始 JSON（排除帶 _ 的 Ragic 內部 key 以節省空間）
    public_raw = {k: v for k, v in raw.items() if not k.startswith("_")}
    rec.raw_json = json.dumps(public_raw, ensure_ascii=False, default=str)
    rec.synced_at = twnow()
    return rec


def _detail_to_model(
    ragic_id: str,
    row_raw: dict,
    master_ragic_id: str,
) -> IHGRoomMaintenanceDetail:
    """子表格列 → ORM 明細物件"""
    rec = IHGRoomMaintenanceDetail(ragic_id=ragic_id)
    rec.master_ragic_id = master_ragic_id
    rec.seq_no    = _to_int(_pick(row_raw, DETAIL_FIELD_CANDIDATES["seq_no"], "0"))
    rec.task_name = _pick(row_raw, DETAIL_FIELD_CANDIDATES["task_name"])
    rec.result    = _pick(row_raw, DETAIL_FIELD_CANDIDATES["result"])
    rec.notes     = _pick(row_raw, DETAIL_FIELD_CANDIDATES["notes"])
    rec.is_ok     = rec.result.upper() in ("OK", "V", "✓", "正常", "是")
    rec.raw_json  = json.dumps(row_raw, ensure_ascii=False, default=str)
    rec.synced_at = twnow()
    return rec


# ── 同步主程式 ────────────────────────────────────────────────────────────────

async def sync_master_from_ragic() -> dict:
    """
    同步 Ragic Sheet 4 主表 → ihg_rm_master
    策略：
      1. fetch_all() 取得所有主表記錄（分頁，每次 200 筆）
      2. 逐筆 upsert（以 ragic_id 為 PK）
    """
    adapter = RagicAdapter(
        sheet_path=IHG_SHEET_PATH,
        server_url=IHG_SERVER_URL,
        account=IHG_ACCOUNT,
    )
    logger.info("[IHGSync][Master] 開始同步主表...")

    try:
        raw_data = await adapter.fetch_all()
    except Exception as exc:
        logger.error(f"[IHGSync][Master] 拉取失敗：{exc}")
        return {"fetched": 0, "upserted": 0, "errors": [str(exc)]}

    fetched  = len(raw_data)
    upserted = 0
    errors: list[str] = []
    now = twnow()

    db = SessionLocal()
    try:
        for ragic_id, raw in raw_data.items():
            try:
                new_rec = _master_to_model(str(ragic_id), raw)
                existing = db.get(IHGRoomMaintenanceMaster, str(ragic_id))
                if existing:
                    existing.room_no         = new_rec.room_no
                    existing.floor           = new_rec.floor
                    existing.maint_year      = new_rec.maint_year
                    existing.maint_month     = new_rec.maint_month
                    existing.maint_date      = new_rec.maint_date
                    existing.status          = new_rec.status
                    existing.is_completed    = new_rec.is_completed
                    existing.assignee_name   = new_rec.assignee_name
                    existing.checker_name    = new_rec.checker_name
                    existing.completion_date = new_rec.completion_date
                    existing.maint_type      = new_rec.maint_type
                    existing.notes           = new_rec.notes
                    existing.raw_json        = new_rec.raw_json
                    existing.ragic_created_at = new_rec.ragic_created_at
                    existing.ragic_updated_at = new_rec.ragic_updated_at
                    existing.synced_at       = now
                else:
                    db.add(new_rec)
                upserted += 1
            except Exception as exc:
                errors.append(f"master ragic_id={ragic_id}: {exc}")
                logger.warning(f"[IHGSync][Master] 記錄 {ragic_id} 失敗：{exc}")

        db.commit()
        logger.info(
            f"[IHGSync][Master] 完成：fetched={fetched}, upserted={upserted}, errors={len(errors)}"
        )
    except Exception as exc:
        db.rollback()
        errors.append(f"DB commit error: {exc}")
        logger.error(f"[IHGSync][Master] DB 寫入失敗：{exc}")
    finally:
        db.close()

    return {"fetched": fetched, "upserted": upserted, "errors": errors}


async def sync_details_from_ragic() -> dict:
    """
    同步 Ragic Sheet 4 子表格 → ihg_rm_detail
    策略：
      1. fetch_all() 取得主表記錄 ID 清單
      2. 對每筆記錄呼叫 fetch_one() 取完整資料（含子表格）
      3. 解析子表格列，upsert 到 ihg_rm_detail
    """
    adapter = RagicAdapter(
        sheet_path=IHG_SHEET_PATH,
        server_url=IHG_SERVER_URL,
        account=IHG_ACCOUNT,
    )
    logger.info("[IHGSync][Detail] 開始同步子表格...")

    try:
        raw_data = await adapter.fetch_all()
    except Exception as exc:
        logger.error(f"[IHGSync][Detail] 拉取失敗：{exc}")
        return {"fetched": 0, "upserted": 0, "errors": [str(exc)]}

    if not raw_data:
        logger.warning("[IHGSync][Detail] Ragic 回傳空資料")
        return {"fetched": 0, "upserted": 0, "errors": []}

    master_ids = list(raw_data.keys())
    total_fetched  = 0
    total_upserted = 0
    errors: list[str] = []
    now = twnow()

    db = SessionLocal()
    try:
        for master_ragic_id in master_ids:
            master_id_str = str(master_ragic_id)
            try:
                full_record = await adapter.fetch_one(master_id_str)
            except Exception as exc:
                errors.append(f"fetch_one({master_id_str}): {exc}")
                logger.warning(f"[IHGSync][Detail] fetch_one({master_id_str}) 失敗：{exc}")
                continue

            # Ragic fetch_one 回傳 {"recordId": {fields...}}，unwrap
            if master_id_str in full_record and len(full_record) == 1:
                full_record = full_record[master_id_str]

            sub_rows = _extract_subtable_rows(full_record, master_id_str)
            if not sub_rows:
                continue  # 此記錄無子表格，跳過

            total_fetched += len(sub_rows)

            for row_key, row_raw in sub_rows.items():
                detail_id = f"{master_id_str}_{row_key}"
                try:
                    new_rec = _detail_to_model(detail_id, row_raw, master_id_str)
                    existing = db.get(IHGRoomMaintenanceDetail, detail_id)
                    if existing:
                        existing.master_ragic_id = master_id_str
                        existing.seq_no    = new_rec.seq_no
                        existing.task_name = new_rec.task_name
                        existing.result    = new_rec.result
                        existing.notes     = new_rec.notes
                        existing.is_ok     = new_rec.is_ok
                        existing.raw_json  = new_rec.raw_json
                        existing.synced_at = now
                    else:
                        db.add(new_rec)
                    total_upserted += 1
                except Exception as exc:
                    errors.append(f"detail {detail_id}: {exc}")
                    logger.warning(f"[IHGSync][Detail] 明細 {detail_id} 失敗：{exc}")

        db.commit()
        logger.info(
            f"[IHGSync][Detail] 完成：masters={len(master_ids)}, "
            f"details_fetched={total_fetched}, upserted={total_upserted}, errors={len(errors)}"
        )
    except Exception as exc:
        db.rollback()
        errors.append(f"DB commit error: {exc}")
        logger.error(f"[IHGSync][Detail] DB 寫入失敗：{exc}")
    finally:
        db.close()

    return {"fetched": total_fetched, "upserted": total_upserted, "errors": errors}


async def sync_from_ragic() -> dict:
    """完整同步：先同步主表，再同步子表格"""
    master_result = await sync_master_from_ragic()
    detail_result = await sync_details_from_ragic()
    return {
        "master": master_result,
        "detail": detail_result,
    }
