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
async def get_summary(view_scope: str = Query("own", regex="^(own|all)$"), db: Session = Depends(get_db), user: User = Depends(get_viewer_or_admin_or_analyst)):
    """
    Returns the absolute total income, absolute total expense, and Net Balance calculation.
    Offloaded deeply to PostgreSQL via `DashboardRepository.get_summary()`.
    
    **Access Control:**
    - **Roles Allowed:** ADMIN, ANALYST, VIEWER
    - **Data Scope:** 
      - Viewers: Own Records Only.
      - Analysts/Admins: Can query their own dashboard (`?view_scope=own`) or the global dashboard (`?view_scope=all`).
    """
    return ApiResponse.ok(data=DashboardService(db).get_summary(user, view_scope))


@router.get("/category-breakdown", summary="Category Breakdown", response_model=ApiResponse[CategoryBreakdownResponse])
async def get_category_breakdown(view_scope: str = Query("own", regex="^(own|all)$"), db: Session = Depends(get_db), user: User = Depends(get_viewer_or_admin_or_analyst)):
    """
    Categorizes financial records strictly by Income and Expense branches.
    Provides mathematically verified percentage ratios directly from the SQL engine.
    
    **Access Control:**
    - **Roles Allowed:** ADMIN, ANALYST, VIEWER
    - **Data Scope:** 
      - Viewers: Own Records Only.
      - Analysts/Admins: Can query their own dashboard (`?view_scope=own`) or the global dashboard (`?view_scope=all`).
    """
    return ApiResponse.ok(data=DashboardService(db).get_category_breakdown(user, view_scope))


@router.get("/trends", summary="Monthly Trends", response_model=ApiResponse[TrendsResponse])
async def get_trends(view_scope: str = Query("own", regex="^(own|all)$"), db: Session = Depends(get_db), user: User = Depends(get_viewer_or_admin_or_analyst)):
    """
    Returns monthly trends for income and expenses.
    
    **Access Control:**
    - **Roles Allowed:** ADMIN, ANALYST, VIEWER
    - **Data Scope:** 
      - Viewers: Own Records Only.
      - Analysts/Admins: Can query their own dashboard (`?view_scope=own`) or the global dashboard (`?view_scope=all`).
    """
    return ApiResponse.ok(data=DashboardService(db).get_trends(user, view_scope))


@router.get("/recent", summary="Recent Records", response_model=ApiResponse[PaginatedData[RecordResponse]])
async def get_recent(view_scope: str = Query("own", regex="^(own|all)$"), page: int = Query(1, ge=1), limit: int = Query(10, ge=1, le=100),
                     db: Session = Depends(get_db), user: User = Depends(get_viewer_or_admin_or_analyst)):
    """
    Retrieves recent financial records.
    
    **Access Control:**
    - **Roles Allowed:** ADMIN, ANALYST, VIEWER
    - **Data Scope:** 
      - Viewers: Own Records Only.
      - Analysts/Admins: Can query their own dashboard (`?view_scope=own`) or the global dashboard (`?view_scope=all`).
    """
    records, total = DashboardService(db).get_recent(user, page, limit, view_scope)
    return ApiResponse.ok(data=PaginatedData(
        items=records, total=total, page=page, limit=limit,
        total_pages=math.ceil(total / limit) if total > 0 else 0,
    ))


@router.get("/insights", summary="Financial Insights", response_model=ApiResponse[InsightsResponse])
async def get_insights(view_scope: str = Query("own", regex="^(own|all)$"), db: Session = Depends(get_db), user: User = Depends(get_viewer_or_admin_or_analyst)):
    """
    Connects multiple disparate queries strictly at the Database Repository layer to avoid
    memory overflow in Python:
    - Finds highest expense group.
    - Calculates moving month-over-month growth.
    - Detects anomalous single-day spending spikes mathematically.
    
    **Access Control:**
    - **Roles Allowed:** ADMIN, ANALYST, VIEWER
    - **Data Scope:** 
      - Viewers: Own Records Only.
      - Analysts/Admins: Can query their own dashboard (`?view_scope=own`) or the global dashboard (`?view_scope=all`).
    """
    return ApiResponse.ok(data=DashboardService(db).get_insights(user, view_scope))
