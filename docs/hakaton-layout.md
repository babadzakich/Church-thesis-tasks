# Hakaton Repo Layout

## Public repository

The public repository contains only:

- `hakaton/task.json`
- `hakaton/checker.py`
- `hakaton/tests/simple/` with a small public test set
- `hakaton/teams/example/` with starter files
- `hakaton/teams/<team-name>/` folders created by participants
- CI scripts and workflow files

Participants should not edit `hakaton/teams/example/`.
Each team creates its own folder inside `hakaton/teams/` and places exactly one solution file there:

- `solution.c`
- `solution.cpp`
- `solution.rs`
- `team.hash`

## Private repository

The private repository is the source of truth for the full test set.
It contains:

- the public tests in `hakaton/tests/simple/`
- the canonical reference solution used by hidden CI
- all hidden tests in `hakaton/tests/` with names matching `H*.in`

## CI model

- A single trusted workflow runs on `pull_request_target`
- It checks out the private repository and recomputes both public and hidden results from it
- Public tests are still visible in the public repository for participants, but the trusted workflow treats the private repository as the scoring source of truth
- The workflow uses the reference solution from the private repository, not from the public one
- This avoids relying on secrets in a regular `pull_request` workflow, because GitHub does not expose secrets to untrusted fork PRs

## Scoring behavior

`ci/run_task_tests.py` runs all tests in the selected directory, compares output with the canonical expected answer, and prints a final summary:

- `Passed X/Y tests`
- `Failed: Z`
- `Points: A/B`

The command exits with a non-zero code if at least one test fails.

The CI uses the task author's model from `gen.py`:

- public tests are checked against committed `.ans` files
- in the trusted hidden workflow, the public tests are taken from the private repository copy at `hakaton/tests/simple/`
- hidden tests are checked against the exact output of the private reference solution
- hidden CI selects only `H*.in` from the private `tests/` directory

`hakaton/task.json` stores the scoring model:

- public tests have weight `5`
- hidden tests have weight `10`
- the final report is normalized to `100`

The hidden workflow recomputes both groups in a trusted context and posts a final PR comment with:

- final score out of `100`
- raw points
- total passed tests
- names of passed and failed tests in each group

## Pipeline API

After the hidden workflow builds the final score, it sends:

- `team=<hash>`
- `task=<pipeline_task_id>`
- `score=<normalized_score>`
- `token=<secret token>`

to:

- `GET /api/pipeline`

Required secrets in GitHub Actions:

- `PIPELINE_API_BASE_URL`
- `PIPELINE_TOKEN`

`PIPELINE_API_BASE_URL` should be a host with scheme, for example:

- `https://example.com`
- `http://example.com`

The workflow resolves the team name and team hash from the submission path:

- `hakaton/teams/<team-name>/solution.*`
- `hakaton/teams/<team-name>/team.hash`
