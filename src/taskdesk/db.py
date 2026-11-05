from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine

from taskdesk.config import get_settings


def make_engine(url: str) -> Engine:
    """Create an engine; SQLite needs a flag so it can be used across FastAPI's threads."""
    kwargs: dict[str, Any] = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **kwargs)


@lru_cache
def get_engine() -> Engine:
    return make_engine(get_settings().database_url)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one database session per request."""
    with Session(get_engine()) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
