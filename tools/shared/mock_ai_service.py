#!/usr/bin/env python3
"""Shared mock AI service used by local tooling workflows.

This module provides one deterministic summarization implementation so tools that
need AI-like behavior can rely on a single contract without external API calls.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MockAICompletion:
    """Deterministic completion payload emitted by the mock AI service."""

    summary: str
    model: str
    is_mock: bool


class MockAIService:
    """Deterministic mock AI service used for local tooling workflows."""

    def __init__(self, model: str = "mock-ai-v1") -> None:
        self._model = model

    @property
    def model(self) -> str:
        """Return the mock model identifier for reporting/debugging."""
        return self._model

    def complete_summary(
        self,
        *,
        title: str,
        source_text: str,
        max_sentences: int = 2,
    ) -> MockAICompletion:
        """Generate a deterministic summary from source text and title fallback."""
        normalized_title = _normalize_whitespace(title) or "Untitled Article"
        normalized_source = _normalize_whitespace(source_text)

        if normalized_source and max_sentences > 0:
            sentence_candidates = [
                sentence.strip() for sentence in normalized_source.split(".") if sentence.strip()
            ]
            selected = sentence_candidates[:max_sentences]
            if selected:
                return MockAICompletion(
                    summary=". ".join(selected) + ".",
                    model=self._model,
                    is_mock=True,
                )

        return MockAICompletion(
            summary=f"{normalized_title}.",
            model=self._model,
            is_mock=True,
        )


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


_SHARED_MOCK_AI_SERVICE = MockAIService()


def get_shared_mock_ai_service() -> MockAIService:
    """Return the singleton mock AI service instance shared by tool modules."""
    return _SHARED_MOCK_AI_SERVICE
