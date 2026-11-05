from collections.abc import Sequence
from typing import Annotated

import structlog
from fastapi import APIRouter, HTTPException, Query
from sqlmodel import col, select

from taskdesk.ai import AIUnavailableError, SuggesterDep
from taskdesk.db import SessionDep
from taskdesk.models import (
    StepSuggestions,
    Task,
    TaskCreate,
    TaskRead,
    TaskStatus,
    TaskUpdate,
    utcnow,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/tasks", tags=["tasks"])


def get_task_or_404(session: SessionDep, task_id: int) -> Task:
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("", response_model=TaskRead, status_code=201)
def create_task(payload: TaskCreate, session: SessionDep) -> Task:
    task = Task.model_validate(payload)
    session.add(task)
    session.commit()
    session.refresh(task)
    logger.info("task_created", task_id=task.id)
    return task


@router.get("", response_model=list[TaskRead])
def list_tasks(
    session: SessionDep,
    status: TaskStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Sequence[Task]:
    statement = select(Task).order_by(col(Task.id)).offset(offset).limit(limit)
    if status is not None:
        statement = statement.where(col(Task.status) == status)
    return session.exec(statement).all()


@router.get("/{task_id}", response_model=TaskRead)
def read_task(task_id: int, session: SessionDep) -> Task:
    return get_task_or_404(session, task_id)


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(task_id: int, payload: TaskUpdate, session: SessionDep) -> Task:
    task = get_task_or_404(session, task_id)
    task.sqlmodel_update(payload.model_dump(exclude_unset=True))
    task.updated_at = utcnow()
    session.add(task)
    session.commit()
    session.refresh(task)
    logger.info("task_updated", task_id=task.id)
    return task


@router.post("/{task_id}/suggest-steps", response_model=StepSuggestions)
def suggest_steps(task_id: int, session: SessionDep, suggester: SuggesterDep) -> StepSuggestions:
    """Ask the AI to break a task into steps. Suggestions are returned, not saved."""
    task = get_task_or_404(session, task_id)
    try:
        steps = suggester.suggest_steps(task.title, task.description)
    except AIUnavailableError as exc:
        logger.warning("ai_suggestion_failed", task_id=task_id, error=str(exc))
        raise HTTPException(
            status_code=502, detail="AI service is unavailable, try again later"
        ) from exc
    logger.info("ai_steps_suggested", task_id=task_id, step_count=len(steps))
    return StepSuggestions(task_id=task_id, steps=steps)


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int, session: SessionDep) -> None:
    task = get_task_or_404(session, task_id)
    session.delete(task)
    session.commit()
    logger.info("task_deleted", task_id=task_id)
