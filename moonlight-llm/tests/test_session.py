#!/usr/bin/env python3
"""Session store tests."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.session import SessionStore  # noqa: E402


class SessionTests(unittest.TestCase):
    def test_save_load_clear(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SessionStore(Path(tmp))
            self.assertEqual(store.load(), [])
            msgs = [
                {"role": "user", "content": "hi"},
                {"role": "assistant", "content": "hello"},
            ]
            store.save(msgs, "llama3.2:3b")
            loaded = store.load()
            self.assertEqual(loaded, msgs)
            archived = store.archive()
            self.assertIsNotNone(archived)
            self.assertTrue(archived.exists())
            self.assertEqual(store.load(), [])


if __name__ == "__main__":
    unittest.main()
