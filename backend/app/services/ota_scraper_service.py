"""
OTA 口碑分析 — 擷取編排

建立日期：2026-08-22
規格書：`docs/SPEC_ota_reviews.md` §6.1、§6.2、§6.5

═══════════════════════════════════════════════════════════════════════════
本檔的四條鐵律
═══════════════════════════════════════════════════════════════════════════
1. **抓到 0 筆一律判 failed，不是「成功，新增 0 則」**
   原型工具（`ota_review_gui.py` 第 799 行）不管抓到幾筆都寫「成功」，
   OTA 改版導致 selector 失效會無聲無息地過去，等到有人發現數字停了
   已經是幾個月後。

2. **單一來源失敗不中斷整批**
   Booking 掛了不該讓 Tripadvisor 也不跑。

3. **warnings 不進 errors**
   「某頁沒抓到／某筆日期解析不了」歸 warnings。`sync_tool.py` 只要
   `errors > 0` 就把該模組標成 partial（黃燈），warning 塞進去會永遠黃燈，
   久了沒人看（CLAUDE.md §9 規則 8）。

4. **不重複加鎖**
   `sync_tool.py` 呼叫本模組時**外層已經套了 `sync_lock`**（第 1004 行）。
   本模組只在 APScheduler／CLI／API 這三條路徑自己加鎖，
   由 `run_all()` 的 `use_lock` 參數控制。重複加同一把 FileLock 會自我死鎖。

═══════════════════════════════════════════════════════════════════════════
對外的三個入口
═══════════════════════════════════════════════════════════════════════════
| 函式 | 呼叫者 | 加鎖 |
|------|--------|------|
| `sync_all_enabled()` | `sync_tool.py` MODULES | 否（外層已加） |
| `run_scheduled_sync()` | `main.py` APScheduler 03:05 | 是 |
| `sync_sources(db, ids)` | API `/sync/run`、CLI | 是（由呼叫端決定） |

⚠️ `sync_all_enabled()` **不接參數**（`sync_tool.py` 是 `func()` 呼叫），
   回傳 dict 必須含 `fetched` / `upserted` / `errors` 三個 key。
"""
from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.ota_review import OtaSource
from app.services import ota_browser as BR
from app.services import ota_parser as PR
from app.services.ota_ingest_service import (finish_sync_log, start_sync_log,
                                             upsert_reviews)
from app.services.ota_normalize import normalize_review

logger = logging.getLogger(__name__)

# 抓到的筆數低於站方公布的這個比例，就發出完整度警告。
# 0.8 而不是 1.0 —— 站方數字通常含被隱藏／審核中的評論，本來就抓不到全部。
COMPLETENESS_MIN_RATIO = 0.8

# 翻頁時「連續幾頁沒有新指紋」就停。防的是翻頁按鈕還在但內容不再變的無限迴圈。
STALE_PAGE_LIMIT = 2
# 每頁之間的隨機停頓（秒）
PAGE_DELAY_MIN = 1.5
PAGE_DELAY_MAX = 3.5


@dataclass
class SourceResult:
    source_id: int
    source_label: str
    status: str = "failed"          # success / partial / captcha / failed / skipped
    pages_fetched: int = 0
    found_count: int = 0
    inserted: int = 0
    updated: int = 0
    marked_duplicate: int = 0
    warnings: list[str] = field(default_factory=list)
    error: str = ""


# ══════════════════════════════════════════════════════════════════════════
# 翻頁擷取
# ══════════════════════════════════════════════════════════════════════════
def _click(driver, element) -> None:
    """用 JS 點擊，避免元素被浮動元件遮住導致 ElementClickIntercepted。"""
    driver.execute_script("arguments[0].click()", element)


def _find_cards(driver, parser):
    """
    找評論卡（用於捲動與翻頁的「數量有沒有增加」判斷）。

    語意與 `ota_parser._select_cards()` 一致，由 parser 的
    `card_selectors_additive` 決定：

      - `False`（預設）**退路鏈** —— 用第一組有命中的。
        Booking 的 `featuredreview` 是完整卡片不存在時的精選片段版，
        與 `review-card` 是同一批評論，加總會重複計算。
      - `True` **版型變體聯集** —— Agoda 的新舊屬性可能同頁並存，
        只取第一組會漏掉另一批（捲動因此提早判定「數量沒增加」而停）。

    ⚠️ 這裡不做巢狀去重（parser 那邊有做）—— 這個函式只用來比較「數量有沒有
       變多」，多算幾個容器不會導致漏採，只會讓捲動多跑一輪，代價可接受。
    """
    from selenium.webdriver.common.by import By

    selectors = getattr(parser, "review_card_selectors", (parser.review_card_selector,))
    if not getattr(parser, "card_selectors_additive", False):
        for selector in selectors:
            found = driver.find_elements(By.CSS_SELECTOR, selector)
            if found:
                return found
        return []

    collected: list = []
    seen: set = set()
    for selector in selectors:
        for node in driver.find_elements(By.CSS_SELECTOR, selector):
            key = getattr(node, "id", None) or id(node)
            if key not in seen:
                seen.add(key)
                collected.append(node)
    return collected


def _open_review_dialog(driver, parser, warnings: list[str]) -> None:
    """
    有些站的公開 HTML 只有精選片段，要點「顯示所有評語」才拿得到完整列表
    （Booking、Expedia）。Tripadvisor 的評論直接在頁面上，`open_all_buttons`
    是空 tuple，本函式會立刻返回。

    找不到按鈕時**不拋例外**——有些版型評論卡本來就在頁面上。
    真正抓不到東西會在最後的 0 筆判定被攔下來。
    """
    from selenium.webdriver.common.by import By

    if not getattr(parser, "open_all_buttons", ()):
        return
    if _find_cards(driver, parser):
        return      # 卡片已經在頁面上，不用點

    for selector in parser.open_all_buttons:
        buttons = driver.find_elements(By.CSS_SELECTOR, selector)
        if not buttons:
            continue
        _click(driver, buttons[0])
        BR.wait_ready(driver, timeout=25)
        if _find_cards(driver, parser):
            return
        warnings.append(f"點了 {selector} 但仍未出現評論卡")

    warnings.append("找不到「顯示所有評語」按鈕，改用頁面上既有內容解析")


def _scroll_to_load(driver, parser) -> None:
    """
    捲動觸發 lazy-load（Expedia／Tripadvisor 需要，Booking 不需要）。

    ⚠️ 停止條件是「**卡片數量不再增加**」而不是「捲到底」——
       有些版型會無限捲動載入，捲到底這件事永遠不會發生。
       同時設硬上限 12 次，避免單一頁面吃掉整個逾時預算。

    ⚠️ **2026-08-22 修正的循環依賴**：停止條件依賴「卡片數量」，
       而卡片數量依賴 selector 正確。selector 錯的時候：

           卡片數 = 0 → 捲一次 → 還是 0 → `current <= previous` → 立刻停

       於是**只捲了一次**，SPA 的評論區根本沒載出來，
       然後 `--diagnose` 回報「所有 selector 都沒命中」——
       但真正的原因是「內容還沒渲染」，不是 selector 寫錯。
       查錯方向會整個歪掉（Expedia 實測踩到）。

       修法：一張卡都找不到時，改用**固定次數盲捲**。
       這種情況本來就沒有可信的停止訊號，捲滿再說。
    """
    if not getattr(parser, "scroll_to_load", False):
        return

    previous = len(_find_cards(driver, parser))

    if previous == 0:
        # ⭐ 沒有可信的停止訊號 —— 固定捲 8 次，讓 SPA 有機會把內容載出來
        for _ in range(8):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(1.0, 1.8))
            if _find_cards(driver, parser):
                break       # 卡片出現了，改走下面的正常邏輯
        previous = len(_find_cards(driver, parser))
        if previous == 0:
            return          # 捲滿了還是沒有，交給呼叫端判定

    for _ in range(12):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(0.8, 1.6))
        current = len(_find_cards(driver, parser))
        if current <= previous:
            break
        previous = current


def _expand_long_reviews(driver, parser, warnings: list[str]) -> None:
    """
    點開「閱讀更多」（Tripadvisor 必需，否則只拿得到截斷的前幾行）。

    ⚠️ 只點**當前可見**的按鈕，且逐一 try/except ——
       點開一個會讓版面重排，後面的元素參照可能失效（StaleElementReference），
       那是正常現象，不該讓整批擷取失敗。
    """
    from selenium.webdriver.common.by import By

    selectors = getattr(parser, "expand_buttons", ())
    if not selectors:
        return

    clicked = 0
    for selector in selectors:
        for button in driver.find_elements(By.CSS_SELECTOR, selector):
            try:
                if not button.is_displayed():
                    continue
                _click(driver, button)
                clicked += 1
            except Exception:       # noqa: BLE001 —— 版面重排導致的失效屬正常
                continue
        if clicked:
            break

    if clicked:
        time.sleep(1.0)     # 等展開後的內容渲染完
    elif selectors:
        # 沒有可展開的按鈕未必是問題（可能留言都很短），記 warning 不記 error
        warnings.append("找不到「閱讀更多」按鈕，長留言可能是截斷版本")


def _goto_next_page(driver, parser) -> bool:
    """點下一頁。回傳是否成功換頁。"""
    from selenium.webdriver.common.by import By

    for selector in parser.next_buttons:
        buttons = driver.find_elements(By.CSS_SELECTOR, selector)
        for button in buttons:
            try:
                if not button.is_enabled() or not button.is_displayed():
                    continue
                if (button.get_attribute("aria-disabled") or "").lower() == "true":
                    continue
                if button.get_attribute("disabled") is not None:
                    continue
                _click(driver, button)
                time.sleep(random.uniform(PAGE_DELAY_MIN, PAGE_DELAY_MAX))
                return True
            except Exception:           # noqa: BLE001 —— 換一個候選 selector 繼續試
                continue
    return False



def collapse_warnings(items: list[str]) -> list[str]:
    """
    把重複的 warning 合併成「訊息 ×N」，順序維持第一次出現的順序。

    ⚠️ 2026-08-23 實測踩到的問題：Agoda 翻了 20 頁，每頁都發一則
       「找不到『閱讀更多』按鈕」，於是 CLI 的前 20 則全被它佔滿，
       真正重要的那則（翻頁為什麼停）被截成「⋯ 另有 1 項」看不到。

       **同一則訊息重複 20 次帶來的資訊量，跟出現 1 次是一樣的。**
       重複次數本身有意義（知道它每頁都發生），所以合併而不是去重。
    """
    seen: dict[str, int] = {}
    for item in items:
        seen[item] = seen.get(item, 0) + 1
    return [msg if n == 1 else f"{msg}（{n} 次）" for msg, n in seen.items()]

def _collect_pages(driver, source: OtaSource, parser, warnings: list[str],
                   max_pages: int | None = None):
    """
    翻頁迴圈。

    三個停止條件（規格書 §6.2），缺一不可：
      a. 已達 `source.max_pages`
      b. 找不到「下一頁」按鈕
      c. **連續 2 頁沒有新增任何未見過的指紋** —— 防的是按鈕還在但內容不再變

    回傳 `(reviews, overall, count, pages_fetched)`。

    ⚠️ `max_pages` 傳了就覆寫 `source.max_pages`（本次執行有效，不寫回設定）。
       第一次回補歷史評論時用 —— 預設 20 頁對 Booking 只有約 200 則。
    """
    limit = max_pages if max_pages and max_pages > 0 else source.max_pages
    _open_review_dialog(driver, parser, warnings)

    collected: dict[str, object] = {}
    overall = count = None
    pages = 0
    stale_pages = 0

    while pages < max(limit, 1):
        pages += 1

        # ⚠️ 順序不可顛倒：先捲動把 lazy-load 的卡片全部載出來，
        #    再點開「閱讀更多」（沒載出來的卡片上沒有按鈕可點），
        #    最後才取 page_source。P2 只有 Booking（兩者都不需要），
        #    P3 的 Expedia／Tripadvisor 少了這兩步會抓到截斷內容。
        _scroll_to_load(driver, parser)
        _expand_long_reviews(driver, parser, warnings)

        html = driver.page_source

        if BR.looks_blocked(html):
            raise BR.CaptchaError(f"第 {pages} 頁被要求人機驗證")

        page_reviews, page_overall, page_count = PR.parse_page(source.platform, html)
        overall = overall if overall is not None else page_overall
        count = count if count is not None else page_count

        before = len(collected)
        for review in page_reviews:
            key = review.external_id or "|".join([
                review.author, str(review.score_raw), review.title,
                review.positive_text, review.negative_text,
                review.comment, review.review_date_text,
            ])
            collected[key] = review
        added = len(collected) - before

        logger.info("[OTA] %s 第 %d 頁：本頁 %d 則、新增 %d 則（累計 %d）",
                    source.hotel_name or source.hotel_code, pages,
                    len(page_reviews), added, len(collected))

        if added == 0:
            stale_pages += 1
            if stale_pages >= STALE_PAGE_LIMIT:
                warnings.append(
                    f"連續 {STALE_PAGE_LIMIT} 頁沒有新評論，提前結束翻頁"
                    f"（已翻 {pages} 頁）"
                )
                break
        else:
            stale_pages = 0

        if not _goto_next_page(driver, parser):
            break
        BR.wait_ready(driver, timeout=15)

    if pages >= limit:
        warnings.append(
            f"已達翻頁上限 {limit} 頁，可能還有更舊的評論沒抓到"
            f"（要抓更多請調高來源設定的「翻頁上限」）"
        )

    return list(collected.values()), overall, count, pages


def _fetch_source(source: OtaSource, warnings: list[str],
                  max_pages: int | None = None):
    """
    取得單一來源的所有評論。

    流程（規格書 §6.1）：
      1. 先試 requests（成本最低，不開瀏覽器）
      2. 需要瀏覽器就依 `resolve_modes()` 決定的順序逐一嘗試
      3. headless 抓不到、可見視窗也開不起來 → HeadlessBlockedError（R1）

    ⚠️ Booking 一律走瀏覽器：公開 HTML 只有精選片段，
       靜態抓取拿到的頁面「看起來正常」但只有 3-5 則，比抓不到更危險。
    """
    parser = PR.get_parser(source.platform)
    if parser is None:
        raise BR.ScraperError(
            f"平台「{source.platform}」尚未實作擷取器"
            f"（目前支援：{'、'.join(sorted(PR.PARSERS))}；其餘平台請用 CSV 匯入）"
        )

    # ── 靜態抓取：**只當成廉價的可達性／封鎖探針**，不拿它的評論當結果 ──
    #
    # ⚠️ 2026-08-22（P3）修正：原本這裡對 prefer_visible=False 的平台，
    #    只要靜態頁解析出「任何」評論就直接 return。P2 沒有非 Booking 的
    #    parser，這段從未執行過；P3 一加 Expedia／Tripadvisor 就會活化，
    #    而那正是一個**靜默漏採**的陷阱：
    #
    #      OTA 的靜態 HTML 通常只含 ld+json 裡的幾則精選評論。
    #      抓到 5 則就 return，看起來「成功」，實際上漏掉了幾百則 ——
    #      跟 Booking 精選片段是同一種病，而且更難發現（不會是 0 筆，
    #      所以 §6.1 的「0 筆判 failed」也攔不住它）。
    #
    #    現在只有 parser 明確宣告 `allow_static_only = True` 才走這條捷徑，
    #    目前三個 parser 一律是 False。探針本身仍有價值：先用 requests
    #    察覺 403／429／CAPTCHA，比起動 Chrome 便宜得多。
    if getattr(parser, "allow_static_only", False):
        html, needs_browser = BR.fetch_static(source.url)
        if not needs_browser:
            reviews, overall, count = PR.parse_page(source.platform, html)
            if reviews:
                return reviews, overall, count, 1

    last_error: Exception | None = None
    modes = BR.resolve_modes(parser.prefer_visible)

    for index, headless in enumerate(modes):
        mode_name = "headless" if headless else "visible"
        try:
            with BR.browser(headless) as driver:
                driver.get(source.url)
                BR.wait_ready(driver)
                BR.assert_usable(driver.page_source)
                result = _collect_pages(driver, source, parser, warnings,
                                        max_pages=max_pages)
                if result[0]:
                    if index > 0:
                        warnings.append(f"headless 抓不到，已改用 {mode_name} 模式成功")
                    return result
                last_error = BR.ScraperError(f"{mode_name} 模式解析結果為空")
        except BR.CaptchaError:
            raise                       # ⚠️ 被擋就別再換模式重試，只會被封更久
        except BR.BrowserUnavailableError as exc:
            last_error = exc
            logger.warning("[OTA] %s 模式無法啟動瀏覽器：%s", mode_name, exc)
        except Exception as exc:        # noqa: BLE001
            last_error = exc
            logger.warning("[OTA] %s 模式擷取失敗：%s", mode_name, exc)

        if index + 1 < len(modes):
            warnings.append(f"{mode_name} 模式未取得評論，改試 {'visible' if headless else 'headless'}")

    # 走到這裡代表所有模式都失敗
    if len(modes) > 1:
        raise BR.HeadlessBlockedError(BR.headless_blocked_message(source.url))
    raise BR.ScraperError(
        f"擷取失敗：{last_error}"
        if last_error else "解析結果為空，OTA 版面可能已更新"
    )


# ══════════════════════════════════════════════════════════════════════════
# 單一來源同步
# ══════════════════════════════════════════════════════════════════════════
def sync_source(
    db: Session,
    source: OtaSource,
    *,
    trigger_type: str = "schedule",
    triggered_by: str | None = None,
    max_pages_override: int | None = None,
) -> SourceResult:
    """擷取一個來源並落地。⚠️ 例外一律吃掉轉成 SourceResult，不往外拋。"""
    label = f"{source.hotel_name or source.hotel_code} / {source.platform}"
    result = SourceResult(source_id=source.id, source_label=label)
    warnings: list[str] = []

    log = start_sync_log(db, source.id, trigger_type, triggered_by)
    db.commit()

    try:
        raw_reviews, overall, site_count, pages = _fetch_source(
            source, warnings, max_pages=max_pages_override)
        result.pages_fetched = pages
        result.found_count = len(raw_reviews)

        # ── ⚠️ 鐵律 1：0 筆一律判 failed ─────────────────────────────
        if not raw_reviews:
            raise BR.ScraperError(
                "解析結果為空，OTA 版面可能已更新"
                "（selector 定義在 ota_parser.py 頂端的常數區）"
            )

        normalized = [
            normalize_review(
                raw, hotel_code=source.hotel_code, platform=source.platform,
                default_scale=source.score_scale,
            )
            for raw in raw_reviews
        ]
        upsert = upsert_reviews(db, source, normalized, sync_log_id=log.id)

        result.inserted = upsert.inserted
        result.updated = upsert.updated
        result.marked_duplicate = upsert.marked_duplicate
        warnings.extend(upsert.warnings)
        result.warnings = warnings

        # 站方公布的總分與評論總數：用來比對抓取完整度
        if overall is not None:
            source.overall_score = overall
            source.overall_score_10 = overall * 2 if source.score_scale == 5 else overall
        if site_count is not None:
            source.review_count_site = site_count

        # ⭐⭐ 抓取完整度檢查（2026-08-23）
        #
        # 原型工具的缺陷是「0 筆也算成功」。那個我在 P2 修掉了 ——
        # 但 2026-08-23 實測 Agoda 踩到它的**變形**：
        #
        #     站方公布 1,906 則，我們抓到 99 則，狀態「✅ 成功」
        #
        # 5% 的完整度顯示成綠色的成功，比顯示失敗還糟 —— 沒有人會去查一個
        # 標著成功的東西。而我們**手上就有站方公布的數字**（ld+json 裡的
        # `review_count_site`），只是從來沒拿它跟實際抓到的比。
        #
        # ⚠️ 這是 warning 不是 error（CLAUDE.md §9 規則 8）——
        #    翻頁抓不完整不代表這次同步沒有價值，抓到的那些仍然要入庫。
        #    但它必須**講出兩個數字**，讓人一眼看出差多少。
        if site_count and len(raw_reviews) < site_count * COMPLETENESS_MIN_RATIO:
            warnings.append(
                f"⚠️ 抓取完整度偏低：站方公布 {site_count:,} 則，"
                f"這次只抓到 {len(raw_reviews):,} 則"
                f"（{len(raw_reviews) / site_count:.0%}，共翻了 {pages} 頁）。"
                f"請看上面的翻頁記錄確認是「找不到下一頁」還是「連續無新增」，"
                f"並檢查來源設定的翻頁上限（目前 {source.max_pages}）。"
                f"第一次回補歷史評論請用 --max-pages 200 覆寫。"
            )

        # ⚠️ 有 warning 不等於失敗。抓到資料就是 success，
        #    warning 只是「有幾筆略過／翻頁提前結束」的提醒。
        result.status = "success"
        # ⭐ 合併重複訊息之後才存 log／回傳，否則畫面上會被同一句話洗版
        warnings = collapse_warnings(warnings)
        result.warnings = warnings
        finish_sync_log(db, log, status="success", pages_fetched=pages,
                        found_count=len(raw_reviews), result=upsert, warnings=warnings)

    except BR.CaptchaError as exc:
        result.status, result.error, result.warnings = "captcha", str(exc), warnings
        finish_sync_log(db, log, status="captcha", pages_fetched=result.pages_fetched,
                        found_count=result.found_count, warnings=warnings,
                        error_message=str(exc))
    except Exception as exc:            # noqa: BLE001 —— 單一來源失敗不可中斷整批
        result.status, result.error, result.warnings = "failed", str(exc), warnings
        logger.exception("[OTA] %s 同步失敗", label)
        finish_sync_log(db, log, status="failed", pages_fetched=result.pages_fetched,
                        found_count=result.found_count, warnings=warnings,
                        error_message=str(exc))

    db.commit()
    return result


# ══════════════════════════════════════════════════════════════════════════
# 批次入口
# ══════════════════════════════════════════════════════════════════════════
def _should_skip_today(source: OtaSource, today: date) -> bool:
    """
    當日已成功同步過就跳過（禮貌性節流，規格書 §6.5）。

    只有 `success` 才算數 —— 失敗或被擋的來源應該讓下一輪再試。
    手動觸發（`sync_sources`）不套用這條，使用者按了就是要跑。
    """
    if not settings.OTA_ONCE_PER_DAY:
        return False
    if source.last_status != "success" or not source.last_sync_at:
        return False
    return source.last_sync_at.date() >= today


def _prepare_platforms(db: Session) -> None:
    """
    補齊內建平台並刷新顯示快取。

    ⚠️ 排程與 CLI 是**獨立 process**，`ota_normalize` 的常數快取裡只有
       內建那五個。不先刷新的話，使用者自建平台（例：Hotels.com）的
       同步紀錄與匯出檔會顯示成代碼 `hotels_com` 而不是「Hotels.com」。
       只影響顯示，但看起來像資料壞掉。

    ⚠️ 刷不到**不擋同步** —— 顯示名稱是加值，資料進不來才是問題。
    """
    from app.services.ota_platform_service import (ensure_builtin_platforms,
                                                   refresh_caches)
    try:
        ensure_builtin_platforms(db)
        db.commit()
        refresh_caches(db)
    except Exception:           # noqa: BLE001
        db.rollback()
        logger.warning("[OTA] 平台快取刷新失敗，顯示名稱可能會是代碼")


def sync_sources(
    db: Session,
    source_ids: list[int] | None = None,
    *,
    trigger_type: str = "manual",
    triggered_by: str | None = None,
    respect_daily_limit: bool = False,
    max_pages_override: int | None = None,
) -> dict:
    """
    同步指定來源（省略 `source_ids` ＝ 所有啟用中的來源）。

    ⚠️ 不自己加鎖 —— 由呼叫端決定（`sync_tool.py` 外層已加，重複加會死鎖）。

    ⚠️ `max_pages_override` **只影響本次執行，不寫回來源設定**。
       用途是第一次回補歷史評論 —— 來源預設 `max_pages=20`，
       Booking 約 10 則/頁、Agoda 約 25 則/頁，
       於是不管站方有幾千則都只抓得到 200~500 則，而且狀態是綠色的「成功」。

       ⚠️ 不寫回設定是刻意的：回補是一次性的事，日常同步不需要翻 100 頁。
          （雖然「連續 2 頁沒有新指紋就停」本來就會讓日常同步提早結束，
            但把一次性的參數持久化仍然是把臨時決定變成永久設定。）
    """
    _prepare_platforms(db)
    stmt = select(OtaSource).where(OtaSource.is_enabled.is_(True))
    if source_ids:
        stmt = stmt.where(OtaSource.id.in_(source_ids))
    stmt = stmt.order_by(OtaSource.sort_order, OtaSource.id)
    sources = db.execute(stmt).scalars().all()

    today = date.today()
    results: list[SourceResult] = []
    skipped = 0
    warnings: list[str] = []

    for index, source in enumerate(sources):
        # ── ⚠️ 沒有擷取器的平台：略過，**不算失敗** ────────────────────
        #
        # 2026-08-22 修正：原本會走進 sync_source() 拋 ScraperError，
        # 於是 status='failed'、進 errors 清單，`sync_tool.py` 看到
        # errors 非空就把整個「OTA 評論擷取」標成 partial（黃燈）。
        #
        # 但「Agoda 還沒有擷取器」不是錯誤，是**設定事實** ——
        # 一個永遠不會消失的黃燈，久了就沒人看了（CLAUDE.md §9 規則 8）。
        # 使用者畫面上看到紅色「失敗」也會以為是壞掉。
        if PR.get_parser(source.platform) is None:
            label = f"{source.hotel_name or source.hotel_code} / {source.platform}"
            logger.info("[OTA] %s 尚無擷取器，略過（請用 HTML 檔或 CSV 匯入）", label)
            warnings.append(
                f"{label}：此平台尚無自動擷取器，略過。"
                f"請改用 CSV 匯入或 --import-html"
            )
            source.last_status = "unsupported"
            source.last_message = (
                f"「{source.platform}」尚無自動擷取器（目前支援："
                f"{'、'.join(sorted(PR.PARSERS))}）。請改用 CSV 匯入或本機 HTML 檔匯入。"
            )
            # ⚠️ 這條路徑跳過了 sync_source()，而 commit 是寫在那裡面的 ——
            #    不自己 commit 的話，狀態只留在 session 裡，畫面上還是舊的紅字。
            db.commit()
            skipped += 1
            continue

        if respect_daily_limit and _should_skip_today(source, today):
            logger.info("[OTA] %s 今日已成功同步，略過", source.hotel_name or source.hotel_code)
            skipped += 1
            continue

        if results:     # 來源之間隨機停頓，避免被判定為攻擊流量
            time.sleep(random.uniform(
                settings.OTA_SOURCE_DELAY_MIN, settings.OTA_SOURCE_DELAY_MAX,
            ))

        results.append(sync_source(
            db, source, trigger_type=trigger_type, triggered_by=triggered_by,
            max_pages_override=max_pages_override,
        ))

    success = [r for r in results if r.status == "success"]
    failed = [r for r in results if r.status in ("failed", "captcha")]

    # ⚠️ errors 只放「整個來源失敗」。warnings 不進去 ——
    #    sync_tool.py 看到 errors > 0 就標 partial（黃燈），
    #    warning 塞進去會永遠黃燈，久了沒人看（§9 規則 8）。
    return {
        "total": len(sources),
        "attempted": len(results),
        "skipped": skipped,
        "success": len(success),
        "fetched": sum(r.found_count for r in results),
        "upserted": sum(r.inserted + r.updated for r in results),
        "inserted": sum(r.inserted for r in results),
        "updated": sum(r.updated for r in results),
        "marked_duplicate": sum(r.marked_duplicate for r in results),
        "errors": [f"{r.source_label}：{r.error}" for r in failed],
        # 「沒有擷取器」的警示（迴圈內收集的）要跟逐筆解析的警示合在一起
        "warnings": warnings + [f"{r.source_label}：{w}" for r in results for w in r.warnings],
        "details": [
            {"source_id": r.source_id, "label": r.source_label, "status": r.status,
             "pages": r.pages_fetched, "found": r.found_count,
             "inserted": r.inserted, "updated": r.updated, "error": r.error}
            for r in results
        ],
    }


def sync_all_enabled() -> dict:
    """
    `sync_tool.py` MODULES 的入口。

    ⚠️ 契約（見 sync_tool.py 第 1003-1017 行）：
       - **不接參數**（以 `func()` 呼叫）
       - 回傳 dict 需含 `fetched` / `upserted` / `errors`
       - `errors` 非空 → 該模組標為 partial（黃燈）
       - 外層**已經套了 `sync_lock`**，本函式不可再加

    ⚠️ 自己開 session：`sync_tool.py` 不會傳 db 進來。
       這是 CLAUDE.md §6「DB Session 一律 Depends(get_db)」的
       「除 sync service 外」例外。
    """
    db = SessionLocal()
    try:
        return sync_sources(
            db, None, trigger_type="schedule", triggered_by="sync_tool",
            respect_daily_limit=True,
        )
    finally:
        db.close()


def run_scheduled_sync() -> dict:
    """
    `main.py` APScheduler（每日 03:05）的入口。

    ⚠️ 與 `sync_all_enabled()` 的差別**只有加不加鎖** ——
       APScheduler 這條路徑沒有外層鎖，必須自己加，
       否則會與 `sync_tool.py` 的手動同步同時寫入 portal.db
       （記憶 project_sync_tool_db_lock_diagnosis）。
    """
    from app.core.sync_lock import sync_lock

    with sync_lock("OTA 評論擷取"):
        return sync_all_enabled()
