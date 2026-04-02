"""
Database-level aggregations for the Analytics and Dashboard endpoints.
Offloads mathematical operations (sums, grouping, trends) directly to PostgreSQL
to preserve memory and guarantee high performance.
"""
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.models.financial_record import FinancialRecord, RecordType


class DashboardRepository:
    """All analytics computed at DB level — no Python-loop aggregation."""

    def __init__(self, db: Session):
        self.db = db

    def _base_query(self, user_id: Optional[int] = None):
        query = self.db.query(FinancialRecord).filter(FinancialRecord.deleted_at.is_(None))
        if user_id is not None:
            query = query.filter(FinancialRecord.user_id == user_id)
        return query

    def _base_filter(self, user_id: Optional[int] = None) -> list:
        filters = [FinancialRecord.deleted_at.is_(None)]
        if user_id is not None:
            filters.append(FinancialRecord.user_id == user_id)
        return filters

    def get_summary(self, user_id: Optional[int] = None) -> dict:
        result = self.db.query(
            func.coalesce(func.sum(case(
                (FinancialRecord.type == RecordType.INCOME, FinancialRecord.amount), else_=Decimal("0")
            )), Decimal("0")).label("total_income"),
            func.coalesce(func.sum(case(
                (FinancialRecord.type == RecordType.EXPENSE, FinancialRecord.amount), else_=Decimal("0")
            )), Decimal("0")).label("total_expense"),
            func.count(FinancialRecord.id).label("record_count"),
        ).filter(*self._base_filter(user_id)).first()

        total_income = result.total_income or Decimal("0")
        total_expense = result.total_expense or Decimal("0")
        return {
            "total_income": total_income,
            "total_expense": total_expense,
            "net_balance": total_income - total_expense,
            "record_count": result.record_count or 0,
        }

    def get_category_breakdown(self, user_id: Optional[int] = None) -> dict:
        results = (
            self.db.query(
                FinancialRecord.type, FinancialRecord.category,
                func.sum(FinancialRecord.amount).label("total"),
                func.count(FinancialRecord.id).label("count"),
            )
            .filter(*self._base_filter(user_id))
            .group_by(FinancialRecord.type, FinancialRecord.category)
            .order_by(func.sum(FinancialRecord.amount).desc())
            .all()
        )

        income_items, expense_items = [], []
        income_total, expense_total = Decimal("0"), Decimal("0")

        for row in results:
            if row.type == RecordType.INCOME:
                income_total += row.total
                income_items.append(row)
            else:
                expense_total += row.total
                expense_items.append(row)

        def build(items, grand_total):
            return [{
                "category": i.category, "total": i.total, "count": i.count,
                "percentage": round(float(i.total / grand_total * 100), 2) if grand_total > 0 else 0.0,
            } for i in items]

        return {"income": build(income_items, income_total), "expense": build(expense_items, expense_total)}

    def get_trends(self, user_id: Optional[int] = None) -> List[dict]:
        results = (
            self.db.query(
                func.to_char(FinancialRecord.date, "YYYY-MM").label("period"),
                func.coalesce(func.sum(case(
                    (FinancialRecord.type == RecordType.INCOME, FinancialRecord.amount), else_=Decimal("0")
                )), Decimal("0")).label("income"),
                func.coalesce(func.sum(case(
                    (FinancialRecord.type == RecordType.EXPENSE, FinancialRecord.amount), else_=Decimal("0")
                )), Decimal("0")).label("expense"),
            )
            .filter(*self._base_filter(user_id))
            .group_by(func.to_char(FinancialRecord.date, "YYYY-MM"))
            .order_by(func.to_char(FinancialRecord.date, "YYYY-MM").asc())
            .all()
        )
        return [{"period": r.period, "income": r.income, "expense": r.expense, "net": r.income - r.expense} for r in results]

    def get_recent_records(self, user_id: Optional[int] = None, page: int = 1, limit: int = 10) -> Tuple[List[FinancialRecord], int]:
        query = self._base_query(user_id).order_by(FinancialRecord.date.desc())
        total = query.count()
        records = query.offset((page - 1) * limit).limit(limit).all()
        return records, total

    def get_top_spending_category(self, user_id: Optional[int] = None) -> Optional[dict]:
        filters = self._base_filter(user_id) + [FinancialRecord.type == RecordType.EXPENSE]
        result = (
            self.db.query(FinancialRecord.category, func.sum(FinancialRecord.amount).label("total"))
            .filter(*filters)
            .group_by(FinancialRecord.category)
            .order_by(func.sum(FinancialRecord.amount).desc())
            .first()
        )
        return {"category": result.category, "total": result.total} if result else None

    def get_monthly_growth(self, user_id: Optional[int] = None) -> Optional[float]:
        results = (
            self.db.query(
                func.to_char(FinancialRecord.date, "YYYY-MM").label("period"),
                func.coalesce(func.sum(case(
                    (FinancialRecord.type == RecordType.INCOME, FinancialRecord.amount), else_=Decimal("0")
                )), Decimal("0")).label("income"),
                func.coalesce(func.sum(case(
                    (FinancialRecord.type == RecordType.EXPENSE, FinancialRecord.amount), else_=Decimal("0")
                )), Decimal("0")).label("expense"),
            )
            .filter(*self._base_filter(user_id))
            .group_by(func.to_char(FinancialRecord.date, "YYYY-MM"))
            .order_by(func.to_char(FinancialRecord.date, "YYYY-MM").desc())
            .limit(2)
            .all()
        )
        if len(results) < 2:
            return None

        current_net = results[0].income - results[0].expense
        previous_net = results[1].income - results[1].expense
        if previous_net == 0:
            return None
        return round(float((current_net - previous_net) / abs(previous_net) * 100), 2)

    def get_average_daily_expense(self, user_id: Optional[int] = None) -> Optional[Decimal]:
        filters = self._base_filter(user_id) + [FinancialRecord.type == RecordType.EXPENSE]
        result = (
            self.db.query(
                func.sum(FinancialRecord.amount).label("total_expense"),
                func.count(func.distinct(FinancialRecord.date)).label("distinct_days"),
            )
            .filter(*filters)
            .first()
        )
        if result and result.distinct_days and result.distinct_days > 0:
            return round(result.total_expense / result.distinct_days, 2)
        return None

    def get_spending_spike(self, user_id: Optional[int] = None) -> Optional[dict]:
        filters = self._base_filter(user_id) + [FinancialRecord.type == RecordType.EXPENSE]
        result = (
            self.db.query(FinancialRecord.date, func.sum(FinancialRecord.amount).label("total"))
            .filter(*filters)
            .group_by(FinancialRecord.date)
            .order_by(func.sum(FinancialRecord.amount).desc())
            .first()
        )
        return {"date": result.date, "total": result.total} if result else None
