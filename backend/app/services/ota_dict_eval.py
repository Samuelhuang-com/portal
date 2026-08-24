"""
OTA 口碑分析 — 主題字典外部驗證工具

建立日期：2026-08-23
規格書：`docs/SPEC_ota_reviews.md` §7.7

═══════════════════════════════════════════════════════════════════════════
這支工具在回答一個我們原本答不出來的問題
═══════════════════════════════════════════════════════════════════════════
主題字典有 80 幾個關鍵詞。**其中有多少會誤觸發？**

「誤觸發」＝評論根本沒在談這件事，字典卻標了那個主題。例如：

    「早餐選擇少」→ 命中「選擇少」→ 標「早餐:neg」        ✅ 對
    「停車位選擇少」→ 也命中「選擇少」→ 標「早餐:neg」    ❌ 錯

第二種在我們自己的資料上**看不出來** —— 沒有正確答案可以比對，
只能靠人一則一則翻，而且翻的人會不自覺地只挑自己想得到的例子。

ASAP 資料集提供了正確答案：46,730 則評論、18 個面向、每個面向標了
`1`(正面) / `0`(中性) / `-1`(負面) / **`-2`(未提及)**。

**`-2` 就是我們要的東西** —— 評論確定沒提到這個面向，
如果我們的字典還是標了，那就是一次誤觸發。

═══════════════════════════════════════════════════════════════════════════
⚠️ 四個必須先講清楚的限制，不然結論會被過度解讀
═══════════════════════════════════════════════════════════════════════════
1. **領域是餐廳不是飯店**。服務／環境／價格／衛生／等候重疊度高，
   但「早餐」「房間」「隔音」「Wi-Fi」「停車」在餐廳語料裡對不上，
   本工具**不會**去評這幾個主題（見 `ASPECT_MAP` 只映射得到的那幾個）。

2. **語料是簡體**。這正是 2026-08-23 發現 61% 字典在簡體上失效的來源。
   修好之後這反而是優點：它同時驗證了簡繁展開有沒有真的生效。

3. **ASAP 的面向比我們的主題細**。例如 `Ambience#Sanitary`（衛生）
   對得上我們的「清潔」，但 `Ambience#Decoration`（裝潢）我們沒有對應主題。
   對不上的一律略過，不硬湊。

4. **這是離線評測，資料不進 DB、不進產品輸出**。
   ASAP 是 Apache-2.0，但**原始評論文字的著作權不屬於上傳者** ——
   不可散布、不可納入產品輸出、不可拿去微調後公開權重。

═══════════════════════════════════════════════════════════════════════════
怎麼用
═══════════════════════════════════════════════════════════════════════════
最快的做法 —— 讓工具自己下載（Apache-2.0，存到 Temp/，不進版控）：

    cd backend
    python -m app.services.ota_dict_eval --download

已經有檔案的話直接指定路徑：

    python -m app.services.ota_dict_eval  C:\\somewhere\\dev.csv

輸出會列出每個主題的誤觸發率，以及**是哪幾個關鍵詞造成的**。
最後那份「元凶排行」是真正可以拿來改字典的東西。
"""
from __future__ import annotations

import csv
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from app.services.ota_analysis_service import BUILTIN_TOPICS
from app.services.ota_normalize import (ZH_CONVERT_AVAILABLE, find_unnegated,
                                        keyword_variants, strip_noise)

# ══════════════════════════════════════════════════════════════════════════
# ASAP 面向 → 我們的主題
# ══════════════════════════════════════════════════════════════════════════
# ⚠️ 只映射**語意真的對得上**的。對不上的寧可不評，也不要硬湊 ——
#    硬湊出來的誤觸發率會把「領域不同」誤算成「字典不準」，
#    然後我們會去改一個根本沒壞的字典。
#
# 沒有映射的 ASAP 面向：Location#Downtown（是否在市中心）、
#   Location#Easy_to_find、Service#Timely（上菜快慢）、Price#Discount、
#   Ambience#Decoration（裝潢）、Food#*（五個都是菜色，飯店沒有對應）
#
# 沒有被驗到的我們的主題：早餐、房間、隔音、Wi-Fi、氣味、設備
#   —— 餐廳語料裡沒有這些面向的標註，**不是字典不好，是驗不到**。
ASPECT_MAP: dict[str, str] = {
    "Ambience#Sanitary": "清潔",
    "Ambience#Noise": "隔音",        # ⭐ 吵不吵 —— 與「隔音」完全對得上
    "Ambience#Space": "房間",        # 空間大小
    "Service#Hospitality": "服務",
    "Service#Timely": "服務",        # ⭐ 等多久 —— 我們的「等很久」就在服務底下
    "Service#Queue": "入住流程",     # 排隊等候，兩邊都是「等」
    "Service#Parking": "停車",
    "Location#Transportation": "位置",
    "Location#Easy_to_find": "位置",  # ⭐ 好不好找 —— 我們的「難找」就是這個
    "Location#Downtown": "位置",      # ⭐ 在不在市中心 —— 我們的「偏僻」就是這個
    "Price#Level": "價格",
    "Price#Cost_effective": "價格",  # 兩個都對到「價格」，取「有提到就算提到」
}

# ⚠️⚠️ 2026-08-23 第一版這張表**漏了四個對得上的面向**，直接產生了假結論：
#
#   Location#Easy_to_find 沒映射 → 「難找」61 次正確命中裡有 46 次被算成誤觸發
#                                  （實測 35 則 ASAP 標了 Easy_to_find = -1，
#                                   也就是**我們是對的**）
#   Ambience#Noise 沒映射         → 我還在報告裡寫「隔音驗不到」，其實驗得到
#
# 教訓：**映射表寫窄，症狀是「字典看起來很爛」**。
# 那份假的誤觸發率會讓人去改一個根本沒壞的字典 —— 這比不驗還糟。
# 之後要新增主題時，務必把 18 個面向逐一看過再決定映射與否，不要憑印象。

NOT_MENTIONED = "-2"


@dataclass
class TopicStat:
    """單一主題的統計。"""

    fired_and_mentioned: int = 0    # 我們標了、評論也真的有提 → 對
    fired_not_mentioned: int = 0    # 我們標了、評論其實沒提 → ❌ 誤觸發
    missed: int = 0                 # 評論有提、我們沒標 → 漏抓
    quiet: int = 0                  # 都沒有 → 對
    # 誤觸發時是哪個關鍵詞害的（這才是能拿來改字典的東西）
    culprits: Counter = field(default_factory=Counter)

    @property
    def fired(self) -> int:
        return self.fired_and_mentioned + self.fired_not_mentioned

    @property
    def mentioned(self) -> int:
        return self.fired_and_mentioned + self.missed

    @property
    def false_positive_rate(self) -> float:
        """我們標出來的裡面，有多少其實是錯的。"""
        return self.fired_not_mentioned / self.fired if self.fired else 0.0

    @property
    def recall(self) -> float:
        """真的有提到的裡面，我們抓到多少。"""
        return self.fired_and_mentioned / self.mentioned if self.mentioned else 0.0


def _flat_rules() -> list[tuple[str, str, str]]:
    """
    把內建字典攤平成 `(主題, 原始關鍵詞, 正規化後的變體)`。

    ⚠️ 保留**原始關鍵詞**是關鍵 —— 誤觸發報告要能講出「是『選擇少』這個詞
       害的」。只留正規化後的變體的話，簡體變體會出現在報告裡
       （「选择少」），但字典裡根本沒這一筆，使用者會找不到要改哪裡。
    """
    out: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str]] = set()
    for topic, (negatives, positives) in BUILTIN_TOPICS.items():
        for keyword in (*negatives, *positives):
            for variant in keyword_variants(keyword):
                normalized = strip_noise(variant)
                if normalized and (topic, normalized) not in seen:
                    seen.add((topic, normalized))
                    out.append((topic, keyword, normalized))
    return out


def evaluate(csv_path: str, limit: int | None = None) -> dict:
    """跑一遍評測。回傳 `{主題: TopicStat}` 與整體數字。"""
    rules = _flat_rules()
    stats: dict[str, TopicStat] = defaultdict(TopicStat)
    rows = 0

    with open(csv_path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        missing = [a for a in ASPECT_MAP if a not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(
                f"這個 CSV 缺少 ASAP 的面向欄位：{missing[:3]}…\n"
                f"確認下載的是 Meituan-Dianping/asap 的 data/*.csv，"
                f"而不是別的評論資料集。"
            )

        for row in reader:
            if limit and rows >= limit:
                break
            rows += 1
            text = strip_noise(row.get("review") or "")
            if not text:
                continue

            # 這則評論實際提到了哪些主題（ASAP 的正確答案）
            mentioned: set[str] = {
                topic for aspect, topic in ASPECT_MAP.items()
                if (row.get(aspect) or NOT_MENTIONED).strip() != NOT_MENTIONED
            }
            # 我們的字典標了哪些主題（只算有被映射到的，其餘無從驗證）
            evaluable = set(ASPECT_MAP.values())
            fired: dict[str, str] = {}      # topic → 原始關鍵詞
            # ⚠️ 必須跟 `classify_topics` 用**同一個**比對方式（含否定偵測），
            #    否則量出來的數字跟線上實際行為對不上，改進也驗證不了。
            for topic, original, variant in rules:
                if (topic in evaluable and topic not in fired
                        and find_unnegated(text, variant)):
                    fired[topic] = original

            for topic in evaluable:
                stat = stats[topic]
                if topic in fired and topic in mentioned:
                    stat.fired_and_mentioned += 1
                elif topic in fired:
                    stat.fired_not_mentioned += 1
                    stat.culprits[fired[topic]] += 1
                elif topic in mentioned:
                    stat.missed += 1
                else:
                    stat.quiet += 1

    return {"rows": rows, "stats": dict(stats)}


def _bar(rate: float, width: int = 20) -> str:
    filled = round(rate * width)
    return "█" * filled + "·" * (width - filled)


def report(result: dict) -> str:
    """組出人看得懂的報告。"""
    stats: dict[str, TopicStat] = result["stats"]
    lines: list[str] = []
    add = lines.append

    add("=" * 72)
    add(f"主題字典外部驗證 — ASAP 資料集（{result['rows']:,} 則評論）")
    add("=" * 72)
    if not ZH_CONVERT_AVAILABLE:
        add("")
        add("⚠️⚠️ opencc 未安裝，簡繁變體沒有展開。")
        add("     ASAP 是簡體語料，這份報告的漏抓率會嚴重偏高且**不可採信**。")
        add("     pip install opencc-python-reimplemented 之後重跑。")
    add("")
    add("誤觸發率 ＝ 我們標了這個主題、但評論其實沒提到的比例")
    add("漏抓率　 ＝ 評論真的有提到、我們卻沒標到的比例")
    add("")
    add(f"  {'主題':<8} {'標出':>6} {'其中誤觸發':>10} {'誤觸發率':>9}  {'漏抓率':>7}")
    add("  " + "─" * 62)

    ordered = sorted(stats.items(), key=lambda kv: -kv[1].false_positive_rate)
    for topic, stat in ordered:
        if not stat.fired and not stat.mentioned:
            continue
        add(f"  {topic:<8} {stat.fired:>6} {stat.fired_not_mentioned:>10} "
            f"{stat.false_positive_rate:>8.1%}  {1 - stat.recall:>6.1%}  "
            f"{_bar(stat.false_positive_rate)}")

    add("")
    add("─" * 72)
    add("⭐ 誤觸發元凶排行 —— 這些是真的可以拿去改字典的")
    add("─" * 72)
    all_culprits: Counter = Counter()
    origin: dict[str, str] = {}
    for topic, stat in stats.items():
        for keyword, count in stat.culprits.items():
            all_culprits[keyword] += count
            origin[keyword] = topic
    if not all_culprits:
        add("  （沒有誤觸發）")
    for keyword, count in all_culprits.most_common(15):
        add(f"  {count:>5} 次   「{keyword}」  → 主題「{origin[keyword]}」")

    add("")
    add("⚠️ 高誤觸發率**不一定**代表字典要改，先分辨是哪一種：")
    add("   · 詞本身太泛（「態度」「排隊」在餐廳語料到處都是）→ 領域差異，飯店未必有問題")
    add("   · 詞會被別的語境借走（「選擇少」可以講菜色也可以講停車位）→ 這種要改")
    # ⚠️ 這份清單**必須從 ASPECT_MAP 推導**，不可寫死。
    #    2026-08-23 第一版寫死成「早餐、隔音、Wi-Fi、氣味、設備」，
    #    後來補上 Ambience#Noise 映射之後隔音其實驗得到了，
    #    但那行字還在騙人說「驗不到」。
    unverified = sorted(set(BUILTIN_TOPICS) - set(ASPECT_MAP.values()))
    if unverified:
        add("")
        add(f"⚠️ 沒有被驗到的主題：{'、'.join(unverified)}")
        add("   餐廳語料沒有這些面向的標註 —— 是**驗不到**，不是驗過沒問題。")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════
# 自動下載
# ══════════════════════════════════════════════════════════════════════════
ASAP_BASE = "https://raw.githubusercontent.com/Meituan-Dianping/asap/master/data"

# dev 是預設：4,940 則已經足夠看出誤觸發的樣態，而且十秒內跑完。
# train（36,850 則）留給想看更穩定數字的時候。
SPLITS = {"dev": "dev.csv", "test": "test.csv", "train": "train.csv"}

# 使用說明裡的佔位符。使用者很常直接複製貼上跑一次 ——
# 與其回一句「找不到檔案」，不如直接告訴他那是佔位符。
PLACEHOLDERS = {"path\\to\\dev.csv", "path/to/dev.csv", "<asap-csv 路徑>"}


def download(split: str = "dev", dest_dir: str | None = None) -> str:
    """
    下載 ASAP 資料到本機，回傳檔案路徑。已經下載過就直接用，不重抓。

    ⚠️ 存到 `Temp/`（CLAUDE.md §10：純本機產物不進版控）。
       這份檔案有 15~100 MB，而且**原始評論文字的著作權不屬於資料集上傳者**，
       絕對不可以進 git。
    """
    import urllib.request

    filename = SPLITS.get(split)
    if filename is None:
        raise ValueError(f"split 只能是 {'／'.join(SPLITS)}，收到「{split}」")

    if dest_dir is None:
        # backend/app/services/ota_dict_eval.py → 專案根目錄 → Temp/
        root = Path(__file__).resolve().parents[3]
        dest_dir = str(root / "Temp")
    Path(dest_dir).mkdir(parents=True, exist_ok=True)
    target = Path(dest_dir) / f"asap_{filename}"

    if target.exists() and target.stat().st_size > 0:
        print(f"已存在，直接使用：{target}（{target.stat().st_size:,} bytes）")
        return str(target)

    url = f"{ASAP_BASE}/{filename}"
    print(f"下載中：{url}")
    try:
        with urllib.request.urlopen(url, timeout=120) as resp:
            data = resp.read()
    except Exception as exc:                # noqa: BLE001
        raise RuntimeError(
            f"下載失敗：{exc}\n"
            f"請改用瀏覽器手動下載後指定路徑：\n"
            f"  {url}\n"
            f"  python -m app.services.ota_dict_eval  C:\\path\\{filename}"
        ) from exc

    target.write_bytes(data)
    print(f"已存到：{target}（{len(data):,} bytes）")
    return str(target)


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]

    usage = (
        "用法：\n"
        "  python -m app.services.ota_dict_eval --download          "
        "← 自動下載 dev 並評測（建議）\n"
        "  python -m app.services.ota_dict_eval --download train    "
        "← 換成完整訓練集（36,850 則）\n"
        "  python -m app.services.ota_dict_eval <csv 路徑> [筆數上限]"
    )
    if not args:
        print(__doc__)
        print(usage)
        return 1

    limit = None
    if args[0] in ("--download", "-d"):
        split = args[1] if len(args) > 1 and not args[1].isdigit() else "dev"
        if args[-1].isdigit():
            limit = int(args[-1])
        try:
            path = download(split)
        except (ValueError, RuntimeError) as exc:
            print(str(exc))
            return 1
    else:
        path = args[0]
        if path.strip() in PLACEHOLDERS:
            print(f"「{path}」是說明文字裡的**佔位符**，不是真的檔案路徑。")
            print()
            print("最快的做法是讓工具自己下載：")
            print("  python -m app.services.ota_dict_eval --download")
            return 1
        if len(args) > 1 and args[1].isdigit():
            limit = int(args[1])

    try:
        result = evaluate(path, limit=limit)
    except FileNotFoundError:
        print(f"找不到檔案：{path}")
        print()
        print("讓工具自己下載：")
        print("  python -m app.services.ota_dict_eval --download")
        return 1
    except ValueError as exc:
        print(str(exc))
        return 1
    print(report(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
