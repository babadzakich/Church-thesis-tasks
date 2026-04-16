#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from hakaton.checker import normalize_output

MAX_LOG_CHARS = 2000


def load_config(task_dir: Path) -> dict:
    config_path = task_dir / "task.json"
    if not config_path.exists():
        raise SystemExit(f"Missing task config: {config_path}")
    return json.loads(config_path.read_text())


def compile_source(source: Path, output: Path) -> list[str]:
    suffix = source.suffix
    if suffix == ".cpp":
        cmd = ["g++", "-O2", "-std=c++17", str(source), "-o", str(output)]
    elif suffix == ".c":
        cmd = ["gcc", "-O2", "-std=c11", str(source), "-o", str(output)]
    elif suffix == ".rs":
        cmd = ["rustc", "-O", str(source), "-o", str(output)]
    else:
        raise SystemExit(f"Unsupported source file: {source}")

    print(f"Compiling {source}...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise SystemExit(f"Compilation failed for {source}")
    return cmd

def run_binary(binary: Path, test_input: Path, timeout_sec: int) -> tuple[str, float]:
    try:
        with test_input.open("r", encoding="utf-8") as handle:
            started = time.perf_counter()
            result = subprocess.run(
                [str(binary)],
                stdin=handle,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
            elapsed = time.perf_counter() - started
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Timed out on {test_input.name} after {timeout_sec}s") from None

    if result.returncode != 0:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise RuntimeError(f"Program exited with code {result.returncode} on {test_input.name}")

    return result.stdout, elapsed


def read_expected(
    test_input: Path,
    answer_dir: Path | None,
) -> str:
    if answer_dir is None:
        raise SystemExit("Answer directory is required when expected-mode=answers")
    answer_path = answer_dir / f"{test_input.stem}.ans"
    if not answer_path.exists():
        raise SystemExit(f"Missing answer file: {answer_path}")
    return answer_path.read_text(encoding="utf-8")
    


def fail_mismatch(
    test_name: str,
    reason: str,
) -> list[str]:

    lines = [f"[FAIL] {test_name}", reason]
    print(f"[FAIL] {test_name}")
    print(reason)
    return lines


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-dir", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--tests-dir", required=True)
    parser.add_argument("--answers-dir")
    parser.add_argument("--visibility", choices=["public", "hidden"], default="public")
    parser.add_argument("--group-name")
    parser.add_argument("--test-weight", type=int, default=0)
    parser.add_argument("--json-output")
    parser.add_argument("--timeout-sec", type=int, default=5)
    args = parser.parse_args()

    task_dir = Path(args.task_dir).resolve()
    config = load_config(task_dir)

    source = Path(args.source).resolve()
    tests_dir = Path(args.tests_dir).resolve()
    answer_dir = Path(args.answers_dir).resolve() if args.answers_dir else None

    if not tests_dir.exists():
        raise SystemExit(f"Missing tests directory: {tests_dir}")
    if not source.exists():
        raise SystemExit(f"Missing source file: {source}")

    group_name = args.group_name or tests_dir.name
    json_output = Path(args.json_output).resolve() if args.json_output else None

    with tempfile.TemporaryDirectory(prefix="task-tests-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        submission_binary = temp_dir / "submission"
        compile_source(source, submission_binary)

        test_inputs = sorted(tests_dir.glob("*.in"))
        if not test_inputs:
            raise SystemExit(f"No input tests found in {tests_dir}")

        passed = 0
        failed = 0
        total_time = 0.0
        passed_tests: list[str] = []
        failed_tests: list[str] = []
        for test_input in test_inputs:
            try:
                actual_raw, elapsed = run_binary(submission_binary, test_input, args.timeout_sec)
                expected_raw = read_expected(
                    test_input=test_input,
                    answer_dir=answer_dir
                )
                actual = normalize_output(actual_raw)
                expected = normalize_output(expected_raw)
                total_time += elapsed

                if actual != expected:
                    failed += 1
                    failed_tests.append(test_input.stem)
                    fail_mismatch(
                        test_input.stem,
                        reason="Output does not match expected answer."
                    )
                    continue

                passed += 1
                passed_tests.append(test_input.stem)
                print(f"[PASS] {test_input.stem} ({elapsed:.3f}s)")
            except Exception as exc:
                failed += 1
                failed_tests.append(test_input.stem)
                fail_mismatch(
                    test_input.stem,
                    reason=str(exc),
                    visibility=args.visibility,
                )

        total_tests = len(test_inputs)
        points_total = total_tests * args.test_weight
        points_awarded = passed * args.test_weight

        print(f"Passed {passed}/{total_tests} tests in {total_time:.3f}s")
        print(f"Failed: {failed}")
        if args.test_weight:
            print(f"Points: {points_awarded}/{points_total}")
        if passed_tests:
            print("Passed tests: " + ", ".join(passed_tests))
        if failed_tests:
            print("Failed tests: " + ", ".join(failed_tests))

        if json_output:
            summary = {
                "task": config.get("name", task_dir.name),
                "group_name": group_name,
                "visibility": args.visibility,
                "test_weight": args.test_weight,
                "total_tests": total_tests,
                "passed_tests": passed,
                "failed_tests": failed,
                "points_awarded": points_awarded,
                "points_total": points_total,
                "passed_test_names": passed_tests,
                "failed_test_names": failed_tests,
                "total_time_sec": round(total_time, 3),
                "success": failed == 0,
            }
            json_output.write_text(
                json.dumps(summary, ensure_ascii=True, indent=2) + "\n",
                encoding="utf-8",
            )

        if failed:
            raise SystemExit(1)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
