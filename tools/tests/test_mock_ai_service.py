#!/usr/bin/env python3
"""Unit tests for shared mock AI service implementation."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.shared.mock_ai_service import (
    MockAIService,
    get_shared_mock_ai_service,
)


class MockAIServiceTests(unittest.TestCase):
    def test_complete_summary_returns_deterministic_sentences(self) -> None:
        service = MockAIService()

        completion = service.complete_summary(
            title="Unused title",
            source_text="Sentence one. Sentence two. Sentence three.",
            max_sentences=2,
        )

        self.assertEqual(completion.summary, "Sentence one. Sentence two.")
        self.assertEqual(completion.model, "mock-ai-v1")
        self.assertTrue(completion.is_mock)

    def test_complete_summary_uses_title_fallback_when_source_empty(self) -> None:
        service = MockAIService(model="mock-ai-custom")

        completion = service.complete_summary(
            title="Fallback title",
            source_text="",
            max_sentences=2,
        )

        self.assertEqual(completion.summary, "Fallback title.")
        self.assertEqual(completion.model, "mock-ai-custom")
        self.assertTrue(completion.is_mock)

    def test_shared_service_returns_singleton_instance(self) -> None:
        instance_one = get_shared_mock_ai_service()
        instance_two = get_shared_mock_ai_service()

        self.assertIs(instance_one, instance_two)


if __name__ == "__main__":
    unittest.main()
