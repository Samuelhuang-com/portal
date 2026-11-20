"""
開發統計：解析 CHANGELOG（上傳檔案）、匯入、統計。
- 匯入只新增「尚未存在」的條目，不覆寫已編輯過的開始／結束時間。
- 開發時間標註（backfill 產生）：`> 開發時間：YYYY-MM-DD HH:mm（…）` → 結束時間；`> 時間未知…` → 無時間。
"""
import csv
import io
import re
import subprocess
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.models.dev_log import DevLogEntry
from app.models.requirement import Requirement

# repo 根目錄：backend/app/services/dev_log_service.py → parents[3]
REPO_ROOT = Path(__file__).resolve().parents[3]
TAIPEI = timezone(timedelta(hours=8))  # 台北無日光節約，固定 +08:00
SUBJECT_CATEGORY = {"fix": "Fixed", "feat": "Added"}
GIT_TIMEOUT_SEC = 120  # OneDrive 掛載的 repo 讀取較慢（約 50 秒）；本機磁碟遠快於此

VERSION_RE = re.compile(r"^## \[.*?\] - (\d{4}-\d{2}-\d{2})")
SECTION_RE = re.compile(r"^### (.+)$")
TIME_RE = re.compile(r"^>\s*開發時間：(\d{4}-\d{2}-\d{2} \d{2}:\d{2})")
UNKNOWN_RE = re.compile(r"^>\s*時間未知")
ROUTE_RE = re.compile(r"^>\s*路由[：:]\s*`?([^`\s]+)`?")  # 只接受明確的「路由：」格式
REQ_LINE_RE = re.compile(r"^>\s*需求[：:]\s*`?(REQ-\d+)`?")  # CHANGELOG 條目綁定需求（2026-11-20）
REQ_TAG_RE = re.compile(r"\bREQ-(\d+)\b")  # commit 訊息標記需求，例如 feat: xxx REQ-0012


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
                   "module": module_of(head), "end_at": None, "time_note": None, "route": None, "req_no": None,
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
            q = REQ_LINE_RE.match(ln)
            if q and cur["req_no"] is None:
                cur["req_no"] = q.group(1)
    return entries


def _req_id(text: Optional[str], valid: set) -> Optional[int]:
    """由 "REQ-0012" 等文字取出需求 id；必須存在於需求表才回傳。"""
    m = REQ_TAG_RE.search(text or "")
    if not m:
        return None
    rid = int(m.group(1))
    return rid if rid in valid else None


def import_entries(db: Session, text: str, who: str, now: datetime) -> dict:
    parsed = parse_changelog(text)
    existing = {k for (k,) in db.query(DevLogEntry.source_key).all()}
    added = skipped = 0
    by_key = {e.source_key: e for e in db.query(DevLogEntry).all()} if existing else {}
    valid = _valid_requirement_ids(db)
    linked = 0
    for e in parsed:
        rid = _req_id(e["req_no"], valid)
        if e["source_key"] in existing:
            # 既有條目：只補上空白的路由與需求綁定，不覆寫時間或人工綁定
            row = by_key.get(e["source_key"])
            if row is not None and not row.route and e["route"]:
                row.route = e["route"]
            if row is not None and row.requirement_id is None and rid:
                row.requirement_id = rid
                linked += 1
            skipped += 1
            continue
        db.add(DevLogEntry(
            source_key=e["source_key"], entry_date=e["entry_date"], category=e["category"],
            title=e["title"], module=e["module"], route=e["route"], start_at=None, end_at=e["end_at"],
            time_note=e["time_note"], updated_by=who, updated_at=now, requirement_id=rid))
        added += 1
        linked += 1 if rid else 0
    db.commit()
    return {"parsed": len(parsed), "added": added, "skipped_existing": skipped, "linked_requirement": linked}


def _git_module(files: list) -> str:
    """由 commit 變更的檔案推得模組名：前端頁面資料夾優先，其次後端 router 檔名。"""
    for f in files:
        parts = f.split("/")
        if len(parts) > 3 and parts[:3] == ["frontend", "src", "pages"]:
            return parts[3]
    for f in files:
        if f.startswith("backend/app/routers/") and f.endswith(".py"):
            return Path(f).stem
    return "（未分類）"


def read_git_commits(repo: Path) -> list:
    """讀取 git log（不含 merge），回傳 [{hash, at(台北時間), subject, files}]，最舊在前。"""
    fmt = "%x1e%H%x1f%ci%x1f%s"
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "log", "--no-merges", "--name-only", "--reverse", f"--pretty=format:{fmt}"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=GIT_TIMEOUT_SEC)
    except (OSError, subprocess.SubprocessError) as ex:
        raise RuntimeError(f"無法執行 git（伺服器需安裝 git 且 repo 需含 .git）：{ex}")
    if out.returncode != 0:
        raise RuntimeError(f"git log 失敗：{out.stderr.strip()[:300]}")
    commits = []
    for chunk in out.stdout.split("\x1e"):
        lines = [ln for ln in chunk.split("\n") if ln.strip()]
        if not lines:
            continue
        h, ci, subject = (lines[0].split("\x1f") + ["", ""])[:3]
        if not h:
            continue
        at = datetime.strptime(ci, "%Y-%m-%d %H:%M:%S %z").astimezone(TAIPEI).replace(tzinfo=None)
        commits.append({"hash": h, "at": at, "subject": subject, "files": [x.strip() for x in lines[1:]]})
    return commits


def sync_from_git(db: Session, repo: Path, now: datetime) -> dict:
    """每個 commit 建一筆條目（結束時間＝commit 時間）。只新增，不覆寫既有條目。"""
    commits = read_git_commits(repo)
    existing = {k for (k,) in db.query(DevLogEntry.source_key).all()}
    by_key = {e.source_key: e for e in db.query(DevLogEntry).all()} if existing else {}
    valid = _valid_requirement_ids(db)
    added = skipped = linked = 0
    for c in commits:
        key = f"git|{c['hash']}"
        rid = _req_id(c["subject"], valid)
        if key in existing:
            row = by_key.get(key)
            if row is not None and row.requirement_id is None and rid:
                row.requirement_id = rid
                linked += 1
            skipped += 1
            continue
        prefix = c["subject"].split(":", 1)[0].strip().lower() if ":" in c["subject"] else ""
        db.add(DevLogEntry(
            source_key=key, entry_date=c["at"].date(), category=SUBJECT_CATEGORY.get(prefix, "Changed"),
            title=c["subject"], module=_git_module(c["files"]), route=None, start_at=None, end_at=c["at"],
            time_note=f"依 git commit {c['hash'][:7]}", updated_by="git-sync", updated_at=now, requirement_id=rid))
        added += 1
        linked += 1 if rid else 0
    db.commit()
    return {"commits": len(commits), "added": added, "skipped_existing": skipped, "linked_requirement": linked}


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


# ── 需求管理（2026-11-20）────────────────────────────────────────────
REQ_STATUSES = ("待評估", "進行中", "已完成", "退回")
REQ_PRIORITIES = ("高", "中", "低")
# Jira 狀態 → Portal 四個狀態（比對不分大小寫；無法對應者預設「待評估」並列入回傳的 unmapped_statuses）
JIRA_STATUS_MAP = {
    "to do": "待評估", "todo": "待評估", "待辦事項": "待評估", "open": "待評估", "backlog": "待評估", "new": "待評估",
    "selected for development": "待評估", "reopened": "待評估", "待辦": "待評估", "待處理": "待評估",
    "in progress": "進行中", "in review": "進行中", "review": "進行中", "testing": "進行中",
    "qa": "進行中", "處理中": "進行中", "進行中": "進行中",
    "done": "已完成", "closed": "已完成", "resolved": "已完成", "complete": "已完成",
    "completed": "已完成", "完成": "已完成", "已解決": "已完成", "已完成": "已完成", "已關閉": "已完成",
    "rejected": "退回", "won't do": "退回", "wont do": "退回", "cancelled": "退回",
    "canceled": "退回", "退回": "退回", "不做": "退回",
}
# Jira 優先級 → 高／中／低
JIRA_PRIORITY_MAP = {
    "highest": "高", "blocker": "高", "critical": "高", "high": "高", "最高": "高", "高": "高",
    "medium": "中", "normal": "中", "中": "中",
    "low": "低", "lowest": "低", "minor": "低", "trivial": "低", "低": "低",
}
JIRA_COLUMNS = {
    "key": ("issue key", "issuekey", "議題索引鍵", "鍵值", "問題鍵值"),
    "summary": ("summary", "摘要"),
    "status": ("status", "狀態"),
    "priority": ("priority", "優先級", "優先順序"),
    "reporter": ("reporter", "報告人", "回報者"),
    "description": ("description", "描述"),
    "module": ("component/s", "component", "components", "元件/軟體模組", "元件"),
    "created": ("created", "建立時間", "已建立"),
}


def _valid_requirement_ids(db: Session) -> set:
    return {rid for (rid,) in db.query(Requirement.id).all()}


def req_no(rid: int) -> str:
    return f"REQ-{rid:04d}"


def apply_requirement_fields(r: Requirement, data: dict, who: str, now: datetime) -> None:
    """套用欄位；狀態切換到「已完成」記錄完成時間，離開「已完成」清空。"""
    for k in ("title", "description", "requester", "module", "status", "priority"):
        if k in data:
            setattr(r, k, data[k])
    if "status" in data:
        if data["status"] == "已完成" and r.completed_at is None:
            r.completed_at = now
        elif data["status"] != "已完成":
            r.completed_at = None
    r.updated_by = who
    r.updated_at = now


def requirement_summary(db: Session) -> dict:
    reqs = db.query(Requirement).order_by(Requirement.id.desc()).all()
    per: dict = defaultdict(lambda: {"change_count": 0, "hours": 0.0, "modules": set(), "last": None})
    matrix: Counter = Counter()
    for e in db.query(DevLogEntry).filter(DevLogEntry.requirement_id.isnot(None)).all():
        p = per[e.requirement_id]
        mod = e.module or "（未分類）"
        p["change_count"] += 1
        p["hours"] += _hours(e) or 0.0
        p["modules"].add(mod)
        matrix[(e.requirement_id, mod)] += 1
        t = e.end_at or e.start_at or datetime.combine(e.entry_date, datetime.min.time())
        if p["last"] is None or t > p["last"]:
            p["last"] = t
    items = []
    for r in reqs:
        p = per.get(r.id) or {"change_count": 0, "hours": 0.0, "modules": set(), "last": None}
        items.append({
            "id": r.id, "req_no": req_no(r.id), "title": r.title, "description": r.description or "",
            "requester": r.requester or "", "module": r.module or "", "status": r.status,
            "priority": r.priority, "jira_key": r.jira_key or "",
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "change_count": p["change_count"], "hours": round(p["hours"], 2),
            "modules": sorted(p["modules"]),
            "last_change_at": p["last"].strftime("%Y-%m-%d %H:%M") if p["last"] else None,
        })
    modules = sorted({m for (_, m) in matrix})
    return {
        "items": items,
        "modules": modules,
        "matrix": [{"requirement_id": rid, "req_no": req_no(rid), "module": m, "count": n}
                   for (rid, m), n in sorted(matrix.items())],
        "unbound_entries": db.query(DevLogEntry).filter(DevLogEntry.requirement_id.is_(None)).count(),
        "status_counts": dict(Counter(r.status for r in reqs)),
    }


def _csv_text(raw: bytes) -> str:
    for enc in ("utf-8-sig", "cp950"):  # Jira 匯出為 UTF-8；Excel 另存的繁中 CSV 為 Big5（cp950）
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("CSV 編碼無法辨識（需為 UTF-8 或 Big5）")


def import_jira_csv(db: Session, raw: bytes, who: str, now: datetime) -> dict:
    """匯入 Jira 匯出的 CSV。只新增（以 jira_key 去重），不覆寫既有需求。"""
    reader = csv.DictReader(io.StringIO(_csv_text(raw)))
    headers = {(h or "").strip().lower(): h for h in (reader.fieldnames or [])}

    def find(row: dict, field: str) -> str:
        for alias in JIRA_COLUMNS[field]:
            h = headers.get(alias)
            if h is not None:
                return (row.get(h) or "").strip()
        return ""

    if not any(a in headers for a in JIRA_COLUMNS["key"]) or not any(a in headers for a in JIRA_COLUMNS["summary"]):
        raise ValueError("找不到 Issue key／Summary 欄位，請確認是 Jira 匯出的 CSV")
    existing = {k for (k,) in db.query(Requirement.jira_key).filter(Requirement.jira_key.isnot(None)).all()}
    rows = added = skipped_existing = skipped_invalid = 0
    unmapped: set = set()
    for row in reader:
        rows += 1
        key, summary = find(row, "key"), find(row, "summary")
        if not key or not summary:
            skipped_invalid += 1
            continue
        if key in existing:
            skipped_existing += 1
            continue
        raw_status = find(row, "status")
        status = JIRA_STATUS_MAP.get(raw_status.lower())
        if status is None:
            status = "待評估"
            if raw_status:
                unmapped.add(raw_status)
        priority = JIRA_PRIORITY_MAP.get(find(row, "priority").lower(), "中")
        module = find(row, "module").split(",")[0].strip()
        created_text = find(row, "created")
        desc = find(row, "description")
        if created_text:
            desc = f"（Jira 建立時間：{created_text}）\n{desc}" if desc else f"（Jira 建立時間：{created_text}）"
        r = Requirement(
            title=summary[:300], description=desc or None, requester=find(row, "reporter") or None,
            module=module[:120], status=status, priority=priority, jira_key=key[:60],
            created_by=who, created_at=now, updated_by=who, updated_at=now,
            completed_at=now if status == "已完成" else None)
        db.add(r)
        existing.add(key)
        added += 1
    db.commit()
    return {"rows": rows, "added": added, "skipped_existing": skipped_existing,
            "skipped_invalid": skipped_invalid, "unmapped_statuses": sorted(unmapped)}
