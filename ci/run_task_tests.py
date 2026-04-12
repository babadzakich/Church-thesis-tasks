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

from hakaton.checker import normalize_output, parse_test_file, validate_output


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

    if result.returncode != 0:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise SystemExit(f"Program exited with code {result.returncode} on {test_input.name}")

    return result.stdout, elapsed


def read_expected(
    test_input: Path,
    expected_mode: str,
    answer_dir: Path | None,
    reference_binary: Path | None,
    timeout_sec: int,
) -> str:
    if expected_mode == "answers":
        if answer_dir is None:
            raise SystemExit("Answer directory is required when expected-mode=answers")
        answer_path = answer_dir / f"{test_input.stem}.ans"
        if not answer_path.exists():
            raise SystemExit(f"Missing answer file: {answer_path}")
        return answer_path.read_text(encoding="utf-8")

    if reference_binary is None:
        raise SystemExit("Reference binary is required when expected-mode=reference")
    output, _ = run_binary(reference_binary, test_input, timeout_sec)
    return output


def fail_mismatch(
    test_name: str,
    reason: str,
    visibility: str,
    expected: str | None = None,
    actual: str | None = None,
) -> None:
    print(f"[FAIL] {test_name}")
    print(reason)
    if visibility == "public":
        if expected is not None:
            print("Expected:")
            print(expected or "<empty>")
        if actual is not None:
            print("Actual:")
            print(actual or "<empty>")
    raise SystemExit(1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-dir", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--tests-subdir")
    parser.add_argument("--tests-dir")
    parser.add_argument("--expected-mode", choices=["answers", "reference"], required=True)
    parser.add_argument("--answer-subdir")
    parser.add_argument("--answers-dir")
    parser.add_argument("--reference-source")
    parser.add_argument("--visibility", choices=["public", "hidden"], default="public")
    parser.add_argument("--timeout-sec", type=int, default=5)
    args = parser.parse_args()

    task_dir = Path(args.task_dir).resolve()
    load_config(task_dir)

    source = Path(args.source).resolve()
    if not args.tests_subdir and not args.tests_dir:
        raise SystemExit("Either --tests-subdir or --tests-dir is required")
    if args.tests_subdir and args.tests_dir:
        raise SystemExit("Use only one of --tests-subdir or --tests-dir")

    if args.answer_subdir and args.answers_dir:
        raise SystemExit("Use only one of --answer-subdir or --answers-dir")

    tests_dir = (
        Path(args.tests_dir).resolve()
        if args.tests_dir
        else (task_dir / args.tests_subdir).resolve()
    )
    answer_dir = (
        Path(args.answers_dir).resolve()
        if args.answers_dir
        else (task_dir / args.answer_subdir).resolve() if args.answer_subdir else None
    )
    reference_source = Path(args.reference_source).resolve() if args.reference_source else None

    if not tests_dir.exists():
        raise SystemExit(f"Missing tests directory: {tests_dir}")
    if not source.exists():
        raise SystemExit(f"Missing source file: {source}")

    with tempfile.TemporaryDirectory(prefix="task-tests-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        submission_binary = temp_dir / "submission"
        compile_source(source, submission_binary)

        reference_binary = None
        if args.expected_mode == "reference":
            if reference_source is None or not reference_source.exists():
                raise SystemExit("Valid --reference-source is required for expected-mode=reference")
            reference_binary = temp_dir / "reference"
            compile_source(reference_source, reference_binary)

        test_inputs = sorted(tests_dir.glob("*.in"))
        if not test_inputs:
            raise SystemExit(f"No input tests found in {tests_dir}")

        passed = 0
        total_time = 0.0
        for test_input in test_inputs:
            actual_raw, elapsed = run_binary(submission_binary, test_input, args.timeout_sec)
            expected_raw = read_expected(
                test_input=test_input,
                expected_mode=args.expected_mode,
                answer_dir=answer_dir,
                reference_binary=reference_binary,
                timeout_sec=args.timeout_sec,
            )

            n, constraints = parse_test_file(test_input)
            actual = normalize_output(actual_raw)
            expected = normalize_output(expected_raw)
            total_time += elapsed

            expected_is_impossible = normalize_output(expected_raw) == "IMPOSSIBLE"
            ok, reason = validate_output(actual_raw, n, constraints, expected_is_impossible)
            if not ok:
                fail_mismatch(
                    test_input.stem,
                    reason=reason,
                    visibility=args.visibility,
                    expected=expected,
                    actual=actual,
                )

            passed += 1
            print(f"[PASS] {test_input.stem} ({elapsed:.3f}s)")

        print(f"Passed {passed}/{len(test_inputs)} tests in {total_time:.3f}s")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
