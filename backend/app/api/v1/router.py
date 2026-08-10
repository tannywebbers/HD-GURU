from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    ads,
    ads_admin,
    analytics_admin,
    auth,
    health,
    settings,
    uploads,
    whatsapp,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(health.router)
api_router.include_router(uploads.router)
api_router.include_router(settings.router)
api_router.include_router(whatsapp.router)
api_router.include_router(whatsapp.public_router)
api_router.include_router(ads.router)
api_router.include_router(ads.analytics_router)
api_router.include_router(admin.router)
api_router.include_router(ads_admin.router)
api_router.include_router(analytics_admin.router)
