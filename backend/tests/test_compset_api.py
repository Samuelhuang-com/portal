"""
競品分析 — API 端點測試

規格書：docs/SPEC_compset_analysis.md §8、§3.5
Router：app/routers/compset_rates.py、app/routers/compset_admin.py

測試策略
────────
用 `TestClient` 掛一個只含這兩支 router 的小 app，
再用 `dependency_overrides` 換掉 `get_db` 與 `get_current_user`。

⚠️ **SQLite ＋ TestClient 的坑**（記憶 project_cycle_purchase_dept_scope）：
   in-memory SQLite 每個連線是**各自獨立的資料庫**。
   一定要 `StaticPool` ＋ `check_same_thread=False`，
   否則測試裡建的資料，app 那邊查不到 —— 而且錯誤訊息只會說「找不到」。

重點測的是「靠前端擋不住」的事：
  · 訂閱隔離（不能看別人的資料）
  · P-1 防提權（不能幫自己加配額）
  · is_self 必須恰一筆
  · 窗口必須遞增
  · 節奏設定會回傳成本試算與資料斷點警告

執行：
    cd backend && python -m pytest tests/test_compset_api.py -v
"""
from __future__ import annotations

import importlib
import pkgutil
from datetime import date

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

import app.models as _models_pkg
from app.core.database import Base, get_db

for _m in pkgutil.iter_modules(_models_pkg.__path__):
    importlib.import_module(f"app.models.{_m.name}")

from app import dependencies as DEP                                 # noqa: E402
from app.models.compset_analysis import (CompsetHotel,              # noqa: E402
                                         CompsetRateSnapshot,
                                         CompsetSubscriber,
                                         CompsetSubscriberUser)
from app.models.user import User                                    # noqa: E402
from app.routers import compset_admin, compset_rates                # noqa: E402

TODAY = date(2026, 9, 9)
OWNER = "u-owner"
CUSTOMER = "u-cust"


@pytest.fixture()
def session():
    # ⚠️ StaticPool：讓 app 與測試共用同一個 in-memory 連線（見檔頭）
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    tables = [t for n, t in Base.metadata.tables.items()
              if n.startswith("compset_") or n in ("users", "audit_logs", "tenants")]
    Base.metadata.create_all(engine, tables=tables)
    s = sessionmaker(bind=engine)()
    s.add(User(id=OWNER, email="owner@example.com"))
    s.add(User(id=CUSTOMER, email="cust@example.com"))
    s.commit()
    yield s
    s.close()


@pytest.fixture()
def data(session):
    subs = {}
    for code, name in (("INTERNAL", "內部"), ("CUST-A", "客戶A")):
        sub = CompsetSubscriber(
            code=code, name=name, plan_level="A", location_query="公館 台北",
            monthly_quota=3500, quota_used=0, quota_anchor_day=1,
            quota_period_start="", window_a_days=14, window_b_days=45,
            window_c_days=120, freq_a_days=1, freq_b_days=3, freq_c_days=7,
            param_adults=2, param_nights=1, param_gl="tw", param_hl="zh-tw",
            param_currency="TWD", is_active=True,
            contact_name="", contact_email="", note="",
        )
        session.add(sub)
        session.flush()
        subs[code] = sub
        for i, (hname, is_self, tok) in enumerate([
                ("瀚寓夏天", True, "tok-self"), ("承攜行旅", False, "tok-guide")]):
            session.add(CompsetHotel(subscriber_id=sub.id, display_name=f"{hname}",
                                     hotel_code=f"{code}-{i}", is_self=is_self,
                                     google_property_token=tok,
                                     google_query_name=hname, is_enabled=True,
                                     sort_order=i, registered_address="", note=""))
    # CUSTOMER 屬於 CUST-A
    session.add(CompsetSubscriberUser(subscriber_id=subs["CUST-A"].id,
                                      user_id=CUSTOMER))
    session.commit()
    return subs


@pytest.fixture()
def client(session, monkeypatch):
    api = FastAPI()
    api.include_router(compset_rates.router, prefix="/api/v1/compset")
    api.include_router(compset_admin.router, prefix="/api/v1/compset")

    state = {"user": OWNER, "perms": ["*"]}

    def _db():
        yield session

    def _user():
        return session.get(User, state["user"])

    def _perms(user_id, db):
        return state["perms"]

    api.dependency_overrides[get_db] = _db
    api.dependency_overrides[DEP.get_current_user] = _user
    monkeypatch.setattr(DEP, "get_user_permissions", _perms)
    # ⚠️ compset_rates 是 `from ... import get_user_permissions`，
    #    所以它自己的模組命名空間也要換掉，否則 is_subscriber_admin 用到舊的。
    monkeypatch.setattr(compset_rates, "get_user_permissions", _perms)

    c = TestClient(api)
    c.state_ = state          # 測試裡切換身分／權限用
    return c


# ══════════════════════════════════════════════════════════════════════════
# 1. 訂閱隔離
# ══════════════════════════════════════════════════════════════════════════
def test_user_without_association_gets_internal(client, data):
    """
    沒有歸屬的使用者（內部人員）→ 拿到 INTERNAL。
    這是刻意的（SPEC D14），不是漏判。
    """
    r = client.get("/api/v1/compset/dashboard")
    assert r.status_code == 200
    assert r.json()["subscriber"]["code"] == "INTERNAL"


def test_associated_user_gets_own_subscriber(client, data):
    client.state_["user"] = CUSTOMER
    client.state_["perms"] = ["compset_view"]
    r = client.get("/api/v1/compset/dashboard")
    assert r.status_code == 200
    assert r.json()["subscriber"]["code"] == "CUST-A"


def test_cannot_peek_at_another_subscriber(client, data):
    """
    ⭐ 靠前端隱藏下拉選單擋不住 —— 後端一定要驗。
    """
    client.state_["user"] = CUSTOMER
    client.state_["perms"] = ["compset_view"]
    r = client.get("/api/v1/compset/dashboard",
                   params={"subscriber_id": data["INTERNAL"].id})
    assert r.status_code == 403


def test_subscriber_admin_may_switch(client, data):
    client.state_["user"] = OWNER
    client.state_["perms"] = ["compset_view", "compset_subscriber_admin"]
    r = client.get("/api/v1/compset/dashboard",
                   params={"subscriber_id": data["CUST-A"].id})
    assert r.status_code == 200 and r.json()["subscriber"]["code"] == "CUST-A"


def test_detail_checks_ownership(client, session, data):
    """明細端點直接吃 id，不檢查就等於全庫可讀。"""
    row = CompsetRateSnapshot(
        subscriber_id=data["INTERNAL"].id,
        compset_hotel_id=session.execute(
            select(CompsetHotel.id).where(
                CompsetHotel.subscriber_id == data["INTERNAL"].id)).scalars().first(),
        snapshot_date="2026-09-09", stay_date="2026-09-20", tier="A",
        fetch_path="token", source="serpapi", price_gross=1900, price_pretax=1645,
        currency="TWD", tax_included="yes", ota_name="", is_official=False,
        free_cancellation=False, room_type_raw="", is_sold_out="no")
    session.add(row)
    session.commit()

    client.state_["user"] = CUSTOMER
    client.state_["perms"] = ["compset_matrix_view"]
    r = client.get("/api/v1/compset/rates/detail", params={"snapshot_id": row.id})
    assert r.status_code == 403


# ══════════════════════════════════════════════════════════════════════════
# 2. 防提權 P-1
# ══════════════════════════════════════════════════════════════════════════
def test_p1_blocks_granting_to_own_subscriber(client, data):
    """⭐ 不能幫自己加配額 —— 這是本模組唯一能「自己給自己加錢」的地方。"""
    client.state_["user"] = CUSTOMER
    client.state_["perms"] = ["compset_subscriber_admin"]
    r = client.post(f"/api/v1/compset/subscribers/{data['CUST-A'].id}/grant-quota",
                    json={"granted_qty": 500, "reason": "自己加"})
    assert r.status_code == 403 and "自己所屬" in r.json()["detail"]


def test_grant_requires_reason(client, data):
    r = client.post(f"/api/v1/compset/subscribers/{data['CUST-A'].id}/grant-quota",
                    json={"granted_qty": 500, "reason": "  "})
    assert r.status_code == 400


def test_grant_does_not_change_monthly_quota(client, data):
    r = client.post(f"/api/v1/compset/subscribers/{data['CUST-A'].id}/grant-quota",
                    json={"granted_qty": 500, "reason": "活動加抓"})
    assert r.status_code == 200
    q = r.json()["quota"]
    assert q["monthly_quota"] == 3500 and q["granted"] == 500 and q["limit"] == 4000


def test_anchor_day_29_rejected_by_api(client, data):
    r = client.put(f"/api/v1/compset/subscribers/{data['INTERNAL'].id}",
                   json={"quota_anchor_day": 29})
    assert r.status_code == 400 and "28" in r.json()["detail"]


# ══════════════════════════════════════════════════════════════════════════
# 3. 競爭組
# ══════════════════════════════════════════════════════════════════════════
def test_cannot_end_up_with_two_selves(client, data, session):
    """⭐ is_self 必須恰一筆 —— DB 做不到，只能在這裡擋。"""
    other = session.execute(
        select(CompsetHotel).where(CompsetHotel.subscriber_id == data["INTERNAL"].id,
                                   CompsetHotel.is_self.is_(False))).scalar_one()
    r = client.put(f"/api/v1/compset/hotels/{other.id}", json={"is_self": True})
    assert r.status_code == 400 and "恰有一家" in r.json()["detail"]


def test_cannot_end_up_with_zero_selves(client, data, session):
    me = session.execute(
        select(CompsetHotel).where(CompsetHotel.subscriber_id == data["INTERNAL"].id,
                                   CompsetHotel.is_self.is_(True))).scalar_one()
    r = client.put(f"/api/v1/compset/hotels/{me.id}", json={"is_self": False})
    assert r.status_code == 400


def test_cannot_delete_self_hotel(client, data, session):
    me = session.execute(
        select(CompsetHotel).where(CompsetHotel.subscriber_id == data["INTERNAL"].id,
                                   CompsetHotel.is_self.is_(True))).scalar_one()
    r = client.delete(f"/api/v1/compset/hotels/{me.id}")
    assert r.status_code == 400


def test_hotel_list_warns_about_missing_token(client, data, session):
    """缺 token 的家 A 級抓不到，畫面要提示，不要讓人以為系統壞了。"""
    h = session.execute(
        select(CompsetHotel).where(CompsetHotel.subscriber_id == data["INTERNAL"].id,
                                   CompsetHotel.is_self.is_(False))).scalar_one()
    h.google_property_token = ""
    session.commit()
    r = client.get("/api/v1/compset/hotels")
    assert r.status_code == 200
    assert any("property_token" in w for w in r.json()["warnings"])
    assert [i for i in r.json()["items"] if not i["has_token"]]


# ══════════════════════════════════════════════════════════════════════════
# 4. 抓取節奏
# ══════════════════════════════════════════════════════════════════════════
def test_cadence_returns_cost_estimate(client, data):
    """⭐ 讓人在按下儲存之前就看到成本，而不是月底看帳單才發現。"""
    r = client.get("/api/v1/compset/settings/cadence")
    assert r.status_code == 200
    est = r.json()["estimate"]
    assert est["per_tier"]["A"] > 0 and est["total"] > 0
    assert est["over_quota"] is False


def test_cadence_rejects_non_increasing_windows(client, data):
    """窗口不遞增 → 該級別會整個不跑而且沒有錯誤訊息，所以在這裡擋。"""
    r = client.put("/api/v1/compset/settings/cadence",
                   json={"window_a_days": 50, "window_b_days": 45})
    assert r.status_code == 400 and "遞增" in r.json()["detail"]


def test_cadence_warns_on_data_break(client, data):
    """⭐ 改擷取參數 ＝ 資料斷點，前後期價格不再可比。"""
    r = client.put("/api/v1/compset/settings/cadence", json={"param_adults": 3})
    assert r.status_code == 200
    assert r.json()["data_break_warning"] and "入住人數" in r.json()["data_break_warning"]


def test_cadence_warns_when_over_quota(client, data):
    r = client.put("/api/v1/compset/settings/cadence",
                   json={"freq_a_days": 1, "window_a_days": 120,
                         "window_b_days": 121, "window_c_days": 122})
    assert r.status_code == 200
    assert r.json()["over_quota_warning"] is not None


# ══════════════════════════════════════════════════════════════════════════
# 5. CSV
# ══════════════════════════════════════════════════════════════════════════
def test_template_download_has_utf8_filename(client, data):
    """⚠️ 中文檔名沒照 RFC 5987 寫就是 500，而且前端只看到「下載失敗」。"""
    r = client.get("/api/v1/compset/import/template")
    assert r.status_code == 200
    assert "filename*=UTF-8''" in r.headers["content-disposition"]
    assert r.content.startswith(b"\xef\xbb\xbf")      # BOM，Excel 開才不亂碼


def test_csv_upload_reports_row_errors(client, data):
    csv = ("快照日期,入住日期,飯店,含稅價,稅前價,幣別,含稅,是否滿房,通路,房型,入住人數\n"
           "2026-09-09,2026-09-20,瀚寓夏天,1900,1645,TWD,是,否,官網,,2\n"
           "2026-09-09,2026-09-20,不存在的飯店,1900,,,,,,,\n")
    r = client.post("/api/v1/compset/import/upload",
                    files={"file": ("t.csv", csv.encode("utf-8-sig"), "text/csv")})
    assert r.status_code == 200
    body = r.json()
    assert body["inserted"] == 1 and body["skipped"] == 1
    assert body["errors"] and body["errors"][0].startswith("第 3 列")


# ══════════════════════════════════════════════════════════════════════════
# 6. 重算
# ══════════════════════════════════════════════════════════════════════════
def test_recompute_is_free_and_idempotent(client, data, session):
    """快取不是來源：重算不打外部 API、不花配額。"""
    hid = session.execute(
        select(CompsetHotel.id).where(
            CompsetHotel.subscriber_id == data["INTERNAL"].id)).scalars().first()
    session.add(CompsetRateSnapshot(
        subscriber_id=data["INTERNAL"].id, compset_hotel_id=hid,
        snapshot_date="2026-09-09", stay_date="2026-09-20", tier="A",
        fetch_path="token", source="serpapi", price_gross=1900, price_pretax=1645,
        currency="TWD", tax_included="yes", ota_name="", is_official=False,
        free_cancellation=False, room_type_raw="", is_sold_out="no"))
    session.commit()

    before = client.get("/api/v1/compset/dashboard").json()["quota"]["used"]
    r = client.post("/api/v1/compset/stats/recompute", json={})
    assert r.status_code == 200 and r.json()["rows"] == 1
    after = client.get("/api/v1/compset/dashboard").json()["quota"]["used"]
    assert before == after == 0
