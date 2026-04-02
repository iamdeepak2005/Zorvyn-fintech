from datetime import date
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel

from app.schemas.record import RecordResponse


class DashboardSummary(BaseModel):
    total_income: Decimal
    total_expense: Decimal
    net_balance: Decimal
    record_count: int


class CategoryBreakdown(BaseModel):
    category: str
    total: Decimal
    count: int
    percentage: float


class CategoryBreakdownResponse(BaseModel):
    income: List[CategoryBreakdown]
    expense: List[CategoryBreakdown]


class TrendPoint(BaseModel):
    period: str
    income: Decimal
    expense: Decimal
    net: Decimal


class TrendsResponse(BaseModel):
    trends: List[TrendPoint]
    granularity: str


class InsightsResponse(BaseModel):
    top_spending_category: Optional[str] = None
    top_spending_amount: Optional[Decimal] = None
    monthly_growth_percentage: Optional[float] = None
    average_daily_expense: Optional[Decimal] = None
    spending_spike_date: Optional[date] = None
    spending_spike_amount: Optional[Decimal] = None
