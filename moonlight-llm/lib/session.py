"""Local-only chat session persistence."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class SessionStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.chats_dir = data_dir / "chats"
        self.chats_dir.mkdir(parents=True, exist_ok=True)
        self.current_path = self.chats_dir / "current.json"

    def load(self) -> list[dict[str, str]]:
        if not self.current_path.exists():
            return []
        try:
            data = json.loads(self.current_path.read_text(encoding="utf-8"))
            messages = data.get("messages") or []
            return [
                {"role": m["role"], "content": m["content"]}
                for m in messages
                if m.get("role") in {"system", "user", "assistant"} and m.get("content")
            ]
        except (json.JSONDecodeError, OSError, KeyError, TypeError):
            return []

    def save(self, messages: list[dict[str, str]], model: str) -> None:
        payload: dict[str, Any] = {
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "model": model,
            "messages": messages,
            "private": True,
            "location": "local disk only",
        }
        self.current_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def clear(self) -> None:
        if self.current_path.exists():
            self.current_path.unlink()

    def archive(self) -> Path | None:
        if not self.current_path.exists():
            return None
        stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
        dest = self.chats_dir / f"archive-{stamp}.json"
        dest.write_text(self.current_path.read_text(encoding="utf-8"), encoding="utf-8")
        self.current_path.unlink()
        return dest
