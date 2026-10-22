# Moonlight Local

**Fully private LLM in your Mac terminal.** Runs on-device via [Ollama](https://ollama.com). No API keys. No cloud models. No telemetry.

```
you › Write a haiku about silence
moonlight › Soft night holds its breath—
            keys rest under quiet light,
            thoughts stay on this Mac.
```

## Requirements

- macOS (Apple Silicon or Intel)
- Python 3.9+ (comes with macOS / Xcode CLT)
- ~2–4 GB free disk for a small local model

## Install (Mac)

From this folder:

```bash
chmod +x install-mac.sh bin/moonlight
./install-mac.sh
```

That will:

1. Install Ollama if needed  
2. Start the **local** server on `127.0.0.1:11434`  
3. Pull `llama3.2:3b` (local weights only)  
4. Put `moonlight` on your PATH (`~/.local/bin`)

Smaller model (faster, less RAM):

```bash
MOONLIGHT_MODEL=llama3.2:1b ./install-mac.sh
```

## Use

```bash
moonlight                  # interactive private chat
moonlight ask "Explain TLS like I'm 5"
moonlight doctor           # health + privacy check
moonlight privacy          # guarantees
moonlight pull llama3.2:1b
moonlight -m llama3.2:1b
```

### In-chat commands

| Command | Action |
|--------|--------|
| `/help` | Show commands |
| `/model name` | Switch local model |
| `/models` | List installed models |
| `/pull name` | Download a local model |
| `/clear` | Clear current chat |
| `/archive` | Save chat to disk archive |
| `/privacy` | Privacy status |
| `/exit` | Quit |

## Privacy guarantees

| Rule | Behavior |
|------|----------|
| Localhost only | Talks only to `127.0.0.1` / `localhost` |
| No cloud models | Tags like `*:cloud` are rejected |
| No remote hosts | `ollama.com`, OpenAI, etc. blocked in code |
| No API keys | Nothing to leak |
| Local history | `~/.moonlight-llm/chats/` on your Mac only |

Chats never leave your machine unless **you** copy them elsewhere.

## Uninstall

```bash
rm -f ~/.local/bin/moonlight
rm -rf ~/.moonlight-llm
# optional: remove Ollama app + models separately
```

## Dev / test

```bash
./bin/moonlight privacy
python3 -m unittest discover -s tests -v
```

## How it works

```
Terminal (moonlight)
    │  HTTP 127.0.0.1 only
    ▼
Ollama (local)
    │
    ▼
Model weights on disk  ← never uploaded
```

Built for Moonlight’s privacy-first ethos — your words stay yours.
