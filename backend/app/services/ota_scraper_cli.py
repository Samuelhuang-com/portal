"""
OTA 口碑分析 — 命令列擷取入口（R1 備援執行路徑）

建立日期：2026-08-22
規格書：`docs/SPEC_ota_reviews.md` §3.3 R1

═══════════════════════════════════════════════════════════════════════════
這支存在的理由
═══════════════════════════════════════════════════════════════════════════
Booking 對無頭瀏覽器偵測較嚴，原型工具對它刻意開可見視窗。
但 Portal 若以 Windows Service（LocalSystem）執行，**沒有互動式桌面 session**，
`webdriver.Chrome()` 開可見視窗會直接失敗。

`OTA_BROWSER_MODE=auto` 會先試 headless、再退可見視窗；兩者都失敗時
`ota_scraper_service` 拋 `HeadlessBlockedError`，訊息就指向這支程式。

**用法（Windows 工作排程器，以「登入的使用者身分」執行）**

    程式：  C:\\portal\\backend\\venv\\Scripts\\python.exe
    參數：  -m app.services.ota_scraper_cli
    起始於：C:\\portal\\backend
    勾選：  「只有使用者登入時才執行」  ← 這是關鍵，才有桌面 session

並在 `backend/.env` 設定：

    OTA_BROWSER_MODE=visible

⚠️ 走這條路時，**Portal 後端的 03:05 排程要關掉**，否則兩邊會搶同一把
   `sync_lock`（不會壞，但其中一邊會白等到逾時）。關法：把
   `sync_tool.py` 的「OTA 評論擷取」停用，或在 .env 設 `SCHEDULER_ENABLED=false`。

═══════════════════════════════════════════════════════════════════════════
參數
═══════════════════════════════════════════════════════════════════════════
    python -m app.services.ota_scraper_cli                # 所有啟用中的來源
    python -m app.services.ota_scraper_cli --ids 1,3      # 只跑指定來源
    python -m app.services.ota_scraper_cli --force        # 忽略「每日一次」限制
    python -m app.services.ota_scraper_cli --list         # 只列出來源，不擷取

    # selector 診斷（不寫入資料庫）—— Tripadvisor／Expedia 首次上線前必跑
    python -m app.services.ota_scraper_cli --diagnose "<url>" --platform tripadvisor

⚠️ **Windows cmd 一定要把網址用雙引號包起來**。
   OTA 網址幾乎都含 `&`（查詢參數），而 cmd 把 `&` 當成「命令分隔字元」，
   沒加引號會被切成好幾條指令：

       ✗ --diagnose https://x.com/a?b=1&c=2 --platform tripadvisor
         → cmd 只吃到 `...?b=1`，後面的 `c=2` 與 `--platform` 全部丟失，
           程式會回報「需要同時指定 --platform」

       ✓ --diagnose "https://x.com/a?b=1&c=2" --platform tripadvisor

   （這與記憶中 `prod-update-newserver.bat` 踩過的「cmd 的 = 是參數分隔字元」
     是同一類問題。PowerShell 用單引號 `'...'`。）

離開碼：0 = 全部成功；1 = 有來源失敗；2 = 設定或環境問題（沒有來源、套件沒裝）
"""
from __future__ import annotations

import argparse
import logging
import sys


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="ota_scraper_cli",
        description="OTA 評論擷取（可見視窗模式的備援執行入口）",
    )
    parser.add_argument("--ids", default="", help="只跑指定來源 id，逗號分隔")
    parser.add_argument("--force", action="store_true",
                        help="忽略「每日至多一次」限制，強制重抓。"
                             "⚠️ 只解除當日限制，**不會**改變翻頁上限")
    parser.add_argument("--max-pages", type=int, default=0, metavar="N",
                        help="本次執行覆寫翻頁上限（1~500），不動來源設定。"
                             "第一次回補歷史評論時用 —— 來源預設只有 20 頁"
                             "（Booking 約 200 則、Agoda 約 500 則）")
    parser.add_argument("--lock-wait", type=int, default=30, metavar="MIN",
                        help="等跨行程同步鎖最多幾分鐘（預設 30）。"
                             "⚠️ 預設的 90 秒是按 Ragic 批次（約 67 秒）訂的，"
                             "OTA 擷取一跑就是 20～40 分鐘 —— 用 90 秒等它"
                             "保證等不到")
    parser.add_argument("--no-lock", action="store_true",
                        help="⚠️ 跳過跨行程同步鎖。**確定沒有其他同步在跑才用**："
                             "兩個行程同時寫 SQLite 會 database-is-locked，"
                             "這把鎖就是 2026-07-15 為了修那個問題才加的")
    parser.add_argument("--list", action="store_true",
                        help="只列出來源與最後同步狀態，不執行擷取")
    parser.add_argument("--diagnose", default="",
                        help="診斷指定網址的 selector 命中狀況（不寫入資料庫）")
    parser.add_argument("--platform", default="",
                        help="搭配 --diagnose／--import-html：booking / tripadvisor / expedia")
    parser.add_argument("--diagnose-file", default="",
                        help="診斷**本機 HTML 檔**（用瀏覽器另存的頁面），不開瀏覽器")
    parser.add_argument("--import-html", default="",
                        help="把本機 HTML 檔的評論匯入資料庫。可給多個檔，逗號分隔")
    parser.add_argument("--source-id", type=int, default=0,
                        help="搭配 --import-html：要匯入到哪一個 OTA 來源")
    return parser.parse_args(argv)


def _read_html(path: str) -> str | None:
    """讀本機 HTML 檔。編碼依序試 utf-8 / utf-8-sig / cp950。"""
    from pathlib import Path

    file = Path(path.strip().strip('"'))
    if not file.is_file():
        print(f"❌ 找不到檔案：{file}")
        return None
    raw = file.read_bytes()
    for encoding in ("utf-8", "utf-8-sig", "cp950"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    print(f"❌ 無法辨識編碼：{file}")
    return None


def _run_diagnose_file(path: str, platform: str) -> int:
    """
    診斷**本機 HTML 檔**，不開瀏覽器。

    ⚠️ 存在的理由（2026-08-22）：Tripadvisor 對自動化存取跳人機驗證，
       而且會隨著重複存取升級封鎖（實測第二輪連可見視窗都只拿到 1,564 字元）。

       CAPTCHA 是明確的存取控制，本專案**不做繞過**（不接住宅代理輪替、
       不接打碼服務）—— 那既是與平台的對抗，也可能影響飯店自己的商家帳號，
       為了兩百則評論賭這個並不划算。

       改走「人去過驗證、程式只負責解析」：使用者用**自己的瀏覽器**開頁面
       （驗證本來就是給人過的），Ctrl+S 另存成 HTML，程式讀檔解析。
       存取是人做的，程式做的是正規化、分制換算、跨站去重。
    """
    from app.services import ota_parser as PR

    parser = PR.get_parser(platform)
    if parser is None:
        print(f"❌ 平台「{platform}」沒有 parser。可用：{', '.join(sorted(PR.PARSERS))}")
        return 2

    html = _read_html(path)
    if html is None:
        return 2

    report = PR.diagnose(html, platform)
    print(f"檔案：{path}")
    print(f"平台：{platform}　{report['html_chars']:,} 字元　"
          f"ld+json 區塊 {report['ld_json_blocks']} 個")
    print("-" * 64)
    _print_report(report, html, platform)
    return 0 if report["parsed"].get("dom_reviews", 0) else 1


def _run_import_html(paths: str, source_id: int) -> int:
    """
    把本機 HTML 檔的評論匯入資料庫。

    走的是與爬蟲**完全相同**的管線（parser → normalize → ingest），
    所以分制換算、日期正規化、同來源與跨站去重的行為完全一致。
    """
    from app.core.database import SessionLocal
    from app.models.ota_review import OtaSource
    from app.services import ota_parser as PR
    from app.services.ota_ingest_service import (finish_sync_log,
                                                 start_sync_log, upsert_reviews)
    from app.services.ota_normalize import normalize_review

    files = [p for p in paths.split(",") if p.strip()]
    if not files:
        print("❌ --import-html 沒有給檔案")
        return 2

    db = SessionLocal()
    try:
        source = db.get(OtaSource, source_id)
        if source is None:
            print(f"❌ 找不到來源 id={source_id}。用 --list 看有哪些來源。")
            return 2

        parser = PR.get_parser(source.platform)
        if parser is None:
            print(f"❌ 來源平台「{source.platform}」沒有 parser")
            return 2

        print(f"匯入到來源 [{source.id}] {source.hotel_name or source.hotel_code}"
              f" / {source.platform}")
        print("-" * 64)

        raws = []
        warnings: list[str] = []
        for path in files:
            html = _read_html(path)
            if html is None:
                return 2
            page_reviews, overall, count = PR.parse_page(source.platform, html)
            print(f"  {path}：{len(page_reviews)} 則")
            if not page_reviews:
                warnings.append(f"{path} 解析不到評論")
            raws.extend(page_reviews)
            if overall is not None and source.overall_score is None:
                source.overall_score = overall
                source.overall_score_10 = (
                    overall * 2 if source.score_scale == 5 else overall)
            if count is not None:
                source.review_count_site = count

        if not raws:
            print("-" * 64)
            print("❌ 所有檔案都解析不到評論。先用 --diagnose-file 看 selector 命中狀況：")
            print(f"   python -m app.services.ota_scraper_cli --diagnose-file "
                  f'"{files[0]}" --platform {source.platform}')
            return 1

        log = start_sync_log(db, source.id, "import", "cli-html")
        db.commit()
        normalized = [
            normalize_review(r, hotel_code=source.hotel_code,
                             platform=source.platform,
                             default_scale=source.score_scale)
            for r in raws
        ]
        result = upsert_reviews(db, source, normalized, sync_log_id=log.id)
        finish_sync_log(db, log, status="success", pages_fetched=len(files),
                        found_count=len(raws), result=result, warnings=warnings)
        db.commit()

        print("-" * 64)
        print(f"✅ 共解析 {len(raws)} 則：新增 {result.inserted}、更新 {result.updated}、"
              f"標記跨站重複 {result.marked_duplicate}")
        if result.warnings:
            print(f"   提醒 {len(result.warnings)} 項（不影響匯入）：")
            for w in result.warnings[:10]:
                print(f"   ・{w}")
        return 0
    finally:
        db.close()


def _run_diagnose(url: str, platform: str) -> int:
    """
    實際開啟頁面，逐一回報每組 selector 命中狀況。

    ⚠️ 這支的用途是「selector 對不對」，所以**不寫入資料庫、不記同步紀錄**。
       Tripadvisor 與 Expedia 的 selector 沒有經過真實頁面驗證
       （Booking 那組有），第一次上線前請先跑這個。
    """
    from app.services import ota_browser as BR
    from app.services import ota_parser as PR
    from app.services.ota_normalize import PLATFORM_LABEL, platform_from_url

    parser = PR.get_parser(platform)
    if parser is None:
        print(f"❌ 平台「{platform}」沒有 parser。可用：{', '.join(sorted(PR.PARSERS))}")
        return 2

    # ── 網址與平台對不對得上 ──────────────────────────────────────────
    # ⚠️ 這道防呆是實際踩到才加的：`tw.trip.com` 配 `--platform tripadvisor`。
    #    Trip.com（攜程）與 Tripadvisor 是不同公司、不同網站，只是名字像。
    #    沒有這道檢查，結果會是「所有 selector 都沒命中」，看起來像 selector
    #    失效，實際上是打錯網站 —— 會往完全錯誤的方向查很久。
    detected, note = platform_from_url(url)
    if note:
        print(f"❌ 這個網址是 {note}")
        print(f"   你指定的平台是「{PLATFORM_LABEL.get(platform, platform)}」，對不上。")
        print(f"   Tripadvisor 的網址長這樣：https://www.tripadvisor.com.tw/Hotel_Review-...")
        return 2
    if detected and detected != platform:
        print(f"❌ 網址看起來是 {PLATFORM_LABEL.get(detected, detected)}，"
              f"但 --platform 指定的是 {PLATFORM_LABEL.get(platform, platform)}")
        print(f"   請改用：--platform {detected}")
        return 2
    if not detected:
        print(f"⚠️  無法從網址判斷平台（{url[:60]}），仍以 --platform {platform} 繼續")

    try:
        import undetected_chromedriver  # noqa: F401
        uc_status = "已安裝"
    except ImportError:
        uc_status = "⚠️ 未安裝（偵測較嚴的站很可能被擋）"

    print(f"開啟頁面：{url}")
    print(f"平台：{platform}")
    print(f"反偵測套件 undetected-chromedriver：{uc_status}")
    print("-" * 64)

    modes = BR.resolve_modes(parser.prefer_visible)
    html = ""
    used_mode = ""
    for headless in modes:
        mode_name = "headless" if headless else "visible"
        try:
            with BR.browser(headless) as driver:
                driver.get(url)
                BR.wait_ready(driver)
                # 與正式擷取走同樣的前置動作，否則診斷的是「還沒展開」的頁面
                from app.services.ota_scraper_service import (
                    _expand_long_reviews, _open_review_dialog, _scroll_to_load,
                )
                warns: list[str] = []
                _open_review_dialog(driver, parser, warns)
                _scroll_to_load(driver, parser)
                _expand_long_reviews(driver, parser, warns)
                page = driver.page_source
                for w in warns:
                    print(f"  ⚠️  {w}")

            # ⚠️ 被擋不會拋例外，只會拿到一張很短的攔截頁。
            #    只有「拿到看起來正常的內容」才算成功、才 break ——
            #    否則 auto 模式下會停在 headless，永遠不會去試可見視窗
            #    （2026-08-22 實測 Tripadvisor 就是卡在這裡）。
            if BR.looks_blocked(page) or BR.looks_empty(page):
                print(f"  ⚠️  {mode_name} 模式只拿到 {len(page):,} 字元"
                      f"{'（攔截頁）' if BR.looks_blocked(page) else ''}")
                html, used_mode = page, mode_name      # 全都失敗時留最後一次的結果供診斷
                continue
            html, used_mode = page, mode_name
            break
        except Exception as exc:            # noqa: BLE001
            print(f"  ❌ {mode_name} 模式失敗：{exc}")

    if not html:
        print("-" * 64)
        print("❌ 瀏覽器啟動不起來，連頁面都沒開到 —— 這與 selector、與 OTA 擋不擋人無關")
        print("")
        print("   最常見的兩個原因：")
        print("   1. ⭐ **chromedriver 與 Chrome 版本對不上**")
        print("      訊息長這樣：This version of ChromeDriver only supports Chrome version N")
        print("                  Current browser version is M")
        print("      本程式會自動偵測 Chrome 主版號並回推重試，若仍失敗：")
        print("      · 把 Chrome 更新到最新版，或")
        print("      · 清掉快取的 driver 讓它重抓：")
        print("        del %APPDATA%\\undetected_chromedriver\\undetected_chromedriver.exe")
        print("   2. 這台機器沒有安裝 Chrome，或 Chrome 不在預設路徑")
        print("")
        chrome_major = None
        try:
            chrome_major = BR.detect_chrome_major()
        except Exception:           # noqa: BLE001
            pass
        print(f"   本機偵測到的 Chrome 主版號：{chrome_major or '偵測不到'}")
        print("")
        print("   （若上方出現 `Exception ignored in: Chrome.__del__ ... WinError 6`，")
        print("     那是 undetected-chromedriver 在啟動失敗後的解構噪音，可忽略。）")
        return 1

    report = PR.diagnose(html, platform)
    print(f"模式：{used_mode}　頁面 {report['html_chars']:,} 字元　"
          f"ld+json 區塊 {report['ld_json_blocks']} 個")

    # ── ⚠️ 頁面根本沒載到內容時，**立刻停止**，不要印 selector 結果 ──────
    #
    # 2026-08-22 實測踩到：Tripadvisor 回了 1,582 字元的攔截頁，
    # 工具照樣把 11 組「未命中」印出來、還叫使用者把輸出貼回去修 selector。
    # 那是把真正的發現（被擋了）埋在雜訊底下，並給出完全錯誤的下一步 ——
    # selector 在空頁上本來就不可能命中，那些 ❌ 一個資訊量都沒有。
    blocked = BR.looks_blocked(html)
    empty = BR.looks_empty(html)
    if blocked or empty:
        print("-" * 64)
        print("❌ 頁面沒有載到真實內容，**這不是 selector 的問題**")
        print(f"   真實的評論頁是數百 KB，這次只拿到 {report['html_chars']:,} 字元"
              + ("（且命中攔截／驗證頁特徵）" if blocked else ""))
        print("")
        print("   依序檢查：")

        try:
            import undetected_chromedriver  # noqa: F401
            has_uc = True
        except ImportError:
            has_uc = False

        step = 1
        if not has_uc:
            print(f"   {step}. ⭐ **undetected-chromedriver 沒有安裝** —— 這多半就是原因。")
            print(f"      Booking 用原生 selenium 就過了，但各站的偵測強度差很多。")
            print(f"      cd backend && pip install -r requirements.txt")
            step += 1
        if used_mode == "headless":
            print(f"   {step}. 改開可見視窗再試一次：.env 設 OTA_BROWSER_MODE=visible")
            step += 1
        print(f"   {step}. 網址可能需要登入或有地區限制 —— 用一般瀏覽器開開看，"
              f"確認不登入也看得到評論")
        print(f"   {step + 1}. 以上都排除後才可能是版面改版，屆時再跑一次本工具")
        print("")
        print("   在頁面能正常載入之前，selector 命中結果沒有參考價值，故不列出。")
        return 1

    return _print_report(report, html, platform)


def _print_report(report: dict, html: str, platform: str) -> int:
    """
    印出 selector 命中狀況與解析結果。

    `--diagnose`（開瀏覽器）與 `--diagnose-file`（讀本機檔）共用這段 ——
    兩者的差別只在「HTML 從哪裡來」，報表格式應該完全一致。
    """
    from app.services import ota_parser as PR

    print("【selector 命中狀況】")
    missed = []
    for group in report["groups"]:
        icon = "✅" if group["matched"] else "❌"
        print(f"  {icon} {group['label']}")
        if not group["matched"]:
            missed.append(group["label"])
        for cand in group["candidates"]:
            mark = "·" if cand["count"] else " "
            sample = f"　→ {cand['sample']}" if cand["sample"] else ""
            print(f"      {mark} {cand['count']:>4}  {cand['selector']}{sample}")

    print("-" * 64)
    print("【解析結果】")
    parsed = report["parsed"]
    print(f"  ld+json：{parsed.get('ld_json_reviews', 0)} 則"
          f"　總分 {parsed.get('ld_json_overall')}　站方評論數 {parsed.get('ld_json_count')}")
    print(f"  DOM 卡片：{parsed.get('dom_reviews', 0)} 則"
          f"　總分 {parsed.get('dom_overall')}　站方評論數 {parsed.get('dom_count')}")
    print(f"  其中有分數 {parsed.get('with_score', 0)} 則"
          f"、有分制 {parsed.get('with_scale', 0)} 則"
          f"、有日期 {parsed.get('with_date', 0)} 則")

    for i, sample in enumerate(parsed.get("samples", []), 1):
        print(f"\n  範例 {i}：")
        for key, value in sample.items():
            if value not in ("", None):
                print(f"      {key:<12} {value}")

    # ── ⭐ 找得到卡片、卻抓不到欄位時，把卡片內部結構印出來 ──────────────
    #
    # 2026-08-22 加這段的原因很具體：Tripadvisor 實測回報
    # 「評論卡命中 10 張，但暱稱／標題／留言／日期全部 0」。
    # 知道「沒命中」卻不知道「實際長什麼樣」，等於還是得猜 —— 又要再跑一輪。
    # 直接把第一張卡的節點與 data-* 屬性列出來，看一眼就知道該用什麼 selector。
    card_found = any(g["label"] == "評論卡" and g["matched"] for g in report["groups"])
    if card_found and parsed.get("dom_reviews", 0) == 0:
        print("-" * 64)
        print("【第一張評論卡的內部結構】← 找得到卡片但抓不到欄位，這段才是修 selector 的依據")
        for line in PR.dump_card_structure(html, platform):
            print(f"  {line}")

    # ── ⭐ 連卡片都找不到時，回報「這個頁面到底長什麼樣」──────────────
    #
    # 2026-08-22 Expedia 實測踩到：13 組 selector 全滅、ld+json 也 0 個。
    # `dump_card_structure()` 幫不上忙 —— 它的前提是「找得到卡片」。
    # 結果輸出只有一長串 ❌，完全看不出來是「selector 猜錯」還是
    # 「內容根本沒渲染」—— 而這兩件事的處理方式完全相反。
    if not card_found:
        print("-" * 64)
        print("【頁面實況】← 一張卡都沒找到，先確認是 selector 錯還是內容沒渲染")
        for line in PR.dump_page_overview(html):
            print(f"  {line}")
        print("")
        print("  怎麼看這段：")
        print("  · 有大量 data-* 屬性、且可見文字含「評論」→ selector 猜錯，照上面的屬性重寫")
        print("  · data-* 很少或沒有、可見文字也沒有評論字樣 → 內容沒渲染，")
        print("    多半要換成專門的評論頁網址，或這一站是登入後才給看")

    print("-" * 64)
    if missed:
        print(f"❌ 有 {len(missed)} 組 selector 完全沒命中：{'、'.join(missed)}")
        print("   請把上面整段輸出貼回對話，我依實際結構修正")
        print(f"   selector 定義在 backend/app/services/ota_parser.py 頂端的常數區")
        return 1
    if parsed.get("dom_reviews", 0) == 0:
        print("❌ 所有 selector 都有命中，但解析出 0 則評論 —— 卡片結構可能已改變")
        return 1
    print(f"✅ selector 全數命中，解析出 {parsed['dom_reviews']} 則評論")
    return 0


def main(argv: list[str] | None = None) -> int:
    _setup_logging()
    args = _parse_args(argv)

    from app.core.config import settings
    from app.core.database import SessionLocal
    from app.services import ota_source_service as SRC
    from app.services.ota_scraper_service import sync_sources
    from app.services.ota_sync_recovery import ensure_worker_columns

    # ⚠️ 這支是**獨立行程**，不會經過後端 lifespan 的 migration。
    #    `ota_sync_logs` 少了 worker_host／worker_pid 時，第一次 INSERT 就會
    #    `no such column` 炸掉 —— 而且是在真的開始擷取之後才炸，白等一場。
    #    回補常常是在還沒重啟後端的機器上跑，所以這裡必須自己確認 schema。
    for _col in ensure_worker_columns():
        print(f"[Migration] ota_sync_logs.{_col} 欄位已新增")

    print("=" * 64)
    print("OTA 評論擷取（CLI）")
    print(f"瀏覽器模式：OTA_BROWSER_MODE={settings.OTA_BROWSER_MODE}")
    if settings.OTA_BROWSER_MODE != "visible":
        print("⚠️  這支程式的用途是「開可見視窗」，建議在 .env 設 OTA_BROWSER_MODE=visible")
    print("=" * 64)

    # ── 診斷模式：不碰資料庫，只回報 selector 命中狀況 ──────────────
    if args.diagnose:
        platform = args.platform.strip().lower()
        if not platform:
            print("❌ --diagnose 需要同時指定 --platform（booking / tripadvisor / expedia）")
            return 2
        return _run_diagnose(args.diagnose, platform)

    # ── 本機 HTML 檔：診斷 ──────────────────────────────────────────
    if args.diagnose_file:
        platform = args.platform.strip().lower()
        if not platform:
            print("❌ --diagnose-file 需要同時指定 --platform")
            return 2
        return _run_diagnose_file(args.diagnose_file, platform)

    # ── 本機 HTML 檔：匯入 ──────────────────────────────────────────
    if args.import_html:
        if not args.source_id:
            print("❌ --import-html 需要同時指定 --source-id（用 --list 看有哪些來源）")
            return 2
        return _run_import_html(args.import_html, args.source_id)

    db = SessionLocal()
    try:
        sources = SRC.list_sources(db)
        if not sources:
            print("❌ 沒有任何 OTA 來源。請先到 Portal →口碑分析 → OTA 來源設定建立。")
            return 2

        if args.list:
            for s in sources:
                flag = "啟用" if s.is_enabled else "停用"
                print(f"  [{s.id:>3}] {flag}  {s.hotel_name or s.hotel_code} / {s.platform}"
                      f"  已收錄 {s.stored_count}  最後同步 {s.last_sync_at or '—'}"
                      f"  狀態 {s.last_status}")
            return 0

        ids = [int(x) for x in args.ids.split(",") if x.strip().isdigit()] or None
        if args.ids and not ids:
            print(f"❌ --ids 格式錯誤：{args.ids}")
            return 2

        # ⚠️ 這條路徑沒有外層鎖，必須自己加 —— 否則會跟後端排程／sync_tool
        #    同時寫入 portal.db（記憶 project_sync_tool_db_lock_diagnosis）
        from filelock import Timeout as LockTimeout

        from app.core.sync_lock import describe_lock_owner, sync_lock

        # ⚠️ 上限 500 —— 再高只是讓一次執行跑到天亮。
        #    Booking 約 10 則/頁、Agoda 約 25 則/頁，500 頁足夠涵蓋數千則。
        if args.max_pages and not (1 <= args.max_pages <= 500):
            print(f"❌ --max-pages 要在 1~500 之間（收到 {args.max_pages}）")
            return 2
        if args.max_pages:
            print(f"本次翻頁上限覆寫為 {args.max_pages} 頁"
                  f"（**不寫回來源設定**，只影響這一次執行）")

        def _run():
            return sync_sources(
                db, ids,
                trigger_type="manual",
                triggered_by="cli",
                respect_daily_limit=not args.force,
                max_pages_override=args.max_pages or None,
            )

        if args.no_lock:
            print("⚠️  --no-lock：跳過跨行程同步鎖。")
            print("    確定後端排程與 sync_tool.py 都沒有在同步，否則會 database-is-locked。")
            result = _run()
        else:
            # ⚠️ 逾時預設拉到 30 分鐘（`--lock-wait` 可調）。
            #    `DEFAULT_TIMEOUT = 90` 是按 Ragic 批次（約 67 秒）訂的，
            #    而 OTA 擷取一個來源就要 20～40 分鐘 —— 用 90 秒去等一個
            #    正在跑的 OTA 同步，**保證等不到**，那不是運氣不好是設計沒跟上。
            wait_seconds = max(60, args.lock_wait * 60)

            def _notice(waited: float, owner: str) -> None:
                print(f"  ⏳ 等待同步鎖…已等 {waited / 60:.0f} 分鐘"
                      f"（上限 {wait_seconds / 60:.0f} 分，可用 --lock-wait 調整）")
                print(f"     {owner}")

            try:
                with sync_lock("OTA 評論擷取（CLI）", timeout=wait_seconds,
                               on_wait=_notice):
                    result = _run()
            except LockTimeout:
                # ⚠️ **不要讓它變成 traceback**（2026-08-25 實測踩到）。
                #    `sync_lock` 記的 log 寫「本次略過」卻往外拋，
                #    而沒有任何呼叫端接住 —— 使用者看到的是一段堆疊，
                #    完全看不出「有別人在跑、等它跑完就好」。
                print()
                print("=" * 64)
                print(f"⏹  等不到同步鎖（已等 {wait_seconds / 60:.0f} 分鐘），本次沒有執行。")
                print(f"   {describe_lock_owner()}")
                print()
                print("   可以這樣做：")
                print("     · 等對方跑完再重試（OTA 擷取一個來源要 20～40 分鐘）")
                print("     · 拉長等待：--lock-wait 60")
                print("     · 確定沒人在跑的話：--no-lock（⚠️ 同時寫入會壞資料）")
                print("=" * 64)
                return 3
    finally:
        db.close()

    print("-" * 64)
    for detail in result["details"]:
        icon = {"success": "✅", "captcha": "⚠️ ", "failed": "❌"}.get(detail["status"], "  ")
        print(f"  {icon} {detail['label']}：{detail['status']}"
              f"  頁數 {detail['pages']}  取得 {detail['found']}"
              f"  新增 {detail['inserted']}  更新 {detail['updated']}")
        if detail["error"]:
            print(f"      └─ {detail['error']}")

    if result["warnings"]:
        print(f"\n提醒（{len(result['warnings'])} 項，不影響其他來源）：")
        for w in result["warnings"][:20]:
            print(f"  ・{w}")
        if len(result["warnings"]) > 20:
            print(f"  ⋯ 另有 {len(result['warnings']) - 20} 項")

    print("-" * 64)
    print(f"完成：{result['success']}/{result['attempted']} 個來源成功"
          f"（略過 {result['skipped']}）"
          f"　新增 {result['inserted']}　更新 {result['updated']}"
          f"　標記跨站重複 {result['marked_duplicate']}")

    if result["errors"]:
        print(f"\n❌ {len(result['errors'])} 個來源失敗：")
        for e in result["errors"]:
            print(f"  ・{e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
