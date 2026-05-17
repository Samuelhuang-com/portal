"""
Ragic Sheet 設定服務

提供統一介面讓 sync services 取得各模組的部門設定清單。
優先從 DB 讀取；DB 為空時 fallback 到 model 檔案中的硬編碼清單。

用法（sync service 中）：
    from app.services.ragic_sheet_config_service import get_sheet_configs
    dept_sheets = get_sheet_configs("purchase")
    for dept in dept_sheets:
        ...
"""
import json
import logging

from app.core.database import SessionLocal
from app.models.ragic_sheet_config import RagicSheetConfig

logger = logging.getLogger(__name__)


def get_sheet_configs(module: str) -> list[dict]:
    """
    取得指定模組的所有啟用部門設定（依 sort_order 排序）。
    回傳格式與原 DEPT_SHEETS list[dict] 完全相容。

    優先從 ragic_sheet_config 資料表讀取；
    若該 module 尚無任何紀錄（首次啟動前），fallback 到 model 硬編碼清單。
    """
    db = SessionLocal()
    try:
        rows = (
            db.query(RagicSheetConfig)
            .filter(
                RagicSheetConfig.module    == module,
                RagicSheetConfig.is_active == True,
            )
            .order_by(RagicSheetConfig.sort_order)
            .all()
        )
        if rows:
            return [r.to_dict() for r in rows]
    except Exception as e:
        logger.warning(f"[RagicSheetConfig] DB 讀取失敗，使用 fallback：{e}")
    finally:
        db.close()

    return _get_fallback(module)


def _get_fallback(module: str) -> list[dict]:
    """DB 無資料時的硬編碼備援。"""
    if module == "purchase":
        from app.models.purchase_request import DEPT_SHEETS
        return list(DEPT_SHEETS)
    if module == "claim":
        from app.models.claim_request import CLAIM_DEPT_SHEETS
        return list(CLAIM_DEPT_SHEETS)
    if module == "nichiyo_purchase":
        from app.models.nichiyo_purchase_request import NICHIYO_DEPT_SHEETS
        return list(NICHIYO_DEPT_SHEETS)
    if module == "nichiyo_claim":
        from app.models.nichiyo_claim_request import NICHIYO_CLAIM_DEPT_SHEETS
        return list(NICHIYO_CLAIM_DEPT_SHEETS)
    return []


# ── Seed helpers（main.py 啟動時呼叫）────────────────────────────────────────

# 正確的 seed 資料（各模組、各部門）
_SEED_DATA: list[dict] = [
    # ── 樂群請購單（purchase）9 部門 ────────────────────────────────────────
    {"module": "purchase", "sort_order": 1,  "display_name": "執董室", "ragic_dept": "執董室",
     "list_path": "lequn-executive-office/10",        "detail_path": "lequn-executive-office/2",
     "extra_json": '{"pageid": "0l4"}'},
    {"module": "purchase", "sort_order": 2,  "display_name": "營業部", "ragic_dept": "營業",
     "list_path": "new-tab/10",                        "detail_path": "new-tab/10",
     "extra_json": '{"pageid": ""}'},
    {"module": "purchase", "sort_order": 3,  "display_name": "行銷部", "ragic_dept": "行銷",
     "list_path": "lequn-marketing-department/12",     "detail_path": "lequn-marketing-department/2",
     "extra_json": '{"pageid": "DfW"}'},
    {"module": "purchase", "sort_order": 4,  "display_name": "財務部", "ragic_dept": "財務",
     "list_path": "lequn-finance-department/9",        "detail_path": "lequn-finance-department/11",
     "extra_json": '{"pageid": ""}'},
    {"module": "purchase", "sort_order": 5,  "display_name": "停管部", "ragic_dept": "客服",
     "list_path": "lequn-traffic-management/6",        "detail_path": "lequn-traffic-management/6",
     "extra_json": '{"pageid": ""}'},
    {"module": "purchase", "sort_order": 6,  "display_name": "管理部", "ragic_dept": "管理",
     "list_path": "community-management-department/22","detail_path": "community-management-department/22",
     "extra_json": '{"pageid": "9xg"}'},
    {"module": "purchase", "sort_order": 7,  "display_name": "資訊部", "ragic_dept": "資訊",
     "list_path": "joy-group-it-department/11",        "detail_path": "joy-group-it-department/12",
     "extra_json": '{"pageid": ""}'},
    {"module": "purchase", "sort_order": 8,  "display_name": "工務部", "ragic_dept": "工務",
     "list_path": "lequn-public-works-department/1",   "detail_path": "lequn-public-works-department/2",
     "extra_json": '{"pageid": "hBY"}'},
    {"module": "purchase", "sort_order": 9,  "display_name": "專案部", "ragic_dept": "專案",
     "list_path": "happy-group-project/2",             "detail_path": "happy-group-project/1",
     "extra_json": '{"pageid": "NVk"}'},

    # ── 樂群請款單（claim）9 部門 ────────────────────────────────────────────
    {"module": "claim", "sort_order": 1, "display_name": "執董室", "ragic_dept": "執董室",
     "list_path": "free-executive-office/9",           "detail_path": "free-executive-office/9",
     "extra_json": '{"flow_type": "零用金型"}'},
    {"module": "claim", "sort_order": 2, "display_name": "營業部", "ragic_dept": "營業",
     "list_path": "new-tab/8",                         "detail_path": "new-tab/8",
     "extra_json": '{"flow_type": "比價型"}'},
    {"module": "claim", "sort_order": 3, "display_name": "行銷部", "ragic_dept": "行銷",
     "list_path": "lequn-marketing-department/13",     "detail_path": "lequn-marketing-department/13",
     "extra_json": '{"flow_type": "比價型"}'},
    {"module": "claim", "sort_order": 4, "display_name": "財務部", "ragic_dept": "財務",
     "list_path": "lequn-finance-department/6",        "detail_path": "lequn-finance-department/6",
     "extra_json": '{"flow_type": "匯款型"}'},
    {"module": "claim", "sort_order": 5, "display_name": "停管部", "ragic_dept": "客服",
     "list_path": "lequn-traffic-management/5",        "detail_path": "lequn-traffic-management/5",
     "extra_json": '{"flow_type": "零用金型"}'},
    {"module": "claim", "sort_order": 6, "display_name": "管理部", "ragic_dept": "管理",
     "list_path": "community-management-department/24","detail_path": "community-management-department/24",
     "extra_json": '{"flow_type": "零用金型"}'},
    {"module": "claim", "sort_order": 7, "display_name": "資訊部", "ragic_dept": "資訊",
     "list_path": "joy-group-it-department/14",        "detail_path": "joy-group-it-department/14",
     "extra_json": '{"flow_type": "匯款型"}'},
    {"module": "claim", "sort_order": 8, "display_name": "工務部", "ragic_dept": "工務",
     "list_path": "lequn-public-works-department/2",   "detail_path": "lequn-public-works-department/2",
     "extra_json": '{"flow_type": "比價型"}'},
    {"module": "claim", "sort_order": 9, "display_name": "專案部", "ragic_dept": "專案",
     "list_path": "happy-group-project/1",             "detail_path": "happy-group-project/1",
     "extra_json": '{"flow_type": "比價型"}'},

    # ── 日曜請購單（nichiyo_purchase）7 部門 ────────────────────────────────
    {"module": "nichiyo_purchase", "sort_order": 1, "display_name": "執董室", "ragic_dept": "執董室",
     "list_path": "free-executive-office/9",           "detail_path": "free-executive-office/9",
     "extra_json": "{}"},
    {"module": "nichiyo_purchase", "sort_order": 2, "display_name": "營業部", "ragic_dept": "營業",
     "list_path": "free-business-division/21",         "detail_path": "free-business-division/21",
     "extra_json": "{}"},
    {"module": "nichiyo_purchase", "sort_order": 3, "display_name": "行銷部", "ragic_dept": "行銷",
     "list_path": "marketing/40",                      "detail_path": "marketing/40",
     "extra_json": "{}"},
    {"module": "nichiyo_purchase", "sort_order": 4, "display_name": "管理部", "ragic_dept": "管理",
     "list_path": "freed-management-division/19",      "detail_path": "freed-management-division/19",
     "extra_json": "{}"},
    {"module": "nichiyo_purchase", "sort_order": 5, "display_name": "資訊部", "ragic_dept": "資訊",
     "list_path": "department-of-free-information/23", "detail_path": "department-of-free-information/23",
     "extra_json": "{}"},
    {"module": "nichiyo_purchase", "sort_order": 6, "display_name": "客服部", "ragic_dept": "客服",
     "list_path": "free-management-department/10",     "detail_path": "free-management-department/10",
     "extra_json": "{}"},
    {"module": "nichiyo_purchase", "sort_order": 7, "display_name": "設計部", "ragic_dept": "設計",
     "list_path": "free-design-department/2",          "detail_path": "free-design-department/2",
     "extra_json": "{}"},

    # ── 日曜請款單（nichiyo_claim）8 部門 ───────────────────────────────────
    {"module": "nichiyo_claim", "sort_order": 1, "display_name": "執董室", "ragic_dept": "執董室",
     "list_path": "free-executive-office/8",           "detail_path": "free-executive-office/8",
     "extra_json": "{}"},
    {"module": "nichiyo_claim", "sort_order": 2, "display_name": "營業部", "ragic_dept": "營業",
     "list_path": "free-business-division/12",         "detail_path": "free-business-division/12",
     "extra_json": "{}"},
    {"module": "nichiyo_claim", "sort_order": 3, "display_name": "行銷部", "ragic_dept": "行銷",
     "list_path": "marketing/32",                      "detail_path": "marketing/32",
     "extra_json": "{}"},
    {"module": "nichiyo_claim", "sort_order": 4, "display_name": "管理部", "ragic_dept": "管理",
     "list_path": "freed-management-division/8",       "detail_path": "freed-management-division/8",
     "extra_json": "{}"},
    {"module": "nichiyo_claim", "sort_order": 5, "display_name": "資訊部", "ragic_dept": "資訊",
     "list_path": "department-of-free-information/22", "detail_path": "department-of-free-information/22",
     "extra_json": "{}"},
    {"module": "nichiyo_claim", "sort_order": 6, "display_name": "客服部", "ragic_dept": "客服",
     "list_path": "free-management-department/8",      "detail_path": "free-management-department/8",
     "extra_json": "{}"},
    {"module": "nichiyo_claim", "sort_order": 7, "display_name": "財務部", "ragic_dept": "財務",
     "list_path": "free-finance-department/15",        "detail_path": "free-finance-department/15",
     "extra_json": "{}"},
    {"module": "nichiyo_claim", "sort_order": 8, "display_name": "設計部", "ragic_dept": "設計",
     "list_path": "free-design-department/1",          "detail_path": "free-design-department/1",
     "extra_json": "{}"},
]


def seed_ragic_sheet_config() -> None:
    """
    啟動時自動填入 ragic_sheet_config 資料表（idempotent）。
    以 (module, list_path) 為唯一鍵，INSERT OR IGNORE，不覆蓋已有設定。
    若已有紀錄但 list_path 有誤，需手動在 DB 中更正或透過管理 API 更新。
    """
    db = SessionLocal()
    try:
        inserted = 0
        for row in _SEED_DATA:
            exists = (
                db.query(RagicSheetConfig)
                .filter(
                    RagicSheetConfig.module    == row["module"],
                    RagicSheetConfig.list_path == row["list_path"],
                )
                .first()
            )
            if not exists:
                db.add(RagicSheetConfig(**row))
                inserted += 1
        db.commit()
        print(f"[RagicSheetConfig] seed checked — {inserted} 筆新增，共 {len(_SEED_DATA)} 筆設定")
    except Exception as e:
        db.rollback()
        logger.error(f"[RagicSheetConfig] seed 失敗：{e}")
    finally:
        db.close()
