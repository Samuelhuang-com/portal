"""
OTA 口碑分析 — 解析層

建立日期：2026-08-22
規格書：`docs/SPEC_ota_reviews.md` §6.2

═══════════════════════════════════════════════════════════════════════════
⚠️ selector 全部集中在本檔頂端的常數區，並標註驗證日期
═══════════════════════════════════════════════════════════════════════════
OTA 改版導致 selector 失效是**幾乎必然會發生**的事（規格書 §3.3 R3）。
把 selector 散在程式碼各處，改版時要一個個找；集中在這裡，
一眼就看得出「這批是哪天驗證過的」。

失效的徵兆是「解析結果為 0 筆」——`ota_scraper_service` 會把它判為
**failed** 而不是「成功，新增 0 則」（原型工具的缺陷）。

═══════════════════════════════════════════════════════════════════════════
解析優先序
═══════════════════════════════════════════════════════════════════════════
1. **`ld+json` 結構化資料**（跨站最穩定，改版最不會動）
2. **DOM 卡片**（`data-testid="review-card"` 那一套）

兩者結果會合併去重。原型工具這段邏輯是對的，原樣搬過來。

四個平台各一個 parser class，共用 `ld+json` 層與 `PARSERS` 註冊表。
加新平台只需要多一個 class 並註冊，`ota_scraper_service` 完全不用改。

selector 驗證狀態（2026-08-22）：

   | 平台 | 驗證程度 |
   |------|---------|
   | Booking | ✅ 完整（原型工具實跑 + 實測 400 則） |
   | **Agoda** | ✅ **完整（實測 headless 通過，依真實 DOM 訂定）** |
   | Tripadvisor | ◐ 部分（3 組命中；站方擋自動存取，走 --import-html） |
   | Expedia | ❌ **未驗證** ——仍是依慣用屬性寫的多組候選 |

⚠️ 未驗證的平台第一次上線前請務必先跑：

       python -m app.services.ota_scraper_cli --diagnose <url> --platform agoda

   （站方擋自動存取時改用 `--diagnose-file <本機另存的 html>`。）
   它會實際開頁面，逐一回報每組 selector 命中幾個節點、抓到什麼樣本值。
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Iterator

from app.services.ota_normalize import SCALE_UNKNOWN, RawReview

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════
# Booking selector（最後驗證：2026-08-22，依原型工具 ota_review_gui.py）
# ⚠️ 改版時只改這一區。每個常數都是「多個候選、由前往後試」。
# ══════════════════════════════════════════════════════════════════════════
BK_REVIEW_CARD = '[data-testid="review-card"]'
BK_FEATURED_CARD = '[data-testid="featuredreview"]'

# 「顯示所有評語」——公開 HTML 只有精選片段，要點開彈窗才有完整列表
BK_OPEN_ALL_BUTTONS = (
    '[data-testid="fr-read-all-reviews"]',
    '[data-testid="review-score-read-all-actionable"]',
)

# 翻頁：Booking 用過好幾種寫法，全部列上
BK_NEXT_BUTTONS = (
    '[data-testid="pagination-next"]',
    'button[aria-label="下一頁"]',
    'button[aria-label="Next page"]',
    '[aria-label="下一頁"]',
    '[aria-label="Next page"]',
)

BK_REVIEWER_NAME = ('[data-testid="reviewer-name"]', '.bui-avatar-block__title', '.reviewer_name')
BK_REVIEW_AVATAR = '[data-testid="review-avatar"]'
BK_SCORE = ('[data-testid="review-score"]', '.review-score-badge', '.bui-review-score__badge')
BK_TITLE = ('[data-testid="review-title"]', '.c-review-block__title')
BK_POSITIVE = ('[data-testid="review-positive-text"]', '.review_pos')
BK_NEGATIVE = ('[data-testid="review-negative-text"]', '.review_neg')
BK_FEATURED_TEXT = ('[data-testid="featuredreview-text"]', '.c-review__body')
BK_DATE = ('[data-testid="review-date"]', '.c-review-block__date', '.review_item_date')
BK_STAY_DATE = ('[data-testid="review-stay-date"]', '.review_staydate')
BK_ROOM_TYPE = ('[data-testid="review-room-name"]', '.room_info_heading')
BK_TRAVELER_TYPE = ('[data-testid="review-traveler-type"]',)
BK_NUM_NIGHTS = ('[data-testid="review-num-nights"]',)

# 站方公布的總分與評論總數（用來比對抓取完整度）
BK_OVERALL = (
    '[data-testid="review-score-right-component"]',
    '.review-score-badge',
    '.bui-review-score__badge',
    '[itemprop="ratingValue"]',
    'meta[itemprop="ratingValue"]',
)
BK_REVIEW_COUNT = ('[itemprop="reviewCount"]', 'meta[itemprop="reviewCount"]')

# 「N 晚」
_RE_NIGHTS = re.compile(r"(\d+)\s*(?:晚|night)", re.IGNORECASE)

# ══════════════════════════════════════════════════════════════════════════
# Tripadvisor selector
#
# 2026-08-22 對真實頁面實測（tripadvisor.com.tw / Hanns House），
# 以下三組**已驗證命中**，其餘仍為多版型候選：
#   ✅ 評論卡   [data-test-target="HR_CC_CARD"]           命中 10 張
#   ✅ 下一頁   [data-smoke-attr="pagination-next-arrow"] 命中 1
#   ✅ 評分     [data-automation="bubbleRatingValue"]     命中 10
#
# ⚠️ **headless 一定被擋**（實測回 1,582 字元攔截頁），可見視窗才拿得到
#    937,440 字元的完整頁面。因此 `prefer_visible = True`。
# ══════════════════════════════════════════════════════════════════════════
TA_REVIEW_CARD = (
    '[data-test-target="HR_CC_CARD"]',    # ✅ 2026-08-22 實測命中，放第一順位
    '[data-automation="reviewCard"]',     # 新版（本次未命中，保留供其他站台版型）
    'div[data-reviewid]',
    '.review-container',                  # 舊版
)
TA_NEXT_BUTTONS = (
    '[data-smoke-attr="pagination-next-arrow"]',
    'a[data-page-number][aria-label*="下一頁"]',
    'a.nav.next',
    '[aria-label="下一頁"]',
    '[aria-label="Next page"]',
)
# 「閱讀更多」——不點開只拿得到截斷的前幾行
TA_EXPAND_BUTTONS = (
    '[data-automation="readMoreButton"]',
    '.taLnk.ulBlueLinks',
    'span.taLnk',
)
TA_TITLE = ('[data-automation="reviewTitle"]', '.noQuotes', 'a.title', '.quote')
TA_TEXT = ('[data-automation="reviewText"]', '.partial_entry', 'q.QewHA', '.prw_reviews_text_summary_hsx')
TA_AUTHOR = ('[data-automation="reviewUsername"]', '.info_text div', '.memberOverlayLink', 'a.ui_header_link')
TA_DATE = ('[data-automation="reviewDate"]', '.ratingDate', '.prw_reviews_stay_date_hsx', '.euPKI')
TA_TRIP_TYPE = ('[data-automation="reviewTripType"]', '.trip_type', '.recommend-titleInline')
TA_OVERALL = (
    '[data-automation="bubbleRatingValue"]',
    '.ui_poi_review_rating .ui_bubble_rating',
    '[itemprop="ratingValue"]',
)
TA_REVIEW_COUNT = ('[data-automation="reviewCount"]', '[itemprop="reviewCount"]', '.reviews_header_count')

# 舊版把評分編碼在 CSS class 裡的泡泡數：`bubble_40` = 4.0 顆（滿分 5）。
# 2026-08-22 實測**現行版型已無此 class**（命中 0），但保留供舊頁面。
_RE_BUBBLE = re.compile(r"bubble_(\d{2})")

# 新版把評分寫成文字。⚠️ 實測台灣站的實際格式是「5 分 (共 5 分)」，
#    不是原先假設的「4.0 分，滿分 5 分」—— 卡片文字範例：
#      Maggie C 已於 2026年3月 發表一則評論 … 12 人推薦 5 分 (共 5 分) 台北
#    另含英文版與斜線版，全部列上由前往後試。
_RE_OF_FIVE = re.compile(
    r"(\d(?:\.\d)?)\s*分\s*[（(]\s*共\s*5\s*分\s*[）)]"      # 5 分 (共 5 分)  ← 台灣站實測
    r"|(\d(?:\.\d)?)\s*分[，,]?\s*滿分\s*5"                   # 4.0 分，滿分 5 分
    r"|(\d(?:\.\d)?)\s*of\s*5"                                # 4.0 of 5 bubbles
    r"|(\d(?:\.\d)?)\s*/\s*5",                                # 4.0/5
    re.IGNORECASE,
)
# ✅ 2026-08-22 實測命中（10 個節點，值如 "4.0"）
TA_BUBBLE_VALUE = ('[data-automation="bubbleRatingValue"]',)


# ══════════════════════════════════════════════════════════════════════════
# Expedia selector（P3，2026-08-22）
# ⚠️ 同上，未經真實頁面驗證，請先用 --diagnose 確認。
# ══════════════════════════════════════════════════════════════════════════
EX_REVIEW_CARD = (
    '[data-stid="review-item"]',
    'article[itemprop="review"]',
    '[data-stid="property-reviews-list"] article',
    '.uitk-card-content-section[itemprop="review"]',
)
EX_NEXT_BUTTONS = (
    '[data-stid="reviews-next-page"]',
    'button[aria-label="下一頁"]',
    'button[aria-label="Next page"]',
    '[data-stid="pagination-next"]',
)
# Expedia 的評論列表要點「查看所有評論」才展開
EX_OPEN_ALL_BUTTONS = (
    '[data-stid="reviews-link"]',
    '[data-stid="see-all-reviews"]',
    'button[data-stid="open-review-list"]',
)
EX_EXPAND_BUTTONS = ('[data-stid="review-see-more"]', 'button[aria-label*="更多"]')
EX_AUTHOR = ('[data-stid="review-author"]', '[itemprop="author"]', '.uitk-text.uitk-type-medium')
EX_TITLE = ('[data-stid="review-title"]', '[itemprop="name"]', 'h3.uitk-heading')
EX_SCORE = ('[data-stid="review-rating"]', '[itemprop="ratingValue"]', '.uitk-badge-base-text')
EX_POSITIVE = ('[data-stid="review-liked"]', '[data-stid="positive-review-text"]')
EX_NEGATIVE = ('[data-stid="review-disliked"]', '[data-stid="negative-review-text"]')
EX_TEXT = ('[data-stid="review-text"]', '[itemprop="reviewBody"]', '.uitk-expando-peek-inner')
EX_DATE = ('[data-stid="review-date"]', '[itemprop="datePublished"]', '.uitk-text.uitk-type-200')
EX_TRIP_TYPE = ('[data-stid="review-trip-type"]',)
EX_STAY = ('[data-stid="review-stay-duration"]',)
EX_OVERALL = ('[data-stid="property-rating-value"]', '[itemprop="ratingValue"]')
EX_REVIEW_COUNT = ('[data-stid="property-review-count"]', '[itemprop="reviewCount"]')

# ⚠️ **Expedia 兩種版型並存**：有的頁面「9.2/10」、有的「4.6/5」。
#    所以抓分數時**必須連分母一起抓**，抓不到分母寧可留白也不猜
#    —— 猜錯會讓整間飯店的平均分歪掉，而且事後看不出來（規格書 §5.2）。
_RE_SCORE_WITH_SCALE = re.compile(r"(\d+(?:\.\d)?)\s*/\s*(10|5)\b")
_RE_SCALE_HINT = re.compile(r"滿分\s*(10|5)|out\s+of\s+(10|5)", re.IGNORECASE)

# ══════════════════════════════════════════════════════════════════════════
# Agoda selector
#
# 2026-08-22 對真實頁面實測（agoda.com/zh-tw/hanns-house），**headless 即通過**
# （1,002,733 字元）。以下依實際 DOM 結構訂定。
#
# ⭐ 實測發現的關鍵結構：
#    · 卡片本體 class 是 `Review-comment`（5 張＝5 則評論）
#    · **業者回覆 `<div class="Review-response">` 也帶
#      `data-element-name="review-comment"`** —— 所以那組 selector 命中 10 個，
#      多出來的 5 個是飯店自己的罐頭回覆，必須排除（見 AG_CARD_EXCLUDE）
#    · 旅客資訊統一用 `data-info-type="..."`：
#      reviewer-name / group-name / room-type / stay-detail
#    · 標題與留言用 `data-testid`：review-title / review-comment
#    · 分數在 styled-components 產生的 class 裡（`sc-aXZVg ...`，**不穩定**），
#      改用「卡片文字開頭就是分數」的特性擷取（見 _agoda_score）
# ══════════════════════════════════════════════════════════════════════════
AG_REVIEW_CARD = (
    '.Review-comment',                          # ✅ 實測命中 5（真正的評論卡）
    '[data-element-name="review-comment"]',     # ⚠️ 也會命中業者回覆，靠 exclude 剔除
    '[data-selenium="review-comment"]',
    '[data-element-name="guest-review-item"]',
)
# ⭐ 業者回覆不是客人評論。混進去會把情緒分析與主題統計整個帶歪 ——
#    那些全是「感謝您選擇入住…期待您再度光臨」的正面客套話。
AG_CARD_EXCLUDE = ('.Review-response',)

AG_NEXT_BUTTONS = (
    '[data-element-name="review-paginator-next"]',   # ✅ 實測命中
    'button[aria-label="下一頁"]',                    # ✅ 實測命中
    '[data-selenium="paginator-next-btn"]',
    '.Review-paginator-nextBtn',
    'button[aria-label="Next"]',
)
# 實測未命中 —— Agoda 的留言似乎不截斷。保留候選，找不到只記 warning。
AG_EXPAND_BUTTONS = (
    '[data-element-name="review-comment-show-more"]',
    '.Review-comment-bodyShowMore',
    'button[data-selenium="review-show-more"]',
)

# ⚠️ `.Review-comment-reviewer` 會命中四個 data-info-type 區塊（暱稱／旅客類型／
#    房型／入住資訊），所以每個欄位都要用 data-info-type 精確定位，
#    不能只靠 class。
AG_AUTHOR = (
    '[data-info-type="reviewer-name"] strong',      # ✅ 實測命中，值 "Sue-Ann"
    '.Review-comment-reviewer strong',
    '[data-element-name="review-comment-reviewer-name"]',
    '[data-selenium="reviewer-name"]',
)
AG_REVIEWER_BLOCK = ('[data-info-type="reviewer-name"]',)   # "Sue-Ann （來自 日本 ）"
AG_TRAVELER_TYPE = (
    '[data-info-type="group-name"]',                # ✅ 實測，值 "團體旅遊"
    '[data-element-name="review-comment-traveller-type"]',
)
AG_ROOM_TYPE = (
    '[data-info-type="room-type"]',                 # ✅ 實測，值 "市景頂級房(大床)"
    '[data-element-name="review-comment-room-type"]',
)
AG_STAY = (
    '[data-info-type="stay-detail"]',               # ✅ 實測，值 "入住1晚（2026年3月）"
    '[data-element-name="review-comment-stay-detail"]',
)
AG_TITLE = (
    '[data-testid="review-title"]',                 # ✅ 實測，值 "“小廚房和無限暢飲飲水”"
    '.Review-comment-bodyTitle',
    '[data-element-name="review-comment-title"]',
)
AG_TEXT = (
    '[data-testid="review-comment"]',               # ✅ 實測
    '[data-selenium="comment"]',
    '.Review-comment-bodyText',                     # ✅ 實測命中 5
    '[data-element-name="review-comment-body"]',
)
AG_DATE = (
    '.Review-statusBar-left',                       # ✅ 實測，值 "評鑑日期：2026年3月20日"
    '[data-element-name="review-comment-date"]',
    '[data-selenium="review-date"]',
)
# 少數版型才有的「喜歡／不喜歡」分區（本次未命中，保留）
AG_POSITIVE = ('[data-element-name="review-comment-positive"]', '.Review-comment-positive')
AG_NEGATIVE = ('[data-element-name="review-comment-negative"]', '.Review-comment-negative')

# 分數的 class 是 styled-components 雜湊（`sc-aXZVg Typographystyled__...`），
# 每次建置都會變，不能拿來當 selector。保留幾個穩定候選，主要靠 _agoda_score()。
AG_SCORE = (
    '[data-element-name="review-comment-score"]',
    '[data-selenium="review-score"]',
    '.Review-comment-leftScore',
)

# ⚠️ 站方總分與評論數**改由 ld+json 提供**（實測 8.9 / 1906，正確）。
#    先前用的 `[data-selenium="hotel-header-review-score"]` 抓到的是
#    「9.4 超棒 位置得分」—— 那是**位置子評分**不是總分，會讓來源清單的
#    「站方公布」欄顯示錯誤數字。寧可留空讓 ld+json 接手。
AG_OVERALL: tuple[str, ...] = ()
AG_REVIEW_COUNT: tuple[str, ...] = ()

# 「（來自 日本 ）」→ 日本
_RE_AG_COUNTRY = re.compile(r"[（(]\s*來自\s*([^）)]+?)\s*[）)]")
# 「評鑑日期：2026年3月20日」→ 2026年3月20日
#
# ⚠️ 必須錨定「評鑑日期」四個字。卡片裡還有業者回覆的
#    「回覆日期2026年3月27日 星期五」—— 直接掃日期會抓到錯的那個
#    （而且回覆日期永遠晚於評鑑日期，會讓月度趨勢整批往後偏）。
_RE_AG_REVIEW_DATE = re.compile(r"評鑑日期\s*[:：]?\s*(\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日)")
# 卡片文字開頭的分數：「8.8 很讚 Sue-Ann …」
_RE_AG_LEADING_SCORE = re.compile(r"^\s*(10(?:\.0)?|\d(?:\.\d)?)\s")


# 分數：0-10，容許一位小數
_RE_SCORE = re.compile(r"(?<!\d)(10(?:\.0)?|[0-9](?:\.\d)?)(?!\d)")


# ══════════════════════════════════════════════════════════════════════════
# 共用小工具
# ══════════════════════════════════════════════════════════════════════════
def _soup(html: str):
    """⚠️ bs4 在函式內 import：沒裝爬蟲相依的機器仍要能 import app.main。"""
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise RuntimeError(
            "未安裝 beautifulsoup4。請執行：pip install -r backend/requirements.txt"
        ) from exc
    try:
        return BeautifulSoup(html, "lxml")
    except Exception:                   # noqa: BLE001 —— 沒裝 lxml 就退回標準解析器
        return BeautifulSoup(html, "html.parser")


def _text(node) -> str:
    return " ".join(node.get_text(" ", strip=True).split()) if node else ""


def _first_text(scope, selectors: tuple[str, ...]) -> str:
    for selector in selectors:
        node = scope.select_one(selector)
        if node:
            text = _text(node)
            if text:
                return text
    return ""


def _select_any(scope, selectors: tuple[str, ...]):
    """
    依序試多組 selector，回傳**第一組有命中的**結果（退路鏈語意）。

    ⚠️ 不是把所有命中結果加起來 —— 有些 selector 是「前一個沒命中才用」的退路，
       例如 Booking 的 `featuredreview` 是**完整卡片不存在時**的精選片段版本，
       它與 `review-card` 指的是同一批評論的兩種呈現。加總會把同一則評論
       的截斷版也收進來，變成重複。

    ⚠️ 若某站的多組 selector 是**可並存的版型變體**（不是退路），
       請改用 `_select_cards(..., additive=True)`。
    """
    for selector in selectors:
        found = scope.select(selector)
        if found:
            return found
    return []


def _select_cards(scope, selectors: tuple[str, ...], additive: bool = False,
                  exclude: tuple[str, ...] = ()):
    """
    取評論卡。`additive` 決定多組 selector 之間的語意：

    | `additive` | 語意 | 適用 |
    |------------|------|------|
    | `False`（預設） | **退路鏈** —— 用第一組有命中的 | Booking（`review-card` → `featuredreview`） |
    | `True` | **版型變體聯集** —— 全部收集後去重 | Agoda（`data-element-name` 新版與 `data-selenium` 舊版可能同頁並存） |

    `exclude` 是「長得像卡片但不是評論」的 selector（例如 Agoda 的業者回覆）。

    ⚠️ `additive=True` 時會做三層過濾，缺一不可：

      1. **排除清單** —— 先剔掉 `exclude` 命中的節點。
         ⭐ Agoda 實測：業者回覆 `<div class="Review-response">` **也帶
         `data-element-name="review-comment"`**，5 則評論會變成 10 張卡，
         另外 5 張是飯店自己寫的罐頭回覆。那些全是正面客套話，
         混進去會把情緒分析與主題統計整個帶歪。

      2. **同一節點被多組 selector 命中** → 依物件識別去重

      3. **容器判定** —— 若某節點**包含 2 個以上**其他命中節點，它是容器不是卡片。
         ⚠️ 這條的門檻是「≥2」而不是「≥1」，這個差別很關鍵：

           · 真正的容器會裝很多張卡片（≥2）
           · 但**一張卡片可能巢狀包含一個子項**（Agoda 的評論卡包著業者回覆）

         初版寫成「有任何子孫命中就當容器、只留最內層」，套到 Agoda 會
         **把真正的評論卡丟掉、只留下飯店的回覆** —— 資料完全相反。
    """
    if not additive:
        return _select_any(scope, selectors)

    excluded: set[int] = set()
    for selector in (exclude or ()):
        for node in scope.select(selector):
            excluded.add(id(node))

    collected: list = []
    seen: set[int] = set()
    for selector in selectors:
        for node in scope.select(selector):
            if id(node) in excluded or id(node) in seen:
                continue
            seen.add(id(node))
            collected.append(node)

    if len(collected) <= 1:
        return collected

    kept_ids = {id(n) for n in collected}
    result = []
    for node in collected:
        nested = sum(1 for d in node.find_all(True) if id(d) in kept_ids)
        if nested < 2:          # 0 或 1 個 → 是卡片（1 個多半是巢狀的子項）
            result.append(node)
    return result


def _all_text(scope, selectors: tuple[str, ...]) -> str:
    """同一組 selector 可能命中多個節點（例如分段的留言），串起來。"""
    parts: list[str] = []
    for selector in selectors:
        for node in scope.select(selector):
            text = _text(node)
            if text and text not in parts:
                parts.append(text)
    return "\n".join(parts)


def _number(text: str) -> float | None:
    if not text:
        return None
    m = _RE_SCORE.search(text.replace(",", ""))
    return float(m.group(1)) if m else None


def _int_or_none(text: str) -> int | None:
    if not text:
        return None
    m = re.search(r"\d+", text.replace(",", ""))
    return int(m.group()) if m else None


def _walk_json(value: Any) -> Iterator[dict]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_json(child)


def parse_ld_json(html: str) -> tuple[list[RawReview], float | None, int | None]:
    """
    解析 `<script type="application/ld+json">`。

    這是**跨站最穩定**的來源 —— 它是給搜尋引擎看的結構化資料，
    改版時比 DOM class 名稱穩定得多。原型工具這段邏輯是對的，原樣搬過來。

    回傳 `(reviews, overall_score, review_count)`。
    """
    soup = _soup(html)
    reviews: list[RawReview] = []
    overall: float | None = None
    count: int | None = None

    for tag in soup.select('script[type="application/ld+json"]'):
        try:
            payload = json.loads(tag.string or tag.get_text())
        except (json.JSONDecodeError, TypeError):
            continue

        for item in _walk_json(payload):
            rating = item.get("aggregateRating")
            if isinstance(rating, dict):
                overall = _number(str(rating.get("ratingValue", ""))) or overall
                raw_count = rating.get("reviewCount") or rating.get("ratingCount")
                if raw_count:
                    count = _int_or_none(str(raw_count)) or count

            if str(item.get("@type", "")).lower() == "review":
                author = item.get("author", "")
                if isinstance(author, dict):
                    author = author.get("name", "")
                item_rating = item.get("reviewRating", {})
                score = (
                    _number(str(item_rating.get("ratingValue", "")))
                    if isinstance(item_rating, dict) else None
                )
                # ld+json 有 bestRating 就能判定分制，沒有就交給呼叫端用平台預設
                scale = None
                if isinstance(item_rating, dict) and item_rating.get("bestRating"):
                    scale = _int_or_none(str(item_rating["bestRating"]))

                reviews.append(RawReview(
                    author=str(author),
                    score_raw=score,
                    score_scale=scale,
                    title=str(item.get("name", "")),
                    comment=str(item.get("reviewBody", "")),
                    review_date_text=str(item.get("datePublished", "")),
                    external_id=str(item.get("@id", "")),
                    raw={"source": "ld+json"},
                ))

    return reviews, overall, count


# ══════════════════════════════════════════════════════════════════════════
# Booking
# ══════════════════════════════════════════════════════════════════════════
class BookingParser:
    """
    Booking.com 評論頁。

    ⚠️ Booking 對無頭瀏覽器的偵測較嚴，`prefer_visible = True`
       （auto 模式下 headless 失敗會自動退可見視窗，見 `ota_browser.resolve_modes`）。
    """

    platform = "booking"
    # 2026-08-22 P2 實測：headless 即通過。auto 模式下兩種都會試，
    # 這個旗標只決定先試哪個 —— 先試 headless 較快。
    # （與 Tripadvisor 相反，那家 headless 必被擋。）
    prefer_visible = False
    allow_static_only = False   # ⚠️ 靜態頁只有精選片段，不可當成全部
    default_scale = 10

    # ── 給 scraper_service 用的瀏覽器操作 ──────────────────────────────
    review_card_selector = BK_REVIEW_CARD
    # ⚠️ 退路鏈不是聯集：featuredreview 是**完整卡片不存在時**的精選片段版，
    #    與 review-card 指的是同一批評論。聯集會把截斷版也收進來變成重複。
    review_card_selectors = (BK_REVIEW_CARD, BK_FEATURED_CARD)
    card_selectors_additive = False
    open_all_buttons = BK_OPEN_ALL_BUTTONS
    next_buttons = BK_NEXT_BUTTONS
    expand_buttons: tuple[str, ...] = ()    # Booking 不需要展開「閱讀更多」
    scroll_to_load = False                  # 評論在彈窗內分頁，不是 lazy-load

    @staticmethod
    def parse_cards(html: str) -> list[RawReview]:
        """
        從 DOM 卡片解析。

        ⚠️ **正評與負評分別存成兩欄，不可用 `\\n` 併成一欄**。
           原型工具第 460 行把它們黏回去，導致主題分析拿不到極性
           （「早餐很好但隔音很差」該算哪一邊？）。
        """
        soup = _soup(html)
        cards = soup.select(BK_REVIEW_CARD)
        if not cards:
            # 沒點開彈窗時只看得到精選片段。仍然解析，但這批沒有分數，
            # 之後有完整卡片時會被同一個指紋覆蓋掉。
            cards = soup.select(BK_FEATURED_CARD)

        reviews: list[RawReview] = []
        for card in cards:
            author = _first_text(card, BK_REVIEWER_NAME)
            if not author:
                # 有些版型把暱稱放在 avatar 區塊的第一行
                avatar = card.select_one(BK_REVIEW_AVATAR)
                if avatar:
                    lines = [ln.strip() for ln in avatar.get_text("\n").splitlines() if ln.strip()]
                    if lines:
                        author = lines[0]

            positive = _all_text(card, BK_POSITIVE)
            negative = _all_text(card, BK_NEGATIVE)
            featured = _all_text(card, BK_FEATURED_TEXT)
            title = _first_text(card, BK_TITLE)

            # 精選片段沒有正負分離，放 comment
            comment = featured if (featured and not positive and not negative) else ""

            if not (positive or negative or comment or title):
                continue        # 整張卡沒有任何文字，多半是版面容器不是評論

            reviews.append(RawReview(
                author=author,
                score_raw=_number(_first_text(card, BK_SCORE)),
                score_scale=10,
                title=title,
                positive_text=positive,
                negative_text=negative,
                comment=comment,
                review_date_text=_first_text(card, BK_DATE),
                stay_date_text=_first_text(card, BK_STAY_DATE),
                room_type=_first_text(card, BK_ROOM_TYPE),
                traveler_type=_first_text(card, BK_TRAVELER_TYPE),
                nights=_int_or_none(_first_text(card, BK_NUM_NIGHTS)) or _nights_from(card),
                raw={"source": "dom"},
            ))
        return reviews

    @staticmethod
    def parse_summary(html: str) -> tuple[float | None, int | None]:
        """站方公布的總分與評論總數。"""
        soup = _soup(html)

        overall: float | None = None
        for selector in BK_OVERALL:
            node = soup.select_one(selector)
            if node:
                overall = _number(node.get("content", "") or _text(node))
                if overall is not None:
                    break

        count: int | None = None
        for selector in BK_REVIEW_COUNT:
            node = soup.select_one(selector)
            if node:
                count = _int_or_none(node.get("content", "") or _text(node))
                if count is not None:
                    break

        return overall, count


def _nights_from(card) -> int | None:
    """從整張卡的文字裡撈「N 晚」，當作 selector 失效時的保險。"""
    m = _RE_NIGHTS.search(_text(card))
    return int(m.group(1)) if m else None




# ══════════════════════════════════════════════════════════════════════════
# Tripadvisor
# ══════════════════════════════════════════════════════════════════════════
def _first_group(match) -> float | None:
    """`_RE_OF_FIVE` 有多個候選 group，取第一個有值的。"""
    if not match:
        return None
    for value in match.groups():
        if value:
            return float(value)
    return None


def _bubble_score(card) -> float | None:
    """
    Tripadvisor 的評分（滿分 5）。

    四種來源依序試 —— 版型換過好幾代，不能只賭一種：

    | 順序 | 來源 | 實測（2026-08-22 台灣站） |
    |------|------|--------------------------|
    | 1 | `[data-automation="bubbleRatingValue"]` 的文字 | ✅ 命中，值如 "4.0" |
    | 2 | class 編碼 `bubble_40` → 4.0 | ❌ 現行版型已無此 class |
    | 3 | aria-label／title／alt 文字 | 未命中，保留 |
    | 4 | **整張卡的文字**（「5 分 (共 5 分)」） | 保險 —— 分數不一定在自己的節點上 |
    """
    # 1) 專用節點（實測有效）
    for selector in TA_BUBBLE_VALUE:
        node = card.select_one(selector)
        if node:
            value = _number(_text(node) or node.get("content", ""))
            if value is not None and value <= 5:
                return value

    # 2) 舊版 class 編碼：bubble_40 → 4.0
    for node in card.select('[class*="bubble_"]'):
        m = _RE_BUBBLE.search(" ".join(node.get("class", [])))
        if m:
            return int(m.group(1)) / 10

    # 3) aria-label / title / alt
    for node in card.select('[aria-label], [title], svg[aria-label], img[alt]'):
        for attr in ("aria-label", "title", "alt"):
            value = _first_group(_RE_OF_FIVE.search(node.get(attr, "") or ""))
            if value is not None:
                return value

    # 4) ⚠️ 整張卡的文字 —— 實測「5 分 (共 5 分)」就散在卡片文字裡，
    #    不在任何帶 aria-label 的節點上。沒有這一層會整批抓不到分數。
    value = _first_group(_RE_OF_FIVE.search(_text(card)))
    if value is not None:
        return value

    # 5) itemprop（只在 <=5 時採信，避免誤吃 10 分制）
    node = card.select_one('[itemprop="ratingValue"]')
    if node:
        value = _number(node.get("content", "") or _text(node))
        if value is not None and value <= 5:
            return value
    return None


class TripadvisorParser:
    """
    Tripadvisor 評論頁。

    三個與 Booking 不同的地方：
      1. **5 分制** —— `score_scale = 5`，`ota_normalize` 會 ×2 換算成 10 分制
      2. **沒有正負評分離** —— 只有單一段落，放 `comment`，
         `positive_text` / `negative_text` 留空字串
      3. **日期多半只到年月** —— `parse_review_date()` 會補為該月 01 日
         並在 `raw_json` 標記 `date_precision="month"`（規格書 §5.4）
    """

    platform = "tripadvisor"
    # ⚠️ 2026-08-22 實測：headless 一定被擋（回 1,582 字元攔截頁），
    #    可見視窗才拿得到 937,440 字元的完整頁面。
    #    先前假設「這家比 Booking 寬鬆」是錯的，剛好相反。
    prefer_visible = True
    allow_static_only = False   # ⚠️ 靜態頁只有 ld+json 幾則，不可當成全部
    default_scale = 5

    review_card_selector = TA_REVIEW_CARD[0]
    review_card_selectors = TA_REVIEW_CARD
    card_selectors_additive = False     # 新舊版型是退路鏈，實測只有一種會命中
    open_all_buttons: tuple[str, ...] = ()      # 評論直接在頁面上，不需要點開彈窗
    next_buttons = TA_NEXT_BUTTONS
    expand_buttons = TA_EXPAND_BUTTONS          # 「閱讀更多」
    scroll_to_load = True                       # lazy-load，要捲動觸發

    @staticmethod
    def parse_cards(html: str) -> list[RawReview]:
        soup = _soup(html)
        cards = _select_any(soup, TA_REVIEW_CARD)

        reviews: list[RawReview] = []
        for card in cards:
            body = _first_text(card, TA_TEXT)
            title = _first_text(card, TA_TITLE)
            if not (body or title):
                continue

            reviews.append(RawReview(
                author=_first_text(card, TA_AUTHOR),
                score_raw=_bubble_score(card),
                score_scale=5,                  # 這家固定 5 分制，不像 Expedia 有兩種
                title=title,
                positive_text="",               # 無正負分離
                negative_text="",
                comment=body,
                review_date_text=_first_text(card, TA_DATE),
                traveler_type=_first_text(card, TA_TRIP_TYPE),
                external_id=card.get("data-reviewid", "") or "",
                raw={"source": "dom", "platform": "tripadvisor"},
            ))
        return reviews

    @staticmethod
    def parse_summary(html: str) -> tuple[float | None, int | None]:
        soup = _soup(html)

        overall: float | None = None
        for selector in TA_OVERALL:
            node = soup.select_one(selector)
            if not node:
                continue
            m = _RE_BUBBLE.search(" ".join(node.get("class", [])))
            if m:
                overall = int(m.group(1)) / 10
                break
            overall = _number(node.get("content", "") or _text(node))
            if overall is not None:
                break

        count: int | None = None
        for selector in TA_REVIEW_COUNT:
            node = soup.select_one(selector)
            if node:
                count = _int_or_none(node.get("content", "") or _text(node))
                if count is not None:
                    break

        return overall, count


# ══════════════════════════════════════════════════════════════════════════
# Expedia
# ══════════════════════════════════════════════════════════════════════════
def _expedia_score(card) -> tuple[float | None, int | None]:
    """
    Expedia 的分數與分制。

    ⚠️ **必須連分母一起抓**。Expedia 兩種版型並存：有的頁面是「9.2/10」、
       有的是「4.6/5」。只抓到分子就當 10 分制，會讓 5 分制的評論被記成
       「4.6 分（滿分 10）」——一間好飯店瞬間變成差評，而且事後看不出來。

    回傳 `(score, scale)`：
      - 找到分母      → `(9.0, 10)` 或 `(4.5, 5)`
      - 有分數沒分母  → `(4.6, SCALE_UNKNOWN)` ← **不可回 None**，
                         None 會被 normalize 當成「沒判斷」而套平台預設 10
      - 連分數都沒有  → `(None, None)`

    `SCALE_UNKNOWN` 會讓 `ota_normalize` 記 warning 並讓 `score_10` 留 NULL。
    寧可留白也不猜（規格書 §5.2）。
    """
    # 1) 「9.2/10」這種完整寫法（最可靠）
    for selector in EX_SCORE:
        for node in card.select(selector):
            text = _text(node) or node.get("content", "")
            m = _RE_SCORE_WITH_SCALE.search(text)
            if m:
                return float(m.group(1)), int(m.group(2))

    # 2) 整張卡的文字裡找「N/10」或「N/5」
    card_text = _text(card)
    m = _RE_SCORE_WITH_SCALE.search(card_text)
    if m:
        return float(m.group(1)), int(m.group(2))

    # 3) 分子與分母分開寫：「9.2」+「滿分 10」
    m_hint = _RE_SCALE_HINT.search(card_text)
    scale = int(m_hint.group(1) or m_hint.group(2)) if m_hint else None

    # 4) schema.org 的 bestRating
    best = card.select_one('[itemprop="bestRating"]')
    if best is not None and scale is None:
        scale = _int_or_none(best.get("content", "") or _text(best))

    score = None
    for selector in EX_SCORE:
        node = card.select_one(selector)
        if node:
            score = _number(node.get("content", "") or _text(node))
            if score is not None:
                break

    if score is None:
        return None, None               # 連分數都沒有，交給平台預設沒差
    if scale is None:
        return score, SCALE_UNKNOWN     # ⚠️ 有分數卻沒分母 —— 這筆不可猜
    return score, scale


class ExpediaParser:
    """
    Expedia 評論頁。

    ⚠️ 這家最麻煩的是**分制不固定**（見 `_expedia_score`）。
       其餘與 Booking 類似：有 Liked／Disliked 兩區，對應正評／負評。
    """

    platform = "expedia"
    prefer_visible = False
    allow_static_only = False
    default_scale = 10          # 只是 fallback，逐筆偵測結果優先

    review_card_selector = EX_REVIEW_CARD[0]
    review_card_selectors = EX_REVIEW_CARD
    card_selectors_additive = False     # 退路鏈（未驗證，實測後可再調整）
    open_all_buttons = EX_OPEN_ALL_BUTTONS
    next_buttons = EX_NEXT_BUTTONS
    expand_buttons = EX_EXPAND_BUTTONS
    scroll_to_load = True

    @staticmethod
    def parse_cards(html: str) -> list[RawReview]:
        soup = _soup(html)
        cards = _select_any(soup, EX_REVIEW_CARD)

        reviews: list[RawReview] = []
        for card in cards:
            positive = _all_text(card, EX_POSITIVE)
            negative = _all_text(card, EX_NEGATIVE)
            body = _all_text(card, EX_TEXT)
            title = _first_text(card, EX_TITLE)

            # 有 Liked／Disliked 就用分離版，否則整段放 comment
            comment = body if (body and not positive and not negative) else ""
            if not (positive or negative or comment or title):
                continue

            score, scale = _expedia_score(card)

            reviews.append(RawReview(
                author=_first_text(card, EX_AUTHOR),
                score_raw=score,
                score_scale=scale,          # ⚠️ None ＝ 偵測不到，normalize 會記 warning
                title=title,
                positive_text=positive,
                negative_text=negative,
                comment=comment,
                review_date_text=_first_text(card, EX_DATE),
                stay_date_text=_first_text(card, EX_STAY),
                traveler_type=_first_text(card, EX_TRIP_TYPE),
                nights=_nights_from(card),
                raw={"source": "dom", "platform": "expedia",
                     "scale_detected": scale is not None},
            ))
        return reviews

    @staticmethod
    def parse_summary(html: str) -> tuple[float | None, int | None]:
        soup = _soup(html)

        overall: float | None = None
        for selector in EX_OVERALL:
            node = soup.select_one(selector)
            if node:
                text = _text(node) or node.get("content", "")
                m = _RE_SCORE_WITH_SCALE.search(text)
                overall = float(m.group(1)) if m else _number(text)
                if overall is not None:
                    break

        count: int | None = None
        for selector in EX_REVIEW_COUNT:
            node = soup.select_one(selector)
            if node:
                count = _int_or_none(node.get("content", "") or _text(node))
                if count is not None:
                    break

        return overall, count


# ══════════════════════════════════════════════════════════════════════════
# Agoda
# ══════════════════════════════════════════════════════════════════════════
def _agoda_score(card) -> float | None:
    """
    Agoda 的評分（10 分制）。

    ⚠️ **分數的 class 是 styled-components 產生的雜湊**
       （`sc-aXZVg Typographystyled__TypographySty...`），每次建置都會變，
       不能拿來當 selector。實測 `AG_SCORE` 那三組全數未命中。

    改用兩層：

      1. `AG_SCORE` 的穩定候選（其他版型可能有）
      2. ⭐ **卡片文字開頭就是分數** —— 實測卡片文字長這樣：
             「8.8 很讚 Sue-Ann （來自 日本 ） 團體旅遊 …」
         所以用錨定在開頭的正則抓第一個數字。

    ⚠️ **不可退回「掃整張卡文字找數字」** —— 卡片裡還有
       「入住1晚」「回覆日期2026年3月27日」等數字，掃到的不會是分數。
       錨定開頭才安全。
    """
    for selector in AG_SCORE:
        node = card.select_one(selector)
        if node:
            value = _number(_text(node))
            if value is not None and 0 <= value <= 10:
                return value

    m = _RE_AG_LEADING_SCORE.match(_text(card))
    if m:
        value = float(m.group(1))
        if 0 <= value <= 10:
            return value
    return None


def _agoda_date(card) -> str:
    """
    評鑑日期。

    實測 `.Review-statusBar-left` 命中（它是那個 span 的父層），
    但 span 自己的 class 是 styled-components 雜湊、每次建置都會變。
    所以加一層**錨定「評鑑日期」四個字**的文字備援。

    ⚠️ 兩層都必須避開業者回覆的「回覆日期2026年3月27日」——
       回覆日期永遠晚於評鑑日期，抓錯會讓月度趨勢整批往後偏。
       · selector 層：評鑑日期在文件順序上排在回覆之前，`_first_text` 取到對的
       · 文字層：正則錨定「評鑑日期」，不會誤中「回覆日期」
    """
    text = _first_text(card, AG_DATE)
    if text and "回覆" not in text:
        return text

    m = _RE_AG_REVIEW_DATE.search(_text(card))
    return m.group(1) if m else ""


def _agoda_nationality(card) -> str:
    """
    從「Sue-Ann （來自 日本 ）」抽出「日本」。

    Agoda 把暱稱與國籍放在同一個 `data-info-type="reviewer-name"` 區塊裡，
    暱稱在 `<strong>`、國籍在後面的括號中，沒有自己的節點。
    """
    block = _first_text(card, AG_REVIEWER_BLOCK)
    m = _RE_AG_COUNTRY.search(block)
    return m.group(1).strip() if m else ""


class AgodaParser:
    """
    Agoda 評論頁。2026-08-22 對真實頁面實測，**headless 即通過**。

    | | Agoda |
    |---|---|
    | 分制 | **固定 10 分制**。不像 Expedia 有兩種版型，可安全套平台預設 |
    | 正負評 | 實測版型**只有單一段落**（`AG_POSITIVE`／`AG_NEGATIVE` 未命中，保留供其他版型） |
    | 旅客資訊 | 統一用 `data-info-type="..."` 定位，不能只靠 class |
    | 分數 | class 是 styled-components 雜湊，改用「卡片文字開頭」擷取 |

    ⚠️ **業者回覆也帶 `data-element-name="review-comment"`** ——
       5 則評論的頁面會命中 10 張卡，多出來的是飯店自己的罐頭回覆。
       靠 `card_exclude_selectors = ('.Review-response',)` 剔除。
       沒剔掉的話，那些正面客套話會把情緒分析與主題統計整個帶歪。

    ⚠️ **Agoda 與 Booking.com 同屬 Booking Holdings**，Agoda 頁面上有時會出現
       來源為 Booking.com 的評論。跨站去重在這兩家之間特別會派上用場。
    """

    platform = "agoda"
    # 2026-08-22 實測 headless 即通過（1,002,733 字元），先試 headless 較快。
    prefer_visible = False
    allow_static_only = False   # ⚠️ 靜態頁多半只有精選片段，不可當成全部
    default_scale = 10

    review_card_selector = AG_REVIEW_CARD[0]
    review_card_selectors = AG_REVIEW_CARD
    # ⚠️ 新舊屬性可能同頁並存，用聯集；再靠 exclude 剔掉業者回覆
    card_selectors_additive = True
    card_exclude_selectors = AG_CARD_EXCLUDE

    open_all_buttons: tuple[str, ...] = ()      # 評論直接在頁面上
    next_buttons = AG_NEXT_BUTTONS
    expand_buttons = AG_EXPAND_BUTTONS
    scroll_to_load = True

    @staticmethod
    def parse_cards(html: str) -> list[RawReview]:
        soup = _soup(html)
        cards = _select_cards(soup, AG_REVIEW_CARD, additive=True,
                              exclude=AG_CARD_EXCLUDE)

        reviews: list[RawReview] = []
        for card in cards:
            positive = _all_text(card, AG_POSITIVE)
            negative = _all_text(card, AG_NEGATIVE)
            body = _all_text(card, AG_TEXT)
            title = _first_text(card, AG_TITLE)

            comment = body if (body and not positive and not negative) else ""
            if not (positive or negative or comment or title):
                continue

            reviews.append(RawReview(
                author=_first_text(card, AG_AUTHOR),
                score_raw=_agoda_score(card),
                score_scale=10,                 # Agoda 固定 10 分制
                title=title,
                positive_text=positive,
                negative_text=negative,
                comment=comment,
                review_date_text=_agoda_date(card),
                stay_date_text=_first_text(card, AG_STAY),
                nationality=_agoda_nationality(card),
                traveler_type=_first_text(card, AG_TRAVELER_TYPE),
                room_type=_first_text(card, AG_ROOM_TYPE),
                nights=_nights_from(card),      # 「入住1晚（2026年3月）」→ 1
                raw={"source": "dom", "platform": "agoda"},
            ))
        return reviews

    @staticmethod
    def parse_summary(html: str) -> tuple[float | None, int | None]:
        """
        ⚠️ 實測 Agoda 的站方總分／評論數**改由 `ld+json` 提供**（8.9 / 1906，正確）。

        原先用的 `[data-selenium="hotel-header-review-score"]` 抓到的是
        「9.4 超棒 位置得分」—— 那是**位置子評分**不是總分。
        寧可回 (None, None) 讓 `parse_page()` 退回 ld+json，
        也不要回一個看起來像總分的錯誤數字。
        """
        if not AG_OVERALL and not AG_REVIEW_COUNT:
            return None, None

        soup = _soup(html)
        overall = count = None
        for selector in AG_OVERALL:
            node = soup.select_one(selector)
            if node:
                overall = _number(node.get("content", "") or _text(node))
                if overall is not None:
                    break
        for selector in AG_REVIEW_COUNT:
            node = soup.select_one(selector)
            if node:
                count = _int_or_none(node.get("content", "") or _text(node))
                if count is not None:
                    break
        return overall, count


# ══════════════════════════════════════════════════════════════════════════
# Parser 註冊表
# ══════════════════════════════════════════════════════════════════════════
# 加新平台（例如 Agoda／Google）只需要在這裡多註冊一個 class，
# `ota_scraper_service` 完全不用改。
#
# ⚠️ 每個 class 必須有：platform / prefer_visible / allow_static_only /
#    default_scale / review_card_selectors / next_buttons / parse_cards /
#    parse_summary。選用：open_all_buttons / expand_buttons / scroll_to_load。
PARSERS: dict[str, Any] = {
    "booking": BookingParser,
    "tripadvisor": TripadvisorParser,
    "expedia": ExpediaParser,
    "agoda": AgodaParser,
}


def get_parser(platform: str):
    """取得平台對應的 parser；沒有就回 None（由呼叫端記 warning 並跳過）。"""
    return PARSERS.get((platform or "").strip().lower())


def parse_page(platform: str, html: str) -> tuple[list[RawReview], float | None, int | None]:
    """
    解析單一頁面：`ld+json` 與 DOM 卡片都跑，結果合併。

    合併規則：以 `external_id`（沒有就用內容雜湊）為鍵，
    **後者覆蓋前者** —— DOM 卡片的欄位比 ld+json 完整（有正負評分離、
    房型、旅客類型），所以讓它蓋掉 ld+json 的版本。
    """
    parser = get_parser(platform)
    if parser is None:
        return [], None, None

    ld_reviews, ld_overall, ld_count = parse_ld_json(html)
    dom_reviews = parser.parse_cards(html)
    dom_overall, dom_count = parser.parse_summary(html)

    merged: dict[str, RawReview] = {}
    for review in [*ld_reviews, *dom_reviews]:      # DOM 在後 → 覆蓋 ld+json
        key = review.external_id or "|".join([
            review.author,
            str(review.score_raw),
            review.title,
            review.positive_text,
            review.negative_text,
            review.comment,
            review.review_date_text,
        ])
        merged[key] = review

    return list(merged.values()), (dom_overall or ld_overall), (dom_count or ld_count)


# ══════════════════════════════════════════════════════════════════════════
# selector 診斷
# ══════════════════════════════════════════════════════════════════════════
# 這些 selector 組會被逐一回報命中狀況。新增平台時記得一併登錄，
# 否則 --diagnose 對該平台只會回報卡片層級的資訊。
DIAGNOSE_GROUPS: dict[str, list[tuple[str, tuple[str, ...]]]] = {
    "booking": [
        ("評論卡", (BK_REVIEW_CARD, BK_FEATURED_CARD)),
        ("顯示所有評語", BK_OPEN_ALL_BUTTONS),
        ("下一頁", BK_NEXT_BUTTONS),
        ("暱稱", BK_REVIEWER_NAME),
        ("分數", BK_SCORE),
        ("標題", BK_TITLE),
        ("正評", BK_POSITIVE),
        ("負評", BK_NEGATIVE),
        ("日期", BK_DATE),
        ("入住年月", BK_STAY_DATE),
        ("房型", BK_ROOM_TYPE),
        ("旅客類型", BK_TRAVELER_TYPE),
        ("站方總分", BK_OVERALL),
        ("站方評論數", BK_REVIEW_COUNT),
    ],
    "tripadvisor": [
        ("評論卡", TA_REVIEW_CARD),
        ("下一頁", TA_NEXT_BUTTONS),
        ("閱讀更多", TA_EXPAND_BUTTONS),
        ("暱稱", TA_AUTHOR),
        ("標題", TA_TITLE),
        ("留言", TA_TEXT),
        ("日期", TA_DATE),
        ("旅遊類型", TA_TRIP_TYPE),
        ("泡泡評分（class）", ('[class*="bubble_"]',)),
        ("站方總分", TA_OVERALL),
        ("站方評論數", TA_REVIEW_COUNT),
    ],
    "agoda": [
        ("評論卡", AG_REVIEW_CARD),
        ("下一頁", AG_NEXT_BUTTONS),
        ("展開更多", AG_EXPAND_BUTTONS),
        ("暱稱", AG_AUTHOR),
        ("標題", AG_TITLE),
        ("分數", AG_SCORE),
        ("留言", AG_TEXT),
        ("正評（喜歡）", AG_POSITIVE),
        ("負評（不喜歡）", AG_NEGATIVE),
        ("日期", AG_DATE),
        ("房型", AG_ROOM_TYPE),
        ("旅客類型", AG_TRAVELER_TYPE),
        # 國籍沒有自己的節點，是從暱稱區塊的「（來自 日本 ）」抽出來的
        ("暱稱區塊（含國籍）", AG_REVIEWER_BLOCK),
        ("業者回覆（應排除，不是客人評論）", AG_CARD_EXCLUDE),
    ],
    "expedia": [
        ("評論卡", EX_REVIEW_CARD),
        ("查看所有評論", EX_OPEN_ALL_BUTTONS),
        ("下一頁", EX_NEXT_BUTTONS),
        ("展開更多", EX_EXPAND_BUTTONS),
        ("暱稱", EX_AUTHOR),
        ("標題", EX_TITLE),
        ("分數", EX_SCORE),
        ("正評（Liked）", EX_POSITIVE),
        ("負評（Disliked）", EX_NEGATIVE),
        ("留言", EX_TEXT),
        ("日期", EX_DATE),
        ("站方總分", EX_OVERALL),
        ("站方評論數", EX_REVIEW_COUNT),
    ],
}


def diagnose(html: str, platform: str) -> dict[str, Any]:
    """
    逐一回報每組 selector 命中幾個節點、抓到什麼樣本值。

    存在的理由：Tripadvisor 與 Expedia 的 selector **沒有經過真實頁面驗證**
    （Booking 那組有，取自實跑過的原型工具）。與其等擷取失敗再回頭猜，
    不如提供一支能直接指出「哪一組 selector 沒命中」的工具。

    輸出設計成人看得懂、也貼得回對話裡，不是給程式吃的。
    """
    soup = _soup(html)
    parser = get_parser(platform)

    result: dict[str, Any] = {
        "platform": platform,
        "html_chars": len(html),
        "has_parser": parser is not None,
        "ld_json_blocks": len(soup.select('script[type="application/ld+json"]')),
        "groups": [],
        "parsed": {},
    }

    for label, selectors in DIAGNOSE_GROUPS.get(platform, []):
        hits = []
        for selector in selectors:
            nodes = soup.select(selector)
            sample = ""
            if nodes:
                sample = _text(nodes[0])[:60]
                if not sample:
                    # 沒有文字就秀 class／屬性，泡泡評分那種靠 class 編碼的要靠這個
                    attrs = nodes[0].attrs
                    sample = f"[class={' '.join(attrs.get('class', []))[:40]}]"
            hits.append({"selector": selector, "count": len(nodes), "sample": sample})
        result["groups"].append({
            "label": label,
            "matched": any(h["count"] for h in hits),
            "candidates": hits,
        })

    # 實際跑一次解析，看端到端結果
    ld_reviews, ld_overall, ld_count = parse_ld_json(html)
    result["parsed"]["ld_json_reviews"] = len(ld_reviews)
    result["parsed"]["ld_json_overall"] = ld_overall
    result["parsed"]["ld_json_count"] = ld_count

    if parser is not None:
        dom_reviews = parser.parse_cards(html)
        dom_overall, dom_count = parser.parse_summary(html)
        result["parsed"]["dom_reviews"] = len(dom_reviews)
        result["parsed"]["dom_overall"] = dom_overall
        result["parsed"]["dom_count"] = dom_count
        result["parsed"]["with_score"] = sum(1 for r in dom_reviews if r.score_raw is not None)
        result["parsed"]["with_scale"] = sum(1 for r in dom_reviews if r.score_scale)
        result["parsed"]["with_date"] = sum(1 for r in dom_reviews if r.review_date_text)
        result["parsed"]["samples"] = [
            {
                "author": r.author,
                "score_raw": r.score_raw,
                "score_scale": r.score_scale,
                "title": r.title[:40],
                "positive": r.positive_text[:40],
                "negative": r.negative_text[:40],
                "comment": r.comment[:40],
                "date_text": r.review_date_text[:30],
            }
            for r in dom_reviews[:3]
        ]

    return result


def dump_card_structure(html: str, platform: str, max_nodes: int = 60) -> list[str]:
    """
    把**第一張評論卡的內部結構**逐節點列出來。

    ⚠️ 這是 2026-08-22 加的，起因很具體：Tripadvisor 實測時
    `--diagnose` 告訴我「評論卡命中 10 張，但暱稱／標題／留言／日期全部 0」。
    知道「沒命中」卻不知道「實際長什麼樣」，等於還是得猜 —— 又要再跑一輪。

    所以直接把卡片內部有文字的節點連同 `data-*` 屬性與 class 印出來，
    看一眼就知道該用哪個 selector。

    只印**有文字**的節點，且文字截斷 —— 完整 HTML 動輒數十 KB，貼不回對話。
    """
    parser = get_parser(platform)
    if parser is None:
        return [f"（平台 {platform} 沒有 parser）"]

    soup = _soup(html)
    cards = _select_any(soup, getattr(parser, "review_card_selectors", ()))
    if not cards:
        return ["（找不到任何評論卡，無法 dump 結構）"]

    card = cards[0]
    lines: list[str] = []
    for node in card.find_all(True, limit=400):
        # 只取「自己直接擁有文字」的節點，避免把每一層外框都印一遍
        own = "".join(
            c for c in node.find_all(string=True, recursive=False)
        ).strip()
        attrs = node.attrs or {}
        interesting = {k: v for k, v in attrs.items()
                       if k.startswith("data-") or k in ("aria-label", "title", "alt", "href")}
        if not own and not interesting:
            continue

        desc = f"<{node.name}"
        for key, value in list(interesting.items())[:3]:
            val = " ".join(value) if isinstance(value, list) else str(value)
            desc += f' {key}="{val[:48]}"'
        classes = attrs.get("class") or []
        if classes:
            desc += f' class="{" ".join(classes)[:40]}"'
        desc += ">"

        text = " ".join(own.split())[:60]
        lines.append(f"{desc}  {text}" if text else desc)
        if len(lines) >= max_nodes:
            lines.append(f"…（只列前 {max_nodes} 個節點）")
            break

    if not lines:
        lines.append("（卡片內找不到帶文字或 data-* 屬性的節點）")
    return lines


def dump_page_overview(html: str, top: int = 25) -> list[str]:
    """
    當**一組 selector 都沒命中**時，回報「這個頁面到底長什麼樣」。

    ⚠️ 2026-08-22 加這個的原因：Expedia 實測 13 組 selector 全滅、
       ld+json 也是 0 個。`dump_card_structure()` 幫不上忙 ——
       它的前提是「找得到卡片」。結果診斷輸出只有一長串 ❌，
       完全看不出來是「selector 猜錯」還是「內容根本沒渲染」。

       這兩件事的處理方式**完全相反**（改 selector vs 加等待／捲動），
       分不出來就只能瞎試。

    回報四類線索：
      1. `<title>` 與 `<h1>` —— 確認開對頁面了沒（會不會被導去登入頁）
      2. **出現最多次的 `data-*` 屬性名** —— 這一項最有用，
         直接告訴我這個站實際用什麼命名慣例（`data-stid`？`data-testid`？）
      3. 關鍵字是否出現在可見文字 —— 「評論」「review」有沒有在頁面上
      4. 元素總數與文字長度 —— 判斷是完整頁面還是骨架
    """
    from collections import Counter

    soup = _soup(html)
    lines: list[str] = []

    title = soup.title.get_text(strip=True) if soup.title else ""
    lines.append(f"<title>：{title[:80] or '（無）'}")
    for tag in ("h1", "h2"):
        texts = [_text(n)[:50] for n in soup.select(tag)[:3] if _text(n)]
        if texts:
            lines.append(f"<{tag}>：{' ｜ '.join(texts)}")

    all_nodes = soup.find_all(True)
    body_text = _text(soup.body) if soup.body else ""
    lines.append(f"元素總數：{len(all_nodes):,}　可見文字：{len(body_text):,} 字元")

    # ⭐ 最有用的一項：這個站實際在用什麼 data-* 命名
    counter: Counter = Counter()
    for node in all_nodes:
        for attr in node.attrs:
            if attr.startswith("data-"):
                counter[attr] += 1
    if counter:
        lines.append("出現最多的 data-* 屬性（← 用這些重寫 selector）：")
        for attr, count in counter.most_common(top):
            sample = ""
            found = soup.select_one(f"[{attr}]")
            if found is not None:
                value = found.get(attr)
                value = " ".join(value) if isinstance(value, list) else str(value or "")
                text = _text(found)[:40]
                sample = f'  值="{value[:30]}"' + (f"  文字={text}" if text else "")
            lines.append(f"    {count:>5}  {attr}{sample}")
    else:
        lines.append("⚠️ 整份頁面沒有任何 data-* 屬性 —— 多半是還沒渲染的骨架")

    # 關鍵字在不在可見文字裡
    hits = [kw for kw in ("評論", "評語", "評價", "review", "Review") if kw in body_text]
    lines.append(f"可見文字含評論相關字詞：{'、'.join(hits) if hits else '❌ 完全沒有'}")

    return lines
