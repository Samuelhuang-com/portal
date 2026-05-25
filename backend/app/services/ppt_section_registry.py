"""
PPT Section Registry — PPT 匯出區塊集中管理
=============================================

使用方式
--------
在各模組的 router 或 service 末尾呼叫 register_section()，即可讓新資料
出現在 PPT 匯出設定頁的可勾選清單中，無需修改 PPT 核心邏輯。

範例
----
    from app.services.ppt_section_registry import register_section, PptSectionDef

    def _my_data_provider(db, params):
        return [{"欄位A": "值", ...}, ...]

    register_section(
        PptSectionDef(
            export_key   = "my_section",
            module_key   = "hotel_overview",
            tab_name     = "我的分組",
            second_title = "我的區塊",
            data_source  = "backend_db",
            sort_order   = 20,
            columns      = [{"key": "欄位A", "label": "欄位A", "width": 2.0}],
        ),
        data_provider = _my_data_provider,
    )

設計原則
--------
- Registry (code) 負責：section metadata、data_provider、columns（欄位定義）
- DB config_json 只負責：enabled、include_detail、sort_order（使用者偏好）
- 新增 Section 不需要 DB migration，只需要 register_section() 呼叫
"""

from dataclasses import dataclass, field
from typing import Optional, Callable, Any
from sqlalchemy.orm import Session


# ─────────────────────────────────────────────────────────────────────────────
# Section 定義
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PptSectionDef:
    """單一可匯出區塊的完整定義。"""

    # ── 識別 ──
    export_key:  str   # 唯一代碼，例："daily_accumulate_table"
    module_key:  str   # 所屬 Dashboard，例："hotel_overview"

    # ── UI 顯示 ──
    tab_name:     str  # Modal / 設定頁分組名稱，例："Dashboard"、"報修管理"
    second_title: str  # 區塊標題，例："主管摘要"、"報修未完成報表"
    description:  str = ""          # 說明文字（Tooltip 用）

    # ── 匯出規格 ──
    export_type:     str = "table"        # kpi_cards / table / summary_text
    slide_layout:    str = "table_full"   # kpi_summary / table_full / chart_full / summary_page
    supports_detail: bool = False         # 是否支援 include_detail
    detail_description: str = ""          # include_detail 說明

    # ── 資料來源 ──
    data_source: str = "frontend_payload"
    # "frontend_payload" → 由前端計算後帶入 body.frontend_data[export_key]
    # "backend_db"       → 後端在匯出時呼叫 data_provider 查 DB

    # ── 欄位定義（table 類型用，空 list = 動態由 provider 決定）──
    columns: list[dict] = field(default_factory=list)
    # 格式：[{"key": "欄位名稱", "label": "顯示名稱", "width": 1.5, "align": "left"}, ...]

    # ── 預設排序 ──
    sort_order: int = 99


# ─────────────────────────────────────────────────────────────────────────────
# Global Registry
# ─────────────────────────────────────────────────────────────────────────────

_SECTION_REGISTRY:  dict[str, list[PptSectionDef]] = {}
_DATA_PROVIDERS:    dict[str, Callable]             = {}
_DETAIL_PROVIDERS:  dict[str, Callable]             = {}


def register_section(
    section:         PptSectionDef,
    data_provider:   Optional[Callable] = None,
    detail_provider: Optional[Callable] = None,
) -> None:
    """
    註冊一個可匯出的 PPT Section。

    Parameters
    ----------
    section:
        PptSectionDef 物件，描述 section 的 metadata。
    data_provider:
        Callable(db: Session, params: dict) -> list[dict]
        params 包含：year, month, inspection_date
        只有 data_source="backend_db" 時才需要提供。
    detail_provider:
        Callable(db: Session, params: dict) -> list[dict]
        include_detail=True 時呼叫，回傳額外明細資料。
    """
    mk = section.module_key
    if mk not in _SECTION_REGISTRY:
        _SECTION_REGISTRY[mk] = []
    _SECTION_REGISTRY[mk].append(section)

    if data_provider is not None:
        _DATA_PROVIDERS[section.export_key] = data_provider
    if detail_provider is not None:
        _DETAIL_PROVIDERS[section.export_key] = detail_provider


def get_sections(module_key: str) -> list[PptSectionDef]:
    """取得指定 module 的所有已註冊 sections（依 sort_order 升冪排列）。"""
    return sorted(
        _SECTION_REGISTRY.get(module_key, []),
        key=lambda s: s.sort_order,
    )


def get_section_def(export_key: str) -> Optional[PptSectionDef]:
    """依 export_key 找到對應的 PptSectionDef。"""
    for sections in _SECTION_REGISTRY.values():
        for s in sections:
            if s.export_key == export_key:
                return s
    return None


def fetch_section_data(
    export_key:     str,
    db:             Session,
    params:         dict,
    include_detail: bool = False,
) -> Optional[dict]:
    """
    呼叫對應 section 的 data_provider 取得資料。

    Returns
    -------
    dict with keys:
        "main":   list[dict]  主要資料列
        "detail": list[dict]  明細資料列（僅 include_detail=True 且有 detail_provider 時）
    或 None（無 data_provider）。
    """
    provider = _DATA_PROVIDERS.get(export_key)
    if provider is None:
        return None

    main_data = provider(db, params)
    result: dict[str, Any] = {"main": main_data}

    if include_detail:
        detail_provider = _DETAIL_PROVIDERS.get(export_key)
        if detail_provider:
            result["detail"] = detail_provider(db, params)

    return result


def build_default_config(module_key: str) -> list[dict]:
    """
    依 Registry 產生預設的 config list（全部 enabled=true, include_detail=false）。
    用於 DB 尚無記錄時回傳給前端。
    """
    return [
        {
            "export_key":     s.export_key,
            "enabled":        True,
            "include_detail": False,
            "sort_order":     s.sort_order,
        }
        for s in get_sections(module_key)
    ]
