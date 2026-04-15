#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def format_group(summary: dict) -> list[str]:
    lines = []
    label = summary["group_name"]
    lines.append(
        f"- {label}: {summary['passed_tests']}/{summary['total_tests']} tests, "
        f"{summary['points_awarded']}/{summary['points_total']} points"
    )
    if summary["passed_test_names"]:
        lines.append(f"  Passed: {', '.join(summary['passed_test_names'])}")
    if summary["failed_test_names"]:
        lines.append(f"  Failed: {', '.join(summary['failed_test_names'])}")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-config", required=True)
    parser.add_argument("--public-summary", required=True)
    parser.add_argument("--hidden-summary", required=True)
    parser.add_argument("--markdown-output", required=True)
    parser.add_argument("--json-output")
    args = parser.parse_args()

    task_config = load(args.task_config)
    public = load(args.public_summary)
    hidden = load(args.hidden_summary)

    final_score_max = task_config.get("scoring", {}).get("final_score_max", 100)
    raw_points_awarded = public["points_awarded"] + hidden["points_awarded"]
    raw_points_total = public["points_total"] + hidden["points_total"]

    if raw_points_total > 0:
        normalized_score = round(raw_points_awarded * final_score_max / raw_points_total)
    else:
        normalized_score = 0

    total_passed = public["passed_tests"] + hidden["passed_tests"]
    total_tests = public["total_tests"] + hidden["total_tests"]
    success = public["success"] and hidden["success"]

    lines = [
        "## Hakaton Score",
        "",
        f"Score: **{normalized_score}/{final_score_max}**",
        f"Raw points: **{raw_points_awarded}/{raw_points_total}**",
        f"Tests passed: **{total_passed}/{total_tests}**",
        "",
        "Breakdown:",
        *format_group(public),
        *format_group(hidden),
    ]

    Path(args.markdown_output).write_text("\n".join(lines) + "\n", encoding="utf-8")

    if args.json_output:
        payload = {
            "success": success,
            "final_score_max": final_score_max,
            "normalized_score": normalized_score,
            "raw_points_awarded": raw_points_awarded,
            "raw_points_total": raw_points_total,
            "total_passed": total_passed,
            "total_tests": total_tests,
            "public": public,
            "hidden": hidden,
        }
        Path(args.json_output).write_text(
            json.dumps(payload, ensure_ascii=True, indent=2) + "\n",
            encoding="utf-8",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
