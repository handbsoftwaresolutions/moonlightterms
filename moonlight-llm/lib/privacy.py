"""Privacy enforcement: localhost-only, no cloud models, no telemetry."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

CLOUD_HOST_MARKERS = (
    "ollama.com",
    "api.openai.com",
    "anthropic.com",
    "googleapis.com",
    "openrouter.ai",
    "together.xyz",
    "groq.com",
)

CLOUD_MODEL_MARKERS = (":cloud",)


class PrivacyError(RuntimeError):
    """Raised when a configuration would leave the local machine."""


def is_loopback_host(host: str) -> bool:
    host = (host or "").strip().lower()
    if host in {"localhost", "127.0.0.1", "::1"}:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        try:
            infos = socket.getaddrinfo(host, None)
        except socket.gaierror:
            return False
        for info in infos:
            addr = info[4][0]
            try:
                if not ipaddress.ip_address(addr).is_loopback:
                    return False
            except ValueError:
                return False
        return bool(infos)


def assert_local_base_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"}:
        raise PrivacyError(f"Unsupported URL scheme: {parsed.scheme!r}")
    host = parsed.hostname or ""
    if any(marker in host for marker in CLOUD_HOST_MARKERS):
        raise PrivacyError(
            f"Remote host blocked for privacy: {host}. "
            "Moonlight Local only talks to 127.0.0.1."
        )
    if not is_loopback_host(host):
        raise PrivacyError(
            f"Non-local host blocked: {host}. "
            "Set host to 127.0.0.1 to stay fully private."
        )
    if parsed.scheme == "https" and is_loopback_host(host):
        # Local Ollama speaks plain HTTP on loopback.
        pass
    return base_url.rstrip("/")


def assert_local_model(model: str) -> str:
    name = (model or "").strip()
    if not name:
        raise PrivacyError("Model name is empty.")
    lowered = name.lower()
    for marker in CLOUD_MODEL_MARKERS:
        if marker in lowered:
            raise PrivacyError(
                f"Cloud model blocked: {name}. "
                "Use a local Ollama tag (for example llama3.2:3b), not :cloud."
            )
    return name


def privacy_report(base_url: str, model: str, data_dir: str) -> list[str]:
    assert_local_base_url(base_url)
    assert_local_model(model)
    return [
        "Privacy mode: ON",
        f"Endpoint: {base_url} (loopback only)",
        f"Model: {model} (local weights)",
        f"Chats saved under: {data_dir}",
        "No API keys. No telemetry. No cloud fallback.",
    ]
