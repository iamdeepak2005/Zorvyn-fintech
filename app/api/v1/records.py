"""
API endpoints for managing Financial Records.
Handles routing for CRUD operations and CSV exports, while enforcing user authentication dependencies.
"""
import logging
import math
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_admin_user, get_analyst_or_admin, get_any_authenticated_user
from app.models.financial_record import RecordType
from app.models.user import User
from app.schemas.common import ApiResponse, PaginatedData
from app.schemas.record import RecordCreate, RecordFilterParams, RecordResponse, RecordUpdate
from app.services.record_service import RecordService
from app.utils.excel_export import generate_excel_bytes

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/records", tags=["Financial Records"])


@router.post("", summary="Create Financial Record", response_model=ApiResponse[RecordResponse], status_code=status.HTTP_201_CREATED)
# Enforce ADMIN only through FastAPI Dependency Injection
async def create_record(data: RecordCreate, db: Session = Depends(get_db), user: User = Depends(get_admin_user),
                        idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")):
    """
    Creates a new financial record (Income/Expense).
    
    Business Logic Flow:
    1. Authorization is enforced blindly at the router level via `Depends(get_admin_user)`.
    2. The `RecordCreate` Pydantic model strictly validates numeric bounds and field lengths.
    3. The payload is passed to the `RecordService` which handles exactly two business layers:
       - Idempotency checks (preventing double-biling/duplicate submissions).
       - Database entry creation & Audit Logging (wrapped in a transaction).
    """
    record_service = RecordService(db)
    try:
        record_data, is_idempotent = record_service.create_record(data, user, idempotency_key)
        msg = "Idempotency hit: Returning cached response" if is_idempotent else "Record created successfully"
        return ApiResponse.ok(data=record_data, message=msg)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "data": None, "error": {"code": "CREATION_FAILED", "message": str(e)}},
        )


@router.get("", summary="List Financial Records", response_model=ApiResponse[PaginatedData[RecordResponse]])
async def list_records(
    type: Optional[RecordType] = Query(None), category: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None), end_date: Optional[date] = Query(None),
    search: Optional[str] = Query(None), page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100), sort_by: Optional[str] = Query("date", regex="^(date|amount|created_at)$"),
    order: Optional[str] = Query("desc", regex="^(asc|desc)$"),
    include_deleted: bool = Query(False),
    db: Session = Depends(get_db), user: User = Depends(get_analyst_or_admin),
):
    """
    Fetches a paginated, filtered list of financial records.
    
    Business Logic Flow:
    1. Dependencies evaluate if the user is an ANALYST or ADMIN.
    2. Input query parameters are aggressively checked and assembled into `RecordFilterParams`.
    3. `RecordService` takes over and injects a "User ID Filter" context natively based on role 
       (limiting Analysts to their own scope but freeing Admins).
    """
    filters = RecordFilterParams(
        type=type, category=category, start_date=start_date, end_date=end_date,
        search=search, page=page, limit=limit, sort_by=sort_by, order=order, include_deleted=include_deleted,
    )
    record_service = RecordService(db)
    records, total = record_service.get_records(filters, user)
    return ApiResponse.ok(data=PaginatedData(
        items=records, total=total, page=page, limit=limit,
        total_pages=math.ceil(total / limit) if total > 0 else 0,
    ))


@router.get("/export", summary="Export Records as Excel", responses={200: {"content": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {}}}})
async def export_records(
    type: Optional[RecordType] = Query(None), category: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None), end_date: Optional[date] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db), user: User = Depends(get_analyst_or_admin),
):
    """
    Compiles raw data into a fully formatted Excel file using openpyxl.
    
    Business Logic Flow:
    1. Instead of loading thousands of DB records into memory, `get_export_records` 
       returns an unexecuted SQL generator (yield yield_per).
    2. `generate_excel_bytes` iteratively consumes the generator while applying 
       visual formatting (green/red typography based on values) to memory buffer.
    """
    record_service = RecordService(db)
    records_gen = record_service.get_export_records(
        user=user, record_type=type, category=category, start_date=start_date, end_date=end_date, search=search,
    )
    excel_bytes = generate_excel_bytes(records_gen)
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=financial_records.xlsx"},
    )


@router.get("/{record_id}", summary="Get Financial Record", response_model=ApiResponse[RecordResponse])
async def get_record(record_id: int, db: Session = Depends(get_db), user: User = Depends(get_analyst_or_admin)):
    record_service = RecordService(db)
    try:
        record = record_service.get_record_by_id(record_id, user)
        return ApiResponse.ok(data=record)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail={"success": False, "data": None, "error": {"code": "NOT_FOUND", "message": str(e)}})
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail={"success": False, "data": None, "error": {"code": "FORBIDDEN", "message": str(e)}})


@router.patch("/{record_id}", summary="Update Financial Record", response_model=ApiResponse[RecordResponse])
# Access locked to ADMIN using dependency injection
async def update_record(record_id: int, data: RecordUpdate, db: Session = Depends(get_db), user: User = Depends(get_admin_user)):
    record_service = RecordService(db)
    try:
        record = record_service.update_record(record_id, data, user)
        return ApiResponse.ok(data=record)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail={"success": False, "data": None, "error": {"code": "NOT_FOUND", "message": str(e)}})
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail={"success": False, "data": None, "error": {"code": "FORBIDDEN", "message": str(e)}})


@router.delete("/{record_id}", summary="Delete Financial Record (Soft)", response_model=ApiResponse)
# Access locked to ADMIN using dependency injection
async def delete_record(record_id: int, db: Session = Depends(get_db), user: User = Depends(get_admin_user)):
    record_service = RecordService(db)
    try:
        record_service.delete_record(record_id, user)
        return ApiResponse.ok(data={"message": f"Record {record_id} deleted successfully"})
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail={"success": False, "data": None, "error": {"code": "NOT_FOUND", "message": str(e)}})
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail={"success": False, "data": None, "error": {"code": "FORBIDDEN", "message": str(e)}})
