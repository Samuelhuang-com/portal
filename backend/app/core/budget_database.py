"""
Budget Database — 獨立 SQLite 連線模組

預算系統使用獨立的 SQLite 檔案（budget_system_v1.sqlite）。
此模組提供 FastAPI Depends 相容的 get_budget_db() 函數。
"""
import sqlite3
from pathlib import Path
from typing import Generator

# 預算 SQLite 相對於 backend 目錄（與 portal.db 同層）
BUDGET_DB_PATH = Path(__file__).parent.parent.parent / "budget_system_v1.sqlite"


def _row_to_dict(row: sqlite3.Row) -> dict:
    """將 sqlite3.Row 轉成一般 dict（支援 JSON 序列化）"""
    return dict(row)


def get_budget_db() -> Generator[sqlite3.Connection, None, None]:
    """
    FastAPI Depends 相容的 budget SQLite connection。
    每個 request 一條連線，request 結束後自動關閉。
    """
    conn = sqlite3.connect(str(BUDGET_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # WAL mode may fail on network/NTFS mounts; use default DELETE mode
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
