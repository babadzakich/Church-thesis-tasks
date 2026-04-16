#!/usr/bin/env python3
import argparse
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path


def load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_team_hash(path: str) -> str:
    team_hash = Path(path).read_text(encoding="utf-8").strip()
    if not team_hash:
        raise SystemExit(f"Team hash file is empty: {path}")
    return team_hash


def normalize_api_base_url(raw_url: str) -> str:
    url = raw_url.strip()
    if not url:
        raise SystemExit("PIPELINE_API_BASE_URL is empty")

    parsed = urllib.parse.urlparse(url)
    if not parsed.scheme:
        url = "https://" + url
        parsed = urllib.parse.urlparse(url)

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SystemExit(
            "Invalid PIPELINE_API_BASE_URL. Use a full host like "
            "'https://example.com' or 'http://example.com'."
        )

    return url.rstrip("/")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-config", required=True)
    parser.add_argument("--score-json", required=True)
    parser.add_argument("--team-name", required=True)
    parser.add_argument("--team-hash-file", required=True)
    parser.add_argument("--api-base-url", required=True)
    parser.add_argument("--token-env", default="PIPELINE_TOKEN")
    args = parser.parse_args()

    task_config = load_json(args.task_config)
    score = load_json(args.score_json)

    token = os.environ.get(args.token_env)
    if not token:
        raise SystemExit(f"Missing environment variable: {args.token_env}")

    pipeline_task_id = task_config.get("pipeline_task_id")
    if pipeline_task_id is None:
        raise SystemExit("Missing 'pipeline_task_id' in task config")

    team_hash = read_team_hash(args.team_hash_file)
    score_value = score["normalized_score"]

    base_url = normalize_api_base_url(args.api_base_url)

    query = urllib.parse.urlencode(
        {
            "team": team_hash,
            "task": pipeline_task_id,
            "score": score_value,
            "token": token,
        }
    )

    url = base_url + "/api/pipeline?" + query
    request = urllib.request.Request(url, method="GET")

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8", errors="replace")
            print(f"Pipeline API status: {response.status}")
            print(body[:1000] or "<empty>")
    except Exception as exc:
        raise SystemExit(f"Failed to publish pipeline score: {exc}") from exc

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
