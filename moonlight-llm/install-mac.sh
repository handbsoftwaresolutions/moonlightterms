#!/usr/bin/env bash
# Install Moonlight Local on macOS — fully private terminal LLM.
set -euo pipefail

BOLD=$'\033[1m'
DIM=$'\033[2m'
OK=$'\033[38;5;114m'
WARN=$'\033[38;5;180m'
ERR=$'\033[38;5;174m'
BRAND=$'\033[38;5;152m'
RESET=$'\033[0m'

say() { printf '%s\n' "$*"; }
ok() { printf '%s✓%s %s\n' "$OK" "$RESET" "$*"; }
warn() { printf '%s!%s %s\n' "$WARN" "$RESET" "$*"; }
die() { printf '%s✗%s %s\n' "$ERR" "$RESET" "$*" >&2; exit 1; }

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL="${MOONLIGHT_MODEL:-llama3.2:3b}"
BIN_DIR="${MOONLIGHT_BIN_DIR:-$HOME/.local/bin}"
DATA_DIR="${MOONLIGHT_LLM_HOME:-$HOME/.moonlight-llm}"

say ""
say "${BRAND}${BOLD}Moonlight Local${RESET} — private LLM for your Mac terminal"
say "${DIM}Nothing leaves this machine. No API keys. No cloud models.${RESET}"
say ""

if [[ "$(uname -s)" != "Darwin" ]]; then
  warn "This installer targets macOS. Continuing anyway (Linux/dev OK)."
fi

# --- Python ---
command -v python3 >/dev/null 2>&1 || die "python3 not found. Install Xcode CLT: xcode-select --install"
ok "Python $(python3 --version 2>&1 | awk '{print $2}')"

# --- Ollama ---
if ! command -v ollama >/dev/null 2>&1; then
  say "Installing Ollama (local inference engine)…"
  curl -fsSL https://ollama.com/install.sh | sh
  # Apple Silicon / Intel app path
  if [[ -x "/Applications/Ollama.app/Contents/Resources/ollama" ]]; then
    export PATH="/Applications/Ollama.app/Contents/Resources:$PATH"
  fi
fi
command -v ollama >/dev/null 2>&1 || die "Ollama install finished but 'ollama' is not on PATH. Open the Ollama app once, then re-run this script."
ok "Ollama $(ollama --version 2>/dev/null | head -1 || echo found)"

# Start server if needed
if ! curl -fsS "http://127.0.0.1:11434/api/tags" >/dev/null 2>&1; then
  say "Starting local Ollama server…"
  if [[ -d "/Applications/Ollama.app" ]]; then
    open -a Ollama 2>/dev/null || true
  fi
  # Fallback headless serve
  if ! curl -fsS "http://127.0.0.1:11434/api/tags" >/dev/null 2>&1; then
    nohup ollama serve >/tmp/moonlight-ollama.log 2>&1 &
  fi
  for _ in $(seq 1 30); do
    if curl -fsS "http://127.0.0.1:11434/api/tags" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
fi
curl -fsS "http://127.0.0.1:11434/api/tags" >/dev/null 2>&1 || die "Could not reach Ollama on 127.0.0.1:11434"
ok "Local server on 127.0.0.1:11434"

# --- Model (local weights only; reject :cloud) ---
case "$MODEL" in
  *:cloud*|*"ollama.com"*) die "Cloud models are blocked. Use a local tag like llama3.2:3b" ;;
esac

say "Pulling local model ${BOLD}${MODEL}${RESET} (stored on this Mac)…"
ollama pull "$MODEL"
ok "Model ready: $MODEL"

# --- Install CLI ---
mkdir -p "$BIN_DIR" "$DATA_DIR"
INSTALL_ROOT="$DATA_DIR/app"
rm -rf "$INSTALL_ROOT"
mkdir -p "$INSTALL_ROOT"
# Copy package (no network after this for the app itself)
cp -R "$ROOT/bin" "$ROOT/lib" "$ROOT/config" "$INSTALL_ROOT/"
chmod +x "$INSTALL_ROOT/bin/moonlight"

WRAPPER="$BIN_DIR/moonlight"
cat > "$WRAPPER" <<EOF
#!/usr/bin/env bash
set -euo pipefail
export MOONLIGHT_LLM_HOME="${DATA_DIR}"
export PYTHONPATH="${INSTALL_ROOT}\${PYTHONPATH:+:\$PYTHONPATH}"
exec python3 -m lib.cli "\$@"
EOF
chmod +x "$WRAPPER"

# Seed user config (privacy locked)
cat > "$DATA_DIR/config.json" <<EOF
{
  "host": "127.0.0.1",
  "port": 11434,
  "default_model": "${MODEL}",
  "allow_remote": false,
  "privacy_banner": true
}
EOF

ok "CLI installed → $WRAPPER"

# PATH hint
case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *)
    warn "Add to your shell profile:"
    say "  ${BOLD}export PATH=\"$BIN_DIR:\$PATH\"${RESET}"
    if [[ -n "${ZSH_VERSION:-}" ]] || [[ "${SHELL:-}" == *zsh ]]; then
      say "  (zsh) echo 'export PATH=\"$BIN_DIR:\$PATH\"' >> ~/.zshrc && source ~/.zshrc"
    else
      say "  (bash) echo 'export PATH=\"$BIN_DIR:\$PATH\"' >> ~/.bash_profile && source ~/.bash_profile"
    fi
    ;;
esac

say ""
say "${OK}${BOLD}You're private.${RESET} Start chatting:"
say "  ${BOLD}moonlight${RESET}"
say "  moonlight ask \"Summarize quantum entanglement in one sentence\""
say "  moonlight doctor"
say "  moonlight privacy"
say ""
say "${DIM}Chats live in $DATA_DIR/chats — never uploaded.${RESET}"
say ""
