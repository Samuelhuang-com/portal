"""
共用「Ragic ↔ Portal 資料筆數比對」工具函式

背景：settings/ragic-connections 頁面「資料比對」TAB（原本只接了大直/商場工務報修
兩個模組，見 app/routers/dazhi_repair.py、luqun_repair.py 的 /verify-count、
/verify-diff）擴充到工作日誌彙整所用到的其餘模組。這裡把重複的機制抽出來，
各模組 router 只需呼叫這些函式並組出自己模組特有的欄位（module_name、model
class、Ragic sheet 位置），不需要每個模組重新寫一次分頁抓取／DB 查詢邏輯。

使用方式（單一 Ragic Sheet 模組，例如 IHG客房保養）：
    portal_count, last_synced_at = await read_portal_count_and_last_sync(
        db, IHGRoomMaintenanceMaster, "IHG客房保養"
    )
    try:
        ragic_count = await fetch_ragic_count(IHG_SHEET_PATH, IHG_SERVER_URL, IHG_ACCOUNT)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ragic 連線失敗：{exc}")
    return build_verify_count_response("IHG客房保養", portal_count, ragic_count, last_synced_at)

使用方式（多 Ragic Sheet 彙總模組，例如飯店每日巡檢，5 張 Sheet 共用同一張 DB 表）：
    sheets = [
        {"sheet_key": k, "sheet_path": cfg["path"], "server_url": HDI_SERVER_URL, "account": HDI_ACCOUNT}
        for k, cfg in SHEET_CONFIGS.items()
    ]
    portal_count, last_synced_at = await read_portal_count_and_last_sync(db, HotelDIBatch, "飯店每日巡檢")
    ragic_count = await fetch_ragic_count_multi(sheets)

差集比對（/verify-diff）用法比照，見 fetch_ragic_url_map_single / fetch_ragic_url_map_multi
+ read_portal_ragic_ids + build_verify_diff_response。

⚠️ 重要限制：本檔案只適用於「DB 表的 ragic_id 與 Ragic Sheet 一列記錄一對一對應」的表
（通常是 batch / master 主表），不要拿子表格展開後的 item／明細表（一筆 Ragic 記錄會
展開成多列）來比對，筆數天生就不會一致。各模組的主表選擇已在
docs/RAGIC_MODULE_MAP.md 相關調查中確認過，新增模組時請一併確認。
"""
from __future__ import annotations

from typing import Sequence

from fastapi.concurrency import run_in_threadpool
from sqlalchemy import desc as _desc
from sqlalchemy.orm import Session

from app.models.module_sync_log import ModuleSyncLog
from app.services.ragic_adapter import RagicAdapter


# ── Portal 端（本地 DB）─────────────────────────────────────────────────────────

async def read_portal_count_and_last_sync(
    db: Session,
    model_cls,
    module_name: str,
) -> tuple[int, str | None]:
    """回傳 (本地 DB 筆數, 最近一次 ModuleSyncLog 開始時間 ISO 字串或 None)。"""

    def _read():
        portal_count = db.query(model_cls).count()
        last_log = (
            db.query(ModuleSyncLog)
            .filter(ModuleSyncLog.module_name == module_name)
            .order_by(_desc(ModuleSyncLog.started_at))
            .first()
        )
        return portal_count, last_log

    portal_count, last_log = await run_in_threadpool(_read)
    last_synced_at = last_log.started_at.isoformat() if last_log else None
    return portal_count, last_synced_at


async def read_portal_ragic_ids(db: Session, model_cls) -> set[str]:
    """回傳本地 DB 該表所有 ragic_id（要求 model_cls 有 ragic_id 欄位）。"""
    rows = await run_in_threadpool(db.query(model_cls.ragic_id).all)
    return {r.ragic_id for r in rows}


# ── Ragic 端（即時查詢）─────────────────────────────────────────────────────────

async def fetch_ragic_count(
    sheet_path: str,
    server_url: str,
    account: str,
    extra_params: dict | None = None,
) -> int:
    """單一 Sheet 的 Ragic 即時筆數。"""
    adapter = RagicAdapter(sheet_path=sheet_path, server_url=server_url, account=account)
    return await adapter.fetch_count(extra_params=extra_params)


async def fetch_ragic_count_multi(sheets: Sequence[dict]) -> int:
    """
    多張 Sheet 加總筆數。
    sheets 每項需含 sheet_path/server_url/account 三個 key，extra_params 選填。
    """
    total = 0
    for cfg in sheets:
        adapter = RagicAdapter(
            sheet_path=cfg["sheet_path"],
            server_url=cfg["server_url"],
            account=cfg["account"],
        )
        total += await adapter.fetch_count(extra_params=cfg.get("extra_params"))
    return total


async def fetch_ragic_url_map_single(
    sheet_path: str,
    server_url: str,
    account: str,
    extra_params: dict | None = None,
) -> dict[str, str]:
    """單一 Sheet：回傳 {ragic_id: ragic_url}，供 verify-diff 比對與連結使用。"""
    adapter = RagicAdapter(sheet_path=sheet_path, server_url=server_url, account=account)
    raw_ids = await adapter.fetch_ids(extra_params=extra_params)
    return {rid: f"{adapter.base_url}/{rid}" for rid in raw_ids}


async def fetch_ragic_url_map_multi(sheets: Sequence[dict]) -> dict[str, str]:
    """
    多張 Sheet：回傳 {"{sheet_key}_{raw_id}": ragic_url}（複合鍵，對應 DB 的組合 ragic_id）。
    sheets 每項需含 sheet_key/sheet_path/server_url/account，extra_params 選填。
    """
    result: dict[str, str] = {}
    for cfg in sheets:
        adapter = RagicAdapter(
            sheet_path=cfg["sheet_path"],
            server_url=cfg["server_url"],
            account=cfg["account"],
        )
        raw_ids = await adapter.fetch_ids(extra_params=cfg.get("extra_params"))
        for rid in raw_ids:
            composite_id = f"{cfg['sheet_key']}_{rid}"
            result[composite_id] = f"{adapter.base_url}/{rid}"
    return result


# ── 回應組裝 ─────────────────────────────────────────────────────────────────────

def build_verify_count_response(
    module_name: str,
    portal_count: int,
    ragic_count: int,
    last_synced_at: str | None,
) -> dict:
    diff = ragic_count - portal_count
    return {
        "module":         module_name,
        "portal_count":   portal_count,
        "ragic_count":    ragic_count,
        "diff":           diff,
        "match":          diff == 0,
        "last_synced_at": last_synced_at,
    }


def build_verify_diff_response(
    ragic_url_map: dict[str, str],
    portal_ids: set[str],
) -> dict:
    """
    ragic_url_map: {ragic_id: ragic_url}（fetch_ragic_url_map_single/multi 的回傳值）
    portal_ids:    本地 DB 的 ragic_id 集合（read_portal_ragic_ids 的回傳值）
    """
    ragic_ids = set(ragic_url_map.keys())
    in_ragic_not_portal = [
        {"ragic_id": rid, "ragic_url": ragic_url_map[rid]}
        for rid in sorted(ragic_ids - portal_ids)
    ]
    in_portal_not_ragic = [
        {"ragic_id": rid}
        for rid in sorted(portal_ids - ragic_ids)
    ]
    return {
        "in_ragic_not_portal": in_ragic_not_portal,
        "in_portal_not_ragic": in_portal_not_ragic,
    }
