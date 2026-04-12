#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-dir", required=True)
    parser.add_argument("--candidate-root", required=True)
    parser.add_argument("--baseline-root")
    args = parser.parse_args()

    task_dir = Path(args.task_dir).resolve()
    candidate_root = Path(args.candidate_root).resolve()
    baseline_root = Path(args.baseline_root).resolve() if args.baseline_root else None

    config = json.loads((task_dir / "task.json").read_text(encoding="utf-8"))
    candidates = config.get("submission_candidates", [])
    task_name = task_dir.name

    changed = []
    for rel_path in candidates:
        candidate_file = candidate_root / task_name / rel_path
        if not candidate_file.exists():
            continue

        if baseline_root is None:
            changed.append(candidate_file)
            continue

        baseline_file = baseline_root / task_name / rel_path
        if not baseline_file.exists():
            changed.append(candidate_file)
            continue

        if candidate_file.read_bytes() != baseline_file.read_bytes():
            changed.append(candidate_file)

    if len(changed) != 1:
        rel_candidates = ", ".join(candidates)
        raise SystemExit(
            "Expected exactly one changed submission file among: "
            f"{rel_candidates}. Found {len(changed)}."
        )

    print(changed[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
