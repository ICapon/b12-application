import hashlib
import hmac
import json
import os
import sys
from datetime import datetime, timezone

import requests

URL = "https://b12.io/apply/submission"


def iso_now() -> str:
    """UTC timestamp, ISO 8601 with milliseconds and a trailing Z."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def build_body(payload: dict) -> bytes:
    """Canonical JSON bytes: sorted keys, compact separators, UTF-8."""
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def sign(body: bytes, secret: bytes) -> str:
    return "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()


def build_payload(env=os.environ) -> dict:
    server = env["GITHUB_SERVER_URL"]
    repo = env["GITHUB_REPOSITORY"]
    run_id = env["GITHUB_RUN_ID"]
    repository_link = f"{server}/{repo}"
    return {
        "timestamp": iso_now(),
        "name": env["APPLICANT_NAME"],
        "email": env["APPLICANT_EMAIL"],
        "resume_link": env["RESUME_LINK"],
        "repository_link": repository_link,
        "action_run_link": f"{repository_link}/actions/runs/{run_id}",
    }


def main() -> int:
    body = build_body(build_payload())
    print('Body', body)
    response = requests.post(
        URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Signature-256": sign(body, os.environ["SIGNING_KEY"].encode("utf-8")),
        },
        timeout=30,
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    response.raise_for_status()
    data = response.json()
    if data.get("success"):
        print(f"RECEIPT: {data['receipt']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
