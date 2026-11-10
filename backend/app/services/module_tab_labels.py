"""
模組頁籤自訂名稱（2026-11-10）—— 讀取／儲存 module_tab_labels。

讀取失敗（例如表還沒建、migration hdi3 未跑）一律退回預設名稱，不讓頁面壞掉。
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.time import twnow
from app.models.module_tab_label import ModuleTabLabel

logger = logging.getLogger(__name__)
MAX_LEN = 100


def get_labels(db: Session, module: str, defaults: dict[str, str]) -> dict[str, str]:
    """{tab_key: 顯示名稱}；沒有自訂的用 defaults。只回 defaults 裡有的 key。"""
    out = dict(defaults)
    try:
        for r in db.query(ModuleTabLabel).filter(ModuleTabLabel.module == module).all():
            if r.tab_key in out and r.custom_label:
                out[r.tab_key] = r.custom_label
    except Exception as exc:  # 表不存在等
        logger.warning(f"[TabLabels] 讀取 {module} 自訂頁籤名稱失敗，改用預設：{exc}")
        db.rollback()
    return out


def save_labels(db: Session, module: str, defaults: dict[str, str],
                labels: dict[str, str | None], user: str) -> dict[str, str]:
    """儲存自訂名稱；空字串或與預設相同＝清除自訂（回到預設）。未知 key 忽略。"""
    now = twnow()
    for key, raw in labels.items():
        if key not in defaults:
            continue
        val = (raw or "").strip()[:MAX_LEN] or None
        if val == defaults[key]:
            val = None
        row = db.get(ModuleTabLabel, (module, key))
        if row is None:
            if val is None:
                continue
            db.add(ModuleTabLabel(module=module, tab_key=key, custom_label=val, updated_at=now, updated_by=user))
        else:
            row.custom_label = val
            row.updated_at = now
            row.updated_by = user
    db.commit()
    return get_labels(db, module, defaults)
