"""
影音教學資料匯出腳本 —— 開發機 → 正式機搬遷用（一次性工具，非常態功能）

用法（在 backend 資料夾下執行）：
    python export_tutorial_videos.py                    # 自動從 .env 的 DATABASE_URL 找 DB
    python export_tutorial_videos.py C:\portal_data\portal.db   # 手動指定 DB 檔案路徑

執行後會在 backend 資料夾下產生 tutorial_videos_export/ 資料夾，內含：
    data.json   模組（tutorial_video_modules）與影片（tutorial_videos）記錄
    files/      實際的 mp4／txt 檔案複本

下一步：把整個 tutorial_videos_export 資料夾複製到正式機的 backend 資料夾下，
再於正式機執行 import_tutorial_videos.py。
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
    print(f"[匯出] 來源資料庫：{db_path}")
    if not Path(db_path).exists():
        print(f"[錯誤] 找不到資料庫檔案：{db_path}")
        print("       請確認路徑，或用參數指定：python export_tutorial_videos.py <完整路徑>")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    tables = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "tutorial_video_modules" not in tables or "tutorial_videos" not in tables:
        print("[匯出] 此資料庫還沒有影音教學相關資料表，無需匯出。")
        conn.close()
        sys.exit(0)

    modules = [
        dict(zip(MODULE_COLS, row))
        for row in cur.execute(f"SELECT {', '.join(MODULE_COLS)} FROM tutorial_video_modules")
    ]
    videos = [
        dict(zip(VIDEO_COLS, row))
        for row in cur.execute(f"SELECT {', '.join(VIDEO_COLS)} FROM tutorial_videos")
    ]
    conn.close()

    if not modules and not videos:
        print("[匯出] 目前資料庫沒有任何影音教學資料，無需匯出。")
        sys.exit(0)

    EXPORT_DIR.mkdir(exist_ok=True)
    FILES_DIR.mkdir(exist_ok=True)

    (EXPORT_DIR / "data.json").write_text(
        json.dumps({"modules": modules, "videos": videos}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    copied, missing = 0, []
    for v in videos:
        for key in ("video_stored_name", "script_stored_name"):
            name = v.get(key)
            if not name:
                continue
            src = VIDEO_ROOT / name
            if src.exists():
                shutil.copy2(src, FILES_DIR / name)
                copied += 1
            else:
                missing.append(str(src))

    print(f"[匯出完成] {len(modules)} 個模組、{len(videos)} 支影片記錄")
    print(f"[匯出完成] 複製了 {copied} 個檔案到 {FILES_DIR}")
    if missing:
        print(f"[警告] 有 {len(missing)} 個檔案在磁碟上找不到（不影響資料庫記錄匯出，但正式機會播放失敗）：")
        for m in missing:
            print("   -", m)
    print(f"\n下一步：把整個資料夾 {EXPORT_DIR} 複製到正式機的 backend 資料夾下，")
    print("然後在正式機執行：python import_tutorial_videos.py")


if __name__ == "__main__":
    main()
