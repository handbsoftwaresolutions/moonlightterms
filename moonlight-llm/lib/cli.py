#!/usr/bin/env python3
"""Moonlight DevSec — GLM-5.2 terminal for cybersecurity & development (not a chatbot)."""

from __future__ import annotations

import argparse
import json
import os
import platform
import readline  # noqa: F401  # enables nicer input() editing
import shutil
import sys
from pathlib import Path

from . import __version__
from .ollama_client import OllamaClient, OllamaError
from .privacy import (
    PrivacyError,
    assert_local_model,
    is_cloud_model,
    privacy_report,
)
from .session import SessionStore

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "config" / "default.json"
DEFAULT_MODEL = "glm-5.2:cloud"

C_RESET = "\033[0m"
C_DIM = "\033[2m"
C_BOLD = "\033[1m"
C_USER = "\033[38;5;189m"
C_AI = "\033[38;5;117m"
C_OK = "\033[38;5;114m"
C_WARN = "\033[38;5;180m"
C_ERR = "\033[38;5;174m"
C_BRAND = "\033[38;5;152m"


def color_enabled() -> bool:
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def c(code: str, text: str) -> str:
    if not color_enabled():
        return text
    return f"{code}{text}{C_RESET}"


def data_dir() -> Path:
    override = os.environ.get("MOONLIGHT_LLM_HOME")
    if override:
        path = Path(override).expanduser()
    else:
        path = Path.home() / ".moonlight-llm"
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_config() -> dict:
    cfg = json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    user_cfg = data_dir() / "config.json"
    if user_cfg.exists():
        try:
            cfg.update(json.loads(user_cfg.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            pass
    if os.environ.get("MOONLIGHT_MODEL"):
        cfg["default_model"] = os.environ["MOONLIGHT_MODEL"]
    if os.environ.get("MOONLIGHT_HOST"):
        cfg["host"] = os.environ["MOONLIGHT_HOST"]
    if os.environ.get("MOONLIGHT_PORT"):
        cfg["port"] = int(os.environ["MOONLIGHT_PORT"])
    if cfg.get("allow_remote"):
        raise PrivacyError(
            "allow_remote is forbidden. Use loopback Ollama only."
        )
    # Normalize default to allowlisted GLM tag
    cfg["default_model"] = assert_local_model(
        cfg.get("default_model") or DEFAULT_MODEL
    )
    return cfg


def save_user_config(updates: dict) -> None:
    path = data_dir() / "config.json"
    current = {}
    if path.exists():
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            current = {}
    current.update(updates)
    current["allow_remote"] = False
    if "default_model" in current:
        current["default_model"] = assert_local_model(current["default_model"])
    path.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")


def make_client(cfg: dict) -> OllamaClient:
    return OllamaClient(host=cfg.get("host", "127.0.0.1"), port=int(cfg.get("port", 11434)))


def print_banner(cfg: dict, model: str) -> None:
    print()
    print(c(C_BRAND + C_BOLD, "  Moonlight DevSec"))
    print(c(C_DIM, f"  cybersecurity · development  ·  v{__version__}"))
    print(c(C_DIM, "  ─────────────────────────────────────"))
    print(c(C_WARN, "  not a chatbot — cyber & engineering tasks only"))
    print(c(C_DIM, f"  model: {model}"))
    if is_cloud_model(model):
        print(c(C_DIM, "  note: GLM-5.2 via Ollama cloud (too large for local Mac weights)"))
    print()
    print(c(C_DIM, "  Commands: /help  /model  /models  /clear  /privacy  /exit"))
    print()


def cmd_help() -> None:
    print(
        """
  /help       Show commands
  /model      Show or set model  (/model glm-5.2:cloud)
  /models     List models known to Ollama
  /pull       Register/pull model  (/pull glm-5.2:cloud)
  /clear      Clear this session
  /archive    Archive session and start fresh
  /privacy    Show endpoint + model policy
  /status     Ollama + model status
  /exit       Quit

  In scope: secure coding, defensive security, debugging, architecture.
  Out of scope: casual chat — keep it cyber/dev.
""".rstrip()
    )
    print()


def ensure_ready(client: OllamaClient, model: str, pull_if_missing: bool = True) -> str:
    model = assert_local_model(model)
    if not client.ping():
        raise OllamaError(
            "Ollama is not running on this Mac.\n"
            "  1) Install:  curl -fsSL https://ollama.com/install.sh | sh\n"
            "  2) Open the Ollama app (or: ollama serve)\n"
            "  3) For GLM-5.2 cloud: ollama signin\n"
            "  4) Re-run:   moonlight"
        )
    if client.has_model(model):
        return model
    if not pull_if_missing:
        raise OllamaError(
            f"Model {model!r} is not available. Run: moonlight pull {model}"
        )
    if is_cloud_model(model):
        print(c(C_WARN, f"  Registering {model} (Ollama cloud — may require: ollama signin)…"))
    else:
        print(c(C_WARN, f"  Pulling local model {model}…"))
    last = ""
    for status in client.pull(model):
        if status != last:
            print(c(C_DIM, f"  {status}"))
            last = status
    print(c(C_OK, f"  Ready: {model}"))
    return model


def console_loop(cfg: dict, model: str) -> int:
    client = make_client(cfg)
    model = ensure_ready(client, model)
    store = SessionStore(data_dir())
    history = store.load()
    system = cfg.get("system_prompt") or ""
    limit = int(cfg.get("history_limit", 40))
    temperature = float(cfg.get("temperature", 0.2))

    if cfg.get("privacy_banner", True):
        print_banner(cfg, model)

    while True:
        try:
            prompt = input(c(C_USER + C_BOLD, "dev › ") + C_RESET)
        except (EOFError, KeyboardInterrupt):
            print()
            print(c(C_DIM, "  Session saved. Out."))
            return 0

        text = prompt.strip()
        if not text:
            continue

        if text.startswith("/"):
            parts = text.split(maxsplit=1)
            cmd = parts[0].lower()
            arg = parts[1].strip() if len(parts) > 1 else ""

            if cmd in {"/exit", "/quit", "/q"}:
                print(c(C_DIM, "  Session saved. Out."))
                return 0
            if cmd == "/help":
                cmd_help()
                continue
            if cmd == "/privacy":
                for line in privacy_report(client.base_url, model, str(data_dir())):
                    print(c(C_OK, f"  {line}"))
                print()
                continue
            if cmd == "/status":
                ok = client.ping()
                print(c(C_OK if ok else C_ERR, f"  Ollama: {'up' if ok else 'down'} @ {client.base_url}"))
                print(c(C_DIM, f"  Model: {model}"))
                print(c(C_DIM, f"  Platform: {platform.system()} {platform.machine()}"))
                print(c(C_DIM, "  Role: DevSec (cyber + development)"))
                print()
                continue
            if cmd == "/models":
                try:
                    models = client.list_models()
                except OllamaError as exc:
                    print(c(C_ERR, f"  {exc}"))
                    continue
                if not models:
                    print(c(C_WARN, "  No models yet. Try: /pull glm-5.2:cloud"))
                else:
                    for name in models:
                        mark = "●" if name.split("@", 1)[0] == model else "○"
                        print(c(C_DIM, f"  {mark} {name}"))
                print()
                continue
            if cmd == "/model":
                if not arg:
                    print(c(C_DIM, f"  Current model: {model}"))
                    print()
                    continue
                try:
                    model = ensure_ready(client, arg)
                    save_user_config({"default_model": model})
                    print(c(C_OK, f"  Switched to {model}"))
                except (OllamaError, PrivacyError) as exc:
                    print(c(C_ERR, f"  {exc}"))
                print()
                continue
            if cmd == "/pull":
                target = arg or model
                try:
                    target = assert_local_model(target)
                    print(c(C_WARN, f"  Pulling {target}…"))
                    for status in client.pull(target):
                        print(c(C_DIM, f"  {status}"))
                    model = target
                    save_user_config({"default_model": model})
                    print(c(C_OK, f"  Ready: {model}"))
                except (OllamaError, PrivacyError) as exc:
                    print(c(C_ERR, f"  {exc}"))
                print()
                continue
            if cmd == "/clear":
                history = []
                store.clear()
                print(c(C_OK, "  Session cleared."))
                print()
                continue
            if cmd == "/archive":
                path = store.archive()
                history = []
                if path:
                    print(c(C_OK, f"  Archived → {path}"))
                else:
                    print(c(C_DIM, "  Nothing to archive."))
                print()
                continue
            print(c(C_WARN, f"  Unknown command: {cmd}. Try /help"))
            print()
            continue

        history.append({"role": "user", "content": text})
        api_messages = [{"role": "system", "content": system}] + history[-limit:]

        print(c(C_AI + C_BOLD, "devsec › "), end="", flush=True)
        chunks: list[str] = []
        try:
            for piece in client.chat_stream(model, api_messages, temperature=temperature):
                chunks.append(piece)
                print(c(C_AI, piece), end="", flush=True)
            print()
            print()
        except (OllamaError, PrivacyError) as exc:
            print()
            print(c(C_ERR, f"  {exc}"))
            history.pop()
            print()
            continue

        reply = "".join(chunks).strip()
        history.append({"role": "assistant", "content": reply})
        store.save(history, model)

    return 0


def cmd_doctor(cfg: dict) -> int:
    print(c(C_BRAND + C_BOLD, "Moonlight DevSec — doctor"))
    print(c(C_DIM, f"Platform: {platform.system()} {platform.machine()}  Python {platform.python_version()}"))
    ollama_bin = shutil.which("ollama")
    print(c(C_OK if ollama_bin else C_WARN, f"ollama binary: {ollama_bin or 'not found'}"))
    client = make_client(cfg)
    up = client.ping()
    print(c(C_OK if up else C_ERR, f"local server: {'reachable' if up else 'not reachable'} ({client.base_url})"))
    model = assert_local_model(cfg.get("default_model") or DEFAULT_MODEL)
    if up:
        try:
            models = client.list_models()
            print(c(C_DIM, f"models: {', '.join(models) if models else '(none)'}"))
            has = client.has_model(model)
            label = "ready" if has else "missing — run: moonlight pull"
            print(c(C_OK if has else C_WARN, f"default model {model}: {label}"))
        except OllamaError as exc:
            print(c(C_ERR, str(exc)))
    for line in privacy_report(client.base_url, model, str(data_dir())):
        print(c(C_OK, line))
    if platform.system() != "Darwin":
        print(c(C_WARN, "Note: designed for macOS; Linux works for testing."))
    return 0 if up else 1


def cmd_pull(cfg: dict, model: str) -> int:
    client = make_client(cfg)
    try:
        model = assert_local_model(model)
        ensure_ready(client, model, pull_if_missing=True)
        save_user_config({"default_model": model})
        print(c(C_OK, f"Model ready: {model}"))
        return 0
    except (OllamaError, PrivacyError) as exc:
        print(c(C_ERR, str(exc)), file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="moonlight",
        description="Moonlight DevSec — GLM-5.2 terminal for cybersecurity & development (not a chatbot).",
    )
    p.add_argument("-v", "--version", action="version", version=f"moonlight {__version__}")
    p.add_argument("-m", "--model", help="Model tag (default: glm-5.2:cloud)")
    sub = p.add_subparsers(dest="command")

    sub.add_parser("console", help="Start DevSec console (default)")
    sub.add_parser("chat", help=argparse.SUPPRESS)  # alias
    sub.add_parser("doctor", help="Check Ollama + model policy")
    pull = sub.add_parser("pull", help="Pull/register model")
    pull.add_argument("name", nargs="?", help="Model tag, e.g. glm-5.2:cloud")
    sub.add_parser("privacy", help="Print endpoint + model policy")
    ask = sub.add_parser("ask", help="One-shot cyber/dev question")
    ask.add_argument("prompt", nargs="+", help="Technical question")
    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    args = parser.parse_args(argv if argv else ["console"])
    if args.command is None:
        args.command = "console"
    if args.command == "chat":
        args.command = "console"

    try:
        cfg = load_config()
    except PrivacyError as exc:
        print(c(C_ERR, str(exc)), file=sys.stderr)
        return 2

    model = assert_local_model(args.model or cfg.get("default_model") or DEFAULT_MODEL)

    try:
        if args.command == "doctor":
            return cmd_doctor(cfg)
        if args.command == "privacy":
            client = make_client(cfg)
            for line in privacy_report(client.base_url, model, str(data_dir())):
                print(line)
            return 0
        if args.command == "pull":
            return cmd_pull(cfg, getattr(args, "name", None) or model)
        if args.command == "ask":
            client = make_client(cfg)
            model = ensure_ready(client, model)
            prompt = " ".join(args.prompt)
            messages = [
                {"role": "system", "content": cfg.get("system_prompt", "")},
                {"role": "user", "content": prompt},
            ]
            for piece in client.chat_stream(
                model, messages, float(cfg.get("temperature", 0.2))
            ):
                print(piece, end="", flush=True)
            print()
            return 0
        return console_loop(cfg, model)
    except PrivacyError as exc:
        print(c(C_ERR, f"Policy block: {exc}"), file=sys.stderr)
        return 2
    except OllamaError as exc:
        print(c(C_ERR, str(exc)), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
