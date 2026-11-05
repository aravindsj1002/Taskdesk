from datetime import UTC, datetime
from enum import StrEnum

from pydantic import field_validator
from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(UTC)


class TaskStatus(StrEnum):
    # Member names equal their values on purpose: SQLAlchemy stores enum *names*,
    # and the Alembic migration lists these same strings.
    todo = "todo"
    in_progress = "in_progress"
    done = "done"


class TaskBase(SQLModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    status: TaskStatus = TaskStatus.todo


class Task(TaskBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow, sa_type=DateTime(timezone=True))
    updated_at: datetime = Field(default_factory=utcnow, sa_type=DateTime(timezone=True))


class TaskCreate(TaskBase):
    pass


class TaskRead(TaskBase):
    id: int
    created_at: datetime
    updated_at: datetime


class StepSuggestions(SQLModel):
    task_id: int
    steps: list[str]


class TaskUpdate(SQLModel):
    """Partial update: only the fields the client sends are changed."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    status: TaskStatus | None = None

    @field_validator("title", "status")
    @classmethod
    def reject_null(cls, value: object) -> object:
        # These columns are NOT NULL, so an explicit null is a client error.
        # (description may be set to null to clear it.)
        if value is None:
            raise ValueError("must not be null")
        return value
