from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Health Check", response_model=dict)
async def health_check():
    """
    Returns the health status of the application.
    
    **Access Control:**
    - **Roles Allowed:** Public Access (Anyone)
    """
    return {"status": "ok"}
