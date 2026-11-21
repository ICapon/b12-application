import secrets
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import utcnow
from app.models import Application, Note, Stage, StageName
from app.schemas import ApplicationCreate
from app.services.stages import validate_transition


def generate_receipt(now: datetime | None = None) -> str:
    now = now or utcnow()
    stamp = now.strftime("%Y%m%d%H%M%S") + f"{now.microsecond // 1000:03d}"
    return f"thank-you-from-b12-{stamp}-{secrets.token_hex(6)}"


def create_application(db: Session, payload: ApplicationCreate) -> Application:
    now = utcnow()
    submitted = payload.timestamp or now
    app = Application(
        name=payload.name,
        email=payload.email,
        timestamp=submitted,
        resume_link=payload.resume_link,
        repository_link=payload.repository_link,
        action_run_link=payload.action_run_link,
        receipt=generate_receipt(now),
    )
    app.stages.append(Stage(name=StageName.NEW, entered_at=now))
    db.add(app)
    db.commit()
    return app


def get_application(db: Session, application_id: int) -> Application | None:
    return db.get(Application, application_id)


def list_applications(
    db: Session,
    *,
    page: int,
    page_size: int,
    submitted_from: date | None = None,
    submitted_to: date | None = None,
    email: str | None = None,
    receipt: str | None = None,
) -> tuple[list[Application], int]:
    """Filters are AND-ed. Date bounds are inclusive whole UTC days."""
    query = select(Application)
    if submitted_from:
        start = datetime.combine(submitted_from, time.min, tzinfo=timezone.utc)
        query = query.where(Application.timestamp >= start)
    if submitted_to:
        end = datetime.combine(submitted_to + timedelta(days=1), time.min, tzinfo=timezone.utc)
        query = query.where(Application.timestamp < end)
    if email:
        query = query.where(func.lower(Application.email) == email.lower())
    if receipt:
        query = query.where(Application.receipt == receipt)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(
        query.order_by(Application.timestamp.desc(), Application.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(items), total


def change_stage(db: Session, app: Application, new: StageName) -> Application:
    validate_transition(app.current_stage.name, new)  # raises InvalidTransition
    app.stages.append(Stage(name=new, entered_at=utcnow()))
    db.commit()
    return app


def add_note(db: Session, app: Application, content: str) -> Note:
    note = Note(stage=app.current_stage, content=content)
    db.add(note)
    db.commit()
    return note
