"""
競品分析 — 配額服務單元測試

規格書：docs/SPEC_compset_analysis.md §3.3～§3.5、D14、D15
服務層：app/services/compset_quota_service.py

測試策略
────────
配額直接等於 API 成本與對外收費，所以這裡測的不是「有沒有噴錯」，
而是**每一條會讓錢算錯的路徑**：

  · 週期邊界（day == anchor、跨年、anchor 29 被擋）
  · 預留的「全有全無」——失敗時一次都不可以扣
  · 退還綁定期間——跨期退還必須被拒絕，否則等於憑空發額度
  · 加發不改 monthly_quota、不結轉到下一期
  · 防提權 P-1、稽核 P-3

執行：
    cd backend && python -m pytest tests/test_compset_quota.py -v
"""
from __future__ import annotations

import importlib
import pkgutil
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models as _models_pkg
from app.core.database import Base

# env.py 的同一招：逐一 import 整個 models package。
# 少 import 一個模組，User／AuditLog 的 relationship 就設定不起來。
for _m in pkgutil.iter_modules(_models_pkg.__path__):
    importlib.import_module(f"app.models.{_m.name}")

from app.models.audit_log import AuditLog                       # noqa: E402
from app.models.compset_analysis import (CompsetSubscriber,      # noqa: E402
                                         CompsetSubscriberUser)
from app.models.user import User                                 # noqa: E402
from app.services import compset_quota_service as Q              # noqa: E402

TODAY = date(2026, 9, 20)          # anchor=15 → 本期 2026-09-15
NEXT_PERIOD = date(2026, 10, 20)   # → 2026-10-15

OWNER = "u-owner"     # 不屬於任何 subscriber
CUSTOMER = "u-cust"   # 屬於受測 subscriber


@pytest.fixture()
def db():
    engine = create_engine("sqlite://")
    tables = [t for name, t in Base.metadata.tables.items()
              if name.startswith("compset_") or name in ("users", "audit_logs", "tenants")]
    Base.metadata.create_all(engine, tables=tables)
    session = sessionmaker(bind=engine)()
    session.add(User(id=OWNER, email="owner@example.com"))
    session.add(User(id=CUSTOMER, email="cust@example.com"))
    session.commit()
    yield session
    session.close()


@pytest.fixture()
def sub(db):
    row = CompsetSubscriber(
        code="INTERNAL", name="內部", monthly_quota=10, quota_used=0,
        quota_anchor_day=15, quota_period_start="",
        plan_level="A", window_a_days=14, window_b_days=45, window_c_days=120,
        freq_a_days=1, freq_b_days=3, freq_c_days=7,
        param_adults=2, param_nights=1, param_gl="tw", param_hl="zh-tw",
        param_currency="TWD", is_active=True,
        contact_name="", contact_email="", note="",
    )
    db.add(row)
    db.commit()
    return row


# ══════════════════════════════════════════════════════════════════════════
# 1. 計費週期
# ══════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("day,anchor,expected", [
    (date(2026, 9, 20), 15, "2026-09-15"),   # 當月
    (date(2026, 9, 3), 15, "2026-08-15"),    # 尚未到 anchor → 上一期
    (date(2026, 9, 15), 15, "2026-09-15"),   # 邊界：day == anchor 算當期
    (date(2026, 1, 3), 15, "2025-12-15"),    # 跨年
    (date(2026, 3, 1), 1, "2026-03-01"),     # anchor=1
])
def test_period_start_for(day, anchor, expected):
    assert Q.period_start_for(day, anchor) == expected


def test_anchor_day_29_rejected():
    """29~31 在 2 月會歸零失敗，必須在寫入時就擋掉。"""
    with pytest.raises(Q.InvalidAnchorDay):
        Q.validate_anchor_day(29)


def test_ensure_period_is_idempotent(db, sub):
    assert Q.ensure_period(db, sub.id, TODAY) == "2026-09-15"
    assert Q.ensure_period(db, sub.id, TODAY) == "2026-09-15"


# ══════════════════════════════════════════════════════════════════════════
# 2. 預留：全有全無（SPEC D15）
# ══════════════════════════════════════════════════════════════════════════
def test_reserve_is_all_or_nothing(db, sub):
    """額度 10：先預留 6 成功；再預留 6 必須整組失敗，且一次都不能扣。"""
    assert Q.reserve(db, sub.id, 6, TODAY) is True
    db.commit()
    assert Q.reserve(db, sub.id, 6, TODAY) is False
    db.commit()
    assert Q.quota_status(db, sub.id, TODAY)["used"] == 6


def test_reserve_exact_fit_then_exhausted(db, sub):
    Q.reserve(db, sub.id, 6, TODAY)
    db.commit()
    assert Q.reserve(db, sub.id, 4, TODAY) is True      # 剛好用完
    db.commit()
    assert Q.reserve(db, sub.id, 1, TODAY) is False
    st = Q.quota_status(db, sub.id, TODAY)
    assert st["is_exhausted"] and st["available"] == 0


def test_reserve_blocked_when_inactive(db, sub):
    sub.is_active = False
    db.commit()
    assert Q.reserve(db, sub.id, 1, TODAY) is False


# ══════════════════════════════════════════════════════════════════════════
# 3. 退還：必須綁定期間
# ══════════════════════════════════════════════════════════════════════════
def test_refund_rejects_wrong_period(db, sub):
    """
    ⭐ 跨期退還必須回 0。

    若不擋，期間滾動後的退還會把新期間的 quota_used 扣成負的 ——
    等於憑空多發一批額度。
    """
    Q.reserve(db, sub.id, 6, TODAY)
    db.commit()
    assert Q.refund(db, sub.id, 2, "2026-08-15") == 0
    db.commit()
    assert Q.quota_status(db, sub.id, TODAY)["used"] == 6


def test_refund_returns_unused(db, sub):
    Q.reserve(db, sub.id, 6, TODAY)
    db.commit()
    assert Q.refund(db, sub.id, 2, "2026-09-15") == 2
    db.commit()
    assert Q.quota_status(db, sub.id, TODAY)["used"] == 4


def test_refund_never_goes_negative(db, sub):
    Q.reserve(db, sub.id, 2, TODAY)
    db.commit()
    assert Q.refund(db, sub.id, 5, "2026-09-15") == 0     # 退比用掉的還多 → 不退
    db.commit()
    assert Q.quota_status(db, sub.id, TODAY)["used"] == 2


# ══════════════════════════════════════════════════════════════════════════
# 4. 手動加發
# ══════════════════════════════════════════════════════════════════════════
def test_grant_adds_capacity_without_changing_monthly_quota(db, sub):
    Q.grant_quota(db, subscriber_id=sub.id, granted_qty=5, reason="臨時活動加抓",
                  granted_by_user_id=OWNER, today=TODAY)
    db.commit()
    st = Q.quota_status(db, sub.id, TODAY)
    assert st["limit"] == 15 and st["granted"] == 5
    assert st["monthly_quota"] == 10          # ⭐ 加發不可變成永久漲價


def test_grant_writes_audit_log(db, sub):
    """P-3：加發必須同時留在 compset_quota_grants 與 audit_logs。"""
    Q.grant_quota(db, subscriber_id=sub.id, granted_qty=5, reason="測試",
                  granted_by_user_id=OWNER, ip_address="127.0.0.1", today=TODAY)
    db.commit()
    logs = db.query(AuditLog).filter_by(action="compset_quota_grant").all()
    assert len(logs) == 1
    assert logs[0].extra["granted_qty"] == 5
    assert logs[0].extra["period_start"] == "2026-09-15"
    assert len(Q.list_grants(db, sub.id)) == 1


@pytest.mark.parametrize("qty,reason", [(0, "x"), (-1, "x"), (1, "   ")])
def test_grant_rejects_bad_input(db, sub, qty, reason):
    with pytest.raises(Q.InvalidGrant):
        Q.grant_quota(db, subscriber_id=sub.id, granted_qty=qty, reason=reason,
                      granted_by_user_id=OWNER, today=TODAY)


# ══════════════════════════════════════════════════════════════════════════
# 5. 防提權 P-1
# ══════════════════════════════════════════════════════════════════════════
def test_p1_blocks_self_grant(db, sub):
    """屬於該訂閱的使用者不得幫自己加額度。"""
    db.add(CompsetSubscriberUser(subscriber_id=sub.id, user_id=CUSTOMER))
    db.commit()
    with pytest.raises(Q.SelfGrantForbidden):
        Q.grant_quota(db, subscriber_id=sub.id, granted_qty=1, reason="自己加",
                      granted_by_user_id=CUSTOMER, today=TODAY)


def test_p1_allows_unassociated_user(db, sub):
    """
    沒有歸屬的使用者（內部工程人員）不受 P-1 限制 —— 這是刻意的（SPEC D14）。
    調整 INTERNAL 的配額是成本決策，不是提權。
    """
    db.add(CompsetSubscriberUser(subscriber_id=sub.id, user_id=CUSTOMER))
    db.commit()
    assert Q.grant_quota(db, subscriber_id=sub.id, granted_qty=1, reason="ok",
                         granted_by_user_id=OWNER, today=TODAY) is not None


# ══════════════════════════════════════════════════════════════════════════
# 6. 跨期
# ══════════════════════════════════════════════════════════════════════════
def test_period_roll_resets_usage_and_expires_grants(db, sub):
    """⭐ 期間滾動：quota_used 歸零，而且**加發額度不結轉**。"""
    Q.reserve(db, sub.id, 6, TODAY)
    Q.grant_quota(db, subscriber_id=sub.id, granted_qty=5, reason="本期加發",
                  granted_by_user_id=OWNER, today=TODAY)
    db.commit()
    assert Q.quota_status(db, sub.id, TODAY)["limit"] == 15

    st = Q.quota_status(db, sub.id, NEXT_PERIOD)
    assert st["period_start"] == "2026-10-15"
    assert st["used"] == 0
    assert st["granted"] == 0 and st["limit"] == 10
