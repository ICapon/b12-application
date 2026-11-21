import enum
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, UTCDateTime, utcnow


class StageName(str, enum.Enum):
    NEW = "New"
    PHONE_SCREEN_SCHEDULED = "Phone screen scheduled"
    INTERVIEW_SCHEDULED = "Interview scheduled"
    HIRED = "Hired"
    REJECTED = "Rejected"


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Field names mirror the payload built by submit.py (the source of truth).
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(320), index=True)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)
    resume_link: Mapped[str | None] = mapped_column(String(2048), default=None)
    repository_link: Mapped[str | None] = mapped_column(String(2048), default=None)
    action_run_link: Mapped[str | None] = mapped_column(String(2048), default=None)
    receipt: Mapped[str] = mapped_column(String(100), unique=True, index=True)

    # Each row is one entry into a stage; the last one is the current stage.
    stages: Mapped[list["Stage"]] = relationship(
        back_populates="application",
        order_by="Stage.id",
        cascade="all, delete-orphan",
    )

    @property
    def current_stage(self) -> "Stage":
        return self.stages[-1]


class Stage(Base):
    __tablename__ = "stages"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    name: Mapped[StageName] = mapped_column(
        Enum(
            StageName,
            native_enum=False,
            length=30,
            values_callable=lambda e: [m.value for m in e],
        )
    )
    entered_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    application: Mapped[Application] = relationship(back_populates="stages")
    notes: Mapped[list["Note"]] = relationship(
        back_populates="stage", order_by="Note.id", cascade="all, delete-orphan"
    )


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    stage_id: Mapped[int] = mapped_column(ForeignKey("stages.id"), index=True)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    stage: Mapped[Stage] = relationship(back_populates="notes")
