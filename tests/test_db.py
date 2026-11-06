import pytest

from taskdesk.db import normalize_database_url


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "postgresql://user:pw@host/db?sslmode=require",
            "postgresql+psycopg2://user:pw@host/db?sslmode=require",
        ),
        (
            "postgres://user:pw@host/db",
            "postgresql+psycopg2://user:pw@host/db",
        ),
        (
            "postgresql+psycopg2://user:pw@host/db",
            "postgresql+psycopg2://user:pw@host/db",
        ),
        ("sqlite:///./taskdesk.db", "sqlite:///./taskdesk.db"),
    ],
)
def test_normalize_database_url_picks_the_psycopg2_driver(raw: str, expected: str) -> None:
    assert normalize_database_url(raw) == expected


def test_normalize_database_url_strips_stray_whitespace() -> None:
    # A trailing space (easy to copy by accident) breaks `?sslmode=require`.
    assert (
        normalize_database_url("  postgresql://u:p@h/db?sslmode=require \n")
        == "postgresql+psycopg2://u:p@h/db?sslmode=require"
    )
