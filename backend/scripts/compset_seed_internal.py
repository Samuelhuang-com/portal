"""
競品分析 — 建立 INTERNAL 訂閱與瀚寓夏天的競爭組

規格書：docs/SPEC_compset_analysis.md D9、D10、§3
候選與定案：docs/COMPSET_CANDIDATES.md §8

用途
────────────────────────────────────────────────────────────────────────────
migration 建完空表之後，要有一筆訂閱與一組競爭組，抓取層才有東西可跑。
這支就是把 `COMPSET_CANDIDATES.md §8` 的定案內容種進資料庫。

執行
────────────────────────────────────────────────────────────────────────────
    cd backend
    python  scripts/compset_seed_internal.py            # 測試區
    py -3.11 scripts/compset_seed_internal.py           # 正式區
    ...  --dry-run                                      # 只看要做什麼，不寫入

⚠️ **冪等**：重複執行只會更新既有列，不會長出第二筆。
   可以安全地在部署腳本裡重跑。

⚠️ 執行前 migration 必須先套用（`alembic upgrade head`），否則表不存在。

═══════════════════════════════════════════════════════════════════════════
三件不要改錯的事
═══════════════════════════════════════════════════════════════════════════
1. **⭐ 必須恰有一筆 `is_self=True`。** 價位指數的分子與分母都靠它，
   缺了它整個模組算不出主要指標。本腳本結束前會驗證。

2. **⭐ 五月家青年旅舍台大館目前沒有 `google_property_token`。**
   P0 探測時「公館 台北」的前 38 名沒有它（COMPSET_P0_REPORT §2），
   所以 token 還沒拿到。A 級抓取會跳過它並記 warning —— 這是預期行為，
   不是 bug。拿到 token 後回 `/compset/hotels` 補上即可。

3. **`monthly_quota` 預設 3500** ＝ 混合路徑（D10）約 3,153 次／月 ＋ 約 11% 緩衝。
   ⚠️ 改這個數字等於改對外成本，不要順手調。
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select                                    # noqa: E402

from app.core.database import SessionLocal                       # noqa: E402
from app.models.compset_analysis import (CompsetHotel,           # noqa: E402
                                         CompsetSubscriber)
from app.services import compset_quota_service as QS             # noqa: E402

SUBSCRIBER_CODE = "INTERNAL"

# 定案內容見 docs/COMPSET_CANDIDATES.md §8
SUBSCRIBER = {
    "name": "瀚寓夏天（內部）",
    "plan_level": "A",              # 先開 A 級；B／C 等 A 級穩定累積後再開
    "location_query": "公館 台北",   # P0 實測用的查詢字串（B／C 級才會用到）
    "monthly_quota": 3500,
    "quota_anchor_day": 1,
    "param_adults": 2,
    "param_nights": 1,
    "param_gl": "tw",
    "param_hl": "zh-tw",            # ⚠️ 是 zh-tw 不是 zh-Hant，P0 實測值
    "param_currency": "TWD",
    "note": "內部自用。競爭組定案見 docs/COMPSET_CANDIDATES.md §8。",
}

# ⚠️ 欄位順序：display_name, short_name, hotel_code, is_self, token,
#    google_query_name, 房間數, 登記地址, 備註
#
# `short_name` 是表格與標籤用的簡稱。中文飯店全名普遍 8～12 字，
# 塞不進矩陣欄位標題，也塞不進 Dashboard 的滿房標籤。留空會退回全名。
HOTELS: list[tuple[str, str, str, bool, str, str, int | None, str, str]] = [
    ("瀚寓夏天", "瀚寓", "HANNS_SUMMER", True,
     "ChoIo5Xt8-CnkI__ARoNL2cvMTF2bTFsbDRfcxAB", "瀚寓夏天 Hanns Summer",
     69, "臺北市中正區汀州路三段62號", "自己。3 星，10 種房型"),

    ("承攜行旅-台北台大館", "承攜", "GUIDE_NTU", False,
     "ChkIt8Lcl6XB0t84Gg0vZy8xMXEzemY5cWNiEAE", "承攜行旅 - 台北台大館",
     35, "臺北市中正區羅斯福路三段98號1-8樓", "地緣最近，約 0.3 km"),

    ("捷絲旅臺大尊賢館", "捷絲旅", "JUSTSLEEP_NTU", False,
     "ChgIkL_Wyc-o05gUGgwvZy8xMmhyanQwYncQAQ", "捷絲旅 臺大尊賢館 (Just Sleep Taipei NTU)",
     72, "臺北市大安區羅斯福路四段83號", "上檔天花板，且規模最接近（72 vs 69）"),

    ("福華國際文教會館", "福華", "HOWARD_CSIH", False,
     "ChkI_fft0o7vhonPARoML2cvMTJobGp3am15EAE", "福華國際文教會館",
     None, "臺北市大安區新生南路三段30號", "台大正對面，評論量最大。房間數待查"),

    ("谷墨商旅師大館", "谷墨", "GOODMORE_SHIDA", False,
     "ChoIgvfciKa_utLGARoNL2cvMTFidjFuYmJtYhAB", "谷墨商旅 GoodMore Hotel",
     92, "臺北市大安區和平東路一段145、147號", "登記名「謙商旅」。師大商圈"),

    # ⚠️ token 尚未取得，見檔頭第 2 點
    ("五月家青年旅舍台大館", "五月家", "MAYROOMS_NTU", False,
     "", "五月家青年旅舍台大館",
     None, "臺北市文山區羅斯福路四段208號", "地板錨點。⚠️ token 待補，A 級會跳過"),
]


def seed(dry_run: bool = False) -> int:
    db = SessionLocal()
    changed = 0
    try:
        sub = db.execute(
            select(CompsetSubscriber)
            .where(CompsetSubscriber.code == SUBSCRIBER_CODE)
        ).scalar_one_or_none()

        if sub is None:
            print(f"[compset] 建立訂閱 {SUBSCRIBER_CODE}")
            sub = CompsetSubscriber(code=SUBSCRIBER_CODE, **SUBSCRIBER)
            db.add(sub)
            changed += 1
        else:
            print(f"[compset] 訂閱 {SUBSCRIBER_CODE} 已存在（id={sub.id}），更新設定")
            for k, v in SUBSCRIBER.items():
                if getattr(sub, k) != v:
                    print(f"          {k}: {getattr(sub, k)!r} → {v!r}")
                    setattr(sub, k, v)
                    changed += 1
        db.flush()

        for i, (name, short, code, is_self, token, qname,
                rooms, addr, note) in enumerate(HOTELS):
            row = db.execute(
                select(CompsetHotel).where(
                    CompsetHotel.subscriber_id == sub.id,
                    CompsetHotel.display_name == name,
                )
            ).scalar_one_or_none()
            if row is None:
                print(f"[compset] 新增競爭組成員：{name}")
                row = CompsetHotel(subscriber_id=sub.id, display_name=name)
                db.add(row)
                changed += 1
            row.hotel_code = code
            row.short_name = short
            row.is_self = is_self
            row.google_property_token = token
            row.google_query_name = qname
            row.room_count = rooms
            row.registered_address = addr
            row.note = note
            row.is_enabled = True
            row.sort_order = i
        db.flush()

        # ── ⭐ 驗證：is_self 必須恰一筆 ───────────────────────────────
        selves = db.execute(
            select(CompsetHotel).where(CompsetHotel.subscriber_id == sub.id,
                                       CompsetHotel.is_self.is_(True))
        ).scalars().all()
        if len(selves) != 1:
            raise RuntimeError(
                f"is_self 必須恰有一筆，實際 {len(selves)} 筆 —— "
                "價位指數的分子與分母都靠它，缺了整個模組算不出主要指標。"
            )

        no_token = [h.display_name for h in db.execute(
            select(CompsetHotel).where(CompsetHotel.subscriber_id == sub.id)
        ).scalars().all() if not (h.google_property_token or "").strip()]
        if no_token:
            print(f"[compset] ⚠️ 尚未取得 property_token：{'、'.join(no_token)}"
                  "（A 級抓取會跳過並記 warning，這是預期行為）")

        QS.ensure_period(db, sub.id, date.today())

        if dry_run:
            db.rollback()
            print(f"[compset] --dry-run：已回滾，未寫入（原本會變更 {changed} 處）")
        else:
            db.commit()
            st = QS.quota_status(db, sub.id)
            print(f"[compset] 完成。訂閱 id={sub.id}，競爭組 {len(HOTELS)} 家，"
                  f"級別 {sub.plan_level}，配額 {st['used']}/{st['limit']}"
                  f"（期別 {st['period_start']}）")
        return changed
    finally:
        db.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="建立競品分析的 INTERNAL 訂閱與競爭組")
    ap.add_argument("--dry-run", action="store_true", help="只顯示要做什麼，不寫入")
    args = ap.parse_args()
    seed(dry_run=args.dry_run)
