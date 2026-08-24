"""
OTA 口碑分析 — 分析引擎（規則層 + AI 補判）

建立日期：2026-08-22
規格書：`docs/SPEC_ota_reviews.md` §7

═══════════════════════════════════════════════════════════════════════════
兩層設計：規則先跑，AI 只補規則判不出來的
═══════════════════════════════════════════════════════════════════════════
    每一則評論
        ↓
    ① 規則層（主題字典 + 分數門檻）—— 零成本、可離線、結果可解釋
        ↓
    ② 符合 A1–A4 才送 AI —— 只有「規則真的判不出來」或「分數與文字矛盾」

實測預期：雙館每月新增約 150 則，其中約 25% 觸發 AI、每批 20 則打包，
每月約 2 次 API 呼叫，成本可忽略。

═══════════════════════════════════════════════════════════════════════════
⚠️ 三件不可違反的事
═══════════════════════════════════════════════════════════════════════════
1. **AI 失敗不可中斷整批** —— 保留規則層結果，`sentiment_engine` 維持
   `rule`，記 warning。分析是加值不是必要條件，掛了不該讓資料進不來。

2. **人工填的警示欄位不可覆蓋** —— `alert_status` / `alert_note` /
   `alert_handler_id` / `alert_handled_at`。重新分析只更新 `is_alert`，
   不動處理狀態。使用者標了「已處理」，隔天排程把它變回「待處理」
   是最惱人的那種 bug。

3. **內建字典要能自我播種** —— `docs/add_ota_tables.sql` 有 77 筆種子，
   但那份 SQL **未必執行過**（`create_all()` 只建表不塞資料）。
   本模組每次分析前先跑 `ensure_builtin_topic_rules()` 冪等補齊，
   不依賴「有沒有人記得跑 SQL」。
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.time import twnow
from app.models.ota_review import (
    OtaAnalysisCache, OtaReview, OtaTopicCandidate, OtaTopicRule)
from app.services import ota_normalize
from app.services.ota_normalize import (NEGATIVE_SCORE_MAX, find_unnegated,
                                        keyword_variants, strip_noise)

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════
# 情緒與警示門檻（規格書 §7.2、§7.4）
# ══════════════════════════════════════════════════════════════════════════
POSITIVE_MIN = 8.0      # >= 8.0 正面
# ⚠️ 指向 `ota_normalize.NEGATIVE_SCORE_MAX`（見那裡的說明）。
NEGATIVE_MAX = NEGATIVE_SCORE_MAX   # <  此值為負面（6.0–8.0 之間為中立）

# 命中這些主題的負評，即使分數沒有低到門檻也要列入警示 ——
# 這三類是「會直接影響下一位客人」的，不能等分數掉下來才處理。
ALERT_TOPICS = ("清潔", "服務", "設備")

# ══════════════════════════════════════════════════════════════════════════
# ⚠️ 以下字數門檻是**針對中文**校準的，不可照抄英文語料的常見值
# ══════════════════════════════════════════════════════════════════════════
# 中文一個字元承載的資訊量約是英文的 2–3 倍：
#     「隔音真的很差，晚上走廊講話聽得一清二楚，早上六點就被吵醒，
#       而且冷氣聲音也很大，整晚幾乎沒睡好，這點希望能改善。」
# 這段是**五句話、四個具體抱怨**，卻只有 55 個字元。
#
# 2026-08-22 校準過程：初版把 A2 訂在 60 字，寫測試時連續三次想造「很長的
# 抱怨」都落在 40–55 字之間 —— 那不是測資寫得不夠長，是門檻本身對中文太高。
# 一個給 9 分卻還願意寫 40 字抱怨的客人，正是「分數與文字矛盾」最典型的樣子。
ALERT_NEGATIVE_TEXT_LEN = 100   # 警示：負評寫到這個長度，通常是真的有事
AI_CONFLICT_NEG_LEN = 40        # A2：高分卻寫了這麼長的負評
AI_LONG_TEXT_LEN = 300          # A4：長文多議題（中文 300 字已是很長的評論）
AI_BATCH_SIZE = 20              # 每批打包幾則送一次 API


# ══════════════════════════════════════════════════════════════════════════
# 內建主題字典（與 docs/add_ota_tables.sql 的種子一致）
# ══════════════════════════════════════════════════════════════════════════
# 格式：主題 → (負面詞, 正面詞)
BUILTIN_TOPICS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "清潔": (("髒", "灰塵", "霉", "頭髮", "蟑螂", "沒打掃", "不乾淨", "污漬"),
             ("乾淨", "整潔", "一塵不染")),
    "隔音": (("吵", "噪音", "隔音差", "隔音不好", "聽得到", "施工"),
             ("安靜", "隔音好", "很好睡")),
    "服務": (("態度", "冷漠", "不理", "等很久", "擺臉色", "沒禮貌"),
             ("親切", "貼心", "熱情", "服務好")),
    "早餐": (("早餐難吃", "選擇少", "冷掉", "種類不多"),
             ("豐盛", "早餐好吃", "選擇多")),
    "設備": (("故障", "老舊", "水壓", "沒熱水", "冷氣不冷", "壞掉"),
             ("設備齊全", "很新")),
    "房間": (("房間小", "很暗", "壓迫", "床硬"),
             ("寬敞", "舒適", "採光好")),
    # ⚠️「捷運近」「離捷運遠」看起來不像人話，是**故意**這樣寫的 ——
    #    `keyword_variants()` 會把它展成「捷運很近／捷運超近／捷運真的很近」
    #    這些真正會出現的說法。字典裡放最短的骨架，變體交給展開器。
    # ⚠️「很方便」已於 2026-08-23 移除 —— ASAP 實測 112 次命中有 61 次誤觸發：
    #    「吃起來很方便」「點菜很方便」「下單很方便」。它是純形容詞，什麼都能修飾，
    #    飯店同理（「熱水壺很方便」「寄放行李很方便」）。要留就得帶主詞。
    "位置": (("偏僻", "難找", "交通不便", "交通不方便", "離捷運遠", "離地鐵遠"),
             ("地點好", "地點方便", "交通方便", "位置方便",
              "近捷運", "近地鐵", "捷運近", "地鐵近")),
    "價格": (("太貴", "不值", "CP值低", "性價比低"),
             ("划算", "超值", "CP值高", "性價比高")),
    # ⚠️ 原本只有 3 個詞，ASAP 實測漏抓 96.6%（323 則提到停車只抓到 11 則）。
    #    客人實際寫的是「有停車位」「免費停車」「地下停車場」「停車便利」。
    "停車": (("沒車位", "停車困難", "停車不便", "停車不方便", "車位不足", "車位少"),
             ("停車方便", "停車便利", "有停車位", "有車位", "免費停車", "停車場")),
    "Wi-Fi": (("網路慢", "網速慢", "連不上", "訊號差", "信號差"), ("網速快",)),
    "氣味": (("霉味", "菸味", "煙味", "怪味"), ()),
    "入住流程": (("排隊", "押金"), ("入住快速",)),
}

# ⚠️ 上面幾個看起來重複的詞是**刻意的**，不要「順手」清掉：
#
#   近捷運／近地鐵     CP值／性價比      訊號差／信號差      菸味／煙味
#
# 這些是**用詞差異**而不是字形差異 —— `zh_variants()` 用 OpenCC 轉字形，
# 轉得出 髒→脏、寬敞→宽敞，但轉不出「捷運→地铁」（那是兩個不同的詞）。
# 台灣人寫「近捷運」、中國旅客寫「近地铁」，兩邊都要收才抓得到。
#
# 判斷方法：把詞丟進 `zh_variants()`，只回傳自己一個 → 就是用詞差異，
# 必須另外收一筆進字典。


def ensure_builtin_topic_rules(db: Session) -> int:
    """
    冪等補齊內建字典。回傳這次新增了幾筆。

    ⚠️ **不能只靠 `docs/add_ota_tables.sql`** —— `create_all()` 只建表不塞資料，
       那份 SQL 未必有人執行過。字典是空的時候，規則層會安靜地什麼都分不出來
       （不會報錯，只會每一則都沒有主題），非常難察覺。

    ⚠️ 只補**缺少的**，不覆蓋既有列 —— 使用者可能已經把某個內建詞停用了
       （`is_enabled=False`），重跑不該把它復活。
    """
    existing = {
        (topic, keyword, polarity)
        for topic, keyword, polarity in db.execute(
            select(OtaTopicRule.topic, OtaTopicRule.keyword, OtaTopicRule.polarity)
        ).all()
    }

    added = 0
    for topic, (negatives, positives) in BUILTIN_TOPICS.items():
        for keyword in negatives:
            if (topic, keyword, "negative") not in existing:
                db.add(OtaTopicRule(topic=topic, keyword=keyword,
                                    polarity="negative", is_builtin=True))
                added += 1
        for keyword in positives:
            if (topic, keyword, "positive") not in existing:
                db.add(OtaTopicRule(topic=topic, keyword=keyword,
                                    polarity="positive", is_builtin=True))
                added += 1

    if added:
        db.flush()
        logger.info("[OTA] 補齊內建主題字典 %d 筆", added)
    return added


@dataclass
class RuleSet:
    """字典查出來後預先整理好的比對表，避免每則評論都重查 DB。"""

    negative: list[tuple[str, str]] = field(default_factory=list)   # (topic, keyword)
    positive: list[tuple[str, str]] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.negative and not self.positive


def load_rules(db: Session) -> RuleSet:
    """
    載入啟用中的字典。關鍵詞先做 `strip_noise` 正規化，與比對時一致。

    ⭐ **每個關鍵詞都展開成簡繁變體**（2026-08-23）。
       字典是繁體寫的，但 Booking／Agoda 的簡體評論者一樣會抱怨清潔與隔音。
       不展開的話 77 個詞裡有 47 個（61%）在簡體評論上永遠比不中，
       而且**不會報錯** —— 那些評論只是安靜地沒有主題。
       詳見 `ota_normalize.zh_variants()`。
    """
    rules = RuleSet()
    for topic, keyword, polarity in db.execute(
        select(OtaTopicRule.topic, OtaTopicRule.keyword, OtaTopicRule.polarity)
        .where(OtaTopicRule.is_enabled.is_(True))
    ).all():
        bucket = rules.positive if polarity == "positive" else rules.negative
        for variant in keyword_variants(keyword):
            normalized = strip_noise(variant)
            if normalized and (topic, normalized) not in bucket:
                bucket.append((topic, normalized))
    return rules


# ══════════════════════════════════════════════════════════════════════════
# 規則層
# ══════════════════════════════════════════════════════════════════════════
@dataclass
class RuleResult:
    topics: list[str]               # ["清潔:neg", "服務:pos"]
    sentiment: str                  # positive / neutral / negative / ""（判不出來）
    score: float | None             # -1.00 ~ 1.00
    needs_ai: bool
    ai_reason: str                  # A1 / A2 / A3 / A4，供除錯與統計


def classify_topics(review: OtaReview, rules: RuleSet) -> list[str]:
    """
    主題分類。回傳 `["清潔:neg", "服務:pos"]` 形式。

    ⚠️ **極性優先序**：同一主題正負詞都命中時，**以出現在 `negative_text`
       的為準**。客人自己把負面意見分開寫在負評欄，那是他最明確的表態；
       若判成正面，這則評論就不會進負評警示，等於漏掉一個客訴。

    ⚠️ 比對前雙方都做 `strip_noise`（去標點空白、轉小寫、全形轉半形）——
       「隔音 差」「隔音差」「隔音，差」在客人眼裡是同一件事。
    """
    if rules.is_empty:
        return []

    negative_field = strip_noise(review.negative_text or "")
    positive_field = strip_noise(review.positive_text or "")
    other = strip_noise(" ".join([review.title or "", review.comment or ""]))
    whole = negative_field + positive_field + other

    hits: dict[str, str] = {}       # topic → "neg" / "pos"

    # ⭐ 用 find_unnegated 而不是 `in`：「不用排隊」不該算成排隊（2026-08-23）
    for topic, keyword in rules.positive:
        if find_unnegated(whole, keyword):
            hits[topic] = "pos"

    for topic, keyword in rules.negative:
        if find_unnegated(whole, keyword):
            hits[topic] = "neg"

    # ⭐ 最後再掃一次「只看負評欄」—— 這一輪的結果最權威，
    #    客人明確寫在負評欄的東西不可能是正面的
    for topic, keyword in rules.negative:
        if negative_field and find_unnegated(negative_field, keyword):
            hits[topic] = "neg"

    # 反過來也成立：只出現在正評欄、且負評欄沒提到的，維持正面
    for topic, keyword in rules.positive:
        if (positive_field and find_unnegated(positive_field, keyword)
                and hits.get(topic) != "neg"):
            hits[topic] = "pos"

    return [f"{topic}:{polarity}" for topic, polarity in sorted(hits.items())]


def classify_sentiment(review: OtaReview) -> tuple[str, float | None]:
    """
    情緒判定（規格書 §7.2）。回傳 `(label, score)`；label 為空字串代表判不出來。

    有分數時以分數為準 —— 那是客人自己給的總結，比任何文字分析都可靠。
    """
    if review.score_10 is not None:
        value = float(review.score_10)
        if value >= POSITIVE_MIN:
            # 8.0→+0.6，10.0→+1.0 線性映射
            return "positive", round(0.6 + (value - POSITIVE_MIN) * 0.2, 2)
        if value < NEGATIVE_MAX:
            # 6.0→-0.2，0→-1.0
            return "negative", round(-1.0 + value * (0.8 / NEGATIVE_MAX), 2)
        return "neutral", round((value - 7.0) * 0.2, 2)

    # 沒有分數：只靠正負評欄位是否有內容
    has_pos = bool((review.positive_text or "").strip())
    has_neg = bool((review.negative_text or "").strip())
    if has_pos and not has_neg:
        return "positive", 0.6
    if has_neg and not has_pos:
        return "negative", -0.6
    return "", None         # 兩者皆有或皆無 → 交給 AI


def should_use_ai(review: OtaReview, sentiment: str, topics: list[str]) -> tuple[bool, str]:
    """
    是否送 AI（規格書 §7.3 A1–A4）。

    ⚠️ 這四條是**白名單**不是黑名單 —— 預設不送。
       每多送一則就是成本，而規則層對絕大多數評論已經夠準。
    """
    negative_len = len((review.negative_text or "").strip())
    body_len = len(" ".join([
        review.positive_text or "", review.negative_text or "", review.comment or "",
    ]).strip())

    if review.score_10 is None and not sentiment:
        return True, "A1 無分數且規則判不出情緒"
    if review.score_10 is not None and float(review.score_10) >= POSITIVE_MIN \
            and negative_len > AI_CONFLICT_NEG_LEN:
        return True, "A2 高分卻有長負評（分數與文字矛盾）"
    if review.score_10 is not None and float(review.score_10) < NEGATIVE_MAX \
            and not topics:
        return True, "A3 低分卻分不出主題（掉分不知原因）"
    if body_len > AI_LONG_TEXT_LEN:
        return True, "A4 長文多議題"
    return False, ""


def compute_alert(review: OtaReview, sentiment: str, topics: list[str]) -> bool:
    """
    是否列入負評警示（規格書 §7.4）。

    ⚠️ 只算 `is_alert`。**`alert_status` 是人工欄位，這裡絕對不碰** ——
       使用者標了「已處理」，隔天排程把它變回「待處理」是最惱人的那種 bug。
    """
    if review.score_10 is not None and float(review.score_10) < NEGATIVE_MAX:
        return True
    if sentiment == "negative":
        names = {t.split(":")[0] for t in topics if t.endswith(":neg")}
        if names & set(ALERT_TOPICS):
            return True
    if len((review.negative_text or "").strip()) > ALERT_NEGATIVE_TEXT_LEN:
        return True
    return False


def analyze_by_rules(review: OtaReview, rules: RuleSet) -> RuleResult:
    """單則評論的規則層分析。"""
    topics = classify_topics(review, rules)
    sentiment, score = classify_sentiment(review)
    needs_ai, reason = should_use_ai(review, sentiment, topics)
    return RuleResult(topics=topics, sentiment=sentiment, score=score,
                      needs_ai=needs_ai, ai_reason=reason)


# ══════════════════════════════════════════════════════════════════════════
# AI 補判層
# ══════════════════════════════════════════════════════════════════════════
# ⚠️ **刻意維持簡單的 zero-shot 指令，不要疊 CoT／自我檢查／多輪辯論。**
#    2025 年一篇多語 ABSA 評測（arXiv 2412.12564，已發表於 Int. J. Machine
#    Learning and Cybernetics）比較了 9 個 LLM 的各種提示策略，結論是
#    **簡單 zero-shot 常常勝過 CoT、self-consistency、self-debate**，
#    在高資源語言尤其明顯。疊上去只會讓 token 變多、延遲變長。
AI_SYSTEM_PROMPT = """你是飯店口碑分析助手。使用者會給你一批住客評論，
請判斷每一則的情緒與涉及的主題。

已知主題清單（可多選、可不選）：
清潔、隔音、服務、早餐、設備、房間、位置、價格、停車、Wi-Fi、氣味、入住流程

規則：
- sentiment 只能是 positive / neutral / negative 三者之一
- score 是 -1.0（極負面）到 1.0（極正面）的數字
- topics 用「主題:neg」或「主題:pos」表示該主題是被抱怨還是被稱讚
- 分數與文字矛盾時（例如給高分卻抱怨很多），以**文字內容**為準
- 只回 JSON 陣列，不要任何說明文字

⭐ 清單外的議題請放進 new_topics，**不要硬塞進最接近的已知主題**：
- 客人明確在談、但上面清單涵蓋不到的事情（例如電梯、泳池、健身房、
  洗衣、寵物、無障礙、鄰近工地、房型與訂房不符）
- name 用 2–5 個字的繁體中文名詞（「電梯」而不是「電梯很慢」）
- keywords 給 2–5 個客人實際會寫的詞，繁體中文
- 已知清單涵蓋得到的就用 topics，不要重複放進 new_topics
- 沒有就給空陣列

輸出格式（idx 必須對應輸入的編號）：
[{"idx":0,"sentiment":"negative","score":-0.7,"topics":["隔音:neg"],
  "new_topics":[{"name":"電梯","polarity":"neg","keywords":["電梯慢","等電梯"]}]}]"""


def _content_hash(review: OtaReview) -> str:
    """快取鍵：只看會影響判斷的文字，分數變動不需要重問。"""
    payload = "\n".join([
        review.title or "", review.positive_text or "",
        review.negative_text or "", review.comment or "",
    ])
    return hashlib.sha256(payload.encode("utf-8", "ignore")).hexdigest()


def _review_to_prompt(index: int, review: OtaReview) -> str:
    parts = [f"[{index}]"]
    if review.score_10 is not None:
        parts.append(f"分數：{float(review.score_10):.1f}/10")
    if review.title:
        parts.append(f"標題：{review.title}")
    if review.positive_text:
        parts.append(f"正評：{review.positive_text}")
    if review.negative_text:
        parts.append(f"負評：{review.negative_text}")
    if review.comment:
        parts.append(f"留言：{review.comment}")
    return "\n".join(parts)


def _call_ai(batch: list[OtaReview]) -> tuple[dict[int, dict], str]:
    """
    呼叫 Anthropic API 判斷一批評論。回傳 `({idx: result}, warning)`。

    ⚠️ **刻意不用 `ai_service.run_ai_query()`** —— 那支是為「工單自然語言查詢」
       寫的：必帶 `db` 與 `allowed_locations`，內部走 repair case 的 tool-use
       流程，回傳 `{"answer", "has_table", "table_data", ...}`。
       與「丟 20 則評論、回一個 JSON 陣列」語意完全不同，硬套只會更難維護。
       這裡沿用它的 client 初始化慣例（`anthropic.Anthropic` + `ANTHROPIC_MODEL`）。

    ⚠️ 任何失敗都只回 warning，**不拋例外** —— 呼叫端會保留規則層結果。
    """
    if not settings.ANTHROPIC_API_KEY:
        return {}, "未設定 ANTHROPIC_API_KEY，跳過 AI 補判（保留規則層結果）"

    try:
        import anthropic
    except ImportError:
        return {}, "未安裝 anthropic 套件，跳過 AI 補判"

    prompt = "\n\n".join(_review_to_prompt(i, r) for i, r in enumerate(batch))

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=getattr(settings, "ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
            max_tokens=2048,
            system=AI_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        ).strip()
    except Exception as exc:            # noqa: BLE001 —— API 失敗不可中斷整批
        return {}, f"AI 呼叫失敗（保留規則層結果）：{str(exc)[:160]}"

    # 模型偶爾會用 ```json 包起來，去掉再解析
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        if text.startswith("json"):
            text = text[4:].strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}, f"AI 回傳的不是合法 JSON（保留規則層結果）：{text[:120]}"

    if not isinstance(data, list):
        return {}, "AI 回傳的不是陣列（保留規則層結果）"

    parsed: dict[int, dict] = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        idx = item.get("idx")
        if not isinstance(idx, int) or not (0 <= idx < len(batch)):
            continue
        sentiment = str(item.get("sentiment", "")).strip().lower()
        if sentiment not in ("positive", "neutral", "negative"):
            continue        # 值不對就當這一則沒判到，保留規則層結果
        topics = [str(t) for t in item.get("topics", []) if isinstance(t, str)]
        try:
            score = float(item.get("score"))
        except (TypeError, ValueError):
            score = None
        parsed[idx] = {"sentiment": sentiment, "score": score, "topics": topics,
                       "new_topics": _parse_new_topics(item.get("new_topics"))}

    return parsed, ""


# 主題名的長度上限。太長的多半是 AI 把整句抱怨當成主題名
# （「電梯等很久而且很擠」），那種收進來只會變成一次性的垃圾主題。
CANDIDATE_NAME_MAX = 10
CANDIDATE_KEYWORD_MAX = 12
CANDIDATE_KEYWORDS_PER_TOPIC = 5


def _parse_new_topics(raw) -> list[dict]:
    """
    解析 AI 回報的字典外主題，並**擋掉會污染候選清單的東西**。

    ⚠️ 這裡的防守比一般的 JSON 解析嚴格，因為候選清單是要給人看的：
       混進十幾個「電梯等很久而且很擠」這種一次性長句，管理員會直接放棄看它，
       整個「AI 發現 → 人工確認 → 進字典」的閉環就斷在這裡。

    擋掉的東西：
      · 名字太長（多半是把整句抱怨當主題名）
      · 名字其實就是已知主題（AI 偶爾會忽略「不要重複」的指示）
      · 空的或不是字串的關鍵詞
    """
    if not isinstance(raw, list):
        return []
    known = {t.lower() for t in BUILTIN_TOPICS}
    out: list[dict] = []
    for entry in raw[:10]:              # 一則評論最多收 10 個，多的不看
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name", "")).strip()
        if not name or len(name) > CANDIDATE_NAME_MAX or name.lower() in known:
            continue
        keywords = [
            str(k).strip() for k in entry.get("keywords", [])
            if isinstance(k, str) and k.strip()
            and len(str(k).strip()) <= CANDIDATE_KEYWORD_MAX
        ][:CANDIDATE_KEYWORDS_PER_TOPIC]
        polarity = str(entry.get("polarity", "")).strip().lower()
        out.append({
            "name": name,
            "keywords": keywords,
            "polarity": "neg" if polarity.startswith("neg") else "pos",
        })
    return out


def record_topic_candidates(db: Session, review: OtaReview,
                            new_topics: list[dict]) -> int:
    """
    把 AI 回報的字典外主題累積進候選表。回傳新建立幾個。

    ⚠️ **已被否決（rejected）的候選不復活**。管理員說過「這個不要」之後，
       下次 AI 又報一樣的東西不該再跳出來 —— 只更新次數，狀態不動。
       否則那個否決按鈕等於沒有用。

    ⚠️ 樣本只留 5 筆 **id**，不存評論文字（著作權不屬於我們，
       而且文字改了之後兩邊會不一致）。
    """
    created = 0
    for entry in new_topics:
        name = entry["name"]
        candidate = db.execute(
            select(OtaTopicCandidate).where(OtaTopicCandidate.name == name)
        ).scalar_one_or_none()

        if candidate is None:
            candidate = OtaTopicCandidate(
                name=name,
                keywords_json=json.dumps(entry["keywords"], ensure_ascii=False),
                sample_review_ids=json.dumps([review.id]),
                hit_count=1,
                neg_count=1 if entry["polarity"] == "neg" else 0,
            )
            db.add(candidate)
            # ⚠️ **一定要 flush**。本函式在 `analyze_pending` 裡是**逐則呼叫、
            #    整批才 commit**，而同一批 20 則評論很可能都提到同一個新主題
            #    （這正是它會被 AI 報出來的原因）。
            #
            #    不 flush 的話上面那個 select 看不到還在 session 裡的新列，
            #    於是每一則都各建一列 → commit 時 UNIQUE 違反 →
            #    **整個分析批次拋 IntegrityError 掛掉**，連規則層的結果一起賠掉。
            #
            #    這種錯只會在「同批出現重複主題」時發生，單筆測試永遠看不到。
            db.flush()
            created += 1
            continue

        candidate.hit_count += 1
        if entry["polarity"] == "neg":
            candidate.neg_count += 1
        candidate.last_seen_at = twnow()

        # 樣本補到 5 筆為止
        try:
            samples = json.loads(candidate.sample_review_ids or "[]")
        except (TypeError, ValueError):
            samples = []
        if review.id not in samples and len(samples) < 5:
            samples.append(review.id)
            candidate.sample_review_ids = json.dumps(samples)

        # 關鍵詞取聯集（AI 每次可能給不同的詞，多蒐一些給管理員挑）
        try:
            existing = json.loads(candidate.keywords_json or "[]")
        except (TypeError, ValueError):
            existing = []
        merged = existing + [k for k in entry["keywords"] if k not in existing]
        if merged != existing:
            candidate.keywords_json = json.dumps(merged[:10], ensure_ascii=False)

    return created


# ══════════════════════════════════════════════════════════════════════════
# 主流程
# ══════════════════════════════════════════════════════════════════════════
def _apply(review: OtaReview, *, topics: list[str], sentiment: str,
           score: float | None, engine: str) -> None:
    """
    把分析結果寫回評論。

    ⚠️ **只動分析欄位與 `is_alert`**。
       `alert_status` / `alert_note` / `alert_handler_id` / `alert_handled_at`
       是人工填的，這裡碰了就會把使用者標的「已處理」洗掉。
    """
    review.topics_json = json.dumps(topics, ensure_ascii=False) if topics else None
    review.sentiment_label = sentiment
    review.sentiment_score = score
    review.sentiment_engine = engine
    review.is_alert = compute_alert(review, sentiment, topics)
    review.analyzed_at = twnow()


def analyze_pending(db: Session, *, limit: int = 500,
                    rerun_all: bool = False) -> dict:
    """
    分析待處理的評論。

    `rerun_all=True` 會重跑全部（改了字典之後要用）——
    但**不會**清掉人工填的警示處理狀態。

    ⚠️ 自己開 session 的版本是 `run_scheduled_analyze()`，
       這一支要求呼叫端給 db（比照其他 service）。
    """
    added = ensure_builtin_topic_rules(db)
    rules = load_rules(db)

    warnings: list[str] = []
    if rules.is_empty:
        # 字典空的話規則層會安靜地什麼都分不出來 —— 這種沉默失敗要講出來
        warnings.append("主題字典是空的，所有評論都不會有主題標籤")

    # ⭐ opencc 沒裝 → 簡繁變體展不開 → 簡體評論安靜地少掉一半主題。
    #    這種降級**絕對不能靜默**：症狀（簡體評論沒有主題）與原本的 bug
    #    一模一樣，而且不會有任何錯誤訊息可查。
    #    ⚠️ 必須在 `load_rules()` **之後**才讀這個旗標 —— 它是在第一次真的
    #       嘗試轉換時才會被設成 False（import 當下還是預設的 True）。
    if not ota_normalize.ZH_CONVERT_AVAILABLE:
        warnings.append(
            "opencc 未安裝，主題字典無法展開簡繁變體 —— "
            "簡體中文評論會少掉約六成的主題標籤（不會報錯，只會安靜地沒有主題）。"
            "請執行 pip install opencc-python-reimplemented"
        )

    stmt = select(OtaReview).where(OtaReview.is_duplicate.is_(False))
    if not rerun_all:
        stmt = stmt.where(OtaReview.analyzed_at.is_(None))
    reviews = db.execute(stmt.order_by(OtaReview.id).limit(limit)).scalars().all()

    if not reviews:
        return {"total": 0, "rule_count": 0, "ai_count": 0, "cache_hit": 0,
                "new_candidates": 0,
                "alert_count": 0, "seeded_rules": added,
                "warnings": warnings, "errors": []}

    # ── ① 規則層：全部先跑一遍 ────────────────────────────────────────
    pending_ai: list[tuple[OtaReview, RuleResult]] = []
    rule_count = 0
    for review in reviews:
        result = analyze_by_rules(review, rules)
        # 規則判不出情緒時先給中立，AI 判得出來再覆蓋 ——
        # 留空字串會讓前端顯示「尚未分析」，但它其實分析過了
        _apply(review, topics=result.topics,
               sentiment=result.sentiment or "neutral",
               score=result.score, engine="rule")
        rule_count += 1
        if result.needs_ai:
            pending_ai.append((review, result))

    # ── ② AI 補判：先查快取，剩下的才打 API ──────────────────────────
    ai_count = 0
    cache_hit = 0
    new_candidates = 0
    to_call: list[OtaReview] = []

    for review, _result in pending_ai:
        digest = _content_hash(review)
        cached = db.execute(
            select(OtaAnalysisCache).where(OtaAnalysisCache.content_hash == digest)
        ).scalar_one_or_none()
        if cached:
            try:
                topics = json.loads(cached.topics_json) if cached.topics_json else []
            except (json.JSONDecodeError, TypeError):
                topics = []
            _apply(review, topics=topics, sentiment=cached.sentiment_label,
                   score=float(cached.sentiment_score) if cached.sentiment_score is not None else None,
                   engine="ai")
            cache_hit += 1
        else:
            to_call.append(review)

    model = getattr(settings, "ANTHROPIC_MODEL", "")
    for start in range(0, len(to_call), AI_BATCH_SIZE):
        batch = to_call[start:start + AI_BATCH_SIZE]
        parsed, warning = _call_ai(batch)
        if warning:
            warnings.append(warning)
            # ⚠️ 不 break —— 後面的批次可能是暫時性失敗後恢復。
            #    但也不重試，避免 API 掛掉時卡在這裡很久。
            continue
        for index, review in enumerate(batch):
            item = parsed.get(index)
            if not item:
                continue        # 這一則 AI 沒判到，保留規則層結果
            _apply(review, topics=item["topics"], sentiment=item["sentiment"],
                   score=item["score"], engine="ai")
            ai_count += 1
            # ⭐ AI 看到字典外的議題就累積成候選，等人確認後再進字典
            new_candidates += record_topic_candidates(
                db, review, item.get("new_topics") or [])
            db.add(OtaAnalysisCache(
                content_hash=_content_hash(review),
                sentiment_label=item["sentiment"],
                sentiment_score=item["score"],
                topics_json=json.dumps(item["topics"], ensure_ascii=False),
                model=model,
            ))

    db.commit()

    alert_count = sum(1 for r in reviews if r.is_alert)
    if new_candidates:
        # 講出來，不然這張表會靜靜地長大而沒人去看
        warnings.append(
            f"AI 發現 {new_candidates} 個字典外的新主題，"
            f"請到「主題字典」頁面確認要不要收進字典"
        )
    logger.info("[OTA] 分析完成：規則 %d、AI %d、快取命中 %d、警示 %d、新候選 %d",
                rule_count, ai_count, cache_hit, alert_count, new_candidates)

    return {
        "total": len(reviews),
        "rule_count": rule_count,
        "ai_count": ai_count,
        "cache_hit": cache_hit,
        "ai_candidates": len(pending_ai),
        "alert_count": alert_count,
        "new_candidates": new_candidates,
        "seeded_rules": added,
        # ⚠️ warnings 不進 errors —— AI 掛掉不是「同步失敗」，
        #    規則層的結果還在（§9 規則 8）
        "warnings": warnings,
        "errors": [],
    }


def run_scheduled_analyze() -> dict:
    """
    `main.py` APScheduler（每日 03:40）與 `sync_tool.py` 的共同入口。

    ⚠️ 契約（`sync_tool.py` 第 1003-1017 行）：不接參數、回傳含
       `fetched` / `upserted` / `errors`。
    ⚠️ 自己開 session（`sync_tool.py` 不會傳 db 進來）。
    ⚠️ **不加鎖** —— `sync_tool.py` 外層已套 `sync_lock`。
       APScheduler 那條路徑由 `main.py` 的排程函式自己包。
    """
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        result = analyze_pending(db, limit=2000)
        # 對齊 sync_tool 的欄位命名
        result["fetched"] = result["total"]
        result["upserted"] = result["rule_count"]
        return result
    finally:
        db.close()
