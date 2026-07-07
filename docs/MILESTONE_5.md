# Milestone 5 — Windows Installer (Single-Click Delivery)

| | |
|---|---|
| **Client** | Carl Quesinberry |
| **Milestone** | Bundled Windows installer — no Python/pip/terminal setup |
| **Version** | 0.5.3 (package + installer) |
| **Status** | Delivered |

---

## Overview

Carl requested a **single Windows installer** that bundles Python, libraries, Tesseract, Poppler, LibreOffice, and the embedding model. Ollama remains separate with a setup guide.

### Delivered

1. **Windows installer** — `AI-Data-Room-Organizer-Setup.exe` (~603 MB compressed)
2. **Launcher** — `DataRoomOrganizer.exe` (UI, no console) + `DataRoomDoctor.exe` (health check)
3. **Bundled layout** — `app/`, `python/`, `tools/`, `models/`, `launcher/` under install dir
4. **Per-user install** — `%LOCALAPPDATA%\Programs\AI Data Room Organizer\` (no admin required)
5. **User settings & cache** — `%APPDATA%\DataRoomOrganizer\.env` and `cache\` on first launch
6. **Start Menu shortcuts** — Data Room Organizer, Data Room Doctor; optional desktop icon
7. **Operator docs** — bundled under `app\docs\` plus cloud delivery
8. **Build pipeline** — `packaging/build.ps1`, staging scripts, Inno Setup (`packaging/installer.iss`)

### v0.5.1–0.5.3 fixes (post-initial delivery)

| Fix | Version |
|-----|---------|
| Batch classification default (`pipelined: false`) — fast 19-file runs | 0.5.1 |
| User-writable cache (`%APPDATA%\DataRoomOrganizer\cache`) — no Program Files errors | 0.5.1 |
| Per-user install path, desktop shortcut, browse-folder picker | 0.5.1 |
| Live UI status messages (ingesting / classifying / finished) | 0.5.2 |
| Streamlit fragment status fix — no error loop during pipeline run | 0.5.3 |

### Not bundled (by design)

- **Ollama** — optional local LLM; see `docs/OLLAMA_SETUP.md`
- **Git / source repo** — installer is the runtime deliverable

---

## Carl delivery package

Send Carl these files:

| File | Purpose |
|------|---------|
| **`AI-Data-Room-Organizer-Setup.exe`** | Required — the installer (~603 MB) |
| **`docs/INSTALLER_QUICKSTART.md`** | Required — install and first-run guide |
| **`docs/USER_GUIDE.md`** | Recommended — daily workflow, review, rerun, API keys |
| **`docs/OLLAMA_SETUP.md`** | Optional — local LLM without an API key |

Upload Setup.exe + docs to Google Drive, Dropbox, or OneDrive and share the link.

---

## Local smoke test results

Validated on Windows 11 with Carl's 19-file sample:

| Test | Result |
|------|--------|
| Silent install to `%LOCALAPPDATA%\Programs\` | **Pass** |
| `DataRoomDoctor.exe` | **Pass** — Python, Tesseract, Poppler, LibreOffice, embedding model OK |
| Pipeline (19 files, bundled Python) | **Pass** — ~20–40 s, manifest + index exported |
| UI launch + live progress | **Pass** — status updates through ingest/classify/finish; no error loop (v0.5.3) |

Install docs ship inside the app at:

`%LOCALAPPDATA%\Programs\AI Data Room Organizer\app\docs\`

---

## Carl quick start

1. Download and run `AI-Data-Room-Organizer-Setup.exe`
2. Start Menu → **Data Room Organizer** (browser opens automatically)
3. Optional: Start Menu → **Data Room Doctor** to verify environment
4. Set input/output folders in the UI **Run** tab → **Run pipeline**
5. For Ollama hybrid mode: `docs/OLLAMA_SETUP.md`

Full steps: `docs/INSTALLER_QUICKSTART.md`

---

## Rebuild commands (maintainer)

```powershell
# Stop running app
powershell -ExecutionPolicy Bypass -File packaging\stop_dataroom.ps1

# Stage updated app code only (fast)
powershell -ExecutionPolicy Bypass -File packaging\stage_app.ps1

# Build installer (staging must include python/, tools/, models/)
powershell -ExecutionPolicy Bypass -File packaging\build_installer.ps1 -Version 0.5.3

# Full rebuild from scratch (slow — downloads tools, venv, model)
powershell -ExecutionPolicy Bypass -File packaging\build.ps1 -AllowWingetInstall -Version 0.5.3 -BuildInstaller
```

---

## Related documents

- `docs/INSTALLER_QUICKSTART.md` — Carl installer walkthrough
- `docs/USER_GUIDE.md` — day-to-day operator workflow
- `docs/OLLAMA_SETUP.md` — optional Ollama configuration
- `docs/MILESTONE_4.md` — prior milestone (operator UI + exports)
