from fastapi import APIRouter
from app.api.v1 import cities, dashboard, history, observations, trends

api_router = APIRouter()

api_router.include_router(cities.router)
api_router.include_router(observations.router)
api_router.include_router(history.router)
api_router.include_router(dashboard.router)
api_router.include_router(trends.router)
