"""
OTA 口碑分析 — 正規化共用層

建立日期：2026-08-21
規格書：`docs/SPEC_ota_reviews.md` §5

═══════════════════════════════════════════════════════════════════════════
為什麼要獨立成一層
═══════════════════════════════════════════════════════════════════════════
資料有兩條進來的路：**爬蟲**與**CSV 手動匯入**。
兩條路必須走完全相同的正規化與去重管線，否則會產出兩種資料品質，
到時候「為什麼匯入的評論算不進趨勢圖」這種問題會查很久。

所以分制換算、日期解析、指紋計算全部集中在這裡，
`ota_scraper_service` 與 `ota_import_service` 都只呼叫本模組，不各自實作。

═══════════════════════════════════════════════════════════════════════════
設計原則：不確定就留白，不要猜
═══════════════════════════════════════════════════════════════════════════
分制偵測不出來 → `score_10 = None` + warning，**不猜**。
日期解析失敗 → `review_date = ""` + warning，**不填今天**。

猜出來的資料會混進統計，而且事後分不出哪些是猜的。
留白至少看得出「這裡沒有資料」。
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from functools import lru_cache

# ══════════════════════════════════════════════════════════════════════════
# 平台預設分制
# ══════════════════════════════════════════════════════════════════════════
# ⚠️ Expedia 兩種版型都有（有的頁面 9.2/10、有的 4.5 顆星），
#    所以預設值只是 fallback，parser 必須逐筆偵測後覆寫。
PLATFORM_SCALE: dict[str, int] = {
    "booking": 10,
    "agoda": 10,
    "expedia": 10,
    "tripadvisor": 5,
    "google": 5,
}

# ══════════════════════════════════════════════════════════════════════════
# ⭐ 負評門檻：**全模組唯一的一份**（2026-08-23 統一）
# ══════════════════════════════════════════════════════════════════════════
# 在此之前這個 6.0 各自寫在兩個檔案裡：
#     ota_stats_service.NEGATIVE_THRESHOLD  = 6.0   （Dashboard 的「負面評論」）
#     ota_analysis_service.NEGATIVE_MAX     = 6.0   （情緒判定與警示）
#
# 兩份一樣的常數遲早會漂移，而漂移的症狀是**兩個畫面上的數字對不起來**，
# 沒有任何錯誤訊息 —— 使用者只會發現「Dashboard 說 24 則，清單說 31 則」，
# 然後兩個數字都不再相信。
#
# 兩個檔案保留原本的名稱（呼叫點不用改），但都指到這裡。
#
# ⚠️ 是 `<` 不是 `<=`。剛好 6.0 分的評論算**中立**不算負面。
#    這一點在「清單的分數篩選」上特別重要 —— `max_score` 用的是 `<=`，
#    拿它來做「分數 < 6」會多含一批剛好 6.0 的，
#    數字就跟 Dashboard 對不起來（2026-08-23 差點踩到）。
NEGATIVE_SCORE_MAX = 6.0

PLATFORM_LABEL: dict[str, str] = {
    "booking": "Booking.com",
    "agoda": "Agoda",
    "expedia": "Expedia",
    "tripadvisor": "Tripadvisor",
    "google": "Google",
}

VALID_PLATFORMS = set(PLATFORM_SCALE.keys())

# ══════════════════════════════════════════════════════════════════════════
# 網域 → 平台（用來擋「網址與平台對不上」）
# ══════════════════════════════════════════════════════════════════════════
# ⚠️ 2026-08-22 加這個是因為實際踩到：把 `tw.trip.com` 的網址配上
#    `--platform tripadvisor`。**Trip.com（攜程）與 Tripadvisor 是完全不同的
#    兩家公司、不同的網站**，名字像而已。用錯 parser 不會有任何結果，
#    而且會被誤判成「selector 失效」，白白花時間查錯方向。
DOMAIN_PLATFORM: dict[str, str] = {
    "booking.com": "booking",
    "tripadvisor.com": "tripadvisor",
    "tripadvisor.com.tw": "tripadvisor",
    "tripadvisor.cn": "tripadvisor",
    "expedia.com": "expedia",
    "expedia.com.tw": "expedia",
    "expedia.co.jp": "expedia",
    "agoda.com": "agoda",
    # ⚠️ Google 有沒有 parser 是另一回事 —— 它**是** `PLATFORM_SCALE` 裡的合法平台，
    #    所以 google.com 的網址配 platform="google" 是**正確的組合**，不可擋。
    #    「沒有擷取器」由 `platform_options().has_parser` 與同步時的
    #    「略過而非失敗」處理（[1.90.94]），不該混進網址比對這一層。
    "google.com": "google",
}

# 認不出來的第三方網站 —— **不在** `PLATFORM_SCALE` 裡，配任何平台都是錯的。
# 分開列是為了給出精準的訊息：「這是 Trip.com 不是 Tripadvisor」
# 比「找不到 parser」有用得多。
#
# ⚠️ 判斷標準是「**這個網域屬不屬於我們支援的平台清單**」，
#    不是「有沒有寫 parser」。把兩件事混在一起會擋掉正確的設定
#    （2026-08-22 實測踩到：google.com 一度被列在這裡，
#     導致「Google 網址 + platform=google」這個完全正確的組合被拒絕）。
KNOWN_UNSUPPORTED: dict[str, str] = {
    "trip.com": "Trip.com（攜程）—— 與 Tripadvisor 是不同公司，不在支援的平台清單中",
    "ctrip.com": "攜程 Ctrip —— 不在支援的平台清單中",
    "hotels.com": "Hotels.com —— 不在支援的平台清單中",
    "kkday.com": "KKday —— 不在支援的平台清單中",
    "klook.com": "Klook —— 不在支援的平台清單中",
}


def platform_from_url(url: str) -> tuple[str, str]:
    """
    從網址判斷平台。

    回傳 `(platform, note)`：
      - 認得且有 parser  → `("tripadvisor", "")`
      - 認得但沒 parser  → `("", "Trip.com（攜程）—— 與 Tripadvisor 是不同公司…")`
      - 完全不認得       → `("", "")`

    ⚠️ 只用來**提醒**，不用來自動改寫使用者選的平台 ——
       網址千奇百怪（短網址、追蹤參數、地區站台），猜錯比不猜更糟。
    """
    from urllib.parse import urlparse

    try:
        host = (urlparse(url).netloc or "").lower().split(":")[0]
    except ValueError:
        return "", ""
    if not host:
        return "", ""

    # 由長到短比對，避免 `expedia.com` 先命中而蓋掉 `expedia.com.tw`
    for domain in sorted(DOMAIN_PLATFORM, key=len, reverse=True):
        if host == domain or host.endswith("." + domain):
            return DOMAIN_PLATFORM[domain], ""
    for domain, note in KNOWN_UNSUPPORTED.items():
        if host == domain or host.endswith("." + domain):
            return "", note
    return "", ""

# parser 專用的哨兵值：「有抓到分數，但**找不到分母**，無法判定分制」。
#
# ⚠️ 與 `score_scale = None` 語意不同，不可混用：
#     None          —— parser 沒去判斷（該平台分制固定，例如 Booking 永遠 10 分制）
#                      → 套用平台預設
#     SCALE_UNKNOWN —— parser 試過但頁面上沒有分母（Expedia 兩種版型並存）
#                      → `score_10` 留 NULL 並記 warning，**絕不套預設值**
#
# 猜錯的代價：一間 4.6/5（＝9.2 分）的好飯店會被記成 4.6 分的爛飯店，
# 混進平均分裡而且事後分不出來是哪幾筆。
SCALE_UNKNOWN = 0


# ══════════════════════════════════════════════════════════════════════════
# 字串正規化
# ══════════════════════════════════════════════════════════════════════════
def to_halfwidth(text: str) -> str:
    """全形轉半形（NFKC）。中日韓文字不受影響，只影響全形英數與標點。"""
    if not text:
        return ""
    return unicodedata.normalize("NFKC", text)


_PUNCT_RE = re.compile(r"[\s　,，。．、；;：:！!？?~～\-—－_「」『』（）()\[\]【】\"'`|/\\.]+")


def strip_noise(text: str) -> str:
    """
    去除所有空白與標點、轉小寫。
    用於跨 OTA 指紋比對 —— 同一段留言在不同平台可能標點或換行不同。
    """
    if not text:
        return ""
    return _PUNCT_RE.sub("", to_halfwidth(text)).lower()


def collapse_space(text: str) -> str:
    """把連續空白壓成單一空格並去頭尾。用於顯示欄位，不用於指紋。"""
    if not text:
        return ""
    return " ".join(to_halfwidth(text).split())


# ══════════════════════════════════════════════════════════════════════════
# ⭐ 簡繁字形變體（2026-08-23）
# ══════════════════════════════════════════════════════════════════════════
# **77 個內建關鍵詞裡有 47 個（61%）在簡體評論裡一個字都比不中。**
#
#   髒 → 脏      乾淨 → 干净    態度 → 态度    寬敞 → 宽敞
#   親切 → 亲切  設備齊全 → 设备齐全           排隊 → 排队
#
# 而 Booking／Agoda 的台灣飯店頁面**一定**有簡體評論者（中國、星馬、港澳）。
# 症狀極度隱蔽：不會報錯、不會有 warning，那些評論只是安靜地「沒有主題」，
# 然後不會進負評警示、不會進主題統計。看起來就像「這些客人沒抱怨什麼」。
#
# ⚠️ 修在**關鍵詞側**而不是評論側：
#    · 關鍵詞只有 77 個且幾乎不變 → 轉換一次就好，`lru_cache` 之後零成本
#    · 評論有上萬則且會一直增加 → 每則都轉換要付出真實的 CPU
#    · 使用者自己加的關鍵詞也自動享有變體，不必教他「兩種都要打一次」
_OPENCC_LOADED: dict[str, object] = {}
ZH_CONVERT_AVAILABLE = True         # opencc 不在時翻成 False，供呼叫端示警


def _converter(config: str):
    """取得 OpenCC 轉換器；沒安裝套件時回 None（不讓整包 import 掛掉）。"""
    global ZH_CONVERT_AVAILABLE
    if config in _OPENCC_LOADED:
        return _OPENCC_LOADED[config]
    try:
        from opencc import OpenCC
        _OPENCC_LOADED[config] = OpenCC(config)
    except Exception:               # noqa: BLE001 — 沒裝、或字典檔缺失
        ZH_CONVERT_AVAILABLE = False
        _OPENCC_LOADED[config] = None
    return _OPENCC_LOADED[config]


@lru_cache(maxsize=4096)
def zh_variants(keyword: str) -> tuple[str, ...]:
    """
    回傳關鍵詞的所有字形變體（原文 + 簡體 + 繁體），已去重。

        zh_variants("乾淨")  →  ("乾淨", "干净")
        zh_variants("干净")  →  ("干净", "乾淨")
        zh_variants("蟑螂")  →  ("蟑螂",)          # 兩岸同形，不會多產生

    ⚠️ **只處理字形，處理不了用詞差異**。這兩件事常被混為一談：

        字形（OpenCC 能轉）：髒/脏、態度/态度、寬敞/宽敞
        用詞（OpenCC 轉不出來）：捷運/地铁、網路/网络、訊號/信号、
                                菸味/烟味、CP值/性价比

    用詞差異必須**當成不同的關鍵詞收進字典**（見 `BUILTIN_TOPICS`），
    這裡轉不出來也不該假裝轉得出來。

    ⚠️ 沒裝 opencc 時原樣回傳 —— 但 `ZH_CONVERT_AVAILABLE` 會變 False，
       呼叫端**必須**把它變成使用者看得見的警告。這種降級如果是靜默的，
       就跟原本的 bug 一模一樣（安靜地少分類一半的評論）。
    """
    if not keyword:
        return ()
    out = [keyword]
    for config in ("t2s", "s2t"):
        conv = _converter(config)
        if conv is None:
            continue
        try:
            converted = conv.convert(keyword)
        except Exception:           # noqa: BLE001
            continue
        if converted and converted not in out:
            out.append(converted)
    return tuple(out)


# ══════════════════════════════════════════════════════════════════════════
# ⭐ 程度副詞變體（2026-08-23）
# ══════════════════════════════════════════════════════════════════════════
# 字典寫「隔音差」，客人寫「隔音**很**差」—— 中間插一個字就完全比不中。
# 而且插了的那個版本**比字典裡的還自然**：
#
#     字典「房間小」   客人「房間很小」
#     字典「服務好」   客人「服務很好」
#     字典「網路慢」   客人「網路真的很慢」
#
# 83 個內建詞裡有 13 個是這種「名詞＋形容詞」複合詞，全都有這個問題。
#
# ⚠️ 為什麼可以放心多產生一些不自然的變體（例如「種類很不多」）：
#    多出來的變體**只是永遠不會命中**，不會造成誤判。substring 比對多掃
#    幾個字串的成本可以忽略。真正要避免的是「一塵很不染」那種切錯位置的
#    雜訊 —— 所以尾巴用**完全比對白名單**，不是 startswith。
INTENSIFIERS = ("很", "太", "超", "非常", "真的很", "真的", "蠻", "挺", "有點", "比較")

# 會出現在複合詞尾巴的形容詞。**完全比對**，不做前綴比對。
_TRAILING_ADJ = frozenset({
    "好", "差", "小", "大", "慢", "快", "貴", "少", "多", "舊", "硬", "暗", "吵",
    "髒", "脏", "難吃", "好吃", "困難", "困难", "不好", "不多", "不冷", "不便",
    "齊全", "齐全", "老舊", "老旧",
    # 距離 —— 讓「捷運近」展成「捷運很近／捷運超近」，
    # 「離捷運遠」展成「離捷運很遠」。中文講距離幾乎一定帶程度副詞。
    "近", "遠", "远",
})


@lru_cache(maxsize=4096)
def intensifier_variants(keyword: str) -> tuple[str, ...]:
    """
    在「名詞＋形容詞」的接縫插入程度副詞，回傳所有變體（含原詞）。

        intensifier_variants("隔音差")   → ("隔音差", "隔音很差", "隔音太差", …)
        intensifier_variants("蟑螂")     → ("蟑螂",)        # 不是複合詞，不動
        intensifier_variants("一塵不染") → ("一塵不染",)    # 「不染」不在白名單

    ⚠️ 只在**尾巴剛好是白名單裡的形容詞**時才切。用 startswith 的話
       「一塵不染」會被切成「一塵」+「不染」→ 產生「一塵很不染」這種垃圾。
    """
    if not keyword or len(keyword) < 3:
        return (keyword,) if keyword else ()

    out = [keyword]
    for i in range(1, len(keyword)):
        head, tail = keyword[:i], keyword[i:]
        if len(head) < 2 or tail not in _TRAILING_ADJ:
            continue
        for word in INTENSIFIERS:
            variant = f"{head}{word}{tail}"
            if variant not in out:
                out.append(variant)
        break       # 只切最前面那個合法接縫，不要多重切
    return tuple(out)


# ══════════════════════════════════════════════════════════════════════════
# ⭐ 否定偵測（2026-08-23）
# ══════════════════════════════════════════════════════════════════════════
# 「**不用**排隊」命中「排隊」→ 標成「入住流程:neg」→ 進負評警示。
# 客人明明在稱讚，我們把他當成客訴。
#
# ASAP 實測：含「排队」的 444 則裡有 76 則（17%）帶否定詞，
#            含「等位」的 275 則裡有 58 則（21%）。這不是邊角案例。
#
# ⚠️ **只抑制，不翻轉**。「不乾淨」如果翻成負面看似聰明，但字典裡本來就有
#    「不乾淨」這個負面詞會命中 —— 翻轉等於同一件事做兩次，而且翻錯時
#    沒有第二道防線。抑制的話：「乾淨」被否定抑制、「不乾淨」照常命中，
#    結果自然是對的。
_NEGATORS = (
    "不用", "不需", "不必", "不會", "不会", "無需", "无需", "免", "毫無", "毫无",
    "沒有", "没有", "沒", "没", "未", "非", "不",
)

# 否定詞與關鍵詞之間最多容忍幾個字。
# ⚠️ 放太寬會誤傷：「**不**只是有點吵」裡的「不」離「吵」有 5 個字，
#    但它否定的是「只是」不是「吵」。中文的否定作用域很短，2 個字夠了。
NEGATION_WINDOW = 2


def is_negated(text: str, pos: int) -> bool:
    """
    `text[pos:]` 這個命中位置前面是不是接了否定詞。

        is_negated("不用排隊", 2)        → True    （不用 + 排隊）
        is_negated("排隊排很久", 0)      → False
        is_negated("房間不乾淨", 3)      → True    （抑制「乾淨」的正面命中；
                                                    字典裡的「不乾淨」會另外命中負面）
    """
    if pos <= 0:
        return False
    window = text[max(0, pos - NEGATION_WINDOW - 1):pos]
    return any(window.endswith(n) for n in _NEGATORS)


def find_unnegated(text: str, keyword: str) -> bool:
    """
    `keyword` 有沒有在 `text` 裡以**非否定**的形式出現過。

    只要有一次沒被否定就算命中 —— 客人寫「不用排隊，但退房排了很久」，
    後面那次才是重點。
    """
    start = 0
    while True:
        pos = text.find(keyword, start)
        if pos < 0:
            return False
        if not is_negated(text, pos):
            return True
        start = pos + 1


def keyword_variants(keyword: str) -> tuple[str, ...]:
    """
    關鍵詞的完整變體集合＝**程度副詞變體 × 簡繁變體**。

    這是規則層唯一該呼叫的入口 —— 兩種變體要一起展開才有意義：
    簡體使用者一樣會寫「隔音很差」，只展開其中一種還是會漏。

        keyword_variants("隔音差")
          → 隔音差 / 隔音很差 / 隔音太差 / … 以及它們各自的簡體形

    ⚠️ 順序是「先插副詞、再轉簡繁」。反過來也可以，但先轉簡繁會讓
       `_TRAILING_ADJ` 白名單需要同時收兩種字形（已經收了，但依賴更多）。
    """
    out: list[str] = []
    for base in intensifier_variants(keyword):
        for variant in zh_variants(base):
            if variant not in out:
                out.append(variant)
    return tuple(out)


# ══════════════════════════════════════════════════════════════════════════
# 分制統一
# ══════════════════════════════════════════════════════════════════════════
def normalize_score(
    score_raw: float | None,
    score_scale: int | None,
) -> tuple[float | None, int, str]:
    """
    把原始分數換算為 10 分制。

    回傳 `(score_10, score_scale, warning)`。
    `warning` 為空字串代表沒問題。

    ⚠️ 分制不明（scale 不是 5 也不是 10）時回傳 `(None, scale, warning)`，
       **不猜**。猜錯會讓平均分整個歪掉，而且事後看不出來。
    """
    if score_raw is None:
        return None, (score_scale or 10), ""

    if score_scale not in (5, 10):
        return None, (score_scale or 0), (
            f"分制不明（score_scale={score_scale}），score_10 留空未換算："
            f"原始分數 {score_raw}"
        )

    value = float(score_raw)
    score_10 = value * 2 if score_scale == 5 else value

    # 換算後仍應落在 0-10；超出代表原始分數或分制判斷有誤
    if not (0 <= score_10 <= 10):
        return None, score_scale, (
            f"換算後分數 {score_10} 超出 0-10 範圍"
            f"（原始 {value} / {score_scale} 分制），已留空"
        )

    return round(score_10, 1), score_scale, ""


# ══════════════════════════════════════════════════════════════════════════
# 日期正規化
# ══════════════════════════════════════════════════════════════════════════
_MONTH_NAMES = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}

# 2026年7月15日 / 2026 年 7 月 15 日
_RE_CJK_YMD = re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日?")
# 2026年7月（Tripadvisor 常見，只有年月）
_RE_CJK_YM = re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月")
# 2026-07-15 / 2026/07/15 / 2026.07.15
_RE_ISO = re.compile(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})")
# 2026-07 / 2026/07
_RE_ISO_YM = re.compile(r"(\d{4})[-/.](\d{1,2})(?![-/.\d])")
# Jul 15, 2026 / July 15 2026
_RE_EN_MDY = re.compile(r"([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})")
# 15 Jul 2026 / 15 July, 2026
_RE_EN_DMY = re.compile(r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3,9})\.?,?\s+(\d{4})")
# Jul 2026 / July 2026（只有月年）
_RE_EN_MY = re.compile(r"([A-Za-z]{3,9})\.?\s+(\d{4})")
# 3 天前 / 3天前 / 3 days ago / a day ago
_RE_REL_DAY = re.compile(r"(\d+)\s*(?:天前|days?\s+ago)", re.IGNORECASE)
_RE_REL_WEEK = re.compile(r"(\d+)\s*(?:週前|周前|weeks?\s+ago)", re.IGNORECASE)
_RE_REL_MONTH = re.compile(r"(\d+)\s*(?:個?月前|months?\s+ago)", re.IGNORECASE)
_RE_YESTERDAY = re.compile(r"昨天|yesterday", re.IGNORECASE)
_RE_TODAY = re.compile(r"今天|today", re.IGNORECASE)


def _safe_date(year: int, month: int, day: int) -> str:
    """組 ISO 日期字串；日期不合法（如 2 月 30 日）時回空字串。"""
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return ""


def parse_review_date(
    text: str,
    reference: datetime | None = None,
) -> tuple[str, str, str]:
    """
    把各站五花八門的日期字串正規化為 `YYYY-MM-DD`。

    回傳 `(iso_date, precision, warning)`：
      - `iso_date`  — 成功為 ISO 字串，失敗為**空字串**（不是 None，見 model 檔頭慣例）
      - `precision` — `"day"` / `"month"`（只到月，日補 01）/ `""`（失敗）
      - `warning`   — 空字串代表沒問題

    ⚠️ **解析失敗絕不回退成今天**。Tripadvisor 大量評論只有年月，
       若補成今天會讓月度趨勢整批往後挪，比留白危險得多。

    `reference` 用於相對日期（「3 天前」）回推，預設取現在。
    爬蟲應傳入該批次的 `fetched_at`，讓重跑結果可重現。
    """
    if not text:
        return "", "", ""

    raw = collapse_space(text)
    ref = reference or datetime.now()

    # ── 相對日期 ────────────────────────────────────────────────────────
    if _RE_TODAY.search(raw):
        return ref.date().isoformat(), "day", ""
    if _RE_YESTERDAY.search(raw):
        return (ref.date() - timedelta(days=1)).isoformat(), "day", ""
    m = _RE_REL_DAY.search(raw)
    if m:
        return (ref.date() - timedelta(days=int(m.group(1)))).isoformat(), "day", ""
    m = _RE_REL_WEEK.search(raw)
    if m:
        return (ref.date() - timedelta(weeks=int(m.group(1)))).isoformat(), "day", ""
    m = _RE_REL_MONTH.search(raw)
    if m:
        # 月的相對日期只能到月精度，日補 01
        months = int(m.group(1))
        y, mo = ref.year, ref.month - months
        while mo <= 0:
            mo += 12
            y -= 1
        iso = _safe_date(y, mo, 1)
        return iso, ("month" if iso else ""), ""

    # ── 絕對日期（日精度）────────────────────────────────────────────────
    m = _RE_CJK_YMD.search(raw)
    if m:
        iso = _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        return (iso, "day", "") if iso else ("", "", f"日期不合法：{raw}")

    m = _RE_ISO.search(raw)
    if m:
        iso = _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        return (iso, "day", "") if iso else ("", "", f"日期不合法：{raw}")

    m = _RE_EN_MDY.search(raw)
    if m and m.group(1).lower().rstrip(".") in _MONTH_NAMES:
        iso = _safe_date(int(m.group(3)), _MONTH_NAMES[m.group(1).lower().rstrip(".")],
                         int(m.group(2)))
        return (iso, "day", "") if iso else ("", "", f"日期不合法：{raw}")

    m = _RE_EN_DMY.search(raw)
    if m and m.group(2).lower().rstrip(".") in _MONTH_NAMES:
        iso = _safe_date(int(m.group(3)), _MONTH_NAMES[m.group(2).lower().rstrip(".")],
                         int(m.group(1)))
        return (iso, "day", "") if iso else ("", "", f"日期不合法：{raw}")

    # ── 只有年月（Tripadvisor 大宗）→ 日補 01，精度標記 month ──────────
    m = _RE_CJK_YM.search(raw)
    if m:
        iso = _safe_date(int(m.group(1)), int(m.group(2)), 1)
        return (iso, "month", "") if iso else ("", "", f"日期不合法：{raw}")

    m = _RE_ISO_YM.search(raw)
    if m:
        iso = _safe_date(int(m.group(1)), int(m.group(2)), 1)
        return (iso, "month", "") if iso else ("", "", f"日期不合法：{raw}")

    m = _RE_EN_MY.search(raw)
    if m and m.group(1).lower().rstrip(".") in _MONTH_NAMES:
        iso = _safe_date(int(m.group(2)), _MONTH_NAMES[m.group(1).lower().rstrip(".")], 1)
        return (iso, "month", "") if iso else ("", "", f"日期不合法：{raw}")

    return "", "", f"日期無法解析：{raw[:60]}"


def to_month(iso_date: str) -> str:
    """`2026-07-15` → `2026-07`；空字串進、空字串出。"""
    return iso_date[:7] if len(iso_date) >= 7 else ""


# ══════════════════════════════════════════════════════════════════════════
# 指紋
# ══════════════════════════════════════════════════════════════════════════
def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()


def make_fingerprint(
    external_id: str,
    author: str,
    score_raw: float | None,
    title: str,
    body: str,
    review_date: str,
) -> str:
    """
    同來源去重指紋。

    有 `external_id` 就直接用它（OTA 自己給的 ID 最可靠）；
    沒有才退回內容雜湊。

    ⚠️ 這裡刻意**不做** strip_noise —— 同一個來源的同一則評論，
    文字若有變動（客人編輯過）就應該視為需要更新的同一筆，
    靠 `UNIQUE(source_id, fingerprint)` 的 upsert 處理。
    過度正規化反而會讓「編輯後的版本」被誤判為同一筆而漏更新。
    """
    if external_id:
        return _sha256(f"eid|{external_id}")
    return _sha256("|".join([
        author or "",
        "" if score_raw is None else f"{float(score_raw):.1f}",
        title or "",
        body or "",
        review_date or "",
    ]))


def make_cross_fingerprint(
    hotel_code: str,
    author: str,
    review_date: str,
    body: str,
) -> str:
    """
    跨 OTA 去重指紋（規格書 §5.3）。

    與同來源指紋不同，這裡**必須**做重度正規化 —— 同一位客人在 Booking 與
    Expedia 貼的同一段話，標點、換行、全半形都可能不同。

    只取留言前 120 字：各站對長留言的截斷點不一樣，取全文反而比不中。

    留言為空時回傳空字串（不參與跨站去重）—— 只有分數沒有留言的評論，
    光靠暱稱與日期比對誤判率太高，寧可算兩筆。

    ⚠️ **2026-08-22（P3）改用「年月」而非「完整日期」** —— 這是規格書 §5.3
       原訂做法的修正，理由是實測發現原做法對最重要的那組配對根本不會命中：

         Booking 給的是完整日期「2026年7月15日」→ 2026-07-15
         Tripadvisor 大量評論**只有年月**「2026年7月」→ 補為 2026-07-01

       同一則評論、同一個人、同一段話，只因為日期精度不同就算成兩筆
       （規格書 §5.4 明訂月精度要補 01 日，那是為了月度趨勢，
       但拿來當去重鍵就會全部錯開）。

       改用年月幾乎不會放寬誤判空間：暱稱要相同、留言前 120 字正規化後
       要**完全相同**，這兩個條件已經做了絕大部分的判別工作；
       多一個「同月」只是把日期精度的雜訊拿掉。

    ⚠️ 改動後既有資料的 `cross_fingerprint` 是舊格式，新舊混在一起比對不到。
       重新同步／重新匯入會自動覆寫；要立刻套用請跑
       `Temp/recompute_ota_cross_fingerprint.py`。
    """
    normalized_body = strip_noise(body)[:120]
    if not normalized_body:
        return ""
    return _sha256("|".join([
        hotel_code or "",
        strip_noise(author),
        to_month(review_date),      # ⚠️ 年月而非完整日期，理由見 docstring
        normalized_body,
    ]))


# ══════════════════════════════════════════════════════════════════════════
# 統一入口
# ══════════════════════════════════════════════════════════════════════════
@dataclass
class RawReview:
    """
    parser 與 CSV 匯入共同的輸出格式（尚未正規化）。

    分數用 `score_raw` + `score_scale` 兩欄表達；
    parser 偵測不出分制時把 `score_scale` 留 None，交給 normalize 記 warning。
    """

    author: str = ""
    score_raw: float | None = None
    score_scale: int | None = None
    title: str = ""
    positive_text: str = ""
    negative_text: str = ""
    comment: str = ""
    review_date_text: str = ""
    stay_date_text: str = ""
    nationality: str = ""
    traveler_type: str = ""
    room_type: str = ""
    nights: int | None = None
    external_id: str = ""
    review_url: str = ""
    raw: dict = field(default_factory=dict)


@dataclass
class NormalizedReview:
    """正規化後、可直接寫進 ota_reviews 的資料。"""

    author: str
    score_raw: float | None
    score_scale: int
    score_10: float | None
    title: str
    positive_text: str
    negative_text: str
    comment: str
    review_date: str
    review_month: str
    stay_month: str
    nationality: str
    traveler_type: str
    room_type: str
    nights: int | None
    external_id: str
    review_url: str
    fingerprint: str
    cross_fingerprint: str
    date_precision: str
    warnings: list[str]
    raw: dict


def normalize_review(
    raw: RawReview,
    *,
    hotel_code: str,
    platform: str,
    default_scale: int | None = None,
    reference: datetime | None = None,
) -> NormalizedReview:
    """
    把 parser／CSV 產出的 `RawReview` 走完整條正規化管線。

    這是**唯一**的入口 —— 爬蟲與 CSV 匯入都必須經過這裡，
    不可各自實作分制換算或日期解析（規格書 §6.6）。
    """
    warnings: list[str] = []

    # ── 分制 ────────────────────────────────────────────────────────────
    # ⚠️ 2026-08-22（P3）修正：原本寫 `raw.score_scale or default_scale or ...`，
    #    用的是「真值」判斷，於是 parser 回報的 `SCALE_UNKNOWN`(0) 會被當成
    #    「沒填」而落到平台預設 10 —— Expedia 抓到 4.6 卻找不到分母時，
    #    就會被當成 4.6/10 記進去。那正是本檔開頭寫明「不確定就留白，不要猜」
    #    要避免的事，而且錯得無聲無息（事後看不出哪些是猜的）。
    #
    #    現在用 `is not None` 區分三種狀態：
    #      None          —— parser 沒判斷（該平台分制固定），用平台預設
    #      SCALE_UNKNOWN —— parser **試過但找不到分母**，留白並記 warning
    #      5 / 10        —— 確定
    if raw.score_scale is not None:
        scale = raw.score_scale
    else:
        scale = default_scale or PLATFORM_SCALE.get(platform, 10)
    score_10, scale, score_warn = normalize_score(raw.score_raw, scale)
    if score_warn:
        warnings.append(score_warn)

    # ── 日期 ────────────────────────────────────────────────────────────
    review_date, precision, date_warn = parse_review_date(raw.review_date_text, reference)
    if date_warn:
        warnings.append(date_warn)
    stay_date, _, _ = parse_review_date(raw.stay_date_text, reference)

    # ── 文字 ────────────────────────────────────────────────────────────
    author = collapse_space(raw.author) or "匿名旅客"
    title = collapse_space(raw.title)
    positive_text = (raw.positive_text or "").strip()
    negative_text = (raw.negative_text or "").strip()
    comment = (raw.comment or "").strip()

    # 指紋用的「內容」：三個文字欄位串起來，避免只有正評或只有負評時指紋撞在一起
    body_for_fp = "\n".join(t for t in (positive_text, negative_text, comment) if t)

    raw_payload = dict(raw.raw)
    if precision:
        raw_payload["date_precision"] = precision

    return NormalizedReview(
        author=author,
        score_raw=None if raw.score_raw is None else round(float(raw.score_raw), 1),
        score_scale=scale,
        score_10=score_10,
        title=title,
        positive_text=positive_text,
        negative_text=negative_text,
        comment=comment,
        review_date=review_date,
        review_month=to_month(review_date),
        stay_month=to_month(stay_date),
        nationality=collapse_space(raw.nationality),
        traveler_type=collapse_space(raw.traveler_type),
        room_type=collapse_space(raw.room_type),
        nights=raw.nights,
        external_id=(raw.external_id or "").strip(),
        review_url=(raw.review_url or "").strip(),
        fingerprint=make_fingerprint(
            raw.external_id or "", author, raw.score_raw, title, body_for_fp, review_date
        ),
        cross_fingerprint=make_cross_fingerprint(
            hotel_code, author, review_date, body_for_fp
        ),
        date_precision=precision,
        warnings=warnings,
        raw=raw_payload,
    )
