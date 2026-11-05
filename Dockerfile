FROM python:3.12-slim

# uv installs dependencies exactly as pinned in uv.lock
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# The project itself is installed by `uv sync`, so it needs pyproject, README and src first.
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev

COPY alembic.ini ./
COPY migrations ./migrations

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# Apply database migrations, then start the API. Hosts such as Render provide $PORT.
CMD ["sh", "-c", "alembic upgrade head && uvicorn taskdesk.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
