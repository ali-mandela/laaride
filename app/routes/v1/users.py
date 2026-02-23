from fastapi import APIRouter

router = APIRouter(tags=["Users"])


@router.get("/", summary="Get all users")
async def get_users():
    return []


@router.get("/{user_id}", summary="Get a user by ID")
async def get_user(user_id: int):
    return {}


@router.post("/", summary="Create a new user")
async def create_user():
    return {}


@router.put("/{user_id}", summary="Update a user")
async def update_user(user_id: int):
    return {}
