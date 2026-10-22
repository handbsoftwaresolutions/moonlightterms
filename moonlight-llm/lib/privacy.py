"""Privacy + model policy: loopback Ollama client; allowlisted GLM-5.2 cloud tag."""

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

# GLM-5.2 is ~756B — not a Mac-local weight pull. Ollama exposes it only as :cloud.
ALLOWED_CLOUD_MODELS = frozenset(
    {
        "glm-5.2",
        "glm-5.2:cloud",
    }
)

CLOUD_MODEL_MARKERS = (":cloud",)


class PrivacyError(RuntimeError):
    """Raised when a configuration would leave the local machine unsafely."""


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
            f"Remote host blocked: {host}. "
            "Talk to Ollama on 127.0.0.1 only (it may proxy allowlisted models)."
        )
    if not is_loopback_host(host):
        raise PrivacyError(
            f"Non-local host blocked: {host}. "
            "Set host to 127.0.0.1."
        )
    return base_url.rstrip("/")


def normalize_model(model: str) -> str:
    name = (model or "").strip()
    if not name:
        raise PrivacyError("Model name is empty.")
    lowered = name.lower()
    # Accept friendly aliases
    if lowered in {"glm 5.2", "glm5.2", "glm-5.2", "glm-5.2:cloud"}:
        return "glm-5.2:cloud"
    return name


def is_cloud_model(model: str) -> bool:
    return ":cloud" in model.lower() or model.lower() in ALLOWED_CLOUD_MODELS


def assert_local_model(model: str) -> str:
    """Validate model tag. Only glm-5.2:cloud is allowed among :cloud tags."""
    name = normalize_model(model)
    lowered = name.lower()
    if lowered in {m.lower() for m in ALLOWED_CLOUD_MODELS} or lowered == "glm-5.2:cloud":
        return "glm-5.2:cloud"
    for marker in CLOUD_MODEL_MARKERS:
        if marker in lowered:
            raise PrivacyError(
                f"Cloud model blocked: {name}. "
                "Only allowlisted tag is glm-5.2:cloud (GLM-5.2 is not a local Mac download)."
            )
    return name


def privacy_report(base_url: str, model: str, data_dir: str) -> list[str]:
    assert_local_base_url(base_url)
    model = assert_local_model(model)
    lines = [
        f"Mode: DevSec (cybersecurity + development only — not a chatbot)",
        f"Client endpoint: {base_url} (loopback Ollama)",
        f"Model: {model}",
        f"Session logs under: {data_dir}",
    ]
    if is_cloud_model(model):
        lines.extend(
            [
                "Inference: GLM-5.2 runs via Ollama cloud (weights too large for a Mac).",
                "CLI still speaks only to 127.0.0.1; Ollama may forward prompts for this model.",
                "Sign in to Ollama if pull/run requires it: ollama signin",
            ]
        )
    else:
        lines.append("Inference: local weights on this machine.")
    return lines
