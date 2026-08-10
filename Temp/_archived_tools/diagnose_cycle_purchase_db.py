"""
週期採購 — 「後端到底在讀哪一個 cycle-purchase.db」唯讀診斷（2026-08-09）

為什麼需要這支：
  資料明明匯進去了，畫面卻沒有 —— 最常見的原因不是程式壞掉，而是
  **後端讀的根本是另一個檔案**。兩個相對路徑疊在一起造成的：

    1. backend/app/core/config.py 的 env_file=".env"
       → 相對於**行程的工作目錄**，不是相對於 config.py。
         服務不是從 backend/ 啟動的話，.env 整份讀不到。
    2. CYCLE_PURCHASE_DATABASE_URL 的**預設值**是 sqlite:///./cycle-purchase.db
       → 也是相對路徑。.env 沒讀到就走這個預設值，
         於是在服務的工作目錄自己建一個**空的** cycle-purchase.db。

  結果：你匯入 C:\\portal_data\\cycle-purchase.db，後端卻在讀
        D:\\portal\\cycle-purchase.db（或別的地方），畫面當然是空的。

這支腳本**完全不會寫入任何東西**（唯讀模式開檔），可以在服務執行中直接跑。

用法（在正式區）：
    cd D:\\portal\\backend
    python ..\\diagnose_cycle_purchase_db.py

  ⚠️ **請從「服務啟動時的同一個工作目錄」執行**，否則相對路徑算出來的結果
     跟服務實際用的不一樣，診斷就沒意義了。不確定的話，兩個地方都跑一次
     （D:\\portal 和 D:\\portal\\backend）比對看看。
"""

import os
import sqlite3
import sys
from datetime import datetime

# 週採的關鍵資料表（用來判斷某個 db 檔是不是「有料」的那一個）
KEY_TABLES = [
    "cycle_purchase_items",
    "cycle_purchase_item_mappings",
    "cycle_purchase_departments",
    "cycle_purchase_vendors",
    "cycle_purchase_requests",
]

# 要去翻找的位置（依可能性排序）
SEARCH_ROOTS = [
    r"C:\portal_data",
    r"C:\Portal_Data",
    r"D:\portal",
    r"D:\portal\backend",
    r"C:\portal",
    r"C:\portal\backend",
    os.getcwd(),
    os.path.join(os.getcwd(), "backend"),
    os.path.dirname(os.path.abspath(__file__)),
]


def hr(title=""):
    print("=" * 72)
    if title:
        print(f"  {title}")
        print("=" * 72)


def read_env_file(path):
    """用與 pydantic-settings 相同的方式讀 .env（只取我們關心的那一個 key）。"""
    if not os.path.exists(path):
        return None, "檔案不存在"
    try:
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() == "CYCLE_PURCHASE_DATABASE_URL":
                return v.strip().strip('"').strip("'"), None
        return None, "檔案存在，但裡面沒有 CYCLE_PURCHASE_DATABASE_URL 這一行"
    except Exception as e:
        return None, f"讀取失敗：{e}"


def url_to_path(url):
    """sqlite:///C:/x/y.db → C:\\x\\y.db；sqlite:///./y.db → 相對於 cwd 的絕對路徑"""
    if not url:
        return None
    p = url.split("///", 1)[-1] if "///" in url else url
    return os.path.abspath(p)


def inspect_db(path):
    """唯讀檢查一個 db 檔，回傳 (存在, 說明, 各表筆數 dict)"""
    if not os.path.exists(path):
        return False, "檔案不存在", {}
    size = os.path.getsize(path)
    mtime = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S")
    info = f"{size:,} bytes，最後修改 {mtime}"

    counts = {}
    try:
        uri = "file:{}?mode=ro".format(path.replace("\\", "/"))
        con = sqlite3.connect(uri, uri=True)
        for t in KEY_TABLES:
            try:
                counts[t] = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            except sqlite3.Error:
                counts[t] = None       # 表不存在
        con.close()
    except Exception as e:
        return True, f"{info}（無法讀取：{e}）", {}
    return True, info, counts


def describe(counts):
    if not counts:
        return "讀不到資料表"
    if all(v is None for v in counts.values()):
        return "⚠️ 空殼：一張週採資料表都沒有"
    parts = []
    for t, v in counts.items():
        short = t.replace("cycle_purchase_", "")
        parts.append(f"{short}={'—' if v is None else v}")
    return "  ".join(parts)


def main():
    hr("週期採購 — 後端讀的是哪一個 cycle-purchase.db（唯讀診斷）")
    print(f"執行時間　：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"目前工作目錄：{os.getcwd()}")
    print(f"腳本位置　：{os.path.abspath(__file__)}")
    print()
    print("⚠️ 相對路徑是以「目前工作目錄」為準。這支腳本必須從**服務啟動時的同一個")
    print("   工作目錄**執行，結論才有意義。")
    print()

    # ── 1. .env 在哪、讀不讀得到 ────────────────────────────────────────────
    hr("1. .env 與設定值")
    env_candidates = [
        os.path.join(os.getcwd(), ".env"),                    # pydantic 實際會找的位置
        os.path.join(os.getcwd(), "backend", ".env"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend", ".env"),
    ]
    effective_url = None
    env_exists_but_key_missing = False
    for c in dict.fromkeys(env_candidates):
        url, err = read_env_file(c)
        if (os.path.abspath(c) == os.path.abspath(env_candidates[0])
                and not url and err and "沒有 CYCLE_PURCHASE_DATABASE_URL" in err):
            env_exists_but_key_missing = True
        mark = "← pydantic 會讀這個" if os.path.abspath(c) == os.path.abspath(env_candidates[0]) else ""
        if url:
            print(f"  [找到] {c}  {mark}")
            print(f"         CYCLE_PURCHASE_DATABASE_URL = {url}")
            if not effective_url and mark:
                effective_url = url
        else:
            print(f"  [略過] {c}  ({err})  {mark}")
    print()

    if effective_url:
        print(f"  → 後端會用的設定值：{effective_url}")
    else:
        effective_url = "sqlite:///./cycle-purchase.db"
        print("  ⚠️⚠️ 從目前工作目錄**讀不到 .env**，後端會退回程式裡的預設值：")
        print(f"        {effective_url}")
        print("        這是相對路徑，會在工作目錄自己建一個空的 db —— ")
        print("        **這極可能就是「資料匯進去了但畫面沒有」的原因。**")
    print()

    effective_path = url_to_path(effective_url)
    print(f"  → 換算成實際檔案路徑：{effective_path}")
    exists, info, counts = inspect_db(effective_path)
    if exists:
        print(f"    {info}")
        print(f"    {describe(counts)}")
    else:
        print("    ⚠️ 這個檔案目前不存在（後端啟動時會自己建一個空的）")
    print()

    # ── 2. 掃描機器上所有的 cycle-purchase.db ──────────────────────────────
    hr("2. 這台機器上找得到的所有 cycle-purchase.db")
    found = {}
    for root in dict.fromkeys(SEARCH_ROOTS):
        if not os.path.isdir(root):
            continue
        try:
            for name in os.listdir(root):
                if name.lower().endswith(".db") and "cycle" in name.lower():
                    full = os.path.abspath(os.path.join(root, name))
                    found.setdefault(full, None)
        except PermissionError:
            continue

    if effective_path:
        found.setdefault(effective_path, None)

    # Windows 檔名不分大小寫：C:\Portal_Data 與 C:\portal_data 是**同一個檔案**，
    # 不去重的話會列成兩筆，看起來像有兩份資料，很容易誤判。
    deduped = {}
    for path in sorted(found):
        key = None
        for kept in deduped:
            try:
                if os.path.exists(path) and os.path.exists(kept) and os.path.samefile(path, kept):
                    key = kept
                    break
            except OSError:
                pass
        if key:
            deduped[key].append(path)
        else:
            deduped[path] = [path]
    found = deduped

    if not found:
        print("  ⚠️ 完全找不到任何 cycle-purchase.db，請確認匯入的檔案放在哪裡。")
    else:
        for path, aliases in sorted(found.items()):
            if len(aliases) > 1:
                print(f"  （以下這幾個路徑指向**同一個檔案**：{'、'.join(aliases)}）")
            exists, info, counts = inspect_db(path)
            tag = "  ★ 後端正在讀這個" if effective_path and os.path.normcase(path) == os.path.normcase(effective_path) else ""
            print(f"  {path}{tag}")
            if exists:
                print(f"      {info}")
                print(f"      {describe(counts)}")
            else:
                print("      （不存在）")
            print()

    # ── 3. WAL 檔（資料可能還沒寫回主檔）──────────────────────────────────
    hr("3. WAL 檔檢查")
    for path in sorted(found):
        wal = path + "-wal"
        if os.path.exists(wal):
            sz = os.path.getsize(wal)
            print(f"  {wal}")
            print(f"      {sz:,} bytes —— 有 WAL 檔是正常的（WAL 模式），"
                  f"用唯讀模式讀得到已提交的資料，不用特別處理。")
    print("  （沒列出東西就是沒有 WAL 檔）")
    print()

    # ── 4. 結論 ─────────────────────────────────────────────────────────────
    hr("4. 結論")
    ep_exists, _, ep_counts = inspect_db(effective_path) if effective_path else (False, "", {})
    ep_items = ep_counts.get("cycle_purchase_items")
    ep_maps = ep_counts.get("cycle_purchase_item_mappings")

    others_with_data = [
        p for p in found
        if (effective_path is None or os.path.normcase(p) != os.path.normcase(effective_path))
        and (inspect_db(p)[2].get("cycle_purchase_items") or 0)
    ]

    if ep_items:
        print(f"  ✅ 後端讀的那個檔案裡有料號資料（items={ep_items}, mappings={ep_maps}）。")
        print("     那問題就不在 DB 位置，往下查：")
        print("       - 後端服務有沒有**真的重啟過**（Windows 上曾發生過 taskkill 殺不掉、")
        print("         一直是舊 process 在回應的情況，見 README v1.60.x 的排查記錄）")
        print("       - 打 API 直接看：GET /api/v1/cycle-purchase/items?page=1&per_page=20")
        print("         回 200 但 total=0 → 真的沒資料；回 403 → 是權限不是資料")
        print("       - 瀏覽器 F12 Network 看那支 API 的實際回應")
    else:
        print("  ❌ **後端讀的那個檔案裡沒有料號資料。**")
        if others_with_data:
            print("     但這台機器上有別的檔案是有資料的：")
            for p in others_with_data:
                c = inspect_db(p)[2]
                print(f"       {p}  (items={c.get('cycle_purchase_items')}, "
                      f"mappings={c.get('cycle_purchase_item_mappings')})")
            print()
            print("     → 你匯入的是上面那個，後端卻在讀別的。")
            print()
            if env_exists_but_key_missing:
                print("     【本次的情況】.env 檔案**存在、位置也對**，只是裡面沒有")
                print("     CYCLE_PURCHASE_DATABASE_URL 這一行，所以走了程式裡的相對路徑預設值。")
                print()
                print(f"     修法：在 {os.path.join(os.getcwd(), '.env')} 加一行：")
                print(r"       CYCLE_PURCHASE_DATABASE_URL=sqlite:///C:/portal_data/cycle-purchase.db")
                print("     ⚠️ 路徑用正斜線 /，sqlite:/// 是三條斜線。加完**重啟後端服務**。")
            else:
                print("     【本次的情況】從目前工作目錄找不到 .env。修法二選一：")
                print("       (a) 在服務啟動的工作目錄放一份 .env，內容加上：")
                print(r"           CYCLE_PURCHASE_DATABASE_URL=sqlite:///C:/portal_data/cycle-purchase.db")
                print("       (b) 或把服務的啟動工作目錄改成 .env 所在的那一層")
                print("     改完**一定要重啟後端服務**。")
            print()
            print("     ⚠️ 切換之前先確認：後端目前在用的那個檔案裡有沒有**正式區實際產生**")
            print("        的資料（部門／週期設定／請購單）。有的話切過去就看不到了，要先搬。")
            print("        WAL 檔很大時，先**停掉後端服務**再跑一次這支診斷，數字才準確")
            print("        （停掉後 WAL 會被 checkpoint 併回主檔）。")
        else:
            print("     而且這台機器上也找不到有資料的 cycle-purchase.db。")
            print("     → 確認一下匯入時到底寫進哪個檔案了。")
    print()
    hr()
    return 0


if __name__ == "__main__":
    sys.exit(main())
