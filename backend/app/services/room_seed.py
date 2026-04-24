"""
客房主檔種子資料
啟動時若 rooms 表為空，自動填入所有樓層 × 房號。
"""
import logging
from app.core.database import SessionLocal
from app.models.room import Room

logger = logging.getLogger(__name__)

# ── 各樓層房號主檔（依樓層排序，每樓房號依數字排序）────────────────────────────
FLOOR_ROOMS: list[tuple[str, int, list[int]]] = [
    ("5F",  5, [
        501, 502, 503, 505, 506, 507, 508, 509, 510,
        511, 512, 513, 515, 516, 517, 518, 519, 520,
        521, 522, 523, 525, 526, 527, 528, 529, 530, 531,
    ]),
    ("6F",  6, [
        601, 602, 603, 605, 606, 607, 608, 609, 610,
        611, 612, 613, 615, 616, 617, 618, 619, 620,
        621, 622, 623, 625, 626, 627, 628, 629, 630, 631,
    ]),
    ("7F",  7, [
        701, 702, 703, 705, 706, 707, 708, 709, 710,
        711, 712, 713, 715, 716, 717, 718, 719, 720,
        721, 722, 723, 725, 726, 727, 728, 729, 730, 731,
    ]),
    ("8F",  8, [
        801, 803, 805, 806, 807, 808, 809, 810,
        811, 812, 813, 815, 816, 817, 818, 819, 820,
        821, 822, 823, 825, 826, 827, 828, 829, 830, 831,
    ]),
    ("9F",  9, [
        901, 902, 903, 904, 905, 906, 907, 908, 909, 910,
        911, 912, 913, 915, 916, 917, 918, 919, 920,
        921, 922, 923, 925, 926, 927, 928, 929, 930, 931,
    ]),
    ("10F", 10, [
        1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008, 1009, 1010,
        1011, 1012, 1013, 1015, 1016, 1017, 1018, 1019, 1020,
        1021, 1022, 1023, 1025, 1026, 1027, 1028, 1029, 1030, 1031,
    ]),
]


def seed_rooms() -> None:
    """若 rooms 表為空，寫入所有客房主檔資料。"""
    db = SessionLocal()
    try:
        if db.query(Room).count() > 0:
            logger.info("[RoomSeed] rooms 表已有資料，略過 seed。")
            return

        total = 0
        for floor_label, floor_no, room_list in FLOOR_ROOMS:
            for room_no in room_list:
                db.add(Room(
                    floor=floor_label,
                    floor_no=floor_no,
                    room_no=str(room_no),
                ))
                total += 1

        db.commit()
        logger.info(f"[RoomSeed] 完成：寫入 {total} 間客房主檔。")
    except Exception as exc:
        db.rollback()
        logger.error(f"[RoomSeed] 失敗：{exc}")
    finally:
        db.close()
