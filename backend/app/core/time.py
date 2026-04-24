"""
時區工具模組

Portal 系統政策：所有時間戳記一律使用台灣時間（UTC+8）儲存與計算。
資料庫欄位儲存 naive datetime（不帶 tz 資訊），值代表台灣當地時間。

使用方式：
    from app.core.time import twnow

    record.created_at = twnow()          # ORM 欄位賦值
    started = twnow()                    # 計時起點
"""
from datetime import datetime, timedelta, timezone

# 台灣時間常數（UTC+8）
TW_TZ = timezone(timedelta(hours=8))


def twnow() -> datetime:
    """
    回傳台灣當地時間，不含時區資訊（naive datetime）。
    適用於 SQLite DateTime 欄位儲存。

    等效於：datetime.now(TW_TZ).replace(tzinfo=None)
    """
    return datetime.now(TW_TZ).replace(tzinfo=None)
