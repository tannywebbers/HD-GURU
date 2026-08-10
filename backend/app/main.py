from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1.router import api_router
from app.core.bootstrap import run_startup_seeds
from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging import log, setup_logging
from app.core.rate_limit import get_rate_limiter
from app.core.redis import close_redis
from app.middleware.csrf import CSRFProtectionMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_context import RequestContextMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.services import system_log_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(debug=settings.DEBUG)
    log.info("starting", app=settings.APP_NAME, version=settings.APP_VERSION)
    _warn_insecure_production_defaults()
    run_startup_seeds()
    yield
    close_redis()


def _warn_insecure_production_defaults() -> None:
    """Warn (do not block) when a production deployment uses insecure defaults.

    CORS ``*`` combined with ``ALLOWED_HOSTS=*`` disables origin/host pinning,
    the trusted-host filter and the CSRF origin check. Deployments should set
    ``CORS_ORIGINS`` to the exact frontend origin and pin ``ALLOWED_HOSTS`` to
    the backend hostname.
    """
    if settings.ENVIRONMENT.lower() != "production":
        return
    if "*" in settings.cors_origin_list:
        log.warning(
            "production_cors_wildcard",
            message=(
                "CORS_ORIGINS contains '*' in a production environment. "
                "Set CORS_ORIGINS to the exact frontend origin(s) (e.g. "
                "https://hdguru.vercel.app)."
            ),
        )
    if "*" in settings.allowed_hosts_list:
        log.warning(
            "production_hosts_wildcard",
            message=(
                "ALLOWED_HOSTS contains '*' in a production environment. "
                "Pin it to the backend hostname(s) (e.g. hd-guru-api.onrender.com)."
            ),
        )


def _error_body(
    exc: AppError,
    *,
    include_details: bool = True,
) -> dict:
    error: dict = {"code": exc.error_code, "message": exc.message}
    if include_details and exc.details is not None:
        error["details"] = exc.details
    return {"success": False, "error": error}


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "HD Guru backend API. Handles authentication, uploads, "
            "settings, and job orchestration.\n\n"
            "## Error format\n\n"
            "All errors are returned as:\n"
            "```json\n"
            "{\"success\": false, \"error\": {\"code\": \"...\", \"message\": \"...\"}}\n"
            "```\n"
            "## Auth\n\n"
            "Authenticate via `POST /api/v1/auth/login`, then send "
            "`Authorization: Bearer <token>` on protected endpoints."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    origins = settings.cors_origin_list
    allow_credentials = "*" not in origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts_list
    )
    app.add_middleware(CSRFProtectionMiddleware)
    app.add_middleware(RateLimitMiddleware, limiter=get_rate_limiter())
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestContextMiddleware)

    # --- exception handlers ------------------------------------------------
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        log.warning(
            "app_error",
            status_code=exc.status_code,
            error_code=exc.error_code,
            message=exc.message,
        )
        return JSONResponse(status_code=exc.status_code, content=_error_body(exc))

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        errors = [
            {
                "loc": list(e.get("loc", [])),
                "message": e.get("msg", "Invalid value"),
                "type": e.get("type", "value_error"),
            }
            for e in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed.",
                    "details": errors,
                },
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": "HTTP_ERROR",
                    "message": str(exc.detail),
                },
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        log.exception("unhandled_exception", error=str(exc))
        system_log_service.record_error(
            message="unhandled application exception",
            logger_name="app",
            context={"error": str(exc)},
        )
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred.",
                },
            },
        )

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/", include_in_schema=False)
    async def root():
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs",
            "openapi": "/openapi.json",
        }

    return app


app = create_app()
