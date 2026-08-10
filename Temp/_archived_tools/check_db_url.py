"""
確認後端實際連線的資料庫檔案
用法：在 backend 資料夾裡執行（跟啟動 uvicorn 同一個目錄）：
    cd backend
    python check_db_url.py
"""
import os
import sys

print("目前工作目錄 (CWD)：", os.getcwd())
print(".env 是否存在於 CWD：", os.path.exists(".env"))

# 檢查是否有系統/session 環境變數搶先蓋過 .env 內容
env_var = os.environ.get("DATABASE_URL")
print("os.environ 裡的 DATABASE_URL（若有值，會蓋過 .env）：", repr(env_var))

sys.path.insert(0, os.getcwd())
from app.core.config import settings  # noqa: E402

print()
print("=" * 60)
print("Settings 實際解析出的 DATABASE_URL：", settings.DATABASE_URL)
print("=" * 60)

# 把 sqlite URL 轉成檔案路徑並確認是否存在、檔案大小、最後修改時間
url = settings.DATABASE_URL
if url.startswith("sqlite:///"):
    raw_path = url[len("sqlite:///"):]
    abs_path = os.path.abspath(raw_path)
    print("解析出的實際檔案路徑：", abs_path)
    if os.path.exists(abs_path):
        st = os.stat(abs_path)
        import datetime
        print("檔案大小：", st.st_size, "bytes")
        print("最後修改時間：", datetime.datetime.fromtimestamp(st.st_mtime))
    else:
        print("⚠ 這個檔案不存在！")
else:
    print("非 sqlite URL：", url)
