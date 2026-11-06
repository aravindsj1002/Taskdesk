# Taskdesk

**Live demo:** https://taskdesk-78m7.onrender.com/docs
(Free hosting sleeps when idle, so the first load can take about a minute.)

A small task-tracking REST API built to practise a production-style Python backend setup:
FastAPI, SQLModel, Alembic migrations, structured logging, an AI feature with Google Gemini,
tests, strict linting and type checking, and a Docker deployment.

## Features

- Create, read, partially update and delete tasks, with status filtering and pagination.
- AI step suggestions: ask Gemini to break a task into 3 to 6 small steps.
- Database schema managed by Alembic migrations. SQLite locally, PostgreSQL in production.
- Structured logs with a request ID on every line, and the same ID returned in a response header.
- Automated tests that need no network, no API key and no external database.

## Stack

| Area | Tools |
| --- | --- |
| API | FastAPI, Pydantic v2, pydantic-settings |
| Database | SQLModel / SQLAlchemy, Alembic, SQLite (local), PostgreSQL (Neon in production) |
| AI | Google Gemini (free tier) via `google-genai`, behind a swappable interface |
| Logging | structlog: console output locally, JSON lines in production |
| Quality | Pytest, Ruff, Pyright, pre-commit |
| Packaging and hosting | uv, Docker, Render (API), Neon (PostgreSQL) |

## Quick start

```bash
uv sync                              # install dependencies into .venv
uv run alembic upgrade head          # create the database schema (SQLite by default)
uv run uvicorn taskdesk.main:app --reload
```

Open http://127.0.0.1:8000/docs for the interactive API docs.

Settings come from environment variables or a `.env` file. Copy `.env.example` to `.env`
to start.

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| GET | `/` | Welcome message with a link to the docs |
| GET | `/health` | Liveness check |
| POST | `/tasks` | Create a task (`title` required, `status` defaults to `todo`) |
| GET | `/tasks` | List tasks; filter with `?status=done`, page with `?limit=20&offset=0` |
| GET | `/tasks/{id}` | Get one task |
| PATCH | `/tasks/{id}` | Partial update; only the fields you send change |
| DELETE | `/tasks/{id}` | Delete a task |
| POST | `/tasks/{id}/suggest-steps` | AI suggests 3 to 6 steps for the task (not saved) |

Statuses: `todo`, `in_progress`, `done`.

```bash
curl -X POST localhost:8000/tasks -H 'content-type: application/json' \
  -d '{"title": "Write README"}'
curl 'localhost:8000/tasks?status=todo'
curl -X PATCH localhost:8000/tasks/1 -H 'content-type: application/json' \
  -d '{"status": "done"}'
```

## AI step suggestions

`POST /tasks/{id}/suggest-steps` sends the task's title and description to Google Gemini and
returns a short list of concrete steps. The suggestions are returned, never saved.

```bash
export GEMINI_API_KEY=your-key-here      # free key: https://aistudio.google.com/apikey
export AI_MODEL=your-model-id            # optional; defaults to the value in config.py
uv run uvicorn taskdesk.main:app --reload
```

- **No key configured:** the endpoint returns `503`.
- **Provider overloaded or down:** temporary errors (429, 5xx) are retried a few times with a
  short delay, then the API returns `502`. Provider details are logged, never sent to clients.
- **Prompt safety:** the system prompt tells the model to treat task text as data and to
  ignore instructions inside it. The reply is cleaned and capped at 6 steps.
- **Privacy:** the free Gemini tier may use prompts to improve Google products, so do not put
  sensitive information in tasks.
- **Tests** use a fake AI client, so they need no key and make no network calls.

## Using PostgreSQL

Any PostgreSQL connection string works. The app rewrites `postgresql://` to use the installed
`psycopg2` driver and strips stray whitespace, so a string copied from a provider can be used
as it is.

Locally with Docker:

```bash
docker run --name taskdesk-db -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=taskdesk \
  -p 5432:5432 -d postgres:16

export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/taskdesk
uv run alembic upgrade head
```

## Deployment

The live demo runs on Render (Docker, free instance) with a Neon PostgreSQL database.

- The `Dockerfile` installs dependencies with `uv sync --frozen`, then on start runs
  `alembic upgrade head` followed by `uvicorn`, on the port Render provides in `$PORT`.
- Environment variables on the host: `DATABASE_URL`, `LOG_JSON=true`, and optionally
  `GEMINI_API_KEY` and `AI_MODEL`. Leaving `GEMINI_API_KEY` unset turns the AI endpoint off.
- Health check path: `/health`.
- Free instances sleep after about 15 minutes without traffic, which is why the first request
  after a pause is slow.

## Development

```bash
uv run pytest                 # tests use an in-memory SQLite database and a fake AI client
uv run ruff check . && uv run ruff format .
uv run pyright
uv run pre-commit install     # run the checks automatically on every commit
```

Create a new migration after changing `models.py`:

```bash
uv run alembic revision --autogenerate -m "describe the change"
```

## Layout

```
src/taskdesk/
  main.py            app factory, request-logging middleware, /, /health
  routes.py          /tasks endpoints, including AI step suggestions
  models.py          SQLModel tables and request/response schemas
  ai.py              Gemini client behind a StepSuggester interface, retries, reply parsing
  db.py              engine, database URL normalisation, per-request session dependency
  config.py          settings from environment / .env
  logging_config.py  structlog setup
migrations/          Alembic environment and versions
tests/               API, AI and database URL tests (pytest)
Dockerfile           container image used for deployment
```

## Design notes

- Separate schemas for create, update and read (`TaskCreate`, `TaskUpdate`, `TaskRead`), so
  the table model is never exposed directly and clients cannot set `id` or timestamps.
- `PATCH` uses `exclude_unset`, so omitted fields are left alone and `description` can be
  cleared by sending `null`. `title` and `status` reject `null` with a 422.
- The schema is owned by Alembic; the app never calls `create_all` (only the tests do, against
  a throwaway in-memory database).
- The AI route depends on a `StepSuggester` interface, not on Gemini directly. Swapping
  providers means editing only `ai.py`, and tests inject a fake with `dependency_overrides`.
- The model name is a setting, not hard-coded, because hosted model names get retired.
- AI failures never crash the API: they become a logged `502`, and a missing key becomes `503`.

## Ideas for next steps

- Run the AI call as a background job (Celery and Redis) and let clients poll for the result.
- Cache `GET /tasks` in Redis.
- Add users and authentication so each person sees only their own tasks.
- Rate-limit the AI endpoint.
- Add OpenTelemetry tracing.
