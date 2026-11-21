from datetime import datetime
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, EmailStr, StringConstraints

from app.models import StageName

NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


Link = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=2048, pattern=r"^https?://\S+$")
]


class ApplicationCreate(BaseModel):
    """Payload built by submit.py; its field names are the source of truth."""

    model_config = ConfigDict(extra="forbid")

    name: Annotated[NonBlank, StringConstraints(max_length=255)]
    email: EmailStr
    timestamp: AwareDatetime | None = None  # defaults to server time
    resume_link: Link | None = None
    repository_link: Link | None = None
    action_run_link: Link | None = None


class ApplicationListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    timestamp: datetime
    receipt: str


class ApplicationDetail(ApplicationListItem):
    resume_link: str | None
    repository_link: str | None
    action_run_link: str | None
    current_stage: StageName


class ApplicationCreated(ApplicationDetail):
    success: bool = True  # submit.py only prints the receipt when this is true


class ApplicationPage(BaseModel):
    items: list[ApplicationListItem]
    total: int
    page: int
    page_size: int


class StageUpdate(BaseModel):
    stage: StageName


class NoteCreate(BaseModel):
    content: NonBlank


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    stage_id: int
    content: str
    created_at: datetime


class HistoryEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    stage: StageName
    entered_at: datetime
    notes: list[NoteOut]
