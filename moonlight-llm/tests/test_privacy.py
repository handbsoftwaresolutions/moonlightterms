#!/usr/bin/env python3
"""Unit tests for privacy / model policy (no network)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.privacy import (  # noqa: E402
    PrivacyError,
    assert_local_base_url,
    assert_local_model,
    is_cloud_model,
    is_loopback_host,
    normalize_model,
    privacy_report,
)


class PrivacyTests(unittest.TestCase):
    def test_loopback_hosts(self) -> None:
        self.assertTrue(is_loopback_host("127.0.0.1"))
        self.assertTrue(is_loopback_host("localhost"))
        self.assertTrue(is_loopback_host("::1"))
        self.assertFalse(is_loopback_host("8.8.8.8"))
        self.assertFalse(is_loopback_host("ollama.com"))

    def test_local_url_ok(self) -> None:
        self.assertEqual(
            assert_local_base_url("http://127.0.0.1:11434"),
            "http://127.0.0.1:11434",
        )

    def test_remote_url_blocked(self) -> None:
        with self.assertRaises(PrivacyError):
            assert_local_base_url("https://ollama.com")
        with self.assertRaises(PrivacyError):
            assert_local_base_url("http://192.168.1.10:11434")

    def test_glm52_cloud_allowed(self) -> None:
        self.assertEqual(assert_local_model("glm-5.2:cloud"), "glm-5.2:cloud")
        self.assertEqual(assert_local_model("glm-5.2"), "glm-5.2:cloud")
        self.assertEqual(normalize_model("GLM 5.2"), "glm-5.2:cloud")
        self.assertTrue(is_cloud_model("glm-5.2:cloud"))

    def test_other_cloud_model_blocked(self) -> None:
        with self.assertRaises(PrivacyError):
            assert_local_model("gemma4:cloud")

    def test_privacy_report_devsec(self) -> None:
        lines = privacy_report("http://127.0.0.1:11434", "glm-5.2:cloud", "/tmp/x")
        blob = "\n".join(lines)
        self.assertIn("DevSec", blob)
        self.assertIn("glm-5.2:cloud", blob)
        self.assertIn("Ollama cloud", blob)


if __name__ == "__main__":
    unittest.main()
