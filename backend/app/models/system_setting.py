"""
系統設定 Model（key-value）

用途：存放「不屬於任何業務模組、但各 Server 可以不同」的站台層級設定。
目前只有站台品牌名稱（`site.brand`），未來若要加 Logo、頁尾、主題色，
直接新增 key 即可，不必再開資料表。

為什麼存 DB 而不是設定檔（2026-08-11 決策）：
- 前端 `public/config.json` 屬於 build 產物，**每次重新部署前端都會被覆蓋回預設值**，
  等於每次更新版本都要記得手動改回來，很容易漏。
- 各 Server 有各自的 `portal.db`，天生就是「一台一組設定」，符合需求。
- 已在現有備份範圍內，不需要另外顧一個檔案。

新表由 `Base.metadata.create_all()` 於後端啟動時自動建立，**不需要 migration**。
"""
from datetime import datetime

from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.time import twnow


def _now():
    return twnow()


class SystemSetting(Base):
    __tablename__ = "system_settings"

    # 設定鍵，採 `分類.欄位` 命名（例：site.brand）
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    # 設定值；一律以字串存放，需要結構化資料時由呼叫端自行 JSON 編解碼
    value: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)

    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)
    updated_by: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)
