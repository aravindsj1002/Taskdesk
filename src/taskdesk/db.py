from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine

from taskdesk.config import get_settings


def normalize_database_url(url: str) -> str:
    """Make a hosting provider's connection string work with the installed driver.

    Providers such as Neon hand out `postgresql://...` (or the older `postgres://...`), and
    copied strings often carry stray whitespace. This project uses the psycopg2 driver, so
    those prefixes are rewritten to `postgresql+psycopg2://`. Other URLs are left alone.
    """
    url = url.strip()
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg2://" + url[len(prefix) :]
    return url


def make_engine(url: str) -> Engine:
    """Create an engine; SQLite needs a flag so it can be used across FastAPI's threads."""
    url = normalize_database_url(url)
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
