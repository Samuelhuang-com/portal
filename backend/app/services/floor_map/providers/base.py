"""
樓層巡檢圖 — Provider 基底（DEV_SPEC §5）

新模組：繼承 FloorMapProvider，填好類別屬性，實作 groups／day_status／month_status／data_end，
再到 providers/__init__.py 的 PROVIDERS 註冊。其餘（底圖、點位 CRUD、權限、前端）全部共用。

回傳格式（前端只認這個）：
  GroupMeta = {source_ref, label, system, shared_label}
  GroupDay  = GroupMeta + {status, rows, batches, inspectors, actual_minutes}
  rows      = CheckRow[]：{check_content, result_options, kind, status, results, abnormal, abnormal_note}
              results = [{batch_ragic_id, time_label, status, text, readings}]
  DayCell   = {day, date, status, abnormal_rows}
"""
from __future__ import annotations

from typing import Any, ClassVar

from sqlalchemy.orm import Session


class FloorMapProvider:
    module:          ClassVar[str]             # 'mall_facility_inspection'
    label:           ClassVar[str]             # '商場工務巡檢'
    view_permission: ClassVar[str]             # 沿用模組既有檢視 key
    edit_permission: ClassVar[str]             # '{prefix}_floor_map_edit'
    floors:          ClassVar[list[str]]       # 這個模組用到的底圖 key（工具列樓層順序）
    default_floor:   ClassVar[str]
    attr_fields:     ClassVar[list[str]] = []  # 點位自訂屬性欄位（表單與 Tag 用），例：['機房位置', '供應區域']

    # ── 必須實作 ─────────────────────────────────────────────────────────────
    def groups(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    def day_status(self, db: Session, insp_date: str) -> dict[str, dict[str, Any]]:
        """insp_date = 'YYYY/MM/DD'；回傳 {source_ref: GroupDay}（每個 groups() 都要有）"""
        raise NotImplementedError

    def month_status(self, db: Session, source_ref: str, year: int, month: int) -> list[dict[str, Any]]:
        raise NotImplementedError

    def data_end(self, db: Session) -> str | None:
        """資料最後一天 'YYYY/MM/DD'（前端日期預設值）"""
        raise NotImplementedError

    # ── 共用 ─────────────────────────────────────────────────────────────────
    def group_map(self) -> dict[str, dict[str, Any]]:
        return {g["source_ref"]: g for g in self.groups()}

    def has_source(self, source_ref: str) -> bool:
        return source_ref in self.group_map()

    def meta(self) -> dict[str, Any]:
        groups = self.groups()
        return {
            "module":          self.module,
            "label":           self.label,
            "floors":          self.floors,
            "default_floor":   self.default_floor,
            "attr_fields":     self.attr_fields,
            "edit_permission": self.edit_permission,
            "groups":          groups,
            "systems":         list(dict.fromkeys(g["system"] for g in groups if g["system"])),
        }
