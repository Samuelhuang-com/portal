"""
主管交辦／緊急事件 Service Layer

資料來源：
  https://ap12.ragic.com/soutlet001/other-tasks/1

欄位對應（Ragic 中文欄位名 → OtherTask 屬性）
  屬性             → task_type   ("上級交辦" / "緊急事件")
  交辦主管          → supervisor
  工程人員          → engineer
  建立日期          → created_at
  問題說明          → description
  備註             → notes
  最後更新日期       → updated_at
  狀態             → status
  維修工時          → work_hours
  附圖/圖片/上傳圖片 → images (list of {url, filename})

⚠️  若 Ragic 欄位名與預期不符，可呼叫 /raw-fields 取得實際 key 清單，
    再修改下方 RK_* 常數或 RK_ALIASES。
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from app.core.config import settings
from app.services.ragic_adapter import RagicAdapter
from app.services.ragic_data_service import parse_images

logger = logging.getLogger(__name__)

# ═════════════════════════════════════════════════════════════════════════════
# 1. Ragic 連線常數
# ═════════════════════════════════════════════════════════════════════════════

_RAGIC_SERVER  = "ap12.ragic.com"
_RAGIC_ACCOUNT = "soutlet001"
_RAGIC_PATH    = "other-tasks/1"

# ═════════════════════════════════════════════════════════════════════════════
# 2. 欄位名常數與 Alias（多候選確保命中）
# ═════════════════════════════════════════════════════════════════════════════

RK_TASK_TYPE   = "屬性"
RK_VENUE       = "歸屬"
RK_SUPERVISOR  = "交辦主管"
RK_ENGINEER    = "工程人員"
RK_CREATED_AT  = "建立日期"
RK_DESCRIPTION = "問題說明"
RK_NOTES       = "備註"
RK_UPDATED_AT  = "最後更新日期"
RK_STATUS      = "狀態"
RK_WORK_HOURS  = "維修工時"

# 圖片欄位候選清單（依優先順序）
IMAGE_FIELD_CANDIDATES = ["附圖", "圖片", "上傳圖片", "照片", "附件", "相片",
                          "上傳圖片.1", "維修照上傳", "維修照", "圖檔"]

RK_ALIASES: dict[str, list[str]] = {
    RK_TASK_TYPE:   ["屬性", "類型", "任務類型", "事件類型"],
    RK_VENUE:       ["歸屬", "歸屬類別", "場館歸屬", "所屬場館", "所屬"],
    RK_SUPERVISOR:  ["交辦主管", "主管", "督導主管", "負責主管", "交辦人"],
    RK_ENGINEER:    ["工程人員", "執行人員", "負責人員", "維修人員", "工務人員", "技術人員"],
    # 建立日期：Ragic 可能回傳多種名稱
    RK_CREATED_AT:  ["建立日期", "建立時間", "報修日期", "開單日期",
                     "創建日期", "創建時間", "Create Date", "Created Date",
                     "_creation_dt", "create_dt", "建立"],
    RK_DESCRIPTION: ["問題說明", "描述", "說明", "事項說明", "工作說明",
                     "問題描述", "任務說明", "詳細說明", "內容", "工作內容"],
    RK_NOTES:       ["備註", "附記", "補充說明", "備注"],
    # 最後更新日期：Ragic 可能回傳多種名稱
    RK_UPDATED_AT:  ["最後更新日期", "更新日期", "最後更新時間", "最後更新",
                     "修改日期", "修改時間", "更新時間",
                     "_modification_dt", "modify_dt", "Modified Date",
                     "Last Update", "Last Modified"],
    RK_STATUS:      ["狀態", "處理狀態", "進度", "執行狀態"],
    RK_WORK_HOURS:  ["維修工時", "工時", "花費工時", "工作時數", "工時（小時）",
                     "維修時數", "耗時"],
}

COMPLETED_STATUSES = {"結案", "已結案", "已完成", "完成"}


# ═════════════════════════════════════════════════════════════════════════════
# 3. 欄位解析工具
# ═════════════════════════════════════════════════════════════════════════════

def _get_field(raw: dict, canonical_key: str) -> Any:
    """依 alias 清單按優先順序取值，全部未命中回傳 ''"""
    aliases = RK_ALIASES.get(canonical_key, [canonical_key])
    for alias in aliases:
        if alias in raw:
            return raw[alias]
    return ""


def _str(v: Any) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    if s in {"--", "-", "N/A", "null", "None"}:
        return ""
    return s


def _float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


# 日期格式清單（由精確到模糊）
_DATE_FMTS = [
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%Y/%m/%d",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%Y.%m.%d %H:%M:%S",
    "%Y.%m.%d %H:%M",
    "%Y.%m.%d",
]

def _parse_datetime(v: Any) -> Optional[datetime]:
    """解析 Ragic 日期時間字串 → datetime | None"""
    s = _str(v)
    if not s:
        return None
    for fmt in _DATE_FMTS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    # fallback：提取 YYYY/MM/DD 或 YYYY-MM-DD
    m = re.search(r"(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})", s)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    logger.debug(f"[OtherTasks] 日期解析失敗：{s!r}")
    return None


def _scan_dates_from_raw(raw: dict, used_keys: set[str]) -> tuple[Optional[datetime], Optional[datetime]]:
    """
    泛型日期掃描：當主要 alias 沒命中日期時，
    掃描 raw 中所有尚未使用的欄位，找出最早與最晚的日期值，
    分別作為 created_at / updated_at。
    """
    dates: list[tuple[str, datetime]] = []
    for k, v in raw.items():
        if k in used_keys or not v:
            continue
        dt = _parse_datetime(v)
        if dt:
            dates.append((k, dt))

    if not dates:
        return None, None

    dates.sort(key=lambda x: x[1])
    created = dates[0][1]
    updated = dates[-1][1] if len(dates) > 1 else None
    logger.debug(f"[OtherTasks] 泛型日期掃描命中：created={created}, updated={updated}，來源欄位={[k for k,_ in dates]}")
    return created, updated


def _parse_image_fields(raw: dict) -> list[dict]:
    """掃描圖片欄位候選清單，解析回傳 [{url, filename}, ...]"""
    for field_key in IMAGE_FIELD_CANDIDATES:
        val = raw.get(field_key)
        if val:
            imgs = parse_images(val, server=_RAGIC_SERVER, account=_RAGIC_ACCOUNT)
            if imgs:
                logger.debug(f"[OtherTasks] 附圖欄位 {field_key!r} → {len(imgs)} 張")
                return imgs
    return []


# ═════════════════════════════════════════════════════════════════════════════
# 4. OtherTaskRecord 資料物件
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class OtherTaskRecord:
    ragic_id:    str
    task_type:   str
    venue:       str
    supervisor:  str
    engineer:    str
    created_at:  Optional[datetime]
    description: str
    notes:       str
    updated_at:  Optional[datetime]
    status:      str
    work_hours:  Optional[float]
    images:      list = field(default_factory=list)
    year:        Optional[int] = field(default=None)
    month:       Optional[int] = field(default=None)

    def __post_init__(self):
        if self.created_at:
            self.year  = self.created_at.year
            self.month = self.created_at.month

    @property
    def is_completed(self) -> bool:
        return self.status.strip() in COMPLETED_STATUSES

    @classmethod
    def from_raw(cls, ragic_id: str, raw: dict) -> "OtherTaskRecord":
        # ── 工時（過濾異常值）───────────────────────────────────────────────
        work_hours = _float(_get_field(raw, RK_WORK_HOURS))
        if work_hours is not None and (work_hours < 0 or work_hours > 9999):
            work_hours = None

        # ── 日期（先用 alias，再泛型掃描）────────────────────────────────────
        created_at = _parse_datetime(_get_field(raw, RK_CREATED_AT))
        updated_at = _parse_datetime(_get_field(raw, RK_UPDATED_AT))

        if not created_at or not updated_at:
            # 收集已使用的 key，避免重複計算
            used: set[str] = set()
            for aliases in RK_ALIASES.values():
                for a in aliases:
                    if a in raw:
                        used.add(a)
            scan_created, scan_updated = _scan_dates_from_raw(raw, used)
            if not created_at:
                created_at = scan_created
            if not updated_at:
                updated_at = scan_updated

        # ── 附圖 ────────────────────────────────────────────────────────────
        images = _parse_image_fields(raw)

        return cls(
            ragic_id    = str(ragic_id),
            task_type   = _str(_get_field(raw, RK_TASK_TYPE)),
            venue       = _str(_get_field(raw, RK_VENUE)),
            supervisor  = _str(_get_field(raw, RK_SUPERVISOR)),
            engineer    = _str(_get_field(raw, RK_ENGINEER)),
            created_at  = created_at,
            description = _str(_get_field(raw, RK_DESCRIPTION)),
            notes       = _str(_get_field(raw, RK_NOTES)),
            updated_at  = updated_at,
            status      = _str(_get_field(raw, RK_STATUS)),
            work_hours  = work_hours,
            images      = images,
        )


# ═════════════════════════════════════════════════════════════════════════════
# 5. Ragic 抓取
# ═════════════════════════════════════════════════════════════════════════════

def _make_adapter() -> RagicAdapter:
    return RagicAdapter(
        sheet_path=_RAGIC_PATH,
        server_url=_RAGIC_SERVER,
        account=_RAGIC_ACCOUNT,
        api_key=settings.RAGIC_API_KEY,
    )


async def fetch_raw_fields() -> dict:
    """回傳 Ragic 第一筆欄位名稱與值（debug 用）"""
    adapter = _make_adapter()
    try:
        raw = await adapter.fetch_all()
        ids = [k for k in raw if k.lstrip("-").isdigit()]
        if not ids:
            return {"error": "no records", "keys": []}
        first = raw[ids[0]]
        return {
            "record_id": ids[0],
            "total_records": len(ids),
            "keys": list(first.keys()),
            "sample": first,
        }
    except Exception as exc:
        return {"error": str(exc)}


async def fetch_all_records() -> list[OtherTaskRecord]:
    """從 Ragic 拉取所有主管交辦／緊急事件記錄"""
    adapter = _make_adapter()
    raw_data = await adapter.fetch_all()

    records: list[OtherTaskRecord] = []
    for rid, raw in raw_data.items():
        if not str(rid).lstrip("-").isdigit():
            continue
        try:
            rec = OtherTaskRecord.from_raw(str(rid), raw)
            records.append(rec)
        except Exception as exc:
            logger.warning(f"[OtherTasks] 解析失敗 ragic_id={rid}：{exc}")

    logger.info(f"[OtherTasks] 共抓取 {len(records)} 筆，有日期={sum(1 for r in records if r.created_at)} 筆，有附圖={sum(1 for r in records if r.images)} 筆")
    return records
