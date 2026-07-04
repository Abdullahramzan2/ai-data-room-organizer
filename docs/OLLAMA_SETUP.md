# Ollama Setup — Data Room Organizer

Ollama is an **optional** local LLM for Tier 3 classification (ambiguous documents). It is **not** bundled in the Windows installer — install it separately if you want smarter escalation without cloud API keys.

---

## When you need Ollama

| Mode | Ollama needed? |
|------|----------------|
| `CLASSIFICATION_MODE=local` | No — keywords + embeddings only |
| `CLASSIFICATION_MODE=hybrid` + Ollama | Yes — for local Tier 3 when files are ambiguous |
| OpenAI / enterprise API configured | No — cloud provider used instead |

Default installer settings use **local** mode. Ollama is only required if you want to upgrade to hybrid with a **local** LLM.

---

## Step 1 — Install Ollama

1. Go to [https://ollama.com](https://ollama.com)
2. Download and install **Ollama for Windows**
3. After install, Ollama runs in the background on `http://localhost:11434`

Verify in PowerShell:

```powershell
ollama list
```

If the command is not found, restart your terminal or sign out and back in.

---

## Step 2 — Pull a model

Recommended model (matches defaults):

```powershell
ollama pull llama3.2
```

Confirm:

```powershell
ollama list
```

You should see `llama3.2` in the list.

---

## Step 3 — Edit settings

### Windows installer users

Settings file:

`%APPDATA%\DataRoomOrganizer\.env`

Open in Notepad:

```powershell
notepad "$env:APPDATA\DataRoomOrganizer\.env"
```

### Zip / developer install users

Edit `.env` in the project root.

---

## Step 4 — Configure `.env`

Minimum for Ollama-based hybrid mode:

```env
CLASSIFICATION_MODE=hybrid
REASONING_PROVIDER=ollama

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

Save the file.

| Variable | Purpose |
|----------|---------|
| `CLASSIFICATION_MODE` | `hybrid` enables Tier 3 when local confidence is low |
| `REASONING_PROVIDER` | `ollama` forces Ollama (or use `auto` to pick first available provider) |
| `OLLAMA_BASE_URL` | Default local URL; change only if Ollama runs elsewhere |
| `OLLAMA_MODEL` | Must match a model from `ollama list` |

---

## Step 5 — Restart and verify

1. Close the Data Room Organizer UI if it is running
2. Launch **Data Room Organizer** from the Start Menu again
3. Open the **Doctor** tab in the UI, or run **Data Room Doctor** from the Start Menu

Expect:

```
[OK] ollama: Ollama available at http://localhost:11434
```

If Doctor shows **SKIP** for Ollama, `CLASSIFICATION_MODE` is still `local` — update `.env` and restart.

---

## Using `auto` provider instead

If you prefer automatic provider selection:

```env
CLASSIFICATION_MODE=hybrid
REASONING_PROVIDER=auto
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

With `auto`, the tool uses enterprise/OpenAI if configured; otherwise Ollama when running; otherwise local-only.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `ollama` not recognized | Reinstall Ollama; restart terminal |
| Doctor: Ollama not reachable | Start Ollama app; check `http://localhost:11434` in browser |
| Model not found | Run `ollama pull llama3.2` (or match `OLLAMA_MODEL` to an installed model) |
| Changes not applied | Restart the UI after editing `.env` |
| Still using local only | Confirm `CLASSIFICATION_MODE=hybrid` and `REASONING_PROVIDER=ollama` |

---

## Privacy note

Ollama runs **entirely on your machine**. Document excerpts sent to Tier 3 stay local — no cloud API calls when Ollama is the active provider.

KMZ and DWG files remain **local-only** regardless of provider settings.

---

## Related documents

- `docs/INSTALLER_QUICKSTART.md` — install the Windows setup file
- `docs/USER_GUIDE.md` — classification modes and daily workflow
- `docs/CALIBRATION.md` — tune thresholds if Ollama results vary
