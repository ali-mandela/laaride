"""Route endpoints — public read + admin CRUD for fixed intercity routes."""

from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.core.database import get_database
from app.core.security import get_current_active_user, get_current_admin
from app.models.user import UserDocument
from app.schemas.route import RouteCreate, RouteResponse, RouteSearchParams, RouteUpdate
from app.services import route_service

router = APIRouter(tags=["Routes"])


# ── Public (any authenticated user) ────────────────────────────────────────


@router.get("/popular", summary="Get popular routes")
async def get_popular_routes(
    limit: int = Query(default=5, ge=1, le=20),
    _user: UserDocument = Depends(get_current_active_user),
    db: Any = Depends(get_database),
):
    """Return routes ordered by booking popularity (fallback: most recent)."""
    return await route_service.get_popular_routes(limit, db)


@router.get("/slug/{slug}", response_model=RouteResponse, summary="Get route by slug")
async def get_route_by_slug(
    slug: str,
    _user: UserDocument = Depends(get_current_active_user),
    db: Any = Depends(get_database),
):
    """Retrieve a route by its URL-friendly slug (e.g. leh-kargil)."""
    return await route_service.get_route_by_slug(slug, db)


@router.get("/", summary="List routes (search & filter)")
async def list_routes(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    origin_name: Optional[str] = Query(default=None),
    destination_name: Optional[str] = Query(default=None),
    max_fare: Optional[float] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    tag: Optional[str] = Query(default=None),
    _user: UserDocument = Depends(get_current_active_user),
    db: Any = Depends(get_database),
):
    """List routes with optional search/filters. Non-admins only see active routes."""
    params = RouteSearchParams(
        origin_name=origin_name,
        destination_name=destination_name,
        max_fare=max_fare,
        is_active=is_active,
        tag=tag,
    )
    is_admin = _user.role.value == "admin"
    return await route_service.list_routes(params, skip, limit, db, admin=is_admin)


@router.get("/{route_id}", response_model=RouteResponse, summary="Get route by ID")
async def get_route(
    route_id: str,
    _user: UserDocument = Depends(get_current_active_user),
    db: Any = Depends(get_database),
):
    """Retrieve a route by its document ID."""
    return await route_service.get_route_by_id(route_id, db)


# ── Admin only ─────────────────────────────────────────────────────────────


@router.post(
    "/",
    response_model=RouteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a route (admin)",
)
async def create_route(
    data: RouteCreate,
    _admin: UserDocument = Depends(get_current_admin),
    db: Any = Depends(get_database),
):
    """Admin: create a new fixed intercity route."""
    return await route_service.create_route(data, db)


@router.put(
    "/{route_id}",
    response_model=RouteResponse,
    summary="Update a route (admin)",
)
async def update_route(
    route_id: str,
    data: RouteUpdate,
    _admin: UserDocument = Depends(get_current_admin),
    db: Any = Depends(get_database),
):
    """Admin: partially update a route."""
    return await route_service.update_route(route_id, data, db)


@router.delete("/{route_id}", summary="Delete/deactivate a route (admin)")
async def delete_route(
    route_id: str,
    _admin: UserDocument = Depends(get_current_admin),
    db: Any = Depends(get_database),
):
    """Admin: soft-delete (deactivate) or hard-delete a route depending on bookings."""
    return await route_service.delete_route(route_id, db)


@router.post(
    "/{route_id}/thumbnail",
    response_model=RouteResponse,
    summary="Upload route thumbnail (admin)",
)
async def upload_thumbnail(
    route_id: str,
    file: UploadFile = File(...),
    _admin: UserDocument = Depends(get_current_admin),
    db: Any = Depends(get_database),
):
    """Admin: upload a thumbnail image for a route (jpg, png, webp — max 3MB)."""
    return await route_service.upload_route_thumbnail(route_id, file, db)


@router.post("/seed", summary="Seed default routes (admin)")
async def seed_routes(
    _admin: UserDocument = Depends(get_current_admin),
    db: Any = Depends(get_database),
):
    """Admin: seed default Ladakh/Himachal routes. Idempotent — skips existing."""
    return await route_service.seed_default_routes(db)
