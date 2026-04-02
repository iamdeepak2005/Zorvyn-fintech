import logging
import math

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_viewer_or_admin_or_analyst
from app.models.user import User
from app.schemas.common import ApiResponse, PaginatedData
from app.schemas.dashboard import CategoryBreakdownResponse, DashboardSummary, InsightsResponse, TrendsResponse
from app.schemas.record import RecordResponse
from app.services.dashboard_service import DashboardService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["Dashboard Analytics"])


@router.get("/summary", summary="Financial Summary", response_model=ApiResponse[DashboardSummary])
async def get_summary(db: Session = Depends(get_db), user: User = Depends(get_viewer_or_admin_or_analyst)):
    """
    Returns the absolute total income, absolute total expense, and Net Balance calculation.
    Offloaded deeply to PostgreSQL via `DashboardRepository.get_summary()`.
    """
    return ApiResponse.ok(data=DashboardService(db).get_summary(user))


@router.get("/category-breakdown", summary="Category Breakdown", response_model=ApiResponse[CategoryBreakdownResponse])
async def get_category_breakdown(db: Session = Depends(get_db), user: User = Depends(get_viewer_or_admin_or_analyst)):
    """
    Categorizes financial records strictly by Income and Expense branches.
    Provides mathematically verified percentage ratios directly from the SQL engine.
    """
    return ApiResponse.ok(data=DashboardService(db).get_category_breakdown(user))


@router.get("/trends", summary="Monthly Trends", response_model=ApiResponse[TrendsResponse])
async def get_trends(db: Session = Depends(get_db), user: User = Depends(get_viewer_or_admin_or_analyst)):
    return ApiResponse.ok(data=DashboardService(db).get_trends(user))


@router.get("/recent", summary="Recent Records", response_model=ApiResponse[PaginatedData[RecordResponse]])
async def get_recent(page: int = Query(1, ge=1), limit: int = Query(10, ge=1, le=100),
                     db: Session = Depends(get_db), user: User = Depends(get_viewer_or_admin_or_analyst)):
    records, total = DashboardService(db).get_recent(user, page, limit)
    return ApiResponse.ok(data=PaginatedData(
        items=records, total=total, page=page, limit=limit,
        total_pages=math.ceil(total / limit) if total > 0 else 0,
    ))


@router.get("/insights", summary="Financial Insights", response_model=ApiResponse[InsightsResponse])
async def get_insights(db: Session = Depends(get_db), user: User = Depends(get_viewer_or_admin_or_analyst)):
    """
    Connects multiple disparate queries strictly at the Database Repository layer to avoid
    memory overflow in Python:
    - Finds highest expense group.
    - Calculates moving month-over-month growth.
    - Detects anomalous single-day spending spikes mathematically.
    """
    return ApiResponse.ok(data=DashboardService(db).get_insights(user))
