"""
開發統計：解析 CHANGELOG（上傳檔案）、匯入、統計。
- 匯入只新增「尚未存在」的條目，不覆寫已編輯過的開始／結束時間。
- 開發時間標註（backfill 產生）：`> 開發時間：YYYY-MM-DD HH:mm（…）` → 結束時間；`> 時間未知…` → 無時間。
"""
import re
from collections import Counter, defaultdict
from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.dev_log import DevLogEntry

VERSION_RE = re.compile(r"^## \[.*?\] - (\d{4}-\d{2}-\d{2})")
SECTION_RE = re.compile(r"^### (.+)$")
TIME_RE = re.compile(r"^>\s*開發時間：(\d{4}-\d{2}-\d{2} \d{2}:\d{2})")
UNKNOWN_RE = re.compile(r"^>\s*時間未知")
ROUTE_RE = re.compile(r"^>\s*路由[：:]\s*`?([^`\s]+)`?")  # 只接受明確的「路由：」格式


def module_of(head: str) -> str:
    t = head.split("—", 1)[-1].strip()
    return re.split(r"[（(：:]", t)[0].strip() or t


def parse_changelog(text: str) -> list:
    text = text.replace("\r\n", "\n")
    entries = []
    cur_date: Optional[date] = None
    cur = None
    seen: Counter = Counter()
    for ln in text.split("\n"):
        m = VERSION_RE.match(ln)
        if m:
            cur_date = date.fromisoformat(m.group(1))
            cur = None
            continue
        m = SECTION_RE.match(ln)
        if m and cur_date:
            head = m.group(1).strip()
            cat = head.split("—", 1)[0].strip().split(" ")[0]
            if cat.lower().startswith("known"):
                cat = "Known"
            title = head.split("—", 1)[-1].strip() if "—" in head else head
            base = f"{cur_date.isoformat()}|{cat}|{title}"
            seen[base] += 1
            cur = {"entry_date": cur_date, "category": cat, "title": title,
                   "module": module_of(head), "end_at": None, "time_note": None, "route": None,
                   "source_key": f"{base}|{seen[base]}"}
            entries.append(cur)
            continue
        if cur is not None:
            t = TIME_RE.match(ln)
            if t and cur["end_at"] is None:
                cur["end_at"] = datetime.strptime(t.group(1), "%Y-%m-%d %H:%M")
                cur["time_note"] = ln.lstrip("> ").strip()
            elif UNKNOWN_RE.match(ln) and cur["time_note"] is None:
                cur["time_note"] = ln.lstrip("> ").strip()
            r = ROUTE_RE.match(ln)
            if r and cur["route"] is None:
                val = r.group(1).strip()
                cur["route"] = None if val in ("無", "未知") else val
    return entries


def import_entries(db: Session, text: str, who: str, now: datetime) -> dict:
    parsed = parse_changelog(text)
    existing = {k for (k,) in db.query(DevLogEntry.source_key).all()}
    added = skipped = 0
    by_key = {e.source_key: e for e in db.query(DevLogEntry).all()} if existing else {}
    for e in parsed:
        if e["source_key"] in existing:
            # 既有條目：只補上空白的路由，不覆寫時間
            row = by_key.get(e["source_key"])
            if row is not None and not row.route and e["route"]:
                row.route = e["route"]
            skipped += 1
            continue
        db.add(DevLogEntry(
            source_key=e["source_key"], entry_date=e["entry_date"], category=e["category"],
            title=e["title"], module=e["module"], route=e["route"], start_at=None, end_at=e["end_at"],
            time_note=e["time_note"], updated_by=who, updated_at=now))
        added += 1
    db.commit()
    return {"parsed": len(parsed), "added": added, "skipped_existing": skipped}


def _hours(e: DevLogEntry) -> Optional[float]:
    if e.start_at and e.end_at and e.end_at >= e.start_at:
        return (e.end_at - e.start_at).total_seconds() / 3600
    return None


def stats(db: Session, module: Optional[str] = None, month: Optional[str] = None) -> dict:
    q = db.query(DevLogEntry)
    if module:
        q = q.filter(DevLogEntry.module == module)
    if month:
        q = q.filter(DevLogEntry.entry_date >= date.fromisoformat(f"{month}-01"))
    rows = q.all()
    total = len(rows)
    with_time = sum(1 for e in rows if e.start_at or e.end_at)
    with_range = sum(1 for e in rows if _hours(e) is not None)
    by_module = defaultdict(lambda: {"entries": 0, "with_time": 0, "hours": 0.0})
    by_month = defaultdict(lambda: {"entries": 0, "with_time": 0})
    for e in rows:
        m = by_module[e.module or "（未分類）"]
        m["entries"] += 1
        m["with_time"] += 1 if (e.start_at or e.end_at) else 0
        m["hours"] += _hours(e) or 0.0
        k = e.entry_date.strftime("%Y-%m")
        by_month[k]["entries"] += 1
        by_month[k]["with_time"] += 1 if (e.start_at or e.end_at) else 0
    return {
        "total": total,
        "with_time": with_time,
        "unknown": total - with_time,
        "with_range": with_range,
        "by_module": sorted(
            [{"module": k, **v, "hours": round(v["hours"], 2)} for k, v in by_module.items()],
            key=lambda x: -x["entries"]),
        "by_month": [{"month": k, **v} for k, v in sorted(by_month.items())],
        "by_category": dict(Counter(e.category for e in rows)),
    }
