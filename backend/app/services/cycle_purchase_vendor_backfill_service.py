"""
週期採購 — 料號主檔「供應商資料回填」Service（2026-09-30 新增）

── 背景 ──────────────────────────────────────────────────────────────────────
料號主檔的「預設供應商」與料號對照的「叫貨供應商」，當初匯入時直接用**簡稱**
建了一批週採供應商（CPV-NNNN、source_vendor_id 為 NULL，俗稱「簡稱孤兒」）。
同一家廠商在週採鏡像裡其實**已經有**一筆從合約主檔同步來的全名正本
（例：「巨沅」孤兒 vs「巨沅實業有限公司」V-00027）。

孤兒的後果不只是畫面顯示簡稱：拋轉 Ragic 時「廠商(一)」是 Link 欄位、只認全名，
料號對照指著孤兒 → 廠商欄是空的，Ragic 還照樣回 SUCCESS（見 CHANGELOG [2.10.41]）。

── Samuel 2026-09-30 裁示 ────────────────────────────────────────────────────
1. 比對來源是 **Ragic 廠商資料表（sheet 15）的「簡稱」欄**（portal.db vendors 沒存簡稱，
   所以一定要即時抓 Ragic）。
2. 簡稱完全相同 → 預設勾選，但仍要**預覽後由使用者按「套用」才寫入**。
3. 沒有相同簡稱、但有名稱相似的 → 列候選，由使用者自行選定。
4. Ragic 找不到的 → 只列出來，不處理（要先去 Ragic 建檔，再按一次同步）。
5. 「改為 Ragic 名稱」＝**改指向週採鏡像裡的全名正本**，不是把孤兒改名。
   （改名會出現兩筆同名供應商；而且廠商主檔單一真實來源是合約模組，見 CLAUDE.md §9）
6. 回填範圍＝料號主檔 `default_vendor_id` ＋ 料號對照 `vendor_id`。
   孤兒本身**不停用**（要停用請到供應商主檔用既有的「合併」功能）。
7. 2026-09-30 追加裁示：**已彙整、但尚未拋轉 Ragic 也尚未轉採購單**的彙整列一併改指全名。
   原因：拋轉時廠商名稱是依彙整列 vendor_id 即時查的，指著簡稱那筆就會被拋轉前的
   廠商防呆（vendor_rejection_reason）擋下列進 not_pushed。
   **已拋轉**（ragic_pushed 或已有 ragic_record_id，含 STUB）與**已轉採購單**（po_id 非空）
   的彙整列不動 —— 那些已經是對外的單據，改了會跟 Ragic／採購單對不起來。

── 刻意的設計 ────────────────────────────────────────────────────────────────
- 套用時**不再抓 Ragic**：目標一律經 portal.db `vendors.ragic_id` → `vendor_id`
  → 週採 `source_vendor_id` 解析。前端送來的只有「孤兒 id ＋ Ragic 記錄 id」，
  目標供應商由後端重新解析，不吃前端傳的供應商 id。
- 只處理 `source_vendor_id IS NULL` 的供應商。已對照合約主檔的供應商名稱由同步維護，
  本功能不碰。
"""
from __future__ import annotations

import difflib
import logging
import re
import unicodedata
from typing import Optional

import httpx
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.contract import Vendor
from app.models.cycle_purchase_item import CyclePurchaseItem, CyclePurchaseItemMapping
from app.models.cycle_purchase_summary import CyclePurchaseSummary
from app.models.cycle_purchase_vendor import CyclePurchaseVendor

logger = logging.getLogger(__name__)

RAGIC_VENDOR_URL = "https://ap12.ragic.com/soutlet001/community-management-department/15"
RAGIC_VENDOR_WEB = "https://ap12.ragic.com/soutlet001/community-management-department/15"

# 相似度門檻：低於這個分數的不列為候選（只是「列給人選」，不會自動套用）
SIMILAR_MIN_SCORE = 0.6
SIMILAR_MAX_CANDIDATES = 5

# 比對「核心名稱」時剝掉的公司型態字尾（長的放前面，避免「有限公司」先吃掉「股份有限公司」的尾巴）
_SUFFIXES = (
    "股份有限公司", "有限公司", "(股)公司", "股公司", "企業社", "實業社", "服務社",
    "工程行", "工作室", "事務所", "商行", "企業", "實業", "公司",
)


def _unpushed_summary_filter(q):
    """尚未拋轉 Ragic、尚未轉採購單的彙整列（見檔頭第 7 點）。"""
    S = CyclePurchaseSummary
    return q.filter(
        S.ragic_pushed == False,  # noqa: E712
        S.ragic_record_id.is_(None),
        S.po_id.is_(None),
    )


class BackfillError(Exception):
    """可預期的錯誤（router 轉成 4xx）。"""


# ═══════════════════════════════════════════════════════════════════════════
# Ragic
# ═══════════════════════════════════════════════════════════════════════════

def _safe(row: dict, *keys: str) -> str:
    for k in keys:
        v = row.get(k, "")
        if isinstance(v, (dict, list)):
            continue
        if v is not None and str(v).strip() not in ("", "N/A", "-"):
            return str(v).strip()
    return ""


def fetch_ragic_vendors() -> list[dict]:
    """即時抓 Ragic 廠商資料表（含「簡稱」）。欄位名稱與 vendor_sync.py 一致。"""
    try:
        resp = httpx.get(
            RAGIC_VENDOR_URL,
            headers={"Authorization": f"Basic {settings.RAGIC_API_KEY}"},
            params={"api": "", "limit": 1000, "naming": "true"},
            timeout=30,
            verify=settings.RAGIC_VERIFY_SSL,
        )
        resp.raise_for_status()
        raw = resp.json()
    except Exception as exc:
        raise BackfillError(f"讀取 Ragic 廠商資料表失敗：{exc}")

    rows: list[dict] = []
    for ragic_id, row in raw.items():
        if not isinstance(row, dict):
            continue
        name = _safe(row, "名稱", "廠商名稱", "公司名稱")
        if not name:
            continue
        rows.append({
            "ragic_id": str(ragic_id),
            "ragic_code": _safe(row, "廠商編號"),
            "name": name,
            "short_name": _safe(row, "簡稱"),
            "tax_id": _safe(row, "統一編號"),
        })
    return rows


# ═══════════════════════════════════════════════════════════════════════════
# 比對
# ═══════════════════════════════════════════════════════════════════════════

def _norm(text: Optional[str]) -> str:
    """全形轉半形、去空白、大小寫不敏感。"""
    s = unicodedata.normalize("NFKC", text or "")
    s = re.sub(r"\s+", "", s)
    return s.casefold()


def _core(text: Optional[str]) -> str:
    """去掉括號內註記（如「（現行廠商）」）與公司型態字尾，剩下可比對的核心名稱。"""
    s = _norm(text)
    s = re.sub(r"\(.*?\)", "", s)          # NFKC 已把全形括號轉半形
    changed = True
    while changed and s:
        changed = False
        for suf in _SUFFIXES:
            if s.endswith(suf) and len(s) > len(suf):
                s = s[: -len(suf)]
                changed = True
                break
    return s


def _similar_score(portal_name: str, ragic_row: dict) -> float:
    """0～1；包含關係直接給 0.9，其餘用 difflib。只用來排序與篩候選，不會自動套用。"""
    p = _core(portal_name)
    if len(p) < 2:
        return 0.0
    best = 0.0
    for cand in (ragic_row["name"], ragic_row["short_name"]):
        if not cand:
            continue
        c_full = _norm(cand)
        c = _core(cand)
        if not c:
            continue
        if p == c:
            best = max(best, 0.95)
        elif (p in c_full) or (len(c) >= 2 and c in _norm(portal_name)):
            best = max(best, 0.9)
        else:
            best = max(best, difflib.SequenceMatcher(None, p, c).ratio())
    return round(best, 2)


def _target_map(portal_db: Session, cp_db: Session) -> dict[str, CyclePurchaseVendor]:
    """Ragic 記錄 id → 週採鏡像供應商（經 portal.db vendors.ragic_id → vendor_id → source_vendor_id）。"""
    ragic_to_vendor_id = {
        v.ragic_id: v.vendor_id
        for v in portal_db.query(Vendor.ragic_id, Vendor.vendor_id).filter(Vendor.ragic_id.isnot(None)).all()
        if v.ragic_id
    }
    cp_by_source = {
        v.source_vendor_id: v
        for v in cp_db.query(CyclePurchaseVendor).filter(CyclePurchaseVendor.source_vendor_id.isnot(None)).all()
    }
    out: dict[str, CyclePurchaseVendor] = {}
    for ragic_id, vendor_id in ragic_to_vendor_id.items():
        cp = cp_by_source.get(vendor_id)
        if cp is not None:
            out[str(ragic_id)] = cp
    return out


def _candidate(ragic_row: dict, targets: dict[str, CyclePurchaseVendor], score: float) -> dict:
    t = targets.get(ragic_row["ragic_id"])
    if t is None:
        block = "Portal 週採供應商主檔還沒有這家（請先確認合約模組廠商同步是否成功）"
    elif not t.is_active:
        block = f"週採供應商「{t.vendor_name}」已停用，請先到供應商主檔啟用"
    else:
        block = None
    return {
        **ragic_row,
        "ragic_url": f"{RAGIC_VENDOR_WEB}/{ragic_row['ragic_id']}",
        "score": score,
        "target_vendor_id": t.id if t else None,
        "target_vendor_code": t.vendor_code if t else None,
        "target_vendor_name": t.vendor_name if t else None,
        "selectable": block is None,
        "block_reason": block,
    }


def build_preview(portal_db: Session, cp_db: Session, ragic_rows: list[dict]) -> dict:
    """列出所有被料號主檔／料號對照引用、且未對照合約主檔的週採供應商，與其 Ragic 候選。"""
    item_cnt = dict(
        cp_db.query(CyclePurchaseItem.default_vendor_id, func.count(CyclePurchaseItem.id))
        .filter(CyclePurchaseItem.default_vendor_id.isnot(None))
        .group_by(CyclePurchaseItem.default_vendor_id).all()
    )
    map_cnt = dict(
        cp_db.query(CyclePurchaseItemMapping.vendor_id, func.count(CyclePurchaseItemMapping.id))
        .filter(CyclePurchaseItemMapping.vendor_id.isnot(None))
        .group_by(CyclePurchaseItemMapping.vendor_id).all()
    )
    sum_cnt = dict(
        _unpushed_summary_filter(
            cp_db.query(CyclePurchaseSummary.vendor_id, func.count(CyclePurchaseSummary.id))
            .filter(CyclePurchaseSummary.vendor_id.isnot(None))
        ).group_by(CyclePurchaseSummary.vendor_id).all()
    )
    ref_ids = set(item_cnt) | set(map_cnt) | set(sum_cnt)

    orphans = (
        cp_db.query(CyclePurchaseVendor)
        .filter(CyclePurchaseVendor.source_vendor_id.is_(None))
        .order_by(CyclePurchaseVendor.vendor_code, CyclePurchaseVendor.id)
        .all()
    )
    targets = _target_map(portal_db, cp_db)

    by_short: dict[str, list[dict]] = {}
    for r in ragic_rows:
        if r["short_name"]:
            by_short.setdefault(_norm(r["short_name"]), []).append(r)

    rows: list[dict] = []
    for v in orphans:
        if v.id not in ref_ids:
            continue
        short_hits = by_short.get(_norm(v.vendor_name), [])
        if len(short_hits) == 1:
            match_type = "short"
            cands = [_candidate(short_hits[0], targets, 1.0)]
        else:
            scored = []
            for r in ragic_rows:
                s = 1.0 if r in short_hits else _similar_score(v.vendor_name, r)
                if s >= SIMILAR_MIN_SCORE:
                    scored.append((s, r))
            scored.sort(key=lambda x: (-x[0], x[1]["name"]))
            cands = [_candidate(r, targets, s) for s, r in scored[:SIMILAR_MAX_CANDIDATES]]
            match_type = "similar" if cands else "none"

        suggested = None
        if match_type == "short" and cands[0]["selectable"]:
            suggested = cands[0]["ragic_id"]

        rows.append({
            "vendor_id": v.id,
            "vendor_code": v.vendor_code,
            "vendor_name": v.vendor_name,
            "is_active": bool(v.is_active),
            "item_count": int(item_cnt.get(v.id, 0)),
            "mapping_count": int(map_cnt.get(v.id, 0)),
            "summary_count": int(sum_cnt.get(v.id, 0)),
            "match_type": match_type,
            "candidates": cands,
            "suggested_ragic_id": suggested,
        })

    summary = {
        "ragic_vendor_count": len(ragic_rows),
        "ragic_short_name_count": sum(1 for r in ragic_rows if r["short_name"]),
        "orphan_count": len(rows),
        "short_count": sum(1 for r in rows if r["match_type"] == "short"),
        "similar_count": sum(1 for r in rows if r["match_type"] == "similar"),
        "none_count": sum(1 for r in rows if r["match_type"] == "none"),
        "items_without_vendor": int(
            cp_db.query(func.count(CyclePurchaseItem.id))
            .filter(CyclePurchaseItem.default_vendor_id.is_(None)).scalar() or 0
        ),
    }
    return {"summary": summary, "rows": rows}


# ═══════════════════════════════════════════════════════════════════════════
# 套用
# ═══════════════════════════════════════════════════════════════════════════

def apply_backfill(portal_db: Session, cp_db: Session, decisions: list[dict]) -> dict:
    """decisions = [{vendor_id: 孤兒週採供應商 id, ragic_id: Ragic 記錄 id}]。

    全部驗證通過才寫入（任一筆不合法就整批不動，回 BackfillError）。
    不 commit，交給 get_cycle_purchase_db 的 transaction。
    """
    if not decisions:
        raise BackfillError("沒有勾選任何要回填的供應商")

    seen: set[int] = set()
    targets = _target_map(portal_db, cp_db)
    plan: list[tuple[CyclePurchaseVendor, CyclePurchaseVendor, str]] = []
    for d in decisions:
        src_id = int(d["vendor_id"])
        ragic_id = str(d["ragic_id"])
        if src_id in seen:
            raise BackfillError(f"供應商 id={src_id} 重複出現")
        seen.add(src_id)

        src = cp_db.query(CyclePurchaseVendor).filter(CyclePurchaseVendor.id == src_id).first()
        if src is None:
            raise BackfillError(f"找不到週採供應商 id={src_id}（可能已被刪除，請重新同步）")
        if src.source_vendor_id:
            raise BackfillError(
                f"「{src.vendor_name}」已經對照到合約主檔，不在回填範圍（請重新同步預覽）"
            )
        tgt = targets.get(ragic_id)
        if tgt is None:
            raise BackfillError(
                f"「{src.vendor_name}」選的 Ragic 廠商在 Portal 週採供應商主檔找不到對應（Ragic 記錄 {ragic_id}），"
                "請先按一次同步"
            )
        if not tgt.is_active:
            raise BackfillError(f"目標供應商「{tgt.vendor_name}」已停用，請先到供應商主檔啟用")
        if tgt.id == src.id:
            raise BackfillError(f"「{src.vendor_name}」來源與目標是同一筆")
        plan.append((src, tgt, ragic_id))

    results = []
    total_items = total_maps = total_sums = 0
    for src, tgt, ragic_id in plan:
        n_items = (
            cp_db.query(CyclePurchaseItem)
            .filter(CyclePurchaseItem.default_vendor_id == src.id)
            .update({CyclePurchaseItem.default_vendor_id: tgt.id}, synchronize_session=False)
        )
        n_maps = (
            cp_db.query(CyclePurchaseItemMapping)
            .filter(CyclePurchaseItemMapping.vendor_id == src.id)
            .update({CyclePurchaseItemMapping.vendor_id: tgt.id}, synchronize_session=False)
        )
        n_sums = _unpushed_summary_filter(
            cp_db.query(CyclePurchaseSummary).filter(CyclePurchaseSummary.vendor_id == src.id)
        ).update({CyclePurchaseSummary.vendor_id: tgt.id}, synchronize_session=False)
        total_items += n_items
        total_maps += n_maps
        total_sums += n_sums
        results.append({
            "vendor_id": src.id,
            "vendor_name": src.vendor_name,
            "target_vendor_id": tgt.id,
            "target_vendor_name": tgt.vendor_name,
            "items_updated": int(n_items),
            "mappings_updated": int(n_maps),
            "summaries_updated": int(n_sums),
        })
        logger.info(
            "[CP vendor backfill] %s(id=%s) → %s(id=%s)：料號 %s 筆、對照 %s 筆、未拋轉彙整列 %s 筆",
            src.vendor_name, src.id, tgt.vendor_name, tgt.id, n_items, n_maps, n_sums,
        )
    cp_db.flush()
    return {
        "results": results,
        "items_updated": total_items,
        "mappings_updated": total_maps,
        "summaries_updated": total_sums,
    }
