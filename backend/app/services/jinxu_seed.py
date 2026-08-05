"""
金旭 PMS 分析 — 科目分類與分析門檻 seed

規格書：docs/SPEC_jinxu_analytics.md 附錄 C、§7.9

啟動時呼叫 `ensure_jinxu_seed(db)` 冪等寫入。已存在的 subject_code 不覆蓋
（管理員可能已在設定頁調整過分類）。
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models.jinxu_ledger import (
    GROUP_AR,
    GROUP_CARD,
    GROUP_CASH,
    GROUP_DEPOSIT_IN,
    GROUP_DEPOSIT_OUT,
    GROUP_EPAY,
    GROUP_OTHER_REV,
    GROUP_OTHER_SET,
    GROUP_ROOM,
    GROUP_SERVICE,
    GROUP_TELECOM,
    SIDE_REVENUE,
    SIDE_SETTLEMENT,
    JinxuSubjectMap,
)
from app.models.jinxu_setting import DEFAULT_SETTINGS, JinxuAnalysisSetting

logger = logging.getLogger(__name__)

# (code, name, side, group, sort_order, is_memo_only)
# is_memo_only=1 → J20：純記錄性分錄，排除於收入統計（實測 587 筆金額恆 0）
SUBJECT_SEED: list[tuple[str, str, str, str, int, int]] = [
    # ── 收入側 ───────────────────────────────────────────────────────────────
    ("01",  "房租",                SIDE_REVENUE, GROUP_ROOM,       10, 0),
    ("01A", "客房加價",            SIDE_REVENUE, GROUP_ROOM,       11, 0),
    ("04",  "加床費",              SIDE_REVENUE, GROUP_ROOM,       12, 0),
    ("67",  "換房",                SIDE_REVENUE, GROUP_ROOM,       13, 1),
    ("02",  "服務費",              SIDE_REVENUE, GROUP_SERVICE,    20, 0),
    ("05",  "車資",                SIDE_REVENUE, GROUP_SERVICE,    21, 0),
    ("06",  "影印費",              SIDE_REVENUE, GROUP_SERVICE,    22, 0),
    ("09",  "洗衣費",              SIDE_REVENUE, GROUP_SERVICE,    23, 0),
    ("13",  "自助洗衣費",          SIDE_REVENUE, GROUP_SERVICE,    24, 0),
    ("46",  "Hannahspring",        SIDE_REVENUE, GROUP_SERVICE,    25, 0),
    ("50",  "可見即可售",          SIDE_REVENUE, GROUP_SERVICE,    26, 0),
    ("61",  "弈夢空間",            SIDE_REVENUE, GROUP_SERVICE,    27, 1),
    ("62",  "弈夢紅樓",            SIDE_REVENUE, GROUP_SERVICE,    28, 0),
    ("10",  "市內電話",            SIDE_REVENUE, GROUP_TELECOM,    30, 0),
    ("11",  "長途電話",            SIDE_REVENUE, GROUP_TELECOM,    31, 0),
    ("12",  "國際電話",            SIDE_REVENUE, GROUP_TELECOM,    32, 0),
    ("64",  "預收訂金(開)",        SIDE_REVENUE, GROUP_DEPOSIT_IN, 40, 0),
    ("64A", "預收訂金(不開)",      SIDE_REVENUE, GROUP_DEPOSIT_IN, 41, 0),
    ("14",  "雜項",                SIDE_REVENUE, GROUP_OTHER_REV,  50, 0),
    ("39",  "轉帳",                SIDE_REVENUE, GROUP_OTHER_REV,  51, 1),
    ("66",  "代支",                SIDE_REVENUE, GROUP_OTHER_REV,  52, 0),
    # ── 抵充側 ───────────────────────────────────────────────────────────────
    ("73",  "AE信用卡",            SIDE_SETTLEMENT, GROUP_CARD,        60, 0),
    ("74",  "VISA信用卡",          SIDE_SETTLEMENT, GROUP_CARD,        61, 0),
    ("75",  "MASTER信用卡",        SIDE_SETTLEMENT, GROUP_CARD,        62, 0),
    ("77",  "JCB信用卡",           SIDE_SETTLEMENT, GROUP_CARD,        63, 0),
    ("78",  "聯合信用卡",          SIDE_SETTLEMENT, GROUP_CARD,        64, 0),
    ("79",  "銀聯卡",              SIDE_SETTLEMENT, GROUP_CARD,        65, 0),
    ("71A", "電匯",                SIDE_SETTLEMENT, GROUP_EPAY,        70, 0),
    ("71B", "線上授權-LINK PAY",   SIDE_SETTLEMENT, GROUP_EPAY,        71, 0),
    ("71",  "現金",                SIDE_SETTLEMENT, GROUP_CASH,        80, 0),
    ("81",  "沖預收訂金(已開)",    SIDE_SETTLEMENT, GROUP_DEPOSIT_OUT, 90, 0),
    ("81A", "沖預收訂金(要開)",    SIDE_SETTLEMENT, GROUP_DEPOSIT_OUT, 91, 0),
    ("86",  "外客簽帳(不開發票)",  SIDE_SETTLEMENT, GROUP_AR,         100, 0),
    ("86A", "外客簽帳(開立發票)",  SIDE_SETTLEMENT, GROUP_AR,         101, 0),
    ("95",  "信託禮券",            SIDE_SETTLEMENT, GROUP_OTHER_SET,  110, 0),
]


def ensure_jinxu_seed(db: Session) -> dict[str, int]:
    """冪等寫入科目分類與預設門檻。回傳新增筆數統計。"""
    added_subject = 0
    existing = {row.subject_code for row in db.query(JinxuSubjectMap.subject_code).all()}
    for code, name, side, group, order, memo in SUBJECT_SEED:
        if code in existing:
            continue
        db.add(JinxuSubjectMap(
            subject_code=code, subject_name=name, side=side,
            group_code=group, sort_order=order, is_memo_only=memo, is_active=1,
        ))
        added_subject += 1

    added_setting = 0
    existing_keys = {row.setting_key for row in db.query(JinxuAnalysisSetting.setting_key).all()}
    for key, value, vtype, desc in DEFAULT_SETTINGS:
        if key in existing_keys:
            continue
        db.add(JinxuAnalysisSetting(
            property_code="", setting_key=key, setting_value=value,
            value_type=vtype, description=desc,
        ))
        added_setting += 1

    if added_subject or added_setting:
        db.commit()
        logger.info("金旭 seed：新增科目 %d 筆、設定 %d 筆", added_subject, added_setting)
    return {"subjects": added_subject, "settings": added_setting}
