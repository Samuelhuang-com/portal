"""
影音教學資料匯入腳本 —— 搭配 export_tutorial_videos.py 使用（一次性工具，非常態功能）

用法（在正式機 backend 資料夾下執行，且 tutorial_videos_export/ 資料夾已從開發機複製過來）：
    python import_tutorial_videos.py                    # 自動從 .env 的 DATABASE_URL 找 DB
    python import_tutorial_videos.py D:\portal\backend\portal.db   # 手動指定 DB 檔案路徑

已存在的模組／影片（同一個 id）會直接略過，不會重複寫入或覆蓋，可安全重複執行。
執行前請先確保正式機後端至少啟動過一次（讓 Base.metadata.create_all 建好資料表）。
"""
import sys
import json
import shutil
import sqlite3
from pathlib import Path

BACKEND_DIR = Path(__file__).parent
EXPORT_DIR = BACKEND_DIR / "tutorial_videos_export"
FILES_DIR = EXPORT_DIR / "files"
VIDEO_ROOT = BACKEND_DIR / "uploads" / "tutorial_videos"

MODULE_COLS = ["id", "category", "module_name", "module_route", "sort_order", "created_at", "updated_at"]
VIDEO_COLS = [
    "id", "module_id", "episode", "title", "description",
    "video_stored_name", "video_orig_name", "video_size_bytes", "video_content_type",
    "script_stored_name", "script_orig_name", "sort_order", "uploaded_by",
    "created_at", "updated_at",
]


def resolve_db_path() -> str:
    if len(sys.argv) > 1:
        return sys.argv[1]
    env_path = BACKEND_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("DATABASE_URL"):
                url = line.split("=", 1)[1].strip().strip('"').strip("'")
                if url.startswith("sqlite:///"):
                    return url.replace("sqlite:///", "", 1)
    return str(BACKEND_DIR / "portal.db")


def main() -> None:
    db_path = resolve_db_path()
    print(f"[匯入] 目標資料庫：{db_path}")

    data_file = EXPORT_DIR / "data.json"
    if not data_file.exists():
        print(f"[錯誤] 找不到 {data_file}")
        print("       請先在開發機執行 export_tutorial_videos.py，並把整個資料夾複製過來。")
        sys.exit(1)
    if not Path(db_path).exists():
        print(f"[錯誤] 找不到目標資料庫：{db_path}")
        print("       正式機應該已經啟動過一次後端才會有這個檔案，請確認路徑或先啟動一次後端。")
        sys.exit(1)

    data = json.loads(data_file.read_text(encoding="utf-8"))
    modules = data.get("modules", [])
    videos = data.get("videos", [])

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    tables = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "tutorial_video_modules" not in tables or "tutorial_videos" not in tables:
        print("[錯誤] 目標資料庫還沒有 tutorial_video_modules / tutorial_videos 表。")
        print("       請先啟動一次正式機後端（讓 Base.metadata.create_all 建表），再執行本腳本。")
        conn.close()
        sys.exit(1)

    module_insert_sql = (
        f"INSERT INTO tutorial_video_modules ({', '.join(MODULE_COLS)}) "
        f"VALUES ({', '.join(':' + c for c in MODULE_COLS)})"
    )
    video_insert_sql = (
        f"INSERT INTO tutorial_videos ({', '.join(VIDEO_COLS)}) "
        f"VALUES ({', '.join(':' + c for c in VIDEO_COLS)})"
    )

    module_inserted = module_skipped = 0
    for m in modules:
        if cur.execute("SELECT 1 FROM tutorial_video_modules WHERE id = ?", (m["id"],)).fetchone():
            module_skipped += 1
            continue
        cur.execute(module_insert_sql, m)
        module_inserted += 1

    video_inserted = video_skipped = 0
    for v in videos:
        if cur.execute("SELECT 1 FROM tutorial_videos WHERE id = ?", (v["id"],)).fetchone():
            video_skipped += 1
            continue
        cur.execute(video_insert_sql, v)
        video_inserted += 1

    conn.commit()
    conn.close()

    VIDEO_ROOT.mkdir(parents=True, exist_ok=True)
    copied = skipped_files = 0
    if FILES_DIR.exists():
        for f in FILES_DIR.iterdir():
            if not f.is_file():
                continue
            dest = VIDEO_ROOT / f.name
            if dest.exists():
                skipped_files += 1
                continue
            shutil.copy2(f, dest)
            copied += 1

    print(f"[匯入完成] 模組：新增 {module_inserted}、略過（已存在）{module_skipped}")
    print(f"[匯入完成] 影片：新增 {video_inserted}、略過（已存在）{video_skipped}")
    print(f"[匯入完成] 檔案：複製 {copied}、略過（已存在）{skipped_files}")
    print("\n請重新整理正式機網頁確認資料正確顯示。")


if __name__ == "__main__":
    main()
