#!/usr/bin/env python3
"""Unit tests for privacy enforcement (no network)."""

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
    is_loopback_host,
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
        self.assertEqual(
            assert_local_base_url("http://localhost:11434/"),
            "http://localhost:11434",
        )

    def test_remote_url_blocked(self) -> None:
        with self.assertRaises(PrivacyError):
            assert_local_base_url("https://ollama.com")
        with self.assertRaises(PrivacyError):
            assert_local_base_url("http://api.openai.com/v1")
        with self.assertRaises(PrivacyError):
            assert_local_base_url("http://192.168.1.10:11434")

    def test_cloud_model_blocked(self) -> None:
        with self.assertRaises(PrivacyError):
            assert_local_model("gemma4:cloud")
        self.assertEqual(assert_local_model("llama3.2:3b"), "llama3.2:3b")

    def test_privacy_report(self) -> None:
        lines = privacy_report("http://127.0.0.1:11434", "llama3.2:3b", "/tmp/x")
        self.assertTrue(any("Privacy mode: ON" in line for line in lines))
        self.assertTrue(any("No API keys" in line for line in lines))


if __name__ == "__main__":
    unittest.main()
