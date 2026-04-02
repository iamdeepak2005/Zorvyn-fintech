from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Health Check", response_model=dict)
async def health_check():
    return {"status": "ok"}
