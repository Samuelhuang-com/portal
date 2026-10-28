#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Project Hub 開發規範檢查（提醒模式）

依 docs/PROJECT_HUB_CONVENTIONS.md 檢查文件格式。只提醒、不阻擋、不修改文件。

用法：
  python scripts/check_hub_conventions.py                列出全部提醒（基準線內的舊問題會標註）
  python scripts/check_hub_conventions.py FILE ...        只列出指定檔案的提醒
  python scripts/check_hub_conventions.py --save-baseline 把目前全部提醒存為基準線（舊問題之後不再於 hook 提醒）
  python scripts/check_hub_conventions.py --hook          Claude Code PostToolUse hook（從 stdin 讀事件）

Hook 只提醒「不在基準線內」的新問題，既有文件不會被舊問題淹沒。
基準線只存雜湊值，不存文件內容，不會把機密寫進檔案。
任何情況都以 exit 0 結束；內部錯誤靜默放行，不影響開發。
環境變數 HUB_ROOT 可指定專案根目錄（測試用）。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("HUB_ROOT") or Path(__file__).resolve().parent.parent)
BASELINE = ROOT / "scripts" / "hub_conventions_baseline.json"
CHANGELOG = "docs/CHANGELOG.md"
TODO = "docs/TODO.md"
CATEGORIES = {"Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"}
MAX_BYTES = 4 * 1024 * 1024

ANY_VERSION_HEAD = re.compile(r"^## \[")
VERSION_HEAD = re.compile(r"^## \[(\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})\s*$")
MD_HEAD = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
ID_NAMED = re.compile(r"^(REQ|CR)(?![A-Za-z])")
ID_STRICT = re.compile(r"^(REQ|CR)-\d{3,}(?!\d)")
ID_KEY = re.compile(r"^(REQ|CR)-\d{3,}")
TASK_LINE = re.compile(r"^\s*- \[[ xX]\] (TASK-\d{3,})(?!\d)")
TASK_BAD = re.compile(r"^\s*- \[[ xX]\] TASK-\d{0,2}(\D|$)")
UNLABELED = re.compile(r"^\s*- \[ \] (?!TASK-)")
SECRET = re.compile(r"(?i)(password|passwd|api[_-]?key|secret|token)\s*[:=]\s*['\"]?([^\s'\"`]{6,})")
DSN = re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://[^:\s/@]+:([^@\s]{3,})@")
PLACEHOLDER = re.compile(r"(?i)<|\.\.\.|\*\*\*|xxx|your|example|範例")


def in_scope(rel: str) -> bool:
    if rel in ("CLAUDE.md", "README.md"):
        return True
    return rel.startswith("docs/") and rel.endswith(".md")


def iter_docs():
    paths = [ROOT / "CLAUDE.md", ROOT / "README.md"]
    docs_dir = ROOT / "docs"
    if docs_dir.is_dir():
        paths += sorted(docs_dir.rglob("*.md"))
    for p in paths:
        try:
            if not p.is_file() or p.stat().st_size > MAX_BYTES:
                continue
            rel = p.relative_to(ROOT).as_posix()
        except (OSError, ValueError):
            continue
        if in_scope(rel):
            yield rel, p.read_text(encoding="utf-8", errors="replace").splitlines()


def check_changelog(lines):
    out, versions = [], []
    for i, line in enumerate(lines, 1):
        if not ANY_VERSION_HEAD.match(line):
            continue
        m = VERSION_HEAD.match(line)
        if m:
            versions.append((i, m.group(1)))
        else:
            out.append((i, "changelog-heading", "版次標題格式應為 `## [X.Y.Z] - YYYY-MM-DD`"))
    seen = {}
    for i, v in versions:
        if v in seen:
            out.append((i, "changelog-dup", f"版號 {v} 重複出現，已發佈版次不可重複建立"))
        else:
            seen[v] = i
    if versions:
        start = versions[0][0]
        end = versions[1][0] if len(versions) > 1 else len(lines) + 1
        for i in range(start, end):
            line = lines[i - 1]
            if line.startswith("### "):
                name = line[4:].strip()
                if name not in CATEGORIES:
                    out.append((i, "changelog-category", f"類別標題「{name}」應只用 Added／Changed／Deprecated／Removed／Fixed／Security，說明文字請移到條列中"))
    return out


def check_headings(lines):
    out = []
    for i, line in enumerate(lines, 1):
        m = MD_HEAD.match(line)
        if not m:
            continue
        title = m.group(2).strip("*` ")
        if ID_NAMED.match(title) and not ID_STRICT.match(title):
            out.append((i, "req-format", f"需求／變更編號格式應為 `REQ-NNN`／`CR-NNN`（至少三位數字、用連字號）：{title[:40]}"))
    return out


def check_tasks(lines, is_todo):
    out = []
    for i, line in enumerate(lines, 1):
        if TASK_BAD.match(line):
            out.append((i, "task-format", "任務編號格式應為 `TASK-NNN`（至少三位數字）"))
        elif is_todo and UNLABELED.match(line):
            out.append((i, "todo-unlabeled", "待辦缺少 TASK 編號，請寫成 `- [ ] TASK-NNN 標題`"))
    return out


def check_secrets(lines):
    out = []
    for i, line in enumerate(lines, 1):
        hit = any(not PLACEHOLDER.search(m.group(2)) for m in SECRET.finditer(line))
        if not hit:
            m = DSN.search(line)
            hit = bool(m and not PLACEHOLDER.search(m.group(1)))
        if hit:
            out.append((i, "secret", "疑似機密（金鑰／密碼／連線字串／Token），規範第 9 節禁止寫入文件"))
    return out


def check_duplicates(docs):
    out, seen = [], {}
    for rel, lines in docs:
        for i, line in enumerate(lines, 1):
            key = None
            m = MD_HEAD.match(line)
            if m:
                k = ID_KEY.match(m.group(2).strip("*` "))
                if k:
                    key = k.group(0)
            else:
                t = TASK_LINE.match(line)
                if t:
                    key = t.group(1)
            if not key:
                continue
            if key in seen:
                out.append((rel, i, "dup-id", f"編號 {key} 重複（首次在 {seen[key][0]}:{seen[key][1]}），編號在專案內必須唯一"))
            else:
                seen[key] = (rel, i)
    return out


def make_key(rel, rule, text):
    digest = hashlib.sha1(text.strip().encode("utf-8")).hexdigest()[:16]
    return f"{rel}|{rule}|{digest}"


def run_checks(targets=None):
    docs = list(iter_docs())
    raw = []
    for rel, lines in docs:
        items = check_changelog(lines) if rel == CHANGELOG else check_headings(lines)
        items += check_tasks(lines, rel == TODO)
        items += check_secrets(lines)
        raw += [(rel, ln, rule, msg) for ln, rule, msg in items]
    raw += check_duplicates(docs)
    lines_by_rel = dict(docs)
    results = []
    for rel, ln, rule, msg in raw:
        if targets is not None and rel not in targets:
            continue
        src = lines_by_rel.get(rel, [])
        text = src[ln - 1] if 0 < ln <= len(src) else ""
        results.append({"rel": rel, "line": ln, "rule": rule, "msg": msg, "key": make_key(rel, rule, text)})
    results.sort(key=lambda r: (r["rel"], r["line"]))
    return results


def load_baseline():
    try:
        return set(json.loads(BASELINE.read_text(encoding="utf-8")).get("keys", []))
    except Exception:
        return set()


def save_baseline():
    keys = sorted({r["key"] for r in run_checks()})
    BASELINE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "說明": "Project Hub 規範檢查的基準線（既有問題的雜湊值）。由 --save-baseline 產生；hook 只提醒不在此清單內的新問題。",
        "keys": keys,
    }
    BASELINE.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return len(keys)


def hook_main():
    data = json.load(sys.stdin)
    fp = (data.get("tool_input") or {}).get("file_path") or ""
    if not fp:
        return
    rel = Path(fp).resolve().relative_to(ROOT.resolve()).as_posix()
    if not in_scope(rel):
        return
    baseline = load_baseline()
    new = [r for r in run_checks({rel}) if r["key"] not in baseline]
    if not new:
        return
    body = "\n".join(f"- {r['rel']}:{r['line']} {r['msg']}" for r in new)
    print(json.dumps({
        "systemMessage": "Hub 規範提醒（僅提醒，不阻擋）：\n" + body,
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": "[Project Hub 規範提醒，請於本次回覆一併修正或說明]\n" + body,
        },
    }, ensure_ascii=False))


def cli_main(argv):
    if argv == ["--save-baseline"]:
        n = save_baseline()
        print(f"已存入基準線：{n} 筆（既有問題不再於 hook 提醒；新問題仍會提醒）")
        return
    targets = None
    if argv:
        targets = set()
        for a in argv:
            p = Path(a)
            p = p if p.is_absolute() else ROOT / a
            try:
                targets.add(p.resolve().relative_to(ROOT.resolve()).as_posix())
            except ValueError:
                print(f"略過（不在專案內）：{a}")
    base = load_baseline()
    results = run_checks(targets)
    if not results:
        print("OK：未發現 Project Hub 規範提醒")
        return
    new_count = 0
    for r in results:
        old = r["key"] in base
        new_count += 0 if old else 1
        print(f"{r['rel']}:{r['line']} {r['msg']}" + ("（基準線內舊問題）" if old else ""))
    print(f"\n共 {len(results)} 則，其中新問題 {new_count} 則（提醒模式，不阻擋）")


def main(argv):
    try:
        if "--hook" in argv:
            hook_main()
        else:
            try:
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
            cli_main(argv)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
