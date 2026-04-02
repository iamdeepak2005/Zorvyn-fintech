"""
Zorvyn Fintech - Dashboard Tests.
Tests for dashboard analytics calculations.
Verifies DB-level aggregations return correct results.
"""

from datetime import date
from decimal import Decimal

from app.models.financial_record import FinancialRecord, RecordType


class TestDashboardSummary:
    """Test dashboard summary endpoint calculations."""

    def test_summary_returns_correct_totals(self, client, admin_token, db, admin_user):
        """Summary should correctly calculate income, expense, and net balance."""
        # Create test records
        records = [
            FinancialRecord(
                user_id=admin_user.id, amount=Decimal("5000.00"),
                type=RecordType.INCOME, category="Salary", date=date(2026, 3, 1),
            ),
            FinancialRecord(
                user_id=admin_user.id, amount=Decimal("2000.00"),
                type=RecordType.INCOME, category="Freelance", date=date(2026, 3, 15),
            ),
            FinancialRecord(
                user_id=admin_user.id, amount=Decimal("1500.00"),
                type=RecordType.EXPENSE, category="Rent", date=date(2026, 3, 5),
            ),
            FinancialRecord(
                user_id=admin_user.id, amount=Decimal("300.00"),
                type=RecordType.EXPENSE, category="Groceries", date=date(2026, 3, 10),
            ),
        ]
        db.add_all(records)
        db.commit()

        response = client.get(
            "/api/v1/dashboard/summary",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert float(data["total_income"]) == 7000.00
        assert float(data["total_expense"]) == 1800.00
        assert float(data["net_balance"]) == 5200.00
        assert data["record_count"] == 4

    def test_summary_empty_database(self, client, admin_token):
        """Summary with no records should return zeros."""
        response = client.get(
            "/api/v1/dashboard/summary",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert float(data["total_income"]) == 0
        assert float(data["total_expense"]) == 0
        assert float(data["net_balance"]) == 0
        assert data["record_count"] == 0

    def test_summary_excludes_soft_deleted(self, client, admin_token, db, admin_user):
        """Summary should not include soft-deleted records."""
        from datetime import datetime, timezone

        record = FinancialRecord(
            user_id=admin_user.id, amount=Decimal("1000.00"),
            type=RecordType.INCOME, category="Test", date=date(2026, 3, 1),
            deleted_at=datetime.now(timezone.utc),  # Soft deleted
        )
        db.add(record)
        db.commit()

        response = client.get(
            "/api/v1/dashboard/summary",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        data = response.json()["data"]
        assert float(data["total_income"]) == 0
        assert data["record_count"] == 0


class TestCategoryBreakdown:
    """Test category breakdown endpoint."""

    def test_category_breakdown_groups_correctly(self, client, admin_token, db, admin_user):
        """Should group by category and compute correct totals and percentages."""
        records = [
            FinancialRecord(
                user_id=admin_user.id, amount=Decimal("3000.00"),
                type=RecordType.EXPENSE, category="Rent", date=date(2026, 3, 1),
            ),
            FinancialRecord(
                user_id=admin_user.id, amount=Decimal("1000.00"),
                type=RecordType.EXPENSE, category="Groceries", date=date(2026, 3, 5),
            ),
            FinancialRecord(
                user_id=admin_user.id, amount=Decimal("5000.00"),
                type=RecordType.INCOME, category="Salary", date=date(2026, 3, 1),
            ),
        ]
        db.add_all(records)
        db.commit()

        response = client.get(
            "/api/v1/dashboard/category-breakdown",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]

        # Check expense categories
        assert len(data["expense"]) == 2
        # Rent is 3000/4000 = 75%
        rent_cat = next(c for c in data["expense"] if c["category"] == "Rent")
        assert float(rent_cat["total"]) == 3000.00
        assert rent_cat["percentage"] == 75.0

        # Check income categories
        assert len(data["income"]) == 1
        assert data["income"][0]["category"] == "Salary"
        assert data["income"][0]["percentage"] == 100.0


class TestTrends:
    """Test monthly trends endpoint."""

    def test_trends_returns_monthly_data(self, client, admin_token, db, admin_user):
        """Should return monthly aggregated income/expense/net."""
        records = [
            FinancialRecord(
                user_id=admin_user.id, amount=Decimal("5000.00"),
                type=RecordType.INCOME, category="Salary", date=date(2026, 2, 1),
            ),
            FinancialRecord(
                user_id=admin_user.id, amount=Decimal("1000.00"),
                type=RecordType.EXPENSE, category="Rent", date=date(2026, 2, 5),
            ),
            FinancialRecord(
                user_id=admin_user.id, amount=Decimal("6000.00"),
                type=RecordType.INCOME, category="Salary", date=date(2026, 3, 1),
            ),
            FinancialRecord(
                user_id=admin_user.id, amount=Decimal("1500.00"),
                type=RecordType.EXPENSE, category="Rent", date=date(2026, 3, 5),
            ),
        ]
        db.add_all(records)
        db.commit()

        response = client.get(
            "/api/v1/dashboard/trends",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["granularity"] == "monthly"
        assert len(data["trends"]) == 2  # Feb and Mar


class TestInsights:
    """Test financial insights endpoint."""

    def test_insights_returns_data(self, client, admin_token, db, admin_user):
        """Should return insights with correct top spending category."""
        records = [
            FinancialRecord(
                user_id=admin_user.id, amount=Decimal("3000.00"),
                type=RecordType.EXPENSE, category="Rent", date=date(2026, 3, 1),
            ),
            FinancialRecord(
                user_id=admin_user.id, amount=Decimal("500.00"),
                type=RecordType.EXPENSE, category="Groceries", date=date(2026, 3, 5),
            ),
            FinancialRecord(
                user_id=admin_user.id, amount=Decimal("200.00"),
                type=RecordType.EXPENSE, category="Groceries", date=date(2026, 3, 10),
            ),
        ]
        db.add_all(records)
        db.commit()

        response = client.get(
            "/api/v1/dashboard/insights",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["top_spending_category"] == "Rent"
        assert float(data["top_spending_amount"]) == 3000.00
        assert data["average_daily_expense"] is not None

    def test_insights_empty_database(self, client, admin_token):
        """Insights with no data should return nulls gracefully."""
        response = client.get(
            "/api/v1/dashboard/insights",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["top_spending_category"] is None
        assert data["monthly_growth_percentage"] is None


class TestRecentRecords:
    """Test recent records endpoint."""

    def test_recent_returns_paginated(self, client, admin_token, db, admin_user):
        """Should return paginated recent records."""
        for i in range(15):
            db.add(FinancialRecord(
                user_id=admin_user.id, amount=Decimal("100.00"),
                type=RecordType.EXPENSE, category=f"Cat-{i}",
                date=date(2026, 3, i + 1),
            ))
        db.commit()

        response = client.get(
            "/api/v1/dashboard/recent?page=1&limit=5",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["items"]) == 5
        assert data["total"] == 15
        assert data["total_pages"] == 3
