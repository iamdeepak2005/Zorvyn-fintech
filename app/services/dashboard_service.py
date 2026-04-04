import logging
from typing import Optional, Tuple, List

from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.repositories.dashboard_repository import DashboardRepository
from app.schemas.record import RecordResponse

logger = logging.getLogger(__name__)


class DashboardService:
    def __init__(self, db: Session):
        self.db = db
        self.dashboard_repo = DashboardRepository(db)

    def _user_filter(self, user: User, view_scope: str = "own") -> Optional[int]:
        if user.role in [UserRole.ADMIN, UserRole.ANALYST] and view_scope == "all":
            return None
        return user.id

    def get_summary(self, user: User, view_scope: str = "own") -> dict:
        return self.dashboard_repo.get_summary(self._user_filter(user, view_scope))

    def get_category_breakdown(self, user: User, view_scope: str = "own") -> dict:
        return self.dashboard_repo.get_category_breakdown(self._user_filter(user, view_scope))

    def get_trends(self, user: User, view_scope: str = "own") -> dict:
        trends = self.dashboard_repo.get_trends(self._user_filter(user, view_scope))
        return {"trends": trends, "granularity": "monthly"}

    def get_recent(self, user: User, page: int = 1, limit: int = 10, view_scope: str = "own") -> Tuple[List[dict], int]:
        records, total = self.dashboard_repo.get_recent_records(self._user_filter(user, view_scope), page, limit)
        return [RecordResponse.model_validate(r).model_dump(mode="json") for r in records], total

    def get_insights(self, user: User, view_scope: str = "own") -> dict:
        uid = self._user_filter(user, view_scope)

        top_category = self.dashboard_repo.get_top_spending_category(uid)
        monthly_growth = self.dashboard_repo.get_monthly_growth(uid)
        avg_daily_expense = self.dashboard_repo.get_average_daily_expense(uid)
        spending_spike = self.dashboard_repo.get_spending_spike(uid)

        return {
            "top_spending_category": top_category["category"] if top_category else None,
            "top_spending_amount": top_category["total"] if top_category else None,
            "monthly_growth_percentage": monthly_growth,
            "average_daily_expense": avg_daily_expense,
            "spending_spike_date": spending_spike["date"] if spending_spike else None,
            "spending_spike_amount": spending_spike["total"] if spending_spike else None,
        }
