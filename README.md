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
