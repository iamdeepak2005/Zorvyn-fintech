import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.common import ApiResponse
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", summary="User Login", response_model=ApiResponse[TokenResponse], status_code=status.HTTP_200_OK)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticates a user and generates a JWT (JSON Web Token).
    
    Business Logic Flow:
    1. No route-level dependencies block this access (it is a fully public endpoint).
    2. Takes email and plain-text password from the HTTP JSON body payload.
    3. `AuthService.authenticate` natively fetches the user, verifies the bcrypt hash, 
       checks `is_active` status to prevent suspended logins, and generates the encrypted token payload.
       
    **Access Control:**
    - **Roles Allowed:** Public Access (Anyone)
    """
    auth_service = AuthService(db)
    try:
        token_data = auth_service.authenticate(request.email, request.password)
        return ApiResponse.ok(data=token_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "data": None, "error": {"code": "AUTHENTICATION_FAILED", "message": str(e)}},
        )
