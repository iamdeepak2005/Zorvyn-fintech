import logging
import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_admin_user
from app.models.user import User
from app.schemas.common import ApiResponse, PaginatedData
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.user_service import UserService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin - User Management"])


@router.post("/users", summary="Create User", response_model=ApiResponse[UserResponse], status_code=status.HTTP_201_CREATED)
async def create_user(data: UserCreate, db: Session = Depends(get_db), admin: User = Depends(get_admin_user)):
    """
    Provisions a new user physically on the platform.
    
    Business Logic Flow:
    1. `Depends(get_admin_user)` entirely blocks off any request not carrying an ADMIN token.
    2. Request data is structurally checked against the `UserCreate` Pydantic model (ensuring valid emails & strong passwords).
    3. `UserService.create_user` hashes the password securely using bcrypt, creates the database record,
       and instantly maps an explicit Audit Log ensuring Admins are held accountable for creation.
       
    **Access Control:**
    - **Roles Allowed:** ADMIN only.
    """
    user_service = UserService(db)
    try:
        user = user_service.create_user(data, admin.id)
        return ApiResponse.ok(data=UserResponse.model_validate(user))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"success": False, "data": None, "error": {"code": "DUPLICATE_EMAIL", "message": str(e)}},
        )


@router.get("/users", summary="List Users", response_model=ApiResponse[PaginatedData[UserResponse]])
async def list_users(page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100),
                     db: Session = Depends(get_db), admin: User = Depends(get_admin_user)):
    """
    Retrieves a paginated chunk of all registered platform users.
    Only strictly acceptable for execution by the ADMIN tier.
    
    **Access Control:**
    - **Roles Allowed:** ADMIN only.
    """
    user_service = UserService(db)
    users, total = user_service.get_users(page, limit)
    return ApiResponse.ok(data=PaginatedData(
        items=[UserResponse.model_validate(u) for u in users],
        total=total, page=page, limit=limit,
        total_pages=math.ceil(total / limit) if total > 0 else 0,
    ))


@router.patch("/users/{user_id}", summary="Update User", response_model=ApiResponse[UserResponse])
async def update_user(user_id: int, data: UserUpdate, db: Session = Depends(get_db), admin: User = Depends(get_admin_user)):
    """
    Updates user specific columns (like 'is_active') via partial patching.
    Leaves an Audit Log trace reflecting the exact action.
    
    **Access Control:**
    - **Roles Allowed:** ADMIN only.
    """
    user_service = UserService(db)
    try:
        user = user_service.update_user(user_id, data, admin.id)
        return ApiResponse.ok(data=UserResponse.model_validate(user))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "data": None, "error": {"code": "NOT_FOUND", "message": str(e)}},
        )


@router.delete("/users/{user_id}", summary="Delete User", response_model=ApiResponse, status_code=status.HTTP_200_OK)
async def delete_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(get_admin_user)):
    """
    Fully restricts the system from allowing an admin to delete themselves.
    Performs physical removal unless a foreign key restrict (like linked financial records) blocks it.
    
    **Access Control:**
    - **Roles Allowed:** ADMIN only.
    """
    user_service = UserService(db)
    try:
        user_service.delete_user(user_id, admin.id)
        return ApiResponse.ok(data={"message": f"User {user_id} deleted successfully"})
    except ValueError as e:
        code = status.HTTP_400_BAD_REQUEST if "own account" in str(e) else status.HTTP_404_NOT_FOUND
        raise HTTPException(
            status_code=code,
            detail={"success": False, "data": None, "error": {"code": "DELETE_FAILED", "message": str(e)}},
        )
