from __future__ import annotations

from pathlib import Path


Constraint = tuple[str, tuple[int, ...]]


def normalize_output(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    return "\n".join(lines).strip()


def parse_test_file(test_input: str | Path) -> tuple[int, list[Constraint]]:
    path = Path(test_input)
    lines = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not lines:
        raise ValueError(f"Empty test input: {path}")

    n, _ = map(int, lines[0].split())
    constraints: list[Constraint] = []
    for line in lines[1:]:
        parts = line.split()
        kind = parts[0]
        if kind == "DEP":
            constraints.append((kind, (int(parts[1]) - 1, int(parts[2]) - 1)))
        elif kind == "CONFLICT":
            constraints.append((kind, (int(parts[1]) - 1, int(parts[2]) - 1)))
        elif kind == "REQUIRE":
            constraints.append((kind, (int(parts[1]) - 1,)))
        else:
            raise ValueError(f"Unknown constraint {kind} in {path}")
    return n, constraints


def parse_program_output(output: str, n: int) -> str | list[bool]:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if len(lines) == 1 and lines[0] == "IMPOSSIBLE":
        return "IMPOSSIBLE"

    if len(lines) != n:
        raise ValueError(f"Expected {n} output lines, got {len(lines)}")

    assignment = [False] * n
    seen = set()
    for line in lines:
        if ":" not in line:
            raise ValueError(f"Malformed output line: {line}")
        left, right = [part.strip() for part in line.split(":", 1)]
        idx = int(left) - 1
        if idx < 0 or idx >= n:
            raise ValueError(f"Service index out of range: {left}")
        if idx in seen:
            raise ValueError(f"Duplicate service assignment: {left}")
        if right not in {"ON", "OFF"}:
            raise ValueError(f"Malformed state in line: {line}")
        assignment[idx] = right == "ON"
        seen.add(idx)

    return assignment


def assignment_satisfies(
    assignment: list[bool],
    constraints: list[Constraint],
) -> tuple[bool, str]:
    for kind, args in constraints:
        if kind == "DEP":
            a, b = args
            if assignment[a] and not assignment[b]:
                return False, f"DEP {a + 1} {b + 1} violated"
        elif kind == "CONFLICT":
            a, b = args
            if assignment[a] and assignment[b]:
                return False, f"CONFLICT {a + 1} {b + 1} violated"
        elif kind == "REQUIRE":
            (a,) = args
            if not assignment[a]:
                return False, f"REQUIRE {a + 1} violated"
    return True, ""


def validate_output(
    output: str,
    n: int,
    constraints: list[Constraint],
    expected_impossible: bool,
) -> tuple[bool, str]:
    try:
        parsed = parse_program_output(output, n)
    except ValueError as exc:
        return False, str(exc)

    if expected_impossible:
        if parsed == "IMPOSSIBLE":
            return True, ""
        return False, "Expected IMPOSSIBLE, but submission produced an assignment."

    if parsed == "IMPOSSIBLE":
        return False, "A valid assignment exists, but submission reported IMPOSSIBLE."

    return assignment_satisfies(parsed, constraints)
