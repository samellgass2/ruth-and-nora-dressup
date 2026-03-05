#!/usr/bin/env python3
"""Validate Workflow 6 QA evidence for research-story coverage."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

INVALID_JSON_EXIT_CODE = 2
VALIDATION_FAILED_EXIT_CODE = 3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate LLM-crawling/OpenClaw QA evidence for Workflow 6."
    )
    parser.add_argument(
        "--evidence",
        default="research/workflow-6-qa-evidence.json",
        help="Path to QA evidence JSON",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    return parser.parse_args()


def load_payload(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"Evidence file not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Evidence JSON parse error: {error}") from error
    if not isinstance(raw, dict):
        raise ValueError("Evidence root must be a JSON object")
    return raw


def require_object(parent: dict[str, Any], key: str, errors: list[str]) -> dict[str, Any]:
    value = parent.get(key)
    if isinstance(value, dict):
        return value
    errors.append(f"Missing or invalid object: {key}")
    return {}


def require_list(parent: dict[str, Any], key: str, errors: list[str]) -> list[Any]:
    value = parent.get(key)
    if isinstance(value, list):
        return value
    errors.append(f"Missing or invalid list: {key}")
    return []


def source_ids_from_list(sources: list[Any], errors: list[str], label: str) -> set[str]:
    found_ids: set[str] = set()
    for idx, source in enumerate(sources):
        if not isinstance(source, dict):
            errors.append(f"{label}[{idx}] must be an object")
            continue
        source_id = source.get("id")
        if not isinstance(source_id, str) or not source_id.strip():
            errors.append(f"{label}[{idx}] missing non-empty id")
            continue
        found_ids.add(source_id)
    return found_ids


def validate_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if payload.get("task_id") != 66:
        errors.append("task_id must be 66")
    if payload.get("run_id") != 143:
        errors.append("run_id must be 143")

    workflow = payload.get("workflow")
    if workflow != "Research Agent for AI Stories":
        errors.append("workflow must be 'Research Agent for AI Stories'")

    llm_crawling = require_object(payload, "llm_crawling", errors)
    openclaw_coverage = require_object(payload, "openclaw_coverage", errors)
    qa_answers = require_list(payload, "qa_answers", errors)

    if llm_crawling.get("implemented") is not True:
        errors.append("llm_crawling.implemented must be true")
    llm_sources = require_list(llm_crawling, "evidence_sources", errors)
    llm_source_ids = source_ids_from_list(llm_sources, errors, "llm_crawling.evidence_sources")

    crawl_like_url_present = any(
        isinstance(source, dict)
        and isinstance(source.get("url"), str)
        and "crawl" in source["url"].lower()
        for source in llm_sources
    )
    if not crawl_like_url_present:
        errors.append("llm_crawling.evidence_sources must include at least one crawl-related URL")

    if openclaw_coverage.get("included") is not True:
        errors.append("openclaw_coverage.included must be true")
    openclaw_sources = require_list(openclaw_coverage, "sources", errors)
    openclaw_source_ids = source_ids_from_list(openclaw_sources, errors, "openclaw_coverage.sources")

    openclaw_url_present = any(
        isinstance(source, dict)
        and isinstance(source.get("url"), str)
        and "openclaw" in source["url"].lower()
        for source in openclaw_sources
    )
    if not openclaw_url_present:
        errors.append("openclaw_coverage.sources must include an OpenClaw URL")

    all_source_ids = llm_source_ids.union(openclaw_source_ids)
    if len(qa_answers) < 2:
        errors.append("qa_answers must contain at least two answers")

    llm_question_seen = False
    openclaw_question_seen = False
    for idx, answer in enumerate(qa_answers):
        if not isinstance(answer, dict):
            errors.append(f"qa_answers[{idx}] must be an object")
            continue

        question = answer.get("question")
        text_answer = answer.get("answer")
        evidence_ref_ids = answer.get("evidence_ref_ids")

        if not isinstance(question, str) or not question.strip():
            errors.append(f"qa_answers[{idx}].question must be a non-empty string")
        if not isinstance(text_answer, str) or not text_answer.strip():
            errors.append(f"qa_answers[{idx}].answer must be a non-empty string")
        if not isinstance(evidence_ref_ids, list) or not evidence_ref_ids:
            errors.append(f"qa_answers[{idx}].evidence_ref_ids must be a non-empty list")
            continue

        for ref_idx, ref in enumerate(evidence_ref_ids):
            if not isinstance(ref, str) or not ref.strip():
                errors.append(f"qa_answers[{idx}].evidence_ref_ids[{ref_idx}] must be a non-empty string")
                continue
            if ref not in all_source_ids:
                errors.append(f"qa_answers[{idx}] references unknown evidence id '{ref}'")

        lower_question = question.lower() if isinstance(question, str) else ""
        if "llm" in lower_question and "crawl" in lower_question:
            llm_question_seen = True
        if "openclaw" in lower_question:
            openclaw_question_seen = True

    if not llm_question_seen:
        errors.append("qa_answers must include an LLM-crawling question")
    if not openclaw_question_seen:
        errors.append("qa_answers must include an OpenClaw question")

    return errors


def emit_result(errors: list[str], as_json: bool) -> int:
    if as_json:
        result = {"status": "pass" if not errors else "fail", "errors": errors}
        print(json.dumps(result, indent=2))
    elif errors:
        print("QA evidence validation FAILED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
    else:
        print("QA evidence validation PASSED")
    return 0 if not errors else VALIDATION_FAILED_EXIT_CODE


def main() -> int:
    args = parse_args()
    evidence_path = Path(args.evidence)

    try:
        payload = load_payload(evidence_path)
    except ValueError as error:
        message = str(error)
        if args.json:
            print(json.dumps({"status": "fail", "errors": [message]}, indent=2))
        else:
            print(message, file=sys.stderr)
        return INVALID_JSON_EXIT_CODE

    validation_errors = validate_payload(payload)
    return emit_result(validation_errors, args.json)


if __name__ == "__main__":
    raise SystemExit(main())
