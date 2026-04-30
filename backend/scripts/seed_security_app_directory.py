"""
保全巡檢 Ragic App Directory 初始化腳本
=======================================
用途：將 7 張保全巡檢 Sheet 的 Portal 對應記錄寫入 ragic_app_portal_annotations 表。

執行方式（後端停機時）：
    cd backend
    python scripts/seed_security_app_directory.py

注意：請在後端停機狀態下執行，以避免 WAL 鎖定衝突。
"""
import sqlite3
import os
import datetime

# 確認 DB 路徑
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, '..', 'portal.db')
DB_PATH = os.path.normpath(DB_PATH)

# 保全巡檢 7 張 Sheet 對應記錄
# item_no 對應 RAGIC_APPS_STATIC 中的靜態序號
SECURITY_ENTRIES = [
    # (item_no, portal_name, portal_url)
    (13, '保全巡檢 - B1F~B4F夜間巡檢',  '/security/dashboard'),  # security-patrol/1
    (5,  '保全巡檢 - 1F~3F夜間巡檢',    '/security/dashboard'),  # security-patrol/2
    (10, '保全巡檢 - 5F~10F夜間巡檢',   '/security/dashboard'),  # security-patrol/3
    (9,  '保全巡檢 - 4F夜間巡檢',        '/security/dashboard'),  # security-patrol/4
    (8,  '保全巡檢 - 1F飯店大廳',        '/security/dashboard'),  # security-patrol/5
    (6,  '保全巡檢 - 1F閉店巡檢',        '/security/dashboard'),  # security-patrol/6
    (7,  '保全巡檢 - 1F開店準備',        '/security/dashboard'),  # security-patrol/9
]


def main():
    if not os.path.exists(DB_PATH):
        print(f'[ERROR] DB 不存在：{DB_PATH}')
        return

    print(f'[INFO] 連線 DB：{DB_PATH}')
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    success = 0

    for item_no, portal_name, portal_url in SECURITY_ENTRIES:
        cur.execute('''
            INSERT INTO ragic_app_portal_annotations (item_no, portal_name, portal_url, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(item_no) DO UPDATE SET
                portal_name = excluded.portal_name,
                portal_url  = excluded.portal_url,
                updated_at  = excluded.updated_at
        ''', (item_no, portal_name, portal_url, now))
        print(f'  ✅  item_no={item_no:>3}  {portal_name}')
        success += 1

    conn.commit()

    # 驗證
    print(f'\n[INFO] 已寫入 {success} 筆，驗證結果：')
    cur.execute(
        'SELECT item_no, portal_name, portal_url FROM ragic_app_portal_annotations ORDER BY item_no'
    )
    for row in cur.fetchall():
        print(f'  item_no={row[0]:>3}  portal_name={row[1]}  portal_url={row[2]}')

    conn.close()
    print('\n[DONE] 完成。')


if __name__ == '__main__':
    main()
