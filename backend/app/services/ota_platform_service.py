"""
OTA 口碑分析 — 平台清單（資料驅動）

建立日期：2026-08-23
規格書：`docs/SPEC_ota_reviews.md` §5.1

═══════════════════════════════════════════════════════════════════════════
這一層在解決什麼
═══════════════════════════════════════════════════════════════════════════
平台原本是寫死在 `ota_normalize.py` 的五個常數。使用者要加 Hotels.com、
Trip.com、KKday，每加一個都要改程式重新部署。

但**新增平台其實不需要寫任何邏輯** —— 有代碼／名稱／分制／網域就能建來源、
匯入 CSV、跑分析、進統計。需要寫程式的只有「自動擷取器」，
而那件事本來就未必做得到（Tripadvisor、Expedia 都被站方擋）。

═══════════════════════════════════════════════════════════════════════════
⚠️ 常數與 DB 的關係：常數是 seed，DB 是真相
═══════════════════════════════════════════════════════════════════════════
`ota_normalize` 的 `PLATFORM_SCALE` / `PLATFORM_LABEL` / `DOMAIN_PLATFORM`
**保留不動**，理由是它們散落在 12 個呼叫點被當成普通 dict 讀
（`PLATFORM_LABEL.get(code, code)` 這種顯示用途）。全部改成查 DB
會動到一堆不相干的程式碼，也讓純顯示的路徑多背一個 db session。

改成這樣分工：

    常數  ── ensure_builtin_platforms() ──▶  DB（真相）
      ▲                                       │
      └────── refresh_caches() 反向同步 ◀──────┘

  · **判斷正確性的路徑查 DB**：建來源驗證、平台下拉選單
  · **純顯示的路徑讀常數快取**：評論列表的平台名稱、匯出檔的欄位

⚠️ 快取是 process 內的。API、排程、CLI 是不同 process，
   在 A 加的平台要等 B 呼叫 `refresh_caches()` 才會出現在 B 的顯示快取裡。
   **這只影響顯示**（沒同步到的話顯示成代碼而不是名稱），
   不影響驗證與統計 —— 那些都查 DB。
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.ota_review import OtaPlatform
from app.services import ota_normalize as NM

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════
# ⚠️⚠️ 內建平台清單必須在 import 時**凍結**，不可在執行期讀常數
# ══════════════════════════════════════════════════════════════════════════
# 2026-08-23 實測踩到的循環：
#
#   1. `refresh_caches()` 把 DB 的平台寫回 `NM.PLATFORM_SCALE`
#      （為了讓顯示名稱跟得上）
#   2. 使用者自建的 kkday 因此進了 `NM.PLATFORM_SCALE`
#   3. `ensure_builtin_platforms()` 拿 `NM.PLATFORM_SCALE` 當內建清單
#      → **把 kkday 當成內建平台重新建一次**
#   4. 使用者刪掉 kkday → 下次 list_platforms() 又把它復活
#
# 症狀是「刪除按鈕沒有作用」，但錯誤其實在兩層之外。
# 凍結成 tuple 之後，`refresh_caches()` 再怎麼寫也污染不到 seed。
_BUILTIN_CODES: tuple[str, ...] = tuple(NM.PLATFORM_SCALE)
_BUILTIN_SEED: tuple[tuple[str, str, int], ...] = tuple(
    (code, NM.PLATFORM_LABEL.get(code, code), scale)
    for code, scale in NM.PLATFORM_SCALE.items()
)

# 內建平台的網域（從 DOMAIN_PLATFORM 反轉出來，避免兩處各寫一份）
_BUILTIN_DOMAINS: dict[str, list[str]] = {}
for _domain, _code in NM.DOMAIN_PLATFORM.items():
    _BUILTIN_DOMAINS.setdefault(_code, []).append(_domain)


def ensure_builtin_platforms(db: Session) -> int:
    """
    冪等補齊內建平台。回傳新增幾筆。

    ⚠️ 與 `ensure_builtin_topic_rules()` 同一個理由：`create_all()` 只建表
       不塞資料，migration SQL 未必有人跑過。平台表是空的時候，
       來源設定的下拉選單會**整個空掉**，使用者連一筆來源都建不了 ——
       而且不會報錯。

    ⚠️ 只補**缺少的**，不覆蓋既有列 —— 使用者可能改過內建平台的顯示名稱
       或分制，重跑不該把他的修改洗掉。
    """
    existing = set(db.execute(select(OtaPlatform.code)).scalars().all())
    added = 0
    # ⚠️ 用**凍結的** `_BUILTIN_SEED`，不要讀 `NM.PLATFORM_SCALE` ——
    #    後者會被 `refresh_caches()` 寫入自建平台，讀它會把自建平台
    #    當成內建重建（見檔頭的循環說明）。
    for order, (code, label, scale) in enumerate(_BUILTIN_SEED):
        if code in existing:
            continue
        db.add(OtaPlatform(
            code=code,
            label=label,
            score_scale=scale,
            domains=",".join(_BUILTIN_DOMAINS.get(code, [])),
            is_builtin=True,
            sort_order=order,
        ))
        added += 1
    if added:
        db.flush()
        logger.info("[OTA] 補齊內建平台 %d 個", added)
    return added


def list_platforms(db: Session, enabled_only: bool = False) -> list[OtaPlatform]:
    ensure_builtin_platforms(db)
    stmt = select(OtaPlatform)
    if enabled_only:
        stmt = stmt.where(OtaPlatform.is_enabled.is_(True))
    rows = db.execute(
        stmt.order_by(OtaPlatform.sort_order, OtaPlatform.code)
    ).scalars().all()
    db.commit()
    return list(rows)


def domain_map(db: Session) -> dict[str, str]:
    """`{網域: 平台代碼}`，含使用者自建的平台。"""
    out: dict[str, str] = {}
    for row in list_platforms(db):
        for domain in row.domains.split(","):
            domain = domain.strip().lower()
            if domain:
                out[domain] = row.code
    return out


def refresh_caches(db: Session) -> None:
    """
    把 DB 的平台同步回 `ota_normalize` 的常數快取。

    ⚠️ 只**新增／更新**，不刪除。DB 裡被停用或刪掉的平台，
       快取裡仍留著它的顯示名稱 —— 既有評論的 `platform` 欄位還指著那個
       代碼，把名稱拿掉會讓歷史資料顯示成孤兒代碼。
    """
    for row in list_platforms(db):
        NM.PLATFORM_LABEL[row.code] = row.label
        NM.PLATFORM_SCALE[row.code] = row.score_scale
        for domain in row.domains.split(","):
            domain = domain.strip().lower()
            if domain:
                NM.DOMAIN_PLATFORM[domain] = row.code
    NM.VALID_PLATFORMS = set(NM.PLATFORM_SCALE)


def create_platform(db: Session, *, code: str, label: str, score_scale: int,
                    domains: str = "", note: str = "",
                    created_by: str | None = None) -> OtaPlatform:
    """
    新增平台。

    ⚠️ `code` 會被寫進每一筆評論的 `platform` 欄位，而且是統計的分組鍵 ——
       事後改名要一併更新既有評論，成本很高。所以這裡限制成
       小寫英數與底線，並擋掉與既有平台重複。
    """
    code = code.strip().lower()
    if not code:
        raise ValueError("平台代碼不可空白")
    # ⚠️ **不可只用 `isalnum()`** —— Python 的 `"攜".isalnum()` 回傳 True，
    #    中文字會整個通過。必須先要求 ASCII（2026-08-23 測試抓到）。
    if not code.isascii() or not all(c.isalnum() or c == "_" for c in code):
        raise ValueError(
            f"平台代碼只能用小寫英文、數字與底線（收到「{code}」）。"
            f"它會寫進每一筆評論並當成統計的分組鍵，不要用中文或符號。"
            f"中文名稱請填在「顯示名稱」欄。"
        )
    if score_scale not in (5, 10):
        raise ValueError("分制只能是 5 或 10")

    ensure_builtin_platforms(db)
    max_order = db.execute(
        select(OtaPlatform.sort_order).order_by(OtaPlatform.sort_order.desc())
    ).scalars().first() or 0

    row = OtaPlatform(
        code=code, label=label.strip() or code,
        score_scale=score_scale,
        domains=_clean_domains(domains),
        note=note.strip(),
        is_builtin=False, sort_order=max_order + 1,
        created_by=created_by,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError(f"平台代碼「{code}」已經存在") from exc
    db.refresh(row)
    refresh_caches(db)
    return row


def update_platform(db: Session, platform_id: int, *, label: str,
                    score_scale: int, domains: str = "", note: str = "",
                    is_enabled: bool = True) -> OtaPlatform:
    """
    修改平台。

    ⚠️ **`code` 不可改**。它是既有評論的 `platform` 欄位值與統計分組鍵，
       改了會讓所有歷史資料變成孤兒。要換代碼請新增一個再手動搬資料。
    """
    row = db.get(OtaPlatform, platform_id)
    if row is None:
        raise ValueError("找不到這個平台")
    if score_scale not in (5, 10):
        raise ValueError("分制只能是 5 或 10")

    row.label = label.strip() or row.code
    row.score_scale = score_scale
    row.domains = _clean_domains(domains)
    row.note = note.strip()
    row.is_enabled = is_enabled
    db.commit()
    db.refresh(row)
    refresh_caches(db)
    return row


def delete_platform(db: Session, platform_id: int) -> None:
    """
    刪除平台。

    ⚠️ 內建平台**拒絕刪除**，只能停用。
    ⚠️ 底下還有來源時也拒絕 —— 那些來源的 `platform` 會變成孤兒代碼，
       畫面上顯示成 `hotels_com` 而不是「Hotels.com」，統計也認不出來。
    """
    from app.models.ota_review import OtaSource

    row = db.get(OtaPlatform, platform_id)
    if row is None:
        raise ValueError("找不到這個平台")
    if row.is_builtin:
        raise ValueError(
            "內建平台不可刪除，請改用「停用」"
            "（停用是可逆的，而且既有評論的平台名稱還顯示得出來）"
        )
    used = db.execute(
        select(OtaSource.id).where(OtaSource.platform == row.code)
    ).scalars().first()
    if used:
        raise ValueError(
            f"還有來源在用「{row.label}」，無法刪除。"
            f"請先刪掉那些來源，或改用「停用」。"
        )
    db.delete(row)
    db.commit()


def _clean_domains(raw: str) -> str:
    """
    正規化網域字串：去空白、轉小寫、去 www.、去重。

    ⚠️ 去掉 `www.` 是因為比對時用的是 `endswith` 語意 ——
       存 `www.hotels.com` 會讓 `tw.hotels.com` 比不中。
    """
    seen: list[str] = []
    for item in (raw or "").replace("；", ",").replace(";", ",").split(","):
        domain = item.strip().lower()
        for prefix in ("https://", "http://", "www."):
            if domain.startswith(prefix):
                domain = domain[len(prefix):]
        domain = domain.split("/")[0]
        if domain and domain not in seen:
            seen.append(domain)
    return ",".join(seen)
