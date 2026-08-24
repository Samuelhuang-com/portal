"""
OTA 口碑分析 — 資料模型（5 張表）

建立日期：2026-08-21
規格書：`docs/SPEC_ota_reviews.md`
建表 SQL：`docs/add_ota_tables.sql`（create_all 會自動建，該檔供既有 DB 補建用）

═══════════════════════════════════════════════════════════════════════════
本模組是「外部網站擷取型」，與 Ragic 無關，也與 OPERA（人工上傳 TXT）無關
═══════════════════════════════════════════════════════════════════════════
資料來源是 Booking／Expedia／Tripadvisor 的**公開評論頁**。
沒有 ragic_id、沒有 ragic_url，明細 Drawer 的原始連結改用 `review_url`
（等價替代規則見規格書 §9.3）。

═══════════════════════════════════════════════════════════════════════════
三個最容易踩的坑（全部已在欄位設計中處理，改欄位前務必先讀）
═══════════════════════════════════════════════════════════════════════════
1. **分制不統一**
   Booking／Agoda 是 1-10，Tripadvisor／Google 是 1-5，Expedia 兩種都有。
   `score_raw` 存原始值、`score_scale` 存分制、`score_10` 存換算後的 10 分制。
   **所有統計一律用 `score_10`**。任何地方出現 `AVG(score_raw)` 都是 bug。

2. **同一則評論會出現在兩個平台**
   `fingerprint` 只做同來源去重；跨 OTA 靠 `cross_fingerprint`。
   命中重複時**只標記 `is_duplicate=True`，絕不刪除** —— 刪錯救不回來，
   而且各站原始筆數還要對得上站方公布的評論總數。
   統計查詢預設 `WHERE is_duplicate = 0`。

3. **警示狀態是人工填的營運欄位**
   `alert_status` / `alert_note` / `alert_handler_id` / `alert_handled_at`
   由使用者在畫面上填寫。**任何同步或重新分析都不可覆蓋這四欄**
   （比照 CLAUDE.md §9 規則 4 的精神）。

═══════════════════════════════════════════════════════════════════════════
欄位慣例（沿用 opera_segment.py）
═══════════════════════════════════════════════════════════════════════════
- SQLAlchemy 2.0 `Mapped[]` / `mapped_column()` 風格
- **日期一律 `String(10)` 存 ISO 字串**（`YYYY-MM-DD`），不用 Date 型別
- **缺值一律空字串不用 NULL** —— 指紋計算與唯一鍵會用到，
  SQLite 的 NULL 在唯一鍵中的行為與空字串不同
- 例外：數值型（score_raw／score_10／nights）與時間戳允許 NULL，
  因為「沒有分數」與「0 分」語意不同
- 複合索引寫在 `__table_args__`
- 時間戳一律 `app.core.time.twnow`（台灣時間 naive datetime）
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (Boolean, DateTime, ForeignKey, Index, Integer, Numeric,
                        String, Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.time import twnow


# ══════════════════════════════════════════════════════════════════════════
# 1. OTA 來源設定
# ══════════════════════════════════════════════════════════════════════════
class OtaSource(Base):
    """
    一個「飯店 × 平台」＝ 一筆來源。

    `hotel_code` 刻意與 OPERA 的 property_code 對齊（HANNS / HANNS_SUMMER），
    是為了日後能把口碑分數與 ADR／RevPAR 疊圖。
    ⚠️ 但兩者時間口徑不同（評論日期 vs 營業日期），疊圖前需另訂口徑。
    """

    __tablename__ = "ota_sources"
    __table_args__ = (
        UniqueConstraint("url", name="uq_ota_source_url"),
        Index("ix_ota_source_hotel", "hotel_code"),
        Index("ix_ota_source_platform", "platform"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    hotel_code: Mapped[str] = mapped_column(String(20), default="")   # HANNS / HANNS_SUMMER
    hotel_name: Mapped[str] = mapped_column(String(50), default="")   # 顯示用，group by 一律用 hotel_code
    platform: Mapped[str] = mapped_column(String(20), default="")     # booking/expedia/tripadvisor/agoda/google
    url: Mapped[str] = mapped_column(String(500))

    # 該平台的預設分制；Expedia 兩種版型都有，parser 會逐筆覆寫 review.score_scale
    score_scale: Mapped[int] = mapped_column(Integer, default=10)

    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    max_pages: Mapped[int] = mapped_column(Integer, default=20)       # 翻頁上限，約 200 則

    # 站方公布的總分與評論總數（不是我們算出來的，用來比對抓取完整度）
    overall_score: Mapped[float | None] = mapped_column(Numeric(3, 1), nullable=True)
    overall_score_10: Mapped[float | None] = mapped_column(Numeric(3, 1), nullable=True)
    review_count_site: Mapped[int | None] = mapped_column(Integer, nullable=True)

    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # never / success / partial / captcha / failed
    last_status: Mapped[str] = mapped_column(String(20), default="never")
    last_message: Mapped[str] = mapped_column(String(500), default="")

    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=twnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=twnow, onupdate=twnow)


# ══════════════════════════════════════════════════════════════════════════
# 2. 同步批次紀錄
# ══════════════════════════════════════════════════════════════════════════
class OtaSyncLog(Base):
    """
    每次同步一筆，讓「同步是否真的成功」可稽核。

    ⚠️ `warnings_json` 與 `error_message` 的分工不可混用：
    「跳過／比對不到／某頁沒抓到」歸 warnings，**只有真正的失敗才寫 error_message**。
    這是 CLAUDE.md §9 規則 8 的教訓 —— 把 warning 當 error 記，
    來源端只要有一點小狀況就永遠黃燈，久了沒人看。
    """

    __tablename__ = "ota_sync_logs"
    __table_args__ = (
        Index("ix_ota_synclog_source", "source_id", "started_at"),
        Index("ix_ota_synclog_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ota_sources.id", ondelete="RESTRICT"), nullable=False
    )

    trigger_type: Mapped[str] = mapped_column(String(10), default="schedule")  # schedule/manual/import
    started_at: Mapped[datetime | None] = mapped_column(DateTime, default=twnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # running / success / partial / captcha / failed
    status: Mapped[str] = mapped_column(String(20), default="running")

    pages_fetched: Mapped[int] = mapped_column(Integer, default=0)
    found_count: Mapped[int] = mapped_column(Integer, default=0)
    inserted_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)

    warnings_json: Mapped[str | None] = mapped_column(Text, nullable=True)   # JSON array
    error_message: Mapped[str] = mapped_column(String(1000), default="")

    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    triggered_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # ── 誰在跑這一列（2026-08-24 新增，孤兒 running 回收用）──────────────
    #
    # ⚠️ **這兩欄是為了修一個會鎖死整個模組的 bug**，不是稽核用的。
    #
    #    `status='running'` 在 `start_sync_log()` 之後就 commit 落地了，
    #    但收尾只在 `except Exception` 裡 —— Ctrl-C（KeyboardInterrupt 是
    #    BaseException）、行程被砍、後端重啟、driver 崩潰都不會經過它。
    #    那一列於是永遠停在 running，而 `run_sync()` 看到 running 就回 409。
    #    結果不只是按鈕轉圈圈，是**整個 OTA 同步從此按不下去**。
    #
    #    有了 host+pid 就能問一句「那個行程還活著嗎」，而不是靠猜逾時。
    #    ⚠️ host 一定要一起比：pid 只在同一台機器上有意義，
    #       跨機器拿 pid 去問「還在不在」得到的答案是隨機的。
    worker_host: Mapped[str] = mapped_column(String(60), default="")
    worker_pid: Mapped[int | None] = mapped_column(Integer, nullable=True)


# ══════════════════════════════════════════════════════════════════════════
# 3. 評論主表
# ══════════════════════════════════════════════════════════════════════════
class OtaReview(Base):
    """逐筆評論（三個平台統一欄位）"""

    __tablename__ = "ota_reviews"
    __table_args__ = (
        UniqueConstraint("source_id", "fingerprint", name="uq_ota_review_src_fp"),
        Index("ix_ota_review_hotel_month", "hotel_code", "review_month"),
        Index("ix_ota_review_platform_date", "platform", "review_date"),
        Index("ix_ota_review_alert", "is_alert", "alert_status"),
        Index("ix_ota_review_pending", "analyzed_at"),
        Index("ix_ota_review_cross_fp", "cross_fingerprint"),
        Index("ix_ota_review_sentiment", "sentiment_label"),
        Index("ix_ota_review_date", "review_date"),
        Index("ix_ota_review_source", "source_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ota_sources.id", ondelete="RESTRICT"), nullable=False
    )

    # ── 反正規化欄位（避免每次查詢都 join sources）───────────────────────
    hotel_code: Mapped[str] = mapped_column(String(20), default="")
    platform: Mapped[str] = mapped_column(String(20), default="")

    # ── 去重 ────────────────────────────────────────────────────────────
    external_id: Mapped[str] = mapped_column(String(200), default="")    # OTA 自身的評論 ID（有的話）
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)  # 同來源去重
    cross_fingerprint: Mapped[str] = mapped_column(String(64), default="")  # 跨 OTA 去重
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── 旅客資訊（只存 OTA 公開顯示的暱稱，不做身分關聯）─────────────────
    author: Mapped[str] = mapped_column(String(100), default="匿名旅客")
    nationality: Mapped[str] = mapped_column(String(50), default="")
    traveler_type: Mapped[str] = mapped_column(String(30), default="")   # 商務/情侶/家庭/獨自旅行
    room_type: Mapped[str] = mapped_column(String(100), default="")
    nights: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── 分數（三欄一組，缺一不可，理由見檔頭坑 1）─────────────────────────
    score_raw: Mapped[float | None] = mapped_column(Numeric(3, 1), nullable=True)
    score_scale: Mapped[int] = mapped_column(Integer, default=10)
    score_10: Mapped[float | None] = mapped_column(Numeric(3, 1), nullable=True)

    # ── 文字（正負評獨立成欄，不可合併）───────────────────────────────────
    title: Mapped[str] = mapped_column(String(300), default="")
    positive_text: Mapped[str] = mapped_column(Text, default="")
    negative_text: Mapped[str] = mapped_column(Text, default="")
    comment: Mapped[str] = mapped_column(Text, default="")   # 無正負分離的站別（Tripadvisor）

    # ── 日期（正規化為 ISO 字串；解析失敗填空字串並記 warning）───────────
    review_date: Mapped[str] = mapped_column(String(10), default="")
    review_month: Mapped[str] = mapped_column(String(7), default="")   # 寫入時算好，不 runtime substr
    stay_month: Mapped[str] = mapped_column(String(7), default="")
    review_url: Mapped[str] = mapped_column(String(500), default="")   # Drawer 的原始連結

    # ── 分析結果（P4 才會填，P1 全部留空）────────────────────────────────
    sentiment_label: Mapped[str] = mapped_column(String(10), default="")   # positive/neutral/negative
    sentiment_score: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    sentiment_engine: Mapped[str] = mapped_column(String(10), default="")  # rule/ai/manual
    topics_json: Mapped[str | None] = mapped_column(Text, nullable=True)   # JSON array，如 ["清潔:neg"]

    # ── 警示（人工營運欄位，同步與重新分析一律不可覆蓋）───────────────────
    is_alert: Mapped[bool] = mapped_column(Boolean, default=False)
    alert_status: Mapped[str] = mapped_column(String(20), default="open")  # open/acknowledged/resolved/ignored
    alert_note: Mapped[str] = mapped_column(Text, default="")
    alert_handler_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    alert_handled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ── 稽核 ────────────────────────────────────────────────────────────
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)   # 原始擷取結果，selector 失效時可回溯
    sync_log_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime, default=twnow)
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # NULL = 待分析


# ══════════════════════════════════════════════════════════════════════════
# 4. 主題關鍵字字典
# ══════════════════════════════════════════════════════════════════════════
class OtaTopicRule(Base):
    """
    規則式主題分類的字典，可由前端維護。
    `is_builtin=True` 的內建詞在畫面上不可刪除，只能停用（is_enabled=False）——
    刪掉之後沒有還原機制，停用是可逆的。
    """

    __tablename__ = "ota_topic_rules"
    __table_args__ = (
        UniqueConstraint("topic", "keyword", "polarity", name="uq_ota_topic_rule"),
        Index("ix_ota_topic_rule_topic", "topic", "is_enabled"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic: Mapped[str] = mapped_column(String(30))      # 清潔/隔音/服務/早餐/設備...
    keyword: Mapped[str] = mapped_column(String(50))
    polarity: Mapped[str] = mapped_column(String(10), default="negative")  # negative/positive/neutral
    weight: Mapped[int] = mapped_column(Integer, default=1)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)

    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=twnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=twnow, onupdate=twnow)


# ══════════════════════════════════════════════════════════════════════════
# 5. AI 補判快取
# ══════════════════════════════════════════════════════════════════════════
class OtaAnalysisCache(Base):
    """
    以評論文字的 sha256 為鍵，避免同一段文字重複送 API。

    ⚠️ 與 `app/models/ai_cache.py` 不同：那張是「工單問答」的快取，
    語意與 key 結構都不一樣，不可共用。
    """

    __tablename__ = "ota_analysis_cache"
    __table_args__ = (
        UniqueConstraint("content_hash", name="uq_ota_cache_hash"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    sentiment_label: Mapped[str] = mapped_column(String(10), default="")
    sentiment_score: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    topics_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str] = mapped_column(String(50), default="")
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=twnow)


# ══════════════════════════════════════════════════════════════════════════
# 7. ⭐ 平台清單（2026-08-23 改為資料驅動）
# ══════════════════════════════════════════════════════════════════════════
class OtaPlatform(Base):
    """
    OTA 平台清單。原本是寫死在 `ota_normalize.py` 的五個常數。

    ═══════════════════════════════════════════════════════════════════
    為什麼改成資料驅動
    ═══════════════════════════════════════════════════════════════════
    使用者要加 Hotels.com、Trip.com、KKday…… 每加一個就要改程式、
    重新部署。但**新增平台其實不需要寫任何邏輯** —— 只要有：

        代碼 / 顯示名稱 / 分制 / 網域

    就能建來源、匯入 CSV、跑分析、進統計。真正需要寫程式的只有
    「自動擷取器」那一件事，而那件事**本來就未必做得到**
    （Tripadvisor、Expedia 都被站方擋，只能走 --import-html）。

    把「能不能建平台」跟「能不能自動爬」綁在一起，等於讓後者的失敗
    連累前者 —— 使用者連把資料手動收進來一起分析都做不到。

    ═══════════════════════════════════════════════════════════════════
    ⚠️ `has_parser` 是**推導的，不存在這張表**
    ═══════════════════════════════════════════════════════════════════
    有沒有擷取器由 `ota_parser.PARSERS` 決定 —— 那是程式碼事實。
    存進 DB 會變成兩份真相，而且一定會不同步（有人寫了 parser 卻忘了
    改 DB，或反過來）。要用的時候現算，見 `platform_options()`。

    ⚠️ **內建平台不可刪除，只能停用**。內建的五個是既有評論的
       `platform` 欄位值，刪掉會讓那些評論的平台顯示變成孤兒代碼。
    """

    __tablename__ = "ota_platforms"
    __table_args__ = (
        UniqueConstraint("code", name="uq_ota_platform_code"),
        Index("ix_ota_platform_enabled", "is_enabled", "sort_order"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(30))       # booking / hotels_com …
    label: Mapped[str] = mapped_column(String(50))      # 顯示名稱
    # 5 或 10。⚠️ 只是**預設值** —— parser 或匯入時偵測到不同的以偵測為準。
    score_scale: Mapped[int] = mapped_column(Integer, default=10)
    # 這個平台的網域，逗號分隔（例：hotels.com,tw.hotels.com）。
    # 用來擋「網址與平台對不上」，留空就不比對。
    domains: Mapped[str] = mapped_column(String(300), default="")
    note: Mapped[str] = mapped_column(String(200), default="")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=twnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=twnow,
                                                        onupdate=twnow)


# ══════════════════════════════════════════════════════════════════════════
# 6. ⭐ AI 發現的字典外主題候選（2026-08-23）
# ══════════════════════════════════════════════════════════════════════════
class OtaTopicCandidate(Base):
    """
    AI 在評論裡看到、但**不在我們 12 個主題清單裡**的議題。

    ═══════════════════════════════════════════════════════════════════
    為什麼需要這張表
    ═══════════════════════════════════════════════════════════════════
    在此之前，AI 的 prompt 寫死「主題只能從這個清單選」。客人抱怨電梯很慢、
    泳池關閉、隔壁工地、寵物政策 —— AI 只有兩條路：**硬塞**進最接近的主題
    （於是「電梯很慢」變成「設備:neg」，統計上看不出電梯有問題），
    或者**直接不報**。兩種都讓我們永遠發現不了字典缺什麼。

    這張表把第三條路打開：AI 照實回報，累積成候選，管理員在
    「主題字典」頁面按一下就變成正式規則。**規則層因此會自己變強**：

        AI 發現 → 候選累積 → 人工確認 → 進字典 → 規則層免費抓到
                                              ↓
                                    下次同樣的評論不必再送 AI

    ═══════════════════════════════════════════════════════════════════
    ⚠️ 為什麼不直接寫進 `ota_topic_rules`
    ═══════════════════════════════════════════════════════════════════
    1. **AI 會產生同義詞爆炸**：「電梯」「升降梯」「電梯等很久」「電梯慢」
       會被當成四個主題。要先累積、合併、看過樣本，才知道該收哪一個。
    2. **主題清單是統計的維度**。悄悄多出一個主題，月度趨勢圖會憑空多一條線，
       而且沒人知道它是哪來的、可不可信。**必須經過人。**
    3. 候選有自己的生命週期欄位（出現次數、樣本、狀態），塞進規則表會讓
       那張表長出一堆只有候選才用得到的欄位。

    ⚠️ `sample_review_ids` 存的是 id 而非文字 —— 評論文字的著作權不屬於我們，
       不要在系統裡到處複製。要看樣本就用 id 回查。
    """

    __tablename__ = "ota_topic_candidates"
    __table_args__ = (
        UniqueConstraint("name", name="uq_ota_topic_candidate_name"),
        Index("ix_ota_topic_candidate_status", "status", "hit_count"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(30))           # AI 給的主題名（繁中）
    description: Mapped[str] = mapped_column(String(200), default="")
    # AI 建議的關鍵詞，JSON 陣列。管理員採納時直接變成 ota_topic_rules 的列
    keywords_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    neg_count: Mapped[int] = mapped_column(Integer, default=0)
    # 最多留 5 筆樣本評論 id，JSON 陣列
    sample_review_ids: Mapped[str | None] = mapped_column(Text, nullable=True)
    # pending（待確認）/ accepted（已收進字典）/ rejected（不要，之後不再提示）
    status: Mapped[str] = mapped_column(String(10), default="pending")
    reviewed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime, default=twnow)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, default=twnow, onupdate=twnow)
