"""
班表模組種子資料
在 main.py lifespan 中呼叫，僅在資料表為空時插入預設資料。
"""
import logging
from sqlalchemy.orm import Session
from app.models.schedule import ShiftType, Department

logger = logging.getLogger(__name__)

# ── 預設班別 ──────────────────────────────────────────────────
DEFAULT_SHIFTS = [
    {
        "code": "N1",
        "name": "日班",
        "start_time": "09:30",
        "end_time": "18:30",
        "work_minutes": 480,
        "is_overnight": False,
        "color": "#3b82f6",   # 藍
    },
    {
        "code": "Y",
        "name": "早班",
        "start_time": "08:30",
        "end_time": "17:30",
        "work_minutes": 480,
        "is_overnight": False,
        "color": "#10b981",   # 綠
    },
    {
        "code": "E6",
        "name": "晚班",
        "start_time": "14:00",
        "end_time": "23:00",
        "work_minutes": 480,
        "is_overnight": False,
        "color": "#f59e0b",   # 橘
    },
    {
        "code": "G",
        "name": "大夜班",
        "start_time": "23:00",
        "end_time": "08:00",
        "work_minutes": 480,
        "is_overnight": True,
        "color": "#8b5cf6",   # 紫
    },
    {
        "code": "E3",
        "name": "中晚班",
        "start_time": "13:30",
        "end_time": "22:30",
        "work_minutes": 480,
        "is_overnight": False,
        "color": "#ef4444",   # 紅
    },
]

# ── 預設部門 ──────────────────────────────────────────────────
DEFAULT_DEPARTMENTS = [
    {"name": "飯店", "sort_order": 1},
    {"name": "商場", "sort_order": 2},
    {"name": "工務", "sort_order": 3},
    {"name": "保全", "sort_order": 4},
    {"name": "行政", "sort_order": 5},
]


def seed_shift_types(db: Session) -> None:
    """若 shift_types 表為空，插入預設班別"""
    count = db.query(ShiftType).count()
    if count > 0:
        return
    for data in DEFAULT_SHIFTS:
        shift = ShiftType(**data)
        db.add(shift)
    db.commit()
    logger.info("schedule_seed: 插入 %d 筆預設班別", len(DEFAULT_SHIFTS))


def seed_departments(db: Session) -> None:
    """若 departments 表為空，插入預設部門"""
    count = db.query(Department).count()
    if count > 0:
        return
    for data in DEFAULT_DEPARTMENTS:
        dept = Department(**data)
        db.add(dept)
    db.commit()
    logger.info("schedule_seed: 插入 %d 筆預設部門", len(DEFAULT_DEPARTMENTS))


def run_all_seeds(db: Session) -> None:
    """執行全部種子資料（在 main.py lifespan 呼叫）"""
    try:
        seed_departments(db)
        seed_shift_types(db)
    except Exception as e:
        logger.error("schedule_seed 失敗：%s", e)
        db.rollback()
