"""
OTA 口碑分析 Pydantic Schemas

規格書：`docs/SPEC_ota_reviews.md`

註：OPERA 模組沒有 schema 檔（service 直接回 dict）是歷史特例，
    新模組一律照 cycle_purchase 的規範建 schema。
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

# ⚠️ **不可改回 `Literal[...]`**（2026-08-23 平台改為資料驅動）。
#
#    平台清單現在存在 `ota_platforms` 表，使用者可以自己新增 Hotels.com、
#    Trip.com、KKday……。寫成 Literal 的話 Pydantic 會在 schema 層就把
#    自建平台擋掉，而且錯誤訊息長這樣：
#
#        Input should be 'booking', 'expedia', 'tripadvisor', 'agoda' or 'google'
#
#    —— 使用者剛在畫面上建好平台、選了它，卻被告知這個值不合法，
#    完全看不出來問題出在哪一層。
#
#    合法性改由 service 層對 DB 驗證（`_assert_platform_exists`），
#    那裡才知道現在有哪些平台。這裡只管格式。
Platform = str
SyncStatus = Literal["never", "running", "success", "partial", "captcha", "failed"]
AlertStatus = Literal["open", "acknowledged", "resolved", "ignored"]
Sentiment = Literal["positive", "neutral", "negative"]


# ══════════════════════════════════════════════════════════════════════════
# 來源設定
# ══════════════════════════════════════════════════════════════════════════
class OtaSourceBase(BaseModel):
    hotel_code: str = Field(..., min_length=1, max_length=20)
    hotel_name: str = Field("", max_length=50)
    platform: Platform
    url: str = Field(..., min_length=8, max_length=500)
    score_scale: int = 10
    is_enabled: bool = True
    max_pages: int = Field(20, ge=1, le=200)
    sort_order: int = 0

    @field_validator("url")
    @classmethod
    def _check_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            raise ValueError("請輸入完整的 http/https 網址")
        return v

    @field_validator("score_scale")
    @classmethod
    def _check_scale(cls, v: int) -> int:
        if v not in (5, 10):
            raise ValueError("分制只能是 5 或 10")
        return v


class OtaSourceCreate(OtaSourceBase):
    pass


class OtaSourceUpdate(OtaSourceBase):
    pass


class OtaSourceOut(OtaSourceBase):
    id: int
    overall_score: Optional[float] = None
    overall_score_10: Optional[float] = None
    review_count_site: Optional[int] = None
    last_sync_at: str = ""
    last_status: SyncStatus = "never"
    last_message: str = ""
    # 實際落地筆數（不含跨站重複），用來與 review_count_site 比對抓取完整度
    stored_count: int = 0


# ══════════════════════════════════════════════════════════════════════════
# 評論
# ══════════════════════════════════════════════════════════════════════════
class OtaReviewRow(BaseModel):
    """列表用的精簡欄位"""

    id: int
    hotel_code: str
    hotel_name: str
    platform: str
    platform_label: str
    author: str
    score_raw: Optional[float] = None
    score_scale: int = 10
    score_10: Optional[float] = None
    summary: str                      # 標題或留言摘要（後端已截斷）
    review_date: str = ""
    sentiment_label: str = ""
    topics: list[str] = []
    is_alert: bool = False
    alert_status: str = "open"
    is_duplicate: bool = False


class OtaReviewListOut(BaseModel):
    rows: list[OtaReviewRow]
    total: int
    page: int
    page_size: int


class OtaReviewDetailOut(BaseModel):
    """
    明細 Drawer 用。

    `review_url` 是 §7 Drawer 規範中 `ragic_url` 的等價替代（規格書 §9.3）；
    `detail` 用中文欄位名稱作 key，涵蓋所有原始欄位，前端逐項渲染。
    """

    id: int
    hotel_code: str
    hotel_name: str
    platform: str
    platform_label: str
    review_url: str = ""
    author: str
    score_raw: Optional[float] = None
    score_scale: int = 10
    score_10: Optional[float] = None
    title: str = ""
    positive_text: str = ""
    negative_text: str = ""
    comment: str = ""
    review_date: str = ""
    stay_month: str = ""
    sentiment_label: str = ""
    sentiment_score: Optional[float] = None
    sentiment_engine: str = ""
    topics: list[str] = []
    is_alert: bool = False
    alert_status: str = "open"
    alert_note: str = ""
    is_duplicate: bool = False
    fetched_at: str = ""
    detail: dict[str, str] = {}


class AlertUpdateIn(BaseModel):
    alert_status: AlertStatus
    alert_note: str = ""


# ══════════════════════════════════════════════════════════════════════════
# 統計
# ══════════════════════════════════════════════════════════════════════════
class DataRangeOut(BaseModel):
    """
    ⚠️ `StandardRangePicker` 的 `anchor` 來源（CLAUDE.md §8.2）。

    前端**必須**把 `end` 傳給 `anchor`，不可用 `dayjs()` ——
    OTA 評論本來就落後（客人退房幾天後才留言、爬蟲每日才跑一次），
    以今天為基準的「本月」會選到一片空白，使用者會誤判成資料缺漏。
    """

    start: str = ""
    end: str = ""
    total: int = 0


class OverviewOut(BaseModel):
    total: int = 0
    avg_score_10: Optional[float] = None
    negative_count: int = 0
    alert_open_count: int = 0
    this_month_count: int = 0
    last_month_count: int = 0
    this_month_avg: Optional[float] = None
    last_month_avg: Optional[float] = None


class MonthlyPoint(BaseModel):
    review_month: str
    hotel_code: str
    hotel_name: str
    avg_score_10: Optional[float] = None
    count: int = 0
    # ⚠️ 這兩個與 `OverviewOut` 是**同一組條件**算出來的，
    #    月度圖上的數字要跟 Dashboard KPI 對得起來。
    negative_count: int = 0
    alert_open_count: int = 0


class PlatformStat(BaseModel):
    platform: str
    platform_label: str
    hotel_code: str = ""
    avg_score_10: Optional[float] = None
    count: int = 0


class TopicStat(BaseModel):
    topic: str
    negative_count: int = 0
    positive_count: int = 0
    total_count: int = 0


class ScoreBucket(BaseModel):
    """
    分數分布的一格（2026-08-25）。

    ⚠️ 區間是**半開** `[min_score, max_score)`。前端點擊時換算成
       `min_score` + `score_below` 兩個既有參數（後端 `min_score` 是 `>=`、
       `score_below` 是 `<`）—— **不需要新增任何篩選參數**。
       用 `max_score`（`<=`）的話兩格會重疊，剛好等於邊界值的評論被算兩次。

    `min_score` 為 None ＝ 沒有下限（最低那格）；
    `max_score` 為 None ＝ 沒有上限（含滿分 10.0）。
    """

    key: str
    label: str
    count: int = 0
    min_score: Optional[float] = None
    max_score: Optional[float] = None
    # 低於負評門檻 —— 畫警戒色，且這一格的數字應該等於 Dashboard 的「負面評論」
    is_negative: bool = False


class ScoreDistributionOut(BaseModel):
    """
    ⚠️ `no_score_count` **必須跟著回傳**（同 `AlertAgingOut.unknown_count`）。

    抓不到分數的評論（`score_10` 為 NULL）不屬於任何一格 ——
    Expedia 有些版型偵測不出分制，normalize 會刻意留白。
    只是把它們拿掉的話 `sum(buckets) < 總筆數`，看起來像圖表算錯。
    """

    buckets: list[ScoreBucket] = []
    total: int = 0
    no_score_count: int = 0


class AlertDailyPoint(BaseModel):
    """每日警示條帶的一格（2026-08-25）。"""

    date: str                   # YYYY-MM-DD
    count: int = 0
    # ⚠️ 這一天**還沒有資料**（晚於評論資料的最後一天）。
    #    OTA 評論落後現實好幾天 —— 客人退房後才留言、爬蟲每日才跑。
    #    不分開標的話，最近幾天會顯示成「0 件」，
    #    看起來像「這幾天沒出事」，實際上是「還沒抓到」。
    #    **那是這個模組最容易誤導人的一種呈現。**
    no_data: bool = False


class AlertDailyOut(BaseModel):
    """
    ⚠️ **與 `AlertAgingOut` 的口徑不同，同一頁上要講清楚：**

      · 積壓分桶（`AlertAgingOut`）＝ **還沒處理的存量**（open + acknowledged）
      · 這張條帶　　（`AlertDailyOut`）＝ **當天發生了幾件**（不論後來處理了沒）

    如果條帶也只算未處理，處理完的日子會變乾淨 ——
    看起來像「那幾天沒出事」，但事情發生過。
    兩個口徑都對，但混為一談就會變成「兩個數字對不起來」。
    """

    days: list[AlertDailyPoint] = []
    max_count: int = 0
    total: int = 0
    # 評論資料的最後一天（用來判斷哪些格子是「還沒有資料」）
    data_end: str = ""


class AlertAgingBucket(BaseModel):
    """
    警示積壓分桶的一格（2026-08-25）。

    `min_days` / `max_days` 讓前端可以把「點這根柱子」換算成日期區間去篩清單 ——
    積壓 N 天 ⇔ `review_date` 落在 `[今天-max, 今天-min]`，
    所以**不需要另外做一組後端篩選參數**，沿用既有的 start／end 即可。
    `max_days` 為 `None` 代表最後一桶（沒有上限）。
    """

    key: str                    # "0_3" / "4_7" / "8_14" / "15_plus" / "unknown"
    label: str                  # "0–3 天"
    count: int = 0
    min_days: Optional[int] = None
    max_days: Optional[int] = None
    # 這一桶要不要用警戒色（最後一桶＝放太久）
    is_overdue: bool = False


class AlertAgingOut(BaseModel):
    """
    ⚠️ `unknown_count` **必須跟著回傳**，不可以靜默丟掉。

    `review_date` 解析不出來的評論（空字串）不屬於任何積壓區間 ——
    這與 §5.4「空日期不落入任何月份」是同一條規則。
    但如果只是把它們從分桶裡拿掉，`sum(buckets) != 待處理總數`，
    使用者會以為圖表算錯。**畫面必須講出來有幾件無法計算。**
    """

    buckets: list[AlertAgingBucket] = []
    total: int = 0              # 分得出桶的總數（不含 unknown）
    unknown_count: int = 0      # 日期解析不出來、無法計算積壓的件數
    # 起算基準日。⚠️ 這裡**刻意用今天**而不是「資料最後一天」——
    # 積壓是相對於「現在」的，客人三週前抱怨就是積壓三週，
    # 與我們什麼時候爬到無關（CLAUDE.md §8.2 的 anchor 規則不適用於此）。
    as_of: str = ""


# ══════════════════════════════════════════════════════════════════════════
# 同步
# ══════════════════════════════════════════════════════════════════════════
class SyncLogOut(BaseModel):
    id: int
    source_id: int
    hotel_name: str = ""
    platform_label: str = ""
    trigger_type: str = ""
    started_at: str = ""
    completed_at: str = ""
    status: str = ""
    pages_fetched: int = 0
    found_count: int = 0
    inserted_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    warnings: list[str] = []
    error_message: str = ""
    duration_ms: Optional[int] = None


class ImportResultOut(BaseModel):
    """CSV 備援匯入結果"""

    total_rows: int = 0
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    marked_duplicate: int = 0
    warnings: list[str] = []
    errors: list[str] = []


# ══════════════════════════════════════════════════════════════════════════
# 主題字典
# ══════════════════════════════════════════════════════════════════════════
class TopicRuleBase(BaseModel):
    topic: str = Field(..., min_length=1, max_length=30)
    keyword: str = Field(..., min_length=1, max_length=50)
    polarity: Literal["negative", "positive", "neutral"] = "negative"
    weight: int = Field(1, ge=1, le=10)
    is_enabled: bool = True


class TopicRuleCreate(TopicRuleBase):
    pass


class TopicRuleUpdate(BaseModel):
    """
    內建詞只能改 `is_enabled` 與 `weight`（topic/keyword/polarity 是唯一鍵，
    改了等於換一筆）。限制在後端 service 強制，前端 disabled 只是提示。
    """

    polarity: Optional[Literal["negative", "positive", "neutral"]] = None
    weight: Optional[int] = Field(None, ge=1, le=10)
    is_enabled: Optional[bool] = None


class TopicRuleOut(TopicRuleBase):
    id: int
    is_builtin: bool = False


# ══════════════════════════════════════════════════════════════════════════
# AI 發現的字典外主題候選（2026-08-23）
# ══════════════════════════════════════════════════════════════════════════
class TopicCandidateOut(BaseModel):
    id: int
    name: str
    description: str = ""
    keywords: list[str] = []
    hit_count: int = 0
    neg_count: int = 0
    sample_review_ids: list[int] = []
    status: str = "pending"
    first_seen_at: str = ""
    last_seen_at: str = ""


class TopicCandidateAcceptIn(BaseModel):
    """
    採納候選 → 變成正式的字典關鍵詞。

    ⚠️ `topic` 與 `keywords` 都讓管理員可以改再送出 —— AI 給的名字未必是
       我們想在圖表上看到的（它可能寫「電梯設備」，我們想要「電梯」）。
       採納後主題名就會出現在月度趨勢圖的圖例上，改名的成本很高。
    """

    topic: str = Field(..., min_length=1, max_length=30)
    keywords: list[str] = Field(..., min_length=1, max_length=20)
    polarity: Literal["negative", "positive", "neutral"] = "negative"
