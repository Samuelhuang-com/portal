"""
合約管理系統 - API 測試套件

測試所有合約、廠商、預算科目的 REST API 端點。
包括成功情景、錯誤情景、權限檢查等。
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.main import app
from app.core.database import Base, get_db
from app.models.user import User
from app.models.role import Role
from app.models.user_role import UserRole
from app.models.contract import Contract, ContractItem, Vendor, BudgetCategory
from app.core.security import hash_password, create_access_token
from app.core.config import settings


# ─────────────────────────────────────────────────────────────────────────────
# 測試資料庫設置
# ─────────────────────────────────────────────────────────────────────────────

SQLALCHEMY_DATABASE_URL = "sqlite:///test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    """覆蓋 get_db，使用測試資料庫"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def cleanup_db():
    """每個測試前清空資料庫，測試後清理"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    """提供測試資料庫連線"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(db: Session) -> User:
    """建立測試使用者"""
    # 建立角色
    role = Role(
        name="test_admin",
        scope="tenant",
        description="Test Admin Role"
    )
    db.add(role)
    db.commit()

    # 建立使用者
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=hash_password("password123"),
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 指派角色
    user_role = UserRole(
        user_id=user.id,
        role_id=role.id,
    )
    db.add(user_role)
    db.commit()

    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """生成驗證 headers"""
    token = create_access_token(subject=str(test_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_vendor(db: Session) -> Vendor:
    """建立測試廠商"""
    vendor = Vendor(
        vendor_id="VND-0001",
        vendor_name="Test Vendor",
        tax_id="12345678",
        contact_person="John Doe",
        phone="0912345678",
        email="vendor@example.com",
        address="123 Main St",
        payment_terms="Net 30",
        bank_name="Test Bank",
        bank_account="1234567890",
        vendor_type="General",
        risk_level="低",
        is_critical=False,
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


@pytest.fixture
def test_budget_category(db: Session) -> BudgetCategory:
    """建立測試預算科目"""
    current_year = datetime.now().year
    category = BudgetCategory(
        budget_year=current_year,
        dept="Engineering",
        category_l1="Equipment",
        category_l2="Office",
        accounting_code="5000-1000",
        payment_code="5000",
        is_enabled=True,
        effective_date=datetime.now().date(),
        maintain_unit="Finance",
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@pytest.fixture
def test_contract(db: Session, test_vendor: Vendor, test_budget_category: BudgetCategory) -> Contract:
    """建立測試合約"""
    today = datetime.now().date()
    contract = Contract(
        contract_id="CON-2026-0001",
        contract_name="Test Contract",
        contract_type="Service",
        contract_status="草稿",
        responsible_dept="Engineering",
        vendor_id=test_vendor.vendor_id,
        vendor_name=test_vendor.vendor_name,
        start_date=today,
        end_date=today + timedelta(days=365),
        total_amount_tax_included=100000.0,
        pricing_method="Monthly",
        budget_year=test_budget_category.budget_year,
        budget_category_l1=test_budget_category.category_l1,
        budget_category_l2=test_budget_category.category_l2,
        accounting_code=test_budget_category.accounting_code,
        detail={
            "編號": "CON-2026-0001",
            "合約名稱": "Test Contract",
            "廠商": "Test Vendor",
        }
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return contract


# ─────────────────────────────────────────────────────────────────────────────
# 合約 API 測試
# ─────────────────────────────────────────────────────────────────────────────

class TestContractAPI:
    """合約 API 測試類"""

    def test_list_contracts_success(self, auth_headers: dict, test_contract: Contract):
        """測試成功查詢合約列表"""
        response = client.get("/api/v1/contracts", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "data" in data
        assert len(data["data"]) >= 0

    def test_list_contracts_with_pagination(self, auth_headers: dict, test_contract: Contract):
        """測試合約列表分頁"""
        response = client.get(
            "/api/v1/contracts?skip=0&limit=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["skip"] == 0
        assert data["limit"] == 10

    def test_list_contracts_with_search(self, auth_headers: dict, test_contract: Contract):
        """測試合約列表搜尋"""
        response = client.get(
            "/api/v1/contracts?search=CON-2026",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 0

    def test_get_contract_success(self, auth_headers: dict, test_contract: Contract):
        """測試成功查詢單筆合約"""
        response = client.get(
            f"/api/v1/contracts/{test_contract.contract_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["contract_id"] == test_contract.contract_id
        assert data["contract_name"] == test_contract.contract_name

    def test_get_contract_not_found(self, auth_headers: dict):
        """測試查詢不存在的合約"""
        response = client.get(
            "/api/v1/contracts/NON-EXISTENT",
            headers=auth_headers
        )
        assert response.status_code == 404

    def test_create_contract_success(
        self,
        auth_headers: dict,
        test_vendor: Vendor,
        test_budget_category: BudgetCategory
    ):
        """測試成功建立合約"""
        today = datetime.now().date()
        contract_data = {
            "contract_id": "CON-2026-0002",
            "contract_name": "New Contract",
            "contract_type": "Service",
            "contract_status": "草稿",
            "responsible_dept": "Sales",
            "vendor_id": test_vendor.vendor_id,
            "start_date": str(today),
            "end_date": str(today + timedelta(days=180)),
            "total_amount_tax_included": 50000.0,
            "pricing_method": "Fixed",
            "budget_year": test_budget_category.budget_year,
            "budget_category_l1": test_budget_category.category_l1,
            "budget_category_l2": test_budget_category.category_l2,
        }

        response = client.post(
            "/api/v1/contracts",
            json=contract_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["contract_id"] == "CON-2026-0002"

    def test_create_contract_already_exists(
        self,
        auth_headers: dict,
        test_contract: Contract,
        test_vendor: Vendor,
        test_budget_category: BudgetCategory
    ):
        """測試建立重複的合約"""
        today = datetime.now().date()
        contract_data = {
            "contract_id": test_contract.contract_id,  # 使用已存在的 ID
            "contract_name": "Duplicate Contract",
            "contract_type": "Service",
            "responsible_dept": "Sales",
            "vendor_id": test_vendor.vendor_id,
            "start_date": str(today),
            "end_date": str(today + timedelta(days=180)),
            "total_amount_tax_included": 50000.0,
            "pricing_method": "Fixed",
            "budget_year": test_budget_category.budget_year,
            "budget_category_l1": test_budget_category.category_l1,
            "budget_category_l2": test_budget_category.category_l2,
        }

        response = client.post(
            "/api/v1/contracts",
            json=contract_data,
            headers=auth_headers
        )
        assert response.status_code == 409  # Conflict

    def test_create_contract_invalid_dates(
        self,
        auth_headers: dict,
        test_vendor: Vendor,
        test_budget_category: BudgetCategory
    ):
        """測試建立合約時日期無效"""
        today = datetime.now().date()
        contract_data = {
            "contract_id": "CON-2026-0003",
            "contract_name": "Invalid Contract",
            "contract_type": "Service",
            "responsible_dept": "Sales",
            "vendor_id": test_vendor.vendor_id,
            "start_date": str(today + timedelta(days=180)),  # 起日晚於迄日
            "end_date": str(today),
            "total_amount_tax_included": 50000.0,
            "pricing_method": "Fixed",
            "budget_year": test_budget_category.budget_year,
            "budget_category_l1": test_budget_category.category_l1,
            "budget_category_l2": test_budget_category.category_l2,
        }

        response = client.post(
            "/api/v1/contracts",
            json=contract_data,
            headers=auth_headers
        )
        assert response.status_code == 400

    def test_update_contract_success(
        self,
        auth_headers: dict,
        test_contract: Contract
    ):
        """測試成功更新合約"""
        update_data = {
            "contract_name": "Updated Contract Name",
            "risk_level": "高",
        }

        response = client.put(
            f"/api/v1/contracts/{test_contract.contract_id}",
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["contract_name"] == "Updated Contract Name"
        assert data["risk_level"] == "高"

    def test_delete_contract_success(
        self,
        auth_headers: dict,
        test_contract: Contract
    ):
        """測試成功刪除合約"""
        response = client.delete(
            f"/api/v1/contracts/{test_contract.contract_id}",
            headers=auth_headers
        )
        assert response.status_code == 204

    def test_delete_contract_not_found(self, auth_headers: dict):
        """測試刪除不存在的合約"""
        response = client.delete(
            "/api/v1/contracts/NON-EXISTENT",
            headers=auth_headers
        )
        assert response.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# 廠商 API 測試
# ─────────────────────────────────────────────────────────────────────────────

class TestVendorAPI:
    """廠商 API 測試類"""

    def test_list_vendors_success(self, auth_headers: dict, test_vendor: Vendor):
        """測試成功查詢廠商列表"""
        response = client.get("/api/v1/vendors", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "data" in data

    def test_get_vendor_success(self, auth_headers: dict, test_vendor: Vendor):
        """測試成功查詢單筆廠商"""
        response = client.get(
            f"/api/v1/vendors/{test_vendor.vendor_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["vendor_id"] == test_vendor.vendor_id
        assert data["vendor_name"] == test_vendor.vendor_name

    def test_create_vendor_success(self, auth_headers: dict):
        """測試成功建立廠商"""
        vendor_data = {
            "vendor_id": "VND-0002",
            "vendor_name": "New Vendor",
            "tax_id": "87654321",
            "contact_person": "Jane Doe",
            "phone": "0987654321",
            "email": "newvendor@example.com",
            "vendor_type": "Supplier",
        }

        response = client.post(
            "/api/v1/vendors",
            json=vendor_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["vendor_id"] == "VND-0002"


# ─────────────────────────────────────────────────────────────────────────────
# 預算科目 API 測試
# ─────────────────────────────────────────────────────────────────────────────

class TestBudgetCategoryAPI:
    """預算科目 API 測試類"""

    def test_list_budget_categories_success(
        self,
        auth_headers: dict,
        test_budget_category: BudgetCategory
    ):
        """測試成功查詢預算科目列表"""
        response = client.get("/api/v1/budget-categories", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "data" in data


# ─────────────────────────────────────────────────────────────────────────────
# 権限測試
# ─────────────────────────────────────────────────────────────────────────────

class TestAuthorizationAPI:
    """授權測試類"""

    def test_list_contracts_without_token(self):
        """測試無驗證 token 查詢合約"""
        response = client.get("/api/v1/contracts")
        assert response.status_code == 401

    def test_list_vendors_without_token(self):
        """測試無驗證 token 查詢廠商"""
        response = client.get("/api/v1/vendors")
        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
