# b12-application

Submits a job application to B12 through a signed POST request, run from a GitHub Action.

## How it works

`submit.py`:

1. Reads its configuration from environment variables (`APPLICANT_NAME`, `APPLICANT_EMAIL`, `RESUME_LINK`, `SUBMISSION_URL`, `SIGNING_KEY`) and the GitHub run metadata (`GITHUB_SERVER_URL`, `GITHUB_REPOSITORY`, `GITHUB_RUN_ID`).
2. Builds a payload with six fields: `timestamp` (ISO 8601 UTC with milliseconds and a trailing `Z`), `name`, `email`, `resume_link`, `repository_link` and `action_run_link`.
3. Serializes the payload to canonical JSON (sorted keys, no whitespace, unescaped UTF-8). The exact same bytes are signed and sent.
4. Signs the body with HMAC-SHA256 and sends the result in the `X-Signature-256: sha256=<hexdigest>` header.
5. Sends the POST with `Content-Type: application/json`, prints the status and response, and prints `RECEIPT: <receipt>` on success. If the server returns an error, the script fails.

Main functions: `iso_now`, `build_body`, `sign`, `build_payload` and `main`.

## Repository setup

In Settings → Secrets and variables → Actions:

| Type | Name |
|---|---|
| Variable | `SUBMISSION_URL` |
| Variable | `APPLICANT_NAME` |
| Variable | `RESUME_LINK` |
| Secret | `APPLICANT_EMAIL` |
| Secret | `SIGNING_KEY` |

## Running

Trigger the `B12 application` workflow manually from the Actions tab (`workflow_dispatch`). It runs `uv sync --locked` and `uv run python submit.py`.

## Management API (backend)

FastAPI + SQLAlchemy (SQLite by default, override with `DATABASE_URL`).

```
uv run uvicorn app.main:app --reload   # docs at http://localhost:8000/docs
uv run pytest
```

Field names (`name`, `email`, `timestamp`, `resume_link`, `repository_link`, `action_run_link`) are the same in `submit.py`, the API and the database.

### Database migrations

Schema changes go through Alembic (`migrations/`). The app runs `upgrade head` at startup; a database created before migrations existed is detected and stamped at the baseline first, so existing data is kept.

```
uv run alembic revision --autogenerate -m "describe change"   # then review the generated file
uv run alembic upgrade head                                    # apply manually (uses DATABASE_URL)
```

### Signatures

If a request carries `X-Signature-256`, it must equal `sha256=HMAC-SHA256(SIGNING_KEY, raw body)` (else 401; 500 if the server has no `SIGNING_KEY`). Unsigned requests are accepted so the browser frontend works; set `REQUIRE_SIGNATURE=1` to reject them.

### Running `submit.py` against this API

```
SIGNING_KEY=dev-key uv run uvicorn app.main:app &
SUBMISSION_URL=http://127.0.0.1:8000/applications SIGNING_KEY=dev-key \
APPLICANT_NAME="Ada" APPLICANT_EMAIL=ada@example.com RESUME_LINK=https://example.com/cv \
GITHUB_SERVER_URL=https://github.com GITHUB_REPOSITORY=me/repo GITHUB_RUN_ID=1 \
uv run python submit.py
```

A GitHub-hosted runner cannot reach localhost, so the Action needs a deployed API URL in the `SUBMISSION_URL` variable. Keep it pointing at B12 for the real submission.

| Method | Path | Description |
|---|---|---|
| POST | `/applications` | Store an application using the `submit.py` payload (`name`, `email`, optional `timestamp`, `resume_link`, `repository_link`, `action_run_link`; unknown fields are rejected); generates the receipt, starts in `New` and returns `success: true` |
| GET | `/applications` | Paginated list (`page`, `page_size`) filtered by `submitted_from`, `submitted_to` (inclusive dates), `email`, `receipt` |
| GET | `/applications/{id}` | Full details and current stage |
| PUT | `/applications/{id}/stage` | `{"stage": "..."}`; 409 if not a forward move |
| POST | `/applications/{id}/notes` | `{"content": "..."}`; attached to the current stage |
| GET | `/applications/{id}/history` | Stages passed through, entry dates and notes |

Stage rules: `New → Phone screen scheduled → Interview scheduled → Hired`; skipping ahead is allowed, `Rejected` is reachable from any non-final stage, and `Hired`/`Rejected` are final.

## Frontend

A dependency-free page in `frontend/` (plain HTML/CSS/JS, no build step). Start API and frontend together:

```
./run.sh        # API on :8000, frontend on :5173 (override with API_PORT / WEB_PORT); Ctrl+C stops both
```

Open http://localhost:5173/?api=http://127.0.0.1:8000. It has a create form, the filterable and paginated list, and a detail view with stage change, notes and history. An **API log** panel at the bottom shows every request and response, so you can check what each endpoint returns (including the 409/422 errors). The API allows the frontend origin through CORS; set `CORS_ORIGINS` (comma-separated) to change it.
