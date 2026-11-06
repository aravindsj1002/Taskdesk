# Taskdesk
**Live demo:** https://taskdesk-78m7.onrender.com/docs
(Free hosting sleeps when idle, so the first load can take about a minute.)

A small task-tracking REST API built to practise a production-style Python backend setup:
FastAPI, SQLModel, Alembic migrations, structured logging, tests, and strict linting and type
checking.

## Stack

| Area | Tools |
| --- | --- |
| API | FastAPI, Pydantic v2, pydantic-settings |
| Database | SQLModel / SQLAlchemy, Alembic migrations, SQLite for local use, PostgreSQL via `DATABASE_URL` |
| Logging | structlog (console locally, JSON lines in production), per-request `x-request-id` |
| Quality | Pytest, Ruff, Pyright, pre-commit |
| Packaging | uv |

## Quick start

```bash
uv sync                              # install dependencies into .venv
uv run alembic upgrade head          # create the database schema
uv run uvicorn taskdesk.main:app --reload
```

Open http://127.0.0.1:8000/docs for the interactive API docs.

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| GET | `/health` | Liveness check |
| POST | `/tasks` | Create a task (`title` required, `status` defaults to `todo`) |
| GET | `/tasks` | List tasks; filter with `?status=done`, page with `?limit=20&offset=0` |
| GET | `/tasks/{id}` | Get one task |
| PATCH | `/tasks/{id}` | Partial update; only the fields you send change |
| DELETE | `/tasks/{id}` | Delete a task |

Statuses: `todo`, `in_progress`, `done`.

```bash
curl -X POST localhost:8000/tasks -H 'content-type: application/json' \
  -d '{"title": "Write README"}'
curl 'localhost:8000/tasks?status=todo'
curl -X PATCH localhost:8000/tasks/1 -H 'content-type: application/json' \
  -d '{"status": "done"}'
```

## Using PostgreSQL

```bash
docker run --name taskdesk-db -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=taskdesk \
  -p 5432:5432 -d postgres:16

export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/taskdesk
uv run alembic upgrade head
```

Settings can also live in a `.env` file (see `.env.example`).

## Development

```bash
uv run pytest                 # tests use an in-memory SQLite database
uv run ruff check . && uv run ruff format .
uv run pyright
uv run pre-commit install     # run the checks automatically on every commit
```

Creating a new migration after changing `models.py`:

```bash
uv run alembic revision --autogenerate -m "describe the change"
```

## Layout

```
src/taskdesk/
  main.py            app factory, request-logging middleware, /health
  routes.py          /tasks endpoints
  models.py          SQLModel tables and request/response schemas
  db.py              engine and per-request session dependency
  config.py          settings from environment / .env
  logging_config.py  structlog setup
migrations/          Alembic environment and versions
tests/               API tests (pytest + TestClient)
```

## Design notes

- Separate schemas for create, update and read (`TaskCreate`, `TaskUpdate`, `TaskRead`) so the
  table model is never exposed directly and clients cannot set `id` or timestamps.
- `PATCH` uses `exclude_unset`, so omitted fields are left alone and `description` can be
  cleared by sending `null`. `title` and `status` reject `null` with a 422.
- The schema is owned by Alembic; the app never calls `create_all` (only the tests do, against
  a throwaway in-memory database).

## Ideas for next steps

- Add Redis caching for `GET /tasks`.
- Add a Celery task, for example a reminder for tasks that stay `in_progress` too long.
- Add users and authentication so each person sees only their own tasks.
- Add OpenTelemetry tracing.
