from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Application
from app.schemas import (
    ApplicationCreate,
    ApplicationCreated,
    ApplicationDetail,
    ApplicationPage,
    HistoryEntry,
    NoteCreate,
    NoteOut,
    StageUpdate,
)
from app.security import verify_signature
from app.services import applications as svc
from app.services.stages import InvalidTransition

router = APIRouter(prefix="/applications", tags=["applications"])

DB = Annotated[Session, Depends(get_db)]


def _detail(app: Application) -> ApplicationDetail:
    return ApplicationDetail(
        id=app.id,
        name=app.name,
        email=app.email,
        timestamp=app.timestamp,
        resume_link=app.resume_link,
        repository_link=app.repository_link,
        action_run_link=app.action_run_link,
        receipt=app.receipt,
        current_stage=app.current_stage.name,
    )


def _get_or_404(db: Session, application_id: int) -> Application:
    app = svc.get_application(db, application_id)
    if app is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
    return app


@router.post("", response_model=ApplicationCreated, status_code=status.HTTP_201_CREATED)
async def create_application(request: Request, db: DB):
    # Read the raw bytes: the HMAC signature covers exactly what was sent.
    body = await request.body()
    verify_signature(body, request.headers.get("X-Signature-256"))
    try:
        payload = ApplicationCreate.model_validate_json(body)
    except ValidationError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            exc.errors(include_url=False, include_context=False, include_input=False),
        )
    return _detail(svc.create_application(db, payload))


@router.get("", response_model=ApplicationPage)
def list_applications(
    db: DB,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    submitted_from: date | None = None,
    submitted_to: date | None = None,
    email: str | None = None,
    receipt: str | None = None,
):
    if submitted_from and submitted_to and submitted_from > submitted_to:
        raise HTTPException(
            422,
            "submitted_from must not be after submitted_to",
        )
    items, total = svc.list_applications(
        db,
        page=page,
        page_size=page_size,
        submitted_from=submitted_from,
        submitted_to=submitted_to,
        email=email,
        receipt=receipt,
    )
    return ApplicationPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/{application_id}", response_model=ApplicationDetail)
def get_application(application_id: int, db: DB):
    return _detail(_get_or_404(db, application_id))


@router.put("/{application_id}/stage", response_model=ApplicationDetail)
def update_stage(application_id: int, payload: StageUpdate, db: DB):
    app = _get_or_404(db, application_id)
    try:
        svc.change_stage(db, app, payload.stage)
    except InvalidTransition as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    return _detail(app)


@router.post(
    "/{application_id}/notes", response_model=NoteOut, status_code=status.HTTP_201_CREATED
)
def create_note(application_id: int, payload: NoteCreate, db: DB):
    app = _get_or_404(db, application_id)
    return svc.add_note(db, app, payload.content)


@router.get("/{application_id}/history", response_model=list[HistoryEntry])
def get_history(application_id: int, db: DB):
    app = _get_or_404(db, application_id)
    return [
        HistoryEntry(stage=s.name, entered_at=s.entered_at, notes=s.notes) for s in app.stages
    ]
