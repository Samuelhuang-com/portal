"""
搬遷輔助腳本：更新 backend/.env 的 DB 路徑設定，指向 C:\\Portal_Data\\。

由 migrate_db_to_portal_data.bat 呼叫（Step 5），也可單獨執行：
    cd D:\\portal\\backend
    py -3.12 ..\\_migrate_env_update.py

只會修改／新增以下三個 key，其餘內容原封不動：
    DATABASE_URL
    CYCLE_PURCHASE_DATABASE_URL
    BUDGET_DB_PATH
"""
import re
import sys
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent / "backend" / ".env"

NEW_VALUES = {
    "DATABASE_URL": "sqlite:///C:/Portal_Data/portal.db",
    "CYCLE_PURCHASE_DATABASE_URL": "sqlite:///C:/Portal_Data/cycle-purchase.db",
    "BUDGET_DB_PATH": "C:/Portal_Data/budget_system_v1.sqlite",
}


def set_kv(content: str, key: str, value: str) -> str:
    pattern = re.compile(rf"(?m)^{re.escape(key)}=.*$")
    line = f"{key}={value}"
    if pattern.search(content):
        return pattern.sub(line, content, count=1)
    sep = "" if content.endswith("\n") else "\n"
    return content + sep + line + "\n"


def main() -> int:
    if not ENV_PATH.exists():
        print(f"[ERROR] 找不到 {ENV_PATH}，請確認在 D:\\portal 底下執行")
        return 1

    content = ENV_PATH.read_text(encoding="utf-8")
    before = content
    for key, value in NEW_VALUES.items():
        content = set_kv(content, key, value)

    if content == before:
        print("[INFO] .env 內容沒有變化（可能已經是新設定）")
        return 0

    ENV_PATH.write_text(content, encoding="utf-8")
    print(f"[OK] {ENV_PATH} 已更新：")
    for key, value in NEW_VALUES.items():
        print(f"  {key}={value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
