from fastapi import APIRouter

router = APIRouter(tags=["System"])


@router.get("/", summary="Service info")
async def info():
    return {
        "service": "LaaRide API",
        "version": "0.1.0",
        "status": "running",
    }


@router.get("/health", summary="Health check")
async def health():
    return {"status": "ok"}
