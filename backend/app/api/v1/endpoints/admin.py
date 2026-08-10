from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Body, Depends, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.api.responses import standard_responses
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import AppError
from app.core.permissions import role_permissions
from app.core.security import revoke_all_user_tokens
from app.models.api_key import ApiKey
from app.models.audit_log import AuditLog
from app.models.enums import (
    JobStatus,
    MediaStatus,
    Permission,
    UploadStatus,
    UserRole,
    WhatsAppMessageDirection,
    WhatsAppMessageStatus,
)
from app.models.job import Job
from app.models.login_history import LoginHistory
from app.models.media_file import MediaFile
from app.models.processed_media import ProcessedMedia
from app.models.setting import Setting
from app.models.system_log import SystemLog
from app.models.upload import Upload
from app.models.user import User
from app.models.watermark import Watermark
from app.models.whatsapp import (
    WhatsappContact,
    WhatsappMessage,
    WhatsappMessageStatus,
    WhatsappWebhookEvent,
)
from app.models.worker import Worker
from app.schemas.admin import (
    AdminApiKeyItem,
    AdminAuditItem,
    AdminAuditPage,
    AdminHealthResponse,
    AdminJobItem,
    AdminJobPage,
    AdminLoginHistoryItem,
    AdminLoginHistoryPage,
    AdminLogItem,
    AdminLogPage,
    AdminMediaItem,
    AdminMediaPage,
    AdminMe,
    AdminSettingsOut,
    AdminSettingItem,
    AdminUserItem,
    AdminUserPage,
    AdminWhatsappContactItem,
    AdminWhatsappContactPage,
    AdminWhatsappEventItem,
    AdminWhatsappEventPage,
    AdminWhatsappMessageItem,
    AdminWhatsappMessagePage,
    AdminWhatsappStats,
    DashboardResponse,
    JobRetryResult,
    SecurityOverview,
    StorageResponse,
    UserCreateRequest,
    UserUpdateRequest,
    WatermarkIn,
    WatermarkOut,
    WatermarkUpdate,
)
from app.schemas.settings import SettingsItemUpdate
from app.schemas.whatsapp import WhatsAppConfigUpdate
from app.services import audit_service, health_service, upload_service
from app.services.whatsapp import config as whatsapp_config
from app.services.whatsapp import service as whatsapp_service
from app.services.watermark_service import POSITIONS
from app.utils.pagination import Page, paginate
from app.workers.tasks import process_upload

router = APIRouter(prefix="/admin", tags=["Admin"])

_RETRYABLE_JOB_TYPES = ("uploads.process",)


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _mask_settings(settings_out) -> AdminSettingsOut:
    """Never send secrets to the dashboard; only a masked placeholder."""
    items = [
        AdminSettingItem(
            key=row.key,
            group=row.group,
            value="***" if row.is_secret else row.value,
            description=row.description,
            is_secret=row.is_secret,
            updated_at=row.updated_at,
        )
        for row in settings_out.settings
    ]
    return AdminSettingsOut(settings=items)


def _admin_log(
    db: Session,
    request: Request,
    actor: User,
    *,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    details: dict | None = None,
    result: str = "success",
) -> None:
    ip, user_agent = audit_service.client_meta(request)
    audit_service.log_action(
        db,
        action=action,
        actor=actor,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip,
        user_agent=user_agent,
        result=result,
    )


# --- admin context ---------------------------------------------------------


@router.get(
    "/me",
    response_model=AdminMe,
    summary="Current admin context (role + permissions)",
    description=(
        "Returns the authenticated admin's profile plus the effective "
        "permission list so the dashboard can adapt its UI."
    ),
    responses=standard_responses(),
)
def admin_me(
    current_user: User = Depends(require_admin()),
) -> AdminMe:
    return AdminMe(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role.value,
        permissions=role_permissions(current_user.role),
    )


# --- dashboard -------------------------------------------------------------


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    summary="Dashboard overview",
    description=(
        "Aggregated counters, recent activity, storage summary and a live "
        "health snapshot for the dashboard landing page."
    ),
    responses=standard_responses(),
)
def dashboard(
    current_user: User = Depends(require_admin(permission=Permission.DASHBOARD_VIEW)),
    db: Session = Depends(get_db),
) -> DashboardResponse:
    now = _now()
    day_start = now - dt.timedelta(hours=24)

    uploads_total = db.scalar(select(func.count()).select_from(Upload)) or 0
    uploads_today = (
        db.scalar(
            select(func.count())
            .select_from(Upload)
            .where(Upload.created_at >= day_start.replace(tzinfo=None))
        )
        or 0
    )
    media_total = db.scalar(select(func.count()).select_from(MediaFile)) or 0
    media_completed = (
        db.scalar(
            select(func.count())
            .select_from(MediaFile)
            .where(MediaFile.status == MediaStatus.COMPLETED)
        )
        or 0
    )
    downloads_total = db.scalar(select(func.sum(Upload.download_count))) or 0
    whatsapp_deliveries = (
        db.scalar(select(func.sum(Upload.whatsapp_delivery_count))) or 0
    )
    whatsapp_messages = (
        db.scalar(select(func.count()).select_from(WhatsappMessage)) or 0
    )
    whatsapp_contacts = (
        db.scalar(select(func.count()).select_from(WhatsappContact)) or 0
    )
    users_total = db.scalar(select(func.count()).select_from(User)) or 0

    jobs_by_status = dict(
        db.execute(
            select(Job.status, func.count()).group_by(Job.status)
        ).all()
    )
    error_logs_24h = (
        db.scalar(
            select(func.count())
            .select_from(SystemLog)
            .where(
                SystemLog.level == "ERROR",
                SystemLog.created_at >= day_start.replace(tzinfo=None),
            )
        )
        or 0
    )

    recent_uploads = db.scalars(
        select(Upload).order_by(Upload.created_at.desc()).limit(5)
    ).all()
    recent_jobs = db.scalars(
        select(Job).order_by(Job.created_at.desc()).limit(5)
    ).all()

    return DashboardResponse(
        counters={
            "uploads_total": uploads_total,
            "uploads_today": uploads_today,
            "media_total": media_total,
            "media_completed": media_completed,
            "downloads_total": downloads_total,
            "whatsapp_deliveries_total": whatsapp_deliveries,
            "whatsapp_messages_total": whatsapp_messages,
            "whatsapp_contacts_total": whatsapp_contacts,
            "users_total": users_total,
            "jobs_queued": jobs_by_status.get(JobStatus.QUEUED, 0),
            "jobs_running": jobs_by_status.get(JobStatus.RUNNING, 0),
            "jobs_failed": jobs_by_status.get(JobStatus.FAILED, 0)
            + jobs_by_status.get(JobStatus.DEAD, 0),
            "jobs_succeeded": jobs_by_status.get(JobStatus.SUCCEEDED, 0),
            "error_logs_24h": error_logs_24h,
        },
        recent_uploads=[_upload_summary(u) for u in recent_uploads],
        recent_jobs=[
            {
                "id": j.id,
                "job_type": j.job_type,
                "status": j.status.value,
                "upload_public_id": j.args.get("public_id") if j.args else None,
                "created_at": j.created_at,
                "finished_at": j.finished_at,
            }
            for j in recent_jobs
        ],
        storage=_storage_summary(db),
        system={
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "api_prefix": settings.API_V1_PREFIX,
        },
        health=health_service.health_payload(),
    )


def _upload_summary(upload: Upload) -> dict:
    return {
        "public_id": upload.public_id,
        "original_filename": upload.original_filename,
        "status": upload.status.value,
        "file_count": upload.file_count,
        "download_count": upload.download_count,
        "whatsapp_delivery_count": upload.whatsapp_delivery_count,
        "expires_at": upload.expires_at,
        "created_at": upload.created_at,
    }


# --- media -----------------------------------------------------------------


@router.get(
    "/media",
    response_model=AdminMediaPage,
    summary="List media files",
    description=(
        "Server-side paginated media table with optional status and search "
        "filters. Processed artifact metadata and counters are included."
    ),
    responses=standard_responses(),
)
def list_media(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    search: str | None = Query(None, max_length=64),
    current_user: User = Depends(require_admin(permission=Permission.MEDIA_VIEW)),
    db: Session = Depends(get_db),
) -> AdminMediaPage:
    stmt = select(MediaFile)
    if status:
        try:
            media_status = MediaStatus(status)
        except ValueError:
            raise AppError(400, "INVALID_STATUS", "Unknown media status.") from None
        stmt = stmt.where(MediaFile.status == media_status)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            or_(
                MediaFile.public_id.ilike(like),
                MediaFile.original_filename.ilike(like),
            )
        )
    stmt = stmt.order_by(MediaFile.created_at.desc())

    result: Page[MediaFile] = paginate(db, stmt, page=page, per_page=per_page)
    media_ids = [m.id for m in result.items]
    upload_map: dict[uuid.UUID, str] = {}
    processed_map: dict[uuid.UUID, dict] = {}
    if media_ids:
        upload_map = dict(
            db.execute(
                select(Upload.id, Upload.public_id).where(
                    Upload.id.in_(
                        select(MediaFile.upload_id)
                        .where(MediaFile.id.in_(media_ids))
                    )
                )
            ).all()
        )
        for row in db.execute(
            select(
                ProcessedMedia.media_file_id,
                ProcessedMedia.file_size,
                ProcessedMedia.width,
                ProcessedMedia.height,
                ProcessedMedia.duration,
                ProcessedMedia.completed_at,
                ProcessedMedia.watermark_ref,
            ).where(ProcessedMedia.media_file_id.in_(media_ids))
        ).all():
            processed_map[row.media_file_id] = {
                "file_size": row.file_size,
                "width": row.width,
                "height": row.height,
                "duration": row.duration,
                "completed_at": row.completed_at,
                "watermark_ref": row.watermark_ref,
            }

    items = [
        AdminMediaItem(
            id=m.id,
            public_id=m.public_id,
            seq=m.seq,
            original_filename=m.original_filename,
            mime_type=m.mime_type,
            extension=m.extension,
            file_size=m.file_size,
            width=m.width,
            height=m.height,
            duration=m.duration,
            storage_provider=m.storage_provider,
            status=m.status.value,
            error=m.error,
            download_count=m.download_count,
            whatsapp_delivery_count=m.whatsapp_delivery_count,
            created_at=m.created_at,
            updated_at=m.updated_at,
            upload_public_id=upload_map.get(m.upload_id),
            processed=processed_map.get(m.id),
        )
        for m in result.items
    ]
    return AdminMediaPage(
        items=items,
        total=result.total,
        page=result.page,
        per_page=result.per_page,
        pages=result.pages,
    )


@router.delete(
    "/media/{public_id}",
    status_code=204,
    summary="Delete a media file",
    description="Permanently deletes a media file, its processed artifacts and records.",
    responses=standard_responses(),
)
def delete_media(
    public_id: str,
    request: Request,
    current_user: User = Depends(require_admin(permission=Permission.MEDIA_DELETE)),
    db: Session = Depends(get_db),
):
    media = db.scalar(select(MediaFile).where(MediaFile.public_id == public_id))
    if media is None:
        raise AppError(404, "MEDIA_NOT_FOUND", "Media file not found.")
    ip, user_agent = audit_service.client_meta(request)
    upload_service.delete_media_file(
        db,
        media,
        actor=current_user,
        ip_address=ip,
        user_agent=user_agent,
    )
    _admin_log(
        db,
        request,
        current_user,
        action="admin.media_deleted",
        resource_type="media_file",
        resource_id=public_id,
        details={"public_id": public_id},
    )
    return None


# --- jobs ------------------------------------------------------------------


@router.get(
    "/jobs",
    response_model=AdminJobPage,
    summary="List processing jobs",
    description=(
        "Paginated job table. Stack traces are never included in responses."
    ),
    responses=standard_responses(),
)
def list_jobs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    job_type: str | None = Query(None),
    current_user: User = Depends(require_admin(permission=Permission.JOBS_VIEW)),
    db: Session = Depends(get_db),
) -> AdminJobPage:
    stmt = select(Job)
    if status:
        try:
            stmt = stmt.where(Job.status == JobStatus(status))
        except ValueError:
            raise AppError(400, "INVALID_STATUS", "Unknown job status.") from None
    if job_type:
        stmt = stmt.where(Job.job_type == job_type)
    stmt = stmt.order_by(Job.created_at.desc())
    result: Page[Job] = paginate(db, stmt, page=page, per_page=per_page)
    return AdminJobPage(
        items=[
            AdminJobItem(
                id=j.id,
                job_type=j.job_type,
                status=j.status.value,
                upload_id=j.upload_id,
                celery_task_id=j.celery_task_id,
                args=j.args or {},
                result=j.result,
                retries=j.retries,
                max_retries=j.max_retries,
                worker_id=j.worker_id,
                started_at=j.started_at,
                finished_at=j.finished_at,
                created_at=j.created_at,
                updated_at=j.updated_at,
            )
            for j in result.items
        ],
        total=result.total,
        page=result.page,
        per_page=result.per_page,
        pages=result.pages,
    )


@router.post(
    "/jobs/{job_id}/retry",
    response_model=JobRetryResult,
    summary="Retry a failed job",
    description=(
        "Re-enqueues a failed or dead processing job. The job is reset to "
        "queued and assigned a fresh Celery task id."
    ),
    responses=standard_responses(),
)
def retry_job(
    job_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_admin(permission=Permission.JOBS_RETRY)),
    db: Session = Depends(get_db),
) -> JobRetryResult:
    job = db.get(Job, job_id)
    if job is None:
        raise AppError(404, "JOB_NOT_FOUND", "Job not found.")
    if job.status not in (JobStatus.FAILED, JobStatus.DEAD):
        raise AppError(
            409, "JOB_NOT_RETRYABLE", "Only failed or dead jobs can be retried."
        )
    if job.job_type not in _RETRYABLE_JOB_TYPES:
        raise AppError(
            400, "JOB_NOT_RETRYABLE", "This job type cannot be retried manually."
        )
    public_id = (job.args or {}).get("public_id")
    if not public_id:
        raise AppError(400, "JOB_MISSING_ARGS", "The job is missing its payload.")

    try:
        result = process_upload.apply_async(
            args=[str(job.id), public_id], kwargs={}
        )
    except Exception as exc:  # broker/eager failures
        raise AppError(
            503, "QUEUE_UNAVAILABLE", "Could not enqueue the job right now."
        ) from exc

    job.status = JobStatus.QUEUED
    job.celery_task_id = getattr(result, "id", None)
    job.retries = 0
    job.started_at = None
    job.finished_at = None
    job.traceback = None
    upload = db.get(Upload, job.upload_id) if job.upload_id else None
    if upload is not None:
        upload.status = UploadStatus.QUEUED
    db.commit()

    _admin_log(
        db,
        request,
        current_user,
        action="admin.job_retried",
        resource_type="job",
        resource_id=str(job.id),
        details={"public_id": public_id, "job_type": job.job_type},
    )
    return JobRetryResult(
        job_id=job.id,
        status=job.status.value,
        celery_task_id=job.celery_task_id,
    )


# --- users -----------------------------------------------------------------


def _user_item(db: Session, user: User, uploads_count: int | None = None) -> AdminUserItem:
    if uploads_count is None:
        uploads_count = (
            db.scalar(
                select(func.count())
                .select_from(Upload)
                .where(Upload.user_id == user.id)
            )
            or 0
        )
    return AdminUserItem(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        is_active=user.is_active,
        email_verified=user.email_verified,
        last_login_at=user.last_login_at,
        failed_login_count=user.failed_login_count,
        is_locked=user.is_locked,
        locked_until=user.locked_until,
        must_change_password=user.must_change_password,
        token_version=user.token_version,
        created_at=user.created_at,
        updated_at=user.updated_at,
        uploads_count=uploads_count,
    )


@router.get(
    "/users",
    response_model=AdminUserPage,
    summary="List users",
    description="Paginated user table with role and status filters.",
    responses=standard_responses(),
)
def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    role: str | None = Query(None),
    active: bool | None = Query(None),
    search: str | None = Query(None, max_length=64),
    current_user: User = Depends(require_admin(permission=Permission.USERS_VIEW)),
    db: Session = Depends(get_db),
) -> AdminUserPage:
    stmt = select(User)
    if role:
        try:
            stmt = stmt.where(User.role == UserRole(role))
        except ValueError:
            raise AppError(400, "INVALID_ROLE", "Unknown user role.") from None
    if active is not None:
        stmt = stmt.where(User.is_active.is_(active))
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            or_(User.email.ilike(like), User.full_name.ilike(like))
        )
    stmt = stmt.order_by(User.created_at.desc())

    result: Page[User] = paginate(db, stmt, page=page, per_page=per_page)
    user_ids = [u.id for u in result.items]
    counts: dict[uuid.UUID, int] = dict(
        db.execute(
            select(Upload.user_id, func.count())
            .where(Upload.user_id.in_(user_ids))
            .group_by(Upload.user_id)
        ).all()
    )
    return AdminUserPage(
        items=[
            _user_item(db, u, uploads_count=counts.get(u.id, 0))
            for u in result.items
        ],
        total=result.total,
        page=result.page,
        per_page=result.per_page,
        pages=result.pages,
    )


@router.post(
    "/users",
    response_model=AdminUserItem,
    status_code=201,
    summary="Create a user",
    description="Creates a user with the given role and credentials.",
    responses=standard_responses(),
)
def create_user(
    payload: UserCreateRequest,
    request: Request,
    current_user: User = Depends(require_admin(permission=Permission.USERS_MANAGE)),
    db: Session = Depends(get_db),
) -> AdminUserItem:
    from app.core.security import hash_password

    try:
        role = UserRole(payload.role)
    except ValueError:
        raise AppError(400, "INVALID_ROLE", "Unknown user role.") from None
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise AppError(409, "EMAIL_EXISTS", "A user with this email already exists.")

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=role,
        is_active=payload.is_active,
        must_change_password=payload.must_change_password,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    _admin_log(
        db,
        request,
        current_user,
        action="admin.user_created",
        resource_type="user",
        resource_id=str(user.id),
        details={"email": user.email, "role": role.value},
    )
    return _user_item(db, user)


@router.put(
    "/users/{user_id}",
    response_model=AdminUserItem,
    summary="Update a user",
    description=(
        "Updates role, active state, name or password-change flag. A user "
        "cannot deactivate or demote themselves."
    ),
    responses=standard_responses(),
)
def update_user(
    user_id: uuid.UUID,
    payload: UserUpdateRequest,
    request: Request,
    current_user: User = Depends(require_admin(permission=Permission.USERS_MANAGE)),
    db: Session = Depends(get_db),
) -> AdminUserItem:
    user = db.get(User, user_id)
    if user is None:
        raise AppError(404, "USER_NOT_FOUND", "User not found.")

    changes: dict = {}
    if payload.full_name is not None:
        user.full_name = payload.full_name
        changes["full_name"] = user.full_name
    if payload.role is not None:
        try:
            new_role = UserRole(payload.role)
        except ValueError:
            raise AppError(400, "INVALID_ROLE", "Unknown user role.") from None
        if user.id == current_user.id and new_role.value == UserRole.USER.value:
            raise AppError(400, "INVALID_ROLE", "You cannot demote yourself to user.")
        user.role = new_role
        changes["role"] = new_role.value
    if payload.is_active is not None:
        if user.id == current_user.id and not payload.is_active:
            raise AppError(
                400, "SELF_DEACTIVATION", "You cannot deactivate your own account."
            )
        user.is_active = payload.is_active
        changes["is_active"] = payload.is_active
    if payload.must_change_password is not None:
        user.must_change_password = payload.must_change_password
        changes["must_change_password"] = payload.must_change_password
    if payload.email_verified is not None:
        user.email_verified = payload.email_verified
        changes["email_verified"] = payload.email_verified
    db.commit()
    db.refresh(user)

    _admin_log(
        db,
        request,
        current_user,
        action="admin.user_updated",
        resource_type="user",
        resource_id=str(user.id),
        details={"email": user.email, "changes": changes},
    )
    return _user_item(db, user)


@router.delete(
    "/users/{user_id}",
    status_code=204,
    summary="Delete a user",
    description=(
        "Permanently removes a user. Their uploads are detached but kept. "
        "Deleting your own account is not allowed."
    ),
    responses=standard_responses(),
)
def delete_user(
    user_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_admin(permission=Permission.USERS_MANAGE)),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise AppError(404, "USER_NOT_FOUND", "User not found.")
    if user.id == current_user.id:
        raise AppError(400, "SELF_DELETE", "You cannot delete your own account.")
    email = user.email
    db.delete(user)
    db.commit()
    _admin_log(
        db,
        request,
        current_user,
        action="admin.user_deleted",
        resource_type="user",
        resource_id=str(user_id),
        details={"email": email},
    )
    return None


# --- whatsapp --------------------------------------------------------------


@router.get(
    "/whatsapp/overview",
    response_model=AdminWhatsappStats,
    summary="WhatsApp integration overview",
    description=(
        "Message/contact/event counters plus webhook and configuration status. "
        "No secrets are returned."
    ),
    responses=standard_responses(),
)
def whatsapp_overview(
    current_user: User = Depends(require_admin(permission=Permission.WHATSAPP_VIEW)),
    db: Session = Depends(get_db),
) -> AdminWhatsappStats:
    messages_total = db.scalar(select(func.count()).select_from(WhatsappMessage)) or 0
    messages_inbound = (
        db.scalar(
            select(func.count())
            .select_from(WhatsappMessage)
            .where(
                WhatsappMessage.direction
                == WhatsAppMessageDirection.INBOUND
            )
        )
        or 0
    )
    messages_outbound = (
        db.scalar(
            select(func.count())
            .select_from(WhatsappMessage)
            .where(
                WhatsappMessage.direction
                == WhatsAppMessageDirection.OUTBOUND
            )
        )
        or 0
    )
    messages_failed = (
        db.scalar(
            select(func.count())
            .select_from(WhatsappMessage)
            .where(WhatsappMessage.status == WhatsAppMessageStatus.FAILED)
        )
        or 0
    )
    delivered = (
        db.scalar(
            select(func.count())
            .select_from(WhatsappMessageStatus)
            .where(WhatsappMessageStatus.status.in_(("delivered", "read")))
        )
        or 0
    )
    read = (
        db.scalar(
            select(func.count())
            .select_from(WhatsappMessageStatus)
            .where(WhatsappMessageStatus.status == "read")
        )
        or 0
    )
    contacts_total = db.scalar(select(func.count()).select_from(WhatsappContact)) or 0
    events_total = db.scalar(select(func.count()).select_from(WhatsappWebhookEvent)) or 0
    events_failed = (
        db.scalar(
            select(func.count())
            .select_from(WhatsappWebhookEvent)
            .where(WhatsappWebhookEvent.status == "failed")
        )
        or 0
    )
    return AdminWhatsappStats(
        messages_total=messages_total,
        messages_inbound=messages_inbound,
        messages_outbound=messages_outbound,
        messages_failed=messages_failed,
        messages_delivered=delivered,
        messages_read=read,
        contacts_total=contacts_total,
        events_total=events_total,
        events_failed=events_failed,
        webhook=whatsapp_service.webhook_status(db),
        config=whatsapp_config.config_status(db),
    )


@router.get(
    "/whatsapp/messages",
    response_model=AdminWhatsappMessagePage,
    summary="List WhatsApp messages",
    description="Paginated WhatsApp message log with direction/status filters.",
    responses=standard_responses(),
)
def list_whatsapp_messages(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    direction: str | None = Query(None),
    status: str | None = Query(None),
    search: str | None = Query(None, max_length=64),
    current_user: User = Depends(require_admin(permission=Permission.WHATSAPP_VIEW)),
    db: Session = Depends(get_db),
) -> AdminWhatsappMessagePage:
    stmt = select(WhatsappMessage)
    if direction:
        try:
            stmt = stmt.where(
                WhatsappMessage.direction
                == WhatsAppMessageDirection(direction)
            )
        except ValueError:
            raise AppError(400, "INVALID_DIRECTION", "Unknown direction.") from None
    if status:
        try:
            stmt = stmt.where(WhatsappMessage.status == WhatsAppMessageStatus(status))
        except ValueError:
            raise AppError(400, "INVALID_STATUS", "Unknown message status.") from None
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            or_(
                WhatsappMessage.text.ilike(like),
                WhatsappMessage.media_public_id.ilike(like),
                WhatsappMessage.meta_message_id.ilike(like),
            )
        )
    stmt = stmt.order_by(WhatsappMessage.created_at.desc())
    result: Page[WhatsappMessage] = paginate(db, stmt, page=page, per_page=per_page)

    contact_ids = {m.contact_id for m in result.items if m.contact_id}
    contacts: dict[uuid.UUID, tuple[str, str | None]] = {}
    if contact_ids:
        contacts = {
            c.id: (c.phone_number, c.display_name)
            for c in db.scalars(
                select(WhatsappContact).where(
                    WhatsappContact.id.in_(contact_ids)
                )
            )
        }
    items = [
        AdminWhatsappMessageItem(
            id=m.id,
            meta_message_id=m.meta_message_id,
            direction=m.direction.value,
            message_type=m.message_type,
            text=m.text,
            media_public_id=m.media_public_id,
            status=m.status.value,
            error_code=m.error_code,
            error_message=m.error_message,
            timestamp=m.timestamp,
            created_at=m.created_at,
            contact_phone=contacts[m.contact_id][0] if m.contact_id in contacts else None,
            contact_name=contacts[m.contact_id][1] if m.contact_id in contacts else None,
        )
        for m in result.items
    ]
    return AdminWhatsappMessagePage(
        items=items,
        total=result.total,
        page=result.page,
        per_page=result.per_page,
        pages=result.pages,
    )


@router.get(
    "/whatsapp/contacts",
    response_model=AdminWhatsappContactPage,
    summary="List WhatsApp contacts",
    description="Paginated WhatsApp contact list.",
    responses=standard_responses(),
)
def list_whatsapp_contacts(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, max_length=64),
    current_user: User = Depends(require_admin(permission=Permission.WHATSAPP_VIEW)),
    db: Session = Depends(get_db),
) -> AdminWhatsappContactPage:
    stmt = select(WhatsappContact)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            or_(
                WhatsappContact.phone_number.ilike(like),
                WhatsappContact.display_name.ilike(like),
            )
        )
    stmt = stmt.order_by(WhatsappContact.last_seen.desc())
    result: Page[WhatsappContact] = paginate(db, stmt, page=page, per_page=per_page)
    return AdminWhatsappContactPage(
        items=list(result.items),
        total=result.total,
        page=result.page,
        per_page=result.per_page,
        pages=result.pages,
    )


@router.get(
    "/whatsapp/webhook-events",
    response_model=AdminWhatsappEventPage,
    summary="List WhatsApp webhook events",
    description="Paginated webhook event log.",
    responses=standard_responses(),
)
def list_whatsapp_events(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    current_user: User = Depends(require_admin(permission=Permission.WHATSAPP_VIEW)),
    db: Session = Depends(get_db),
) -> AdminWhatsappEventPage:
    stmt = select(WhatsappWebhookEvent)
    if status:
        stmt = stmt.where(WhatsappWebhookEvent.status == status)
    stmt = stmt.order_by(WhatsappWebhookEvent.received_at.desc())
    result: Page[WhatsappWebhookEvent] = paginate(db, stmt, page=page, per_page=per_page)
    return AdminWhatsappEventPage(
        items=list(result.items),
        total=result.total,
        page=result.page,
        per_page=result.per_page,
        pages=result.pages,
    )


@router.get(
    "/whatsapp/config",
    response_model=dict,
    summary="WhatsApp configuration (masked)",
    description="Effective WhatsApp config with secrets masked.",
    responses=standard_responses(),
)
def whatsapp_config_status(
    current_user: User = Depends(require_admin(permission=Permission.WHATSAPP_VIEW)),
    db: Session = Depends(get_db),
):
    return whatsapp_config.config_status(db)


@router.put(
    "/whatsapp/config",
    response_model=dict,
    summary="Update WhatsApp configuration",
    description=(
        "Updates the persisted WhatsApp settings. Secrets are never echoed back."
    ),
    responses=standard_responses(),
)
def update_whatsapp_config(
    payload: WhatsAppConfigUpdate,
    request: Request,
    current_user: User = Depends(
        require_admin(permission=Permission.WHATSAPP_CREDENTIALS)
    ),
    db: Session = Depends(get_db),
):
    kwargs = payload.model_dump(exclude_none=True)
    row = whatsapp_config.upsert_config(db, **kwargs)
    _admin_log(
        db,
        request,
        current_user,
        action="admin.whatsapp_config_updated",
        resource_type="whatsapp_setting",
        resource_id=str(row.id),
        details={"fields": sorted(kwargs.keys())},
    )
    return whatsapp_config.config_status(db)


@router.post(
    "/whatsapp/test",
    response_model=dict,
    summary="Test the WhatsApp connection",
    description="Verifies the configured credentials against the Graph API.",
    responses=standard_responses(),
)
def test_whatsapp_connection(
    request: Request,
    current_user: User = Depends(require_admin(permission=Permission.WHATSAPP_TEST)),
    db: Session = Depends(get_db),
):
    result = whatsapp_service.test_connection(db)
    _admin_log(
        db,
        request,
        current_user,
        action="admin.whatsapp_connection_test",
        result="success" if result.get("success") else "failure",
        details={"success": bool(result.get("success"))},
    )
    return result


# --- watermark -------------------------------------------------------------


@router.get(
    "/watermark",
    response_model=list[WatermarkOut],
    summary="List watermark configurations",
    responses=standard_responses(),
)
def list_watermarks(
    current_user: User = Depends(require_admin(permission=Permission.WATERMARK_VIEW)),
    db: Session = Depends(get_db),
):
    rows = db.scalars(select(Watermark).order_by(Watermark.created_at.asc())).all()
    return [
        WatermarkOut(
            id=w.id,
            name=w.name,
            type=w.type,
            text=w.text,
            image_url=w.image_url,
            position=w.position,
            opacity=w.opacity,
            size_percent=w.size_percent,
            margin=w.margin,
            enabled=w.enabled,
            created_at=w.created_at,
            updated_at=w.updated_at,
        )
        for w in rows
    ]


@router.get(
    "/watermark/positions",
    response_model=list[str],
    summary="Supported watermark positions",
    description="The exact position strings the watermark pipeline supports.",
    responses=standard_responses(),
)
def watermark_positions(
    current_user: User = Depends(require_admin(permission=Permission.WATERMARK_VIEW)),
):
    return list(POSITIONS)


@router.post(
    "/watermark",
    response_model=WatermarkOut,
    status_code=201,
    summary="Create a watermark configuration",
    responses=standard_responses(),
)
def create_watermark(
    payload: WatermarkIn,
    request: Request,
    current_user: User = Depends(
        require_admin(permission=Permission.WATERMARK_MANAGE)
    ),
    db: Session = Depends(get_db),
) -> WatermarkOut:
    _validate_watermark_payload(payload)
    if db.scalar(select(Watermark).where(Watermark.name == payload.name)):
        raise AppError(409, "NAME_EXISTS", "A watermark with this name exists.")
    row = Watermark(
        name=payload.name,
        type=payload.type,
        text=payload.text,
        image_url=payload.image_url,
        position=payload.position,
        opacity=payload.opacity,
        size_percent=payload.size_percent,
        margin=payload.margin,
        enabled=payload.enabled,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    _admin_log(
        db,
        request,
        current_user,
        action="admin.watermark_created",
        resource_type="watermark",
        resource_id=str(row.id),
        details={"name": row.name},
    )
    return _watermark_out(row)


@router.put(
    "/watermark/{watermark_id}",
    response_model=WatermarkOut,
    summary="Update a watermark configuration",
    responses=standard_responses(),
)
def update_watermark(
    watermark_id: uuid.UUID,
    payload: WatermarkUpdate,
    request: Request,
    current_user: User = Depends(
        require_admin(permission=Permission.WATERMARK_MANAGE)
    ),
    db: Session = Depends(get_db),
) -> WatermarkOut:
    row = db.get(Watermark, watermark_id)
    if row is None:
        raise AppError(404, "WATERMARK_NOT_FOUND", "Watermark not found.")
    changes = payload.model_dump(exclude_none=True)
    merged = WatermarkIn(
        name=changes.get("name", row.name),
        type=changes.get("type", row.type),
        text=changes.get("text", row.text),
        image_url=changes.get("image_url", row.image_url),
        position=changes.get("position", row.position),
        opacity=changes.get("opacity", row.opacity),
        size_percent=changes.get("size_percent", row.size_percent),
        margin=changes.get("margin", row.margin),
        enabled=changes.get("enabled", row.enabled),
    )
    _validate_watermark_payload(merged)
    if changes.get("name") and changes["name"] != row.name:
        if db.scalar(select(Watermark).where(Watermark.name == changes["name"])):
            raise AppError(409, "NAME_EXISTS", "A watermark with this name exists.")
    for field, value in changes.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    _admin_log(
        db,
        request,
        current_user,
        action="admin.watermark_updated",
        resource_type="watermark",
        resource_id=str(row.id),
        details={"name": row.name, "changes": sorted(changes.keys())},
    )
    return _watermark_out(row)


@router.delete(
    "/watermark/{watermark_id}",
    status_code=204,
    summary="Delete a watermark configuration",
    responses=standard_responses(),
)
def delete_watermark(
    watermark_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(
        require_admin(permission=Permission.WATERMARK_MANAGE)
    ),
    db: Session = Depends(get_db),
):
    row = db.get(Watermark, watermark_id)
    if row is None:
        raise AppError(404, "WATERMARK_NOT_FOUND", "Watermark not found.")
    name = row.name
    db.delete(row)
    db.commit()
    _admin_log(
        db,
        request,
        current_user,
        action="admin.watermark_deleted",
        resource_type="watermark",
        resource_id=str(watermark_id),
        details={"name": name},
    )
    return None


def _validate_watermark_payload(payload) -> None:
    if payload.position not in POSITIONS:
        raise AppError(
            400,
            "INVALID_POSITION",
            f"Position must be one of: {', '.join(POSITIONS)}.",
        )
    if payload.type == "text" and not (payload.text or "").strip():
        raise AppError(400, "TEXT_REQUIRED", "A text watermark requires text.")
    if payload.type == "image" and not (payload.image_url or "").strip():
        raise AppError(
            400, "IMAGE_REQUIRED", "An image watermark requires an image URL."
        )


def _watermark_out(row: Watermark) -> WatermarkOut:
    return WatermarkOut(
        id=row.id,
        name=row.name,
        type=row.type,
        text=row.text,
        image_url=row.image_url,
        position=row.position,
        opacity=row.opacity,
        size_percent=row.size_percent,
        margin=row.margin,
        enabled=row.enabled,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


# --- storage ---------------------------------------------------------------


def _storage_summary(db: Session) -> dict:
    from app.core.storage import get_storage

    storage = get_storage()
    used_bytes: int | None = None
    if storage.provider == "local":
        base = settings.STORAGE_DIR
        try:
            used_bytes = sum(
                f.stat().st_size
                for f in __import__("pathlib").Path(base).rglob("*")
                if f.is_file()
            )
        except OSError:
            used_bytes = None
    objects = (
        db.scalar(select(func.count()).select_from(MediaFile)) or 0
    ) + (db.scalar(select(func.count()).select_from(ProcessedMedia)) or 0)
    writable = False
    try:
        storage.check_writable()
        writable = True
    except Exception:
        writable = False
    return {
        "driver": settings.STORAGE_DRIVER,
        "provider": storage.provider,
        "base_path": settings.STORAGE_DIR if storage.provider == "local" else None,
        "bucket": getattr(settings, "S3_BUCKET_NAME", None) if storage.provider == "s3" else None,
        "endpoint": getattr(settings, "S3_ENDPOINT_URL", None) if storage.provider == "s3" else None,
        "region": getattr(settings, "S3_REGION", None) or None,
        "media_url_mode": settings.MEDIA_URL_MODE,
        "writable": writable,
        "objects": objects,
        "used_bytes": used_bytes,
    }


@router.get(
    "/storage",
    response_model=StorageResponse,
    summary="Storage status",
    description=(
        "Storage driver/provider status and usage. Credentials and signed "
        "URLs are never returned."
    ),
    responses=standard_responses(),
)
def storage_status(
    current_user: User = Depends(require_admin(permission=Permission.STORAGE_VIEW)),
    db: Session = Depends(get_db),
) -> StorageResponse:
    return StorageResponse(**_storage_summary(db))


# --- settings --------------------------------------------------------------


@router.get(
    "/settings",
    response_model=AdminSettingsOut,
    summary="List application settings (masked)",
    description=(
        "All settings grouped for the dashboard. Secret values are masked and "
        "never sent to the browser."
    ),
    responses=standard_responses(),
)
def admin_settings(
    current_user: User = Depends(require_admin(permission=Permission.SETTINGS_VIEW)),
    db: Session = Depends(get_db),
) -> AdminSettingsOut:
    from app.services.settings_service import list_settings

    return _mask_settings(list_settings(db, is_admin=True))


@router.put(
    "/settings",
    response_model=AdminSettingsOut,
    summary="Update application settings",
    description="Updates settings. Secret values sent as '***' are left unchanged.",
    responses=standard_responses(),
)
def update_settings(
    request: Request,
    payload: list[SettingsItemUpdate] = Body(...),
    current_user: User = Depends(
        require_admin(permission=Permission.SETTINGS_MANAGE)
    ),
    db: Session = Depends(get_db),
) -> AdminSettingsOut:
    from app.services.settings_service import list_settings, update_settings as apply_update

    if not payload:
        raise AppError(400, "EMPTY_PAYLOAD", "At least one setting is required.")
    ip, user_agent = audit_service.client_meta(request)
    result = apply_update(
        db,
        payload,
        actor=current_user,
        ip_address=ip,
        user_agent=user_agent,
    )
    return _mask_settings(result)


# --- logs & audit ----------------------------------------------------------


@router.get(
    "/logs",
    response_model=AdminLogPage,
    summary="List system logs",
    description="Paginated system log table with level filter.",
    responses=standard_responses(),
)
def list_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    level: str | None = Query(None),
    current_user: User = Depends(require_admin(permission=Permission.LOGS_VIEW)),
    db: Session = Depends(get_db),
) -> AdminLogPage:
    stmt = select(SystemLog)
    if level:
        stmt = stmt.where(SystemLog.level == level.upper())
    stmt = stmt.order_by(SystemLog.created_at.desc())
    result: Page[SystemLog] = paginate(db, stmt, page=page, per_page=per_page)
    return AdminLogPage(
        items=list(result.items),
        total=result.total,
        page=result.page,
        per_page=result.per_page,
        pages=result.pages,
    )


@router.get(
    "/audit-logs",
    response_model=AdminAuditPage,
    summary="List audit logs",
    description="Paginated audit trail with action/actor filters.",
    responses=standard_responses(),
)
def list_audit_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    action: str | None = Query(None),
    actor_type: str | None = Query(None),
    current_user: User = Depends(require_admin(permission=Permission.AUDIT_VIEW)),
    db: Session = Depends(get_db),
) -> AdminAuditPage:
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if actor_type:
        stmt = stmt.where(AuditLog.actor_type == actor_type)
    stmt = stmt.order_by(AuditLog.created_at.desc())
    result: Page[AuditLog] = paginate(db, stmt, page=page, per_page=per_page)
    return AdminAuditPage(
        items=list(result.items),
        total=result.total,
        page=result.page,
        per_page=result.per_page,
        pages=result.pages,
    )


# --- security --------------------------------------------------------------


@router.get(
    "/security/overview",
    response_model=SecurityOverview,
    summary="Security overview",
    description="Locked accounts, failed logins, API keys and session counts.",
    responses=standard_responses(),
)
def security_overview(
    current_user: User = Depends(require_admin(permission=Permission.SECURITY_VIEW)),
    db: Session = Depends(get_db),
) -> SecurityOverview:
    now = _now()
    day_start = now - dt.timedelta(hours=24)
    users_total = db.scalar(select(func.count()).select_from(User)) or 0
    locked = (
        db.scalar(
            select(func.count())
            .select_from(User)
            .where(User.locked_until > now.replace(tzinfo=None))
        )
        or 0
    )
    active_keys = (
        db.scalar(
            select(func.count()).select_from(ApiKey).where(ApiKey.is_active.is_(True))
        )
        or 0
    )
    failed_24h = (
        db.scalar(
            select(func.count())
            .select_from(LoginHistory)
            .where(
                LoginHistory.success.is_(False),
                LoginHistory.created_at >= day_start.replace(tzinfo=None),
            )
        )
        or 0
    )
    recent_sessions = (
        db.scalar(
            select(func.count())
            .select_from(LoginHistory)
            .where(
                LoginHistory.success.is_(True),
                LoginHistory.created_at >= day_start.replace(tzinfo=None),
            )
        )
        or 0
    )
    return SecurityOverview(
        users_total=users_total,
        locked_accounts=locked,
        active_api_keys=active_keys,
        failed_logins_24h=failed_24h,
        recent_sessions=recent_sessions,
    )


@router.get(
    "/security/login-history",
    response_model=AdminLoginHistoryPage,
    summary="Login history",
    description="Paginated login attempts across all users.",
    responses=standard_responses(),
)
def list_login_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    success: bool | None = Query(None),
    current_user: User = Depends(require_admin(permission=Permission.SECURITY_VIEW)),
    db: Session = Depends(get_db),
) -> AdminLoginHistoryPage:
    stmt = select(LoginHistory)
    if success is not None:
        stmt = stmt.where(LoginHistory.success.is_(success))
    stmt = stmt.order_by(LoginHistory.created_at.desc())
    result: Page[LoginHistory] = paginate(db, stmt, page=page, per_page=per_page)
    return AdminLoginHistoryPage(
        items=list(result.items),
        total=result.total,
        page=result.page,
        per_page=result.per_page,
        pages=result.pages,
    )


@router.get(
    "/security/api-keys",
    response_model=list[AdminApiKeyItem],
    summary="List API keys",
    description="All API keys with owners and masked metadata. Hashes are never returned.",
    responses=standard_responses(),
)
def list_api_keys(
    current_user: User = Depends(require_admin(permission=Permission.SECURITY_VIEW)),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        select(ApiKey, User.email)
        .join(User, User.id == ApiKey.user_id)
        .order_by(ApiKey.created_at.desc())
    ).all()
    return [
        AdminApiKeyItem(
            id=row.id,
            name=row.name,
            key_prefix=row.key_prefix,
            scopes=row.scopes or [],
            last_used_at=row.last_used_at,
            expires_at=row.expires_at,
            is_active=row.is_active,
            created_at=row.created_at,
            user_email=user_email,
        )
        for row, user_email in rows
    ]


@router.post(
    "/security/api-keys/{key_id}/revoke",
    response_model=AdminApiKeyItem,
    summary="Revoke an API key",
    responses=standard_responses(),
)
def revoke_api_key(
    key_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(
        require_admin(permission=Permission.SECURITY_MANAGE)
    ),
    db: Session = Depends(get_db),
) -> AdminApiKeyItem:
    row = db.get(ApiKey, key_id)
    if row is None:
        raise AppError(404, "API_KEY_NOT_FOUND", "API key not found.")
    row.is_active = False
    db.commit()
    _admin_log(
        db,
        request,
        current_user,
        action="admin.api_key_revoked",
        resource_type="api_key",
        resource_id=str(row.id),
        details={"name": row.name},
    )
    owner = db.scalar(select(User).where(User.id == row.user_id))
    return AdminApiKeyItem(
        id=row.id,
        name=row.name,
        key_prefix=row.key_prefix,
        scopes=row.scopes or [],
        last_used_at=row.last_used_at,
        expires_at=row.expires_at,
        is_active=row.is_active,
        created_at=row.created_at,
        user_email=owner.email if owner else None,
    )


@router.post(
    "/security/users/{user_id}/logout-all",
    response_model=AdminUserItem,
    summary="Sign a user out of every session",
    description="Revokes all access and refresh tokens for a user.",
    responses=standard_responses(),
)
def user_logout_all(
    user_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(
        require_admin(permission=Permission.SECURITY_MANAGE)
    ),
    db: Session = Depends(get_db),
) -> AdminUserItem:
    user = db.get(User, user_id)
    if user is None:
        raise AppError(404, "USER_NOT_FOUND", "User not found.")
    revoke_all_user_tokens(user)
    db.commit()
    _admin_log(
        db,
        request,
        current_user,
        action="admin.user_sessions_revoked",
        resource_type="user",
        resource_id=str(user.id),
        details={"email": user.email, "token_version": user.token_version},
    )
    return _user_item(db, user)


# --- health ----------------------------------------------------------------


@router.get(
    "/health",
    response_model=AdminHealthResponse,
    summary="System health",
    description=(
        "Live health checks for database, redis, workers and storage plus the "
        "registered worker processes."
    ),
    responses=standard_responses(),
)
def admin_health(
    current_user: User = Depends(require_admin(permission=Permission.HEALTH_VIEW)),
    db: Session = Depends(get_db),
) -> AdminHealthResponse:
    payload = health_service.health_payload()
    workers = db.scalars(
        select(Worker).order_by(Worker.last_heartbeat.desc().nulls_last())
    ).all()
    return AdminHealthResponse(
        status=payload["status"],
        version=payload["version"],
        environment=payload["environment"],
        uptime_seconds=payload["uptime_seconds"],
        components=payload["components"],
        timestamp=payload["timestamp"],
        workers=[
            {
                "name": w.name,
                "hostname": w.hostname,
                "status": w.status.value,
                "current_job_id": w.current_job_id,
                "last_heartbeat": w.last_heartbeat,
                "started_at": w.started_at,
            }
            for w in workers
        ],
    )
