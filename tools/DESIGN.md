# Tools Design Document

## Overview
The `tools` directory centralizes project-side utilities that support asset workflows,
local validation, and repetitive developer operations.

This document defines the baseline design for tool artifacts, with explicit guidance
for Python and shell-based utilities.

## Goals
- Keep automation scripts discoverable and safe to run locally.
- Standardize script interfaces and expected inputs/outputs.
- Make maintenance easier by documenting behavior and ownership.
- Provide a stable foundation for future tooling additions.

## Non-Goals
- Replacing application runtime logic in `src/`.
- Introducing production infrastructure automation.
- Managing CI/CD workflows from this directory.

## Directory Scope
- `tools/README.md`: Human-facing summary of purpose and contents.
- `tools/DESIGN.md`: This design and implementation contract.
- Future files may include helper scripts, templates, or small config files.

## Design Principles
- Prefer deterministic scripts over interactive prompts.
- Fail fast with clear error messages and non-zero exit codes.
- Keep dependencies minimal and use project-standard tooling first.
- Document usage directly in each script header.
- Keep scripts idempotent whenever practical.

## Script Categories
### Python Scripts
Python scripts are intended for data processing and file transformation tasks,
including sprite metadata shaping and asset pipeline helpers.

#### Expected Characteristics
- Shebang for explicit interpreter (`#!/usr/bin/env python3`).
- Compatible with the project's supported Python 3 environment.
- Structured entrypoint (`main()`) with argument parsing.
- Predictable exit status:
  - `0` for success.
  - non-zero for validation or runtime failures.
- Clear stderr messaging for actionable troubleshooting.

#### Input/Output Model
- Inputs should be explicit CLI arguments (paths, flags, mode switches).
- Outputs should be deterministic files or console summaries.
- Existing files should be overwritten only when behavior is documented.

#### Logging and Errors
- Use concise logs suitable for local and automated runs.
- Avoid stack traces for known user errors; show friendly guidance.
- Reserve exceptions for truly unexpected failures.

### Shell Scripts
Shell scripts are intended for orchestration tasks that compose existing tools
(e.g., invoking npm scripts, file checks, or chained validations).

#### Expected Characteristics
- POSIX-compatible shell where practical (`#!/usr/bin/env sh` or `bash` when needed).
- Start with strict flags when using bash (`set -euo pipefail`).
- Use quoted variables and robust path handling.
- Exit non-zero on failed command preconditions.

#### Input/Output Model
- Accept parameters instead of editing script internals.
- Echo major steps so users can follow progress.
- Keep output concise and machine-readable where possible.

#### Safety Rules
- No destructive operations without explicit opt-in flag.
- Validate required files/directories before mutation.
- Avoid global system changes and external credential access.

## Naming and Layout Conventions
- Python: `tools/*.py` with verb-driven names (e.g., `generate_*.py`).
- Shell: `tools/*.sh` with action-oriented names (e.g., `check_*.sh`).
- Shared assets/config: `tools/<name>.json|yaml|txt` only when needed.

## Execution and Validation
- Scripts should be runnable from repository root.
- Example validation sequence:
  1. Run script with sample arguments.
  2. Verify expected files or output text.
  3. Run `npx tsc --noEmit` to ensure project integrity.

## Extensibility
When adding a new tool:
1. Add usage docs at the top of the script.
2. Reference the script in `tools/README.md`.
3. Record assumptions, dependencies, and side effects.
4. Add or update tests/check commands if available.

## Open Follow-Ups
- Define script-level test harnesses for `tools` workflows.
- Decide whether shared utility modules should live under `tools/lib`.
- Add linting/formatting conventions for shell and Python scripts.
