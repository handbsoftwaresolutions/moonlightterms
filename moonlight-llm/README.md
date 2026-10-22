# Moonlight DevSec

Terminal specialist for **cybersecurity and software development** — not a general chatbot.

**Model:** [GLM-5.2](https://ollama.com/library/glm-5.2) via Ollama (`glm-5.2:cloud`)

```
dev › Harden this Nginx TLS config for TLS 1.3 only
devsec › …concrete config + rationale…
```

## Why `:cloud`?

GLM-5.2 is a flagship ~756B-class model. It is **not** a consumer Mac local weight download. On Ollama the working tag is `glm-5.2:cloud` (CLI still talks to `127.0.0.1`; Ollama may forward inference). You may need:

```bash
ollama signin
```

## Install (Mac)

```bash
cd moonlight-llm
chmod +x install-mac.sh bin/moonlight
./install-mac.sh
```

## Use

```bash
moonlight                                          # DevSec console
moonlight ask "Threat-model this JWT refresh flow"
moonlight doctor
moonlight privacy
moonlight pull glm-5.2:cloud
```

### In-console commands

| Command | Action |
|--------|--------|
| `/help` | Commands + scope |
| `/model` | Show/set model |
| `/pull glm-5.2:cloud` | Register model |
| `/clear` | Clear session |
| `/privacy` | Endpoint + model policy |
| `/exit` | Quit |

## Scope

**In:** secure coding, defensive security, hardening, threat modeling, debugging, architecture, DevOps.

**Out:** casual chat, trivia, creative writing — and malware / weaponized exploit write-ups / unauthorized access help.

## Policy notes

- Client → Ollama on `127.0.0.1` only  
- Only allowlisted cloud tag: `glm-5.2:cloud`  
- Other `*:cloud` models stay blocked  
- Session logs: `~/.moonlight-llm/chats/`

## Dev / test

```bash
./bin/moonlight privacy
python3 -m unittest discover -s tests -v
```
