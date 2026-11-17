"""
Ragic 簽核掃描同步（soutlet001 全部表單，排除系統表）— 2026-11-12

每日由 sync_tool.py 的「Ragic簽核掃描」排程呼叫 sync_from_ragic()。唯讀（只呼叫 GET）。
  1. 讀取 app/data/ragic_all_forms.txt 的表單清單（排除 ragicsystem/、ragic-setup/）
  2. 每張表取回全部記錄，計算內容雜湊，與上次快照（ragic_scan_fingerprint）比對
  3. 有變動的記錄呼叫 history=true，取最新編輯時間 → ragic_scan_sheet.last_edit_at
  4. 簽核人含「楊國鼎」的記錄寫入 ragic_scan_hit（依表單整批取代）
首次執行只建立基準快照，last_edit_at 保持 NULL。
回傳格式與其他 sync 模組一致：{"fetched", "upserted", "errors"}。
"""
import hashlib
import json
import logging
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.time import twnow
from app.models.ragic_signoff_scan import RagicScanFingerprint, RagicScanHit, RagicScanSheet

logger = logging.getLogger(__name__)

HOST = "ap12.ragic.com"          # soutlet001 所在伺服器（與 settings.RAGIC_SERVER_URL 的 ap16 不同）
ACCOUNT = "soutlet001"
BASE_LINK = f"https://{HOST}/{ACCOUNT}/"
APPROVER = "楊國鼎"
STATUS_WORDS = ["同意", "退簽", "退件", "退回", "駁回"]
EXCLUDE_PREFIX = ("ragicsystem/", "ragic-setup/")
DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "ragic_all_forms.txt")
TZ_TAIPEI = timezone(timedelta(hours=8))


def _read_sheets() -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    with open(DATA_FILE, encoding="utf-8-sig") as f:
        for line in f:
            line = line.rstrip("\r\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            parts = line.split("\t")
            path = parts[0].strip().strip("/")
            if path.startswith(EXCLUDE_PREFIX):
                continue
            typ = parts[1].strip() if len(parts) > 1 else ""
            name = parts[2].strip() if len(parts) > 2 else ""
            out.append((path, typ, name))
    return out


def _get_json(key: str, path: str, params: dict):
    url = f"https://{HOST}/{ACCOUNT}/{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {key}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def _fetch_all(key: str, path: str) -> dict:
    records: dict = {}
    offset, limit = 0, 1000
    while True:
        data = _get_json(key, path, {"api": "", "v": "3", "limit": limit, "offset": offset})
        if not isinstance(data, dict) or not data:
            break
        if [k for k in data if not str(k).isdigit()]:
            raise RuntimeError("API 回傳非紀錄內容：" + json.dumps(data, ensure_ascii=False)[:200])
        records.update(data)
        if len(data) < limit:
            break
        offset += limit
    return records


def _flatten(obj, prefix: str = "") -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out += _flatten(v, f"{prefix}{k}" if not prefix else prefix)
    elif isinstance(obj, list):
        for v in obj:
            out += _flatten(v, prefix)
    elif obj is not None:
        out.append((prefix, str(obj)))
    return out


def _fingerprint(rec: dict) -> str:
    return hashlib.sha256(json.dumps(rec, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _to_taipei_naive(value) -> datetime | None:
    """編輯歷史的時間（毫秒、ISO 或 Y/M/D H:M:S）→ 台北時間（naive，與其他欄位一致）。"""
    if isinstance(value, (int, float)) or (isinstance(value, str) and value.strip().isdigit()):
        n = float(value)
        if n > 1e12:
            n /= 1000.0
        return datetime.fromtimestamp(n, tz=timezone.utc).astimezone(TZ_TAIPEI).replace(tzinfo=None)
    if isinstance(value, str):
        s = value.strip().replace("Z", "+00:00")
        for fmt in ("%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M"):
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                pass
        try:
            d = datetime.fromisoformat(s)
            d = d if d.tzinfo else d.replace(tzinfo=timezone.utc)
            return d.astimezone(TZ_TAIPEI).replace(tzinfo=None)
        except ValueError:
            return None
    return None


def _latest_edit_time(hist) -> datetime | None:
    """遞迴找出回應中 key 含 time/date/時間/日期 的值，取最新者。"""
    best: datetime | None = None

    def walk(o, key: str = "") -> None:
        nonlocal best
        if isinstance(o, dict):
            for k, v in o.items():
                walk(v, str(k))
        elif isinstance(o, list):
            for v in o:
                walk(v, key)
        elif re.search(r"time|date|時間|日期", key, re.I):
            t = _to_taipei_naive(o)
            if t and (best is None or t > best):
                best = t

    walk(hist)
    return best


def sync_from_ragic() -> dict:
    """每日掃描 soutlet001 全部表單（排除系統表）。"""
    key = settings.RAGIC_API_KEY
    if not key:
        return {"fetched": 0, "upserted": 0, "errors": ["RAGIC_API_KEY 未設定"]}

    sheets = _read_sheets()
    fetched = 0
    ok_sheets = 0
    errors: list[str] = []
    db = SessionLocal()
    try:
        for path, typ, name in sheets:
            now = twnow()
            try:
                recs = _fetch_all(key, path)
            except Exception as exc:
                errors.append(f"{path}：{str(exc)[:160]}")
                continue
            fetched += len(recs)

            prev_fp = {r.record_id: r.fp for r in db.query(RagicScanFingerprint)
                       .filter(RagicScanFingerprint.sheet_path == path)}
            prev_sheet = db.get(RagicScanSheet, path)
            baseline = not prev_fp

            hits: list[dict] = []
            changed_ids: list[str] = []
            fp_rows: list[dict] = []
            for rid, rec in recs.items():
                rid = str(rid)
                fp = _fingerprint(rec)
                fp_rows.append({"sheet_path": path, "record_id": rid, "fp": fp, "updated_at": now})
                if not baseline and prev_fp.get(rid) != fp:
                    changed_ids.append(rid)
                fields = _flatten(rec)
                if any(APPROVER in v for _, v in fields):
                    status_vals = sorted({v for _, v in fields
                                          if any(w in v for w in STATUS_WORDS) and len(v) <= 30})
                    hits.append({"sheet_path": path, "sheet_name": name, "record_id": rid,
                                 "link": f"{BASE_LINK}{path}/{rid}",
                                 "status_values": "；".join(status_vals)[:300], "scanned_at": now})

            last_edit = prev_sheet.last_edit_at if prev_sheet else None
            for rid in changed_ids:
                try:
                    hist = _get_json(key, f"{path}/{rid}", {"api": "", "v": "3", "history": "true"})
                    t = _latest_edit_time(hist)
                    if t and (last_edit is None or t > last_edit):
                        last_edit = t
                except Exception as exc:
                    errors.append(f"{path} 記錄 {rid} 歷史：{str(exc)[:120]}")

            # 依表單整批取代快照與命中
            db.query(RagicScanFingerprint).filter(RagicScanFingerprint.sheet_path == path).delete(synchronize_session=False)
            if fp_rows:
                db.execute(pg_insert(RagicScanFingerprint).values(fp_rows))
            db.query(RagicScanHit).filter(RagicScanHit.sheet_path == path).delete(synchronize_session=False)
            if hits:
                db.execute(pg_insert(RagicScanHit).values([{**h, "sheet_name": name} for h in hits]))

            sheet_row = {"sheet_path": path, "sheet_name": name, "sheet_type": typ,
                         "record_count": len(recs), "changed_count": len(changed_ids),
                         "last_edit_at": last_edit, "scanned_at": now}
            stmt = pg_insert(RagicScanSheet).values(sheet_row)
            stmt = stmt.on_conflict_do_update(
                index_elements=["sheet_path"],
                set_={k: stmt.excluded[k] for k in sheet_row if k != "sheet_path"},
            )
            db.execute(stmt)
            db.commit()  # 每張表獨立提交，失敗不影響其他表
            ok_sheets += 1
    except Exception as exc:
        db.rollback()
        logger.exception("Ragic 簽核掃描失敗")
        errors.append(f"整體錯誤：{str(exc)[:200]}")
    finally:
        db.close()

    logger.info("Ragic 簽核掃描：%d 張表成功、%d 筆記錄、%d 項錯誤", ok_sheets, fetched, len(errors))
    return {"fetched": fetched, "upserted": ok_sheets, "errors": errors}
