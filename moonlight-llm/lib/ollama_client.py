"""Minimal localhost Ollama client (stdlib only)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Iterator
from typing import Any

from .privacy import PrivacyError, assert_local_base_url, assert_local_model


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 11434) -> None:
        self.base_url = assert_local_base_url(f"http://{host}:{port}")

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        timeout: float = 120.0,
    ) -> Any:
        url = f"{self.base_url}{path}"
        assert_local_base_url(url.rsplit(path, 1)[0] or self.base_url)
        data = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
                if not raw:
                    return None
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise OllamaError(f"HTTP {exc.code}: {body or exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise OllamaError(
                "Cannot reach local Ollama. Is it running? "
                "Try: ollama serve   or open the Ollama Mac app."
            ) from exc

    def ping(self) -> bool:
        try:
            self._request("GET", "/api/tags", timeout=5.0)
            return True
        except (OllamaError, PrivacyError, json.JSONDecodeError):
            return False

    def list_models(self) -> list[str]:
        data = self._request("GET", "/api/tags", timeout=15.0) or {}
        models = data.get("models") or []
        names: list[str] = []
        for item in models:
            name = item.get("name") or item.get("model")
            if name:
                names.append(assert_local_model(name))
        return names

    def has_model(self, model: str) -> bool:
        model = assert_local_model(model)
        installed = self.list_models()
        bare = {m.split("@", 1)[0] for m in installed}
        if model in bare or model in installed:
            return True
        # Untagged name → accept name:latest only (not every size variant).
        if ":" not in model:
            return f"{model}:latest" in bare
        return False

    def pull(self, model: str) -> Iterator[str]:
        model = assert_local_model(model)
        url = f"{self.base_url}/api/pull"
        payload = json.dumps({"name": model, "stream": True}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=3600.0) as resp:
                for raw_line in resp:
                    line = raw_line.decode("utf-8").strip()
                    if not line:
                        continue
                    event = json.loads(line)
                    if "error" in event:
                        raise OllamaError(event["error"])
                    status = event.get("status", "")
                    completed = event.get("completed")
                    total = event.get("total")
                    if completed is not None and total:
                        pct = int(completed * 100 / total)
                        yield f"{status} ({pct}%)"
                    elif status:
                        yield status
        except urllib.error.URLError as exc:
            raise OllamaError(
                "Pull failed — Ollama is not reachable on localhost."
            ) from exc

    def chat_stream(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
    ) -> Iterator[str]:
        model = assert_local_model(model)
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature},
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=600.0) as resp:
                for raw_line in resp:
                    line = raw_line.decode("utf-8").strip()
                    if not line:
                        continue
                    event = json.loads(line)
                    if "error" in event:
                        raise OllamaError(event["error"])
                    message = event.get("message") or {}
                    content = message.get("content")
                    if content:
                        yield content
                    if event.get("done"):
                        break
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise OllamaError(f"HTTP {exc.code}: {body or exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise OllamaError(
                "Cannot reach local Ollama. Is it running?"
            ) from exc

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
    ) -> str:
        return "".join(self.chat_stream(model, messages, temperature=temperature))
