# Milestone 5 — Windows Installer (Single-Click Delivery)

| | |
|---|---|
| **Client** | Carl Quesinberry |
| **Milestone** | Bundled Windows installer — no Python/pip/terminal setup |
| **Version** | 0.5.0 (package + installer) |
| **Status** | Delivered |

---

## Overview

Carl requested a **single Windows installer** that bundles Python, libraries, Tesseract, Poppler, LibreOffice, and the embedding model. Ollama remains separate with a setup guide.

### Delivered

1. **Windows installer** — `AI-Data-Room-Organizer-Setup.exe` (~602 MB compressed)
2. **Launcher** — `DataRoomOrganizer.exe` (UI, no console) + `DataRoomDoctor.exe` (health check)
3. **Bundled layout** — `app/`, `python/`, `tools/`, `models/`, `launcher/` under install dir
4. **User settings** — `%APPDATA%\DataRoomOrganizer\.env` created on first launch
5. **Start Menu shortcuts** — Data Room Organizer, Data Room Doctor; optional desktop icon
6. **Operator docs** — `docs/INSTALLER_QUICKSTART.md`, `docs/OLLAMA_SETUP.md`, updated `docs/USER_GUIDE.md`
7. **Build pipeline** — `packaging/build.ps1`, staging scripts, Inno Setup (`packaging/installer.iss`)

### Not bundled (by design)

- **Ollama** — optional local LLM; see `docs/OLLAMA_SETUP.md`
- **Git / source repo** — installer is the runtime deliverable

---

## Carl delivery file

| File | Location | Size |
|------|----------|------|
| **Setup installer** | `packaging/dist/AI-Data-Room-Organizer-Setup.exe` | ~602 MB |

Upload this single file to Google Drive, Dropbox, or OneDrive and share the link with Carl.

---

## Local smoke test results (2026-07-04)

Validated from `AI-Data-Room-Organizer-Setup.exe` on Windows 11:

| Test | Result |
|------|--------|
| Silent install to test directory | **Pass** (~6.5 min extract) |
| `DataRoomDoctor.exe` | **Pass** — Python, Tesseract, Poppler, LibreOffice, embedding model all OK |
| Pipeline run (3 sample `.txt` files, bundled tools/models) | **Pass** — 3 processed, 3 organized, manifest + index exported |
| UI launch via bundled launcher | **Pass** — Streamlit HTTP 200 at `http://127.0.0.1:8501` |

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
# Full staging + installer
powershell -ExecutionPolicy Bypass -File packaging\build.ps1 -Version 0.5.0 -BuildInstaller

# Installer only (staging already built)
powershell -ExecutionPolicy Bypass -File packaging\build_installer.ps1 -Version 0.5.0
```

---

## Related documents

- `docs/INSTALLER_QUICKSTART.md` — Carl installer walkthrough
- `docs/OLLAMA_SETUP.md` — optional Ollama configuration
- `docs/USER_GUIDE.md` — day-to-day operator workflow
- `docs/MILESTONE_4.md` — prior milestone (operator UI + exports)
