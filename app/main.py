from fastapi import FastAPI

from app.routes.v1 import v1_router

app = FastAPI(
    title="Laaride Server", description="A scalable transport infrastructure for Ladakh"
)


app.include_router(v1_router)
