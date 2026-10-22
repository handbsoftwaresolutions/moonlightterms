#!/usr/bin/env python3
"""Mock HTTP server tests for OllamaClient."""

from __future__ import annotations

import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.ollama_client import OllamaClient, OllamaError  # noqa: E402
from lib.privacy import PrivacyError  # noqa: E402


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/tags":
            body = json.dumps(
                {"models": [{"name": "llama3.2:3b"}, {"name": "llama3.2:1b"}]}
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        payload = json.loads(raw.decode() or "{}")
        if self.path == "/api/chat":
            # NDJSON stream
            chunks = [
                {"message": {"role": "assistant", "content": "Hello"}, "done": False},
                {"message": {"role": "assistant", "content": " world"}, "done": True},
            ]
            body = "\n".join(json.dumps(c) for c in chunks).encode() + b"\n"
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/api/pull":
            events = [
                {"status": "pulling manifest"},
                {"status": "success"},
            ]
            body = "\n".join(json.dumps(e) for e in events).encode() + b"\n"
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()


class OllamaClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = HTTPServer(("127.0.0.1", 0), _Handler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()

    def test_list_and_chat(self) -> None:
        client = OllamaClient(host="127.0.0.1", port=self.port)
        self.assertTrue(client.ping())
        models = client.list_models()
        self.assertIn("llama3.2:3b", models)
        self.assertTrue(client.has_model("llama3.2:3b"))
        self.assertTrue(client.has_model("llama3.2:1b"))
        self.assertFalse(client.has_model("llama3.2:70b"))
        text = client.chat(
            "llama3.2:3b",
            [{"role": "user", "content": "hi"}],
        )
        self.assertEqual(text, "Hello world")
        statuses = list(client.pull("llama3.2:1b"))
        self.assertTrue(any("success" in s or "manifest" in s for s in statuses))

    def test_rejects_cloud_model(self) -> None:
        client = OllamaClient(host="127.0.0.1", port=self.port)
        with self.assertRaises(PrivacyError):
            list(client.chat_stream("gemma:cloud", [{"role": "user", "content": "x"}]))


if __name__ == "__main__":
    unittest.main()
