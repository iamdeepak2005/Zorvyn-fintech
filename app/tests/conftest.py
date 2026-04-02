"""
Zorvyn Fintech - Test Configuration.
Sets up test database, client, and fixtures for all tests.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.core.security import hash_password, create_access_token
from app.main import app
from app.models.user import User, UserRole
from app.models.financial_record import FinancialRecord, RecordType
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.idempotency_key import IdempotencyKey  # noqa: F401

# Use SQLite in-memory for tests (fast, isolated)
SQLALCHEMY_TEST_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency with test database."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Override the database dependency
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_database():
    """Create tables before each test, drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    """Provide a test database session."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    """Provide a test HTTP client."""
    return TestClient(app)


@pytest.fixture
def admin_user(db):
    """Create and return an admin user."""
    user = User(
        name="Test Admin",
        email="admin@test.com",
        password_hash=hash_password("admin123"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def analyst_user(db):
    """Create and return an analyst user."""
    user = User(
        name="Test Analyst",
        email="analyst@test.com",
        password_hash=hash_password("analyst123"),
        role=UserRole.ANALYST,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def viewer_user(db):
    """Create and return a viewer user."""
    user = User(
        name="Test Viewer",
        email="viewer@test.com",
        password_hash=hash_password("viewer123"),
        role=UserRole.VIEWER,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def inactive_user(db):
    """Create and return an inactive user."""
    user = User(
        name="Inactive User",
        email="inactive@test.com",
        password_hash=hash_password("inactive123"),
        role=UserRole.VIEWER,
        is_active=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_token(admin_user):
    """Generate a JWT token for the admin user."""
    return create_access_token(
        data={"user_id": admin_user.id, "role": admin_user.role.value}
    )


@pytest.fixture
def analyst_token(analyst_user):
    """Generate a JWT token for the analyst user."""
    return create_access_token(
        data={"user_id": analyst_user.id, "role": analyst_user.role.value}
    )


@pytest.fixture
def viewer_token(viewer_user):
    """Generate a JWT token for the viewer user."""
    return create_access_token(
        data={"user_id": viewer_user.id, "role": viewer_user.role.value}
    )


@pytest.fixture
def sample_records(db, admin_user):
    """Create sample financial records for testing."""
    from datetime import date
    from decimal import Decimal

    records = [
        FinancialRecord(
            user_id=admin_user.id,
            amount=Decimal("5000.00"),
            type=RecordType.INCOME,
            category="Salary",
            date=date(2026, 3, 1),
            notes="Monthly salary",
        ),
        FinancialRecord(
            user_id=admin_user.id,
            amount=Decimal("1500.00"),
            type=RecordType.EXPENSE,
            category="Rent",
            date=date(2026, 3, 5),
            notes="Monthly rent payment",
        ),
        FinancialRecord(
            user_id=admin_user.id,
            amount=Decimal("200.00"),
            type=RecordType.EXPENSE,
            category="Groceries",
            date=date(2026, 3, 10),
            notes="Weekly groceries",
        ),
        FinancialRecord(
            user_id=admin_user.id,
            amount=Decimal("3000.00"),
            type=RecordType.INCOME,
            category="Freelance",
            date=date(2026, 2, 15),
            notes="Freelance project",
        ),
        FinancialRecord(
            user_id=admin_user.id,
            amount=Decimal("800.00"),
            type=RecordType.EXPENSE,
            category="Rent",
            date=date(2026, 2, 5),
            notes="February rent",
        ),
    ]
    db.add_all(records)
    db.commit()
    for r in records:
        db.refresh(r)
    return records
