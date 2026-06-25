# AI-Assisted Data Room File Organizer

Local tool to ingest, classify, and organize large document batches into a data-room folder structure. Original source files are never modified.

**Current release: v0.4.0** — see `docs/MILESTONE_4.md` (earlier: `docs/MILESTONE_1.md`, `docs/MILESTONE_2.md`, `docs/MILESTONE_3.md`).

| Document | Purpose |
|----------|---------|
| `docs/USER_GUIDE.md` | Day-to-day operator workflow |
| `README.md` | Quick install, command reference, and Windows setup (below) |
| `docs/DEMO.md` | Stakeholder demo script |
| `docs/TESTING.md` | QA / acceptance test checklist |
| `docs/CALIBRATION.md` | Threshold and taxonomy tuning |

## Windows installation

Step-by-step setup for **v0.4.0** on Windows 10/11. Open **PowerShell** (not CMD) as a normal user.

### 1. Prerequisites

| Requirement | Notes |
|-------------|-------|
| Windows 10 or 11 | 64-bit |
| Python 3.11+ | From [python.org](https://www.python.org/downloads/) — check **Add Python to PATH** during install |
| Git (optional) | For cloning the repository |
| ~2 GB disk | Python venv, PyTorch, embedding model (~90 MB) |
| Internet (first setup) | Hugging Face model download; optional Ollama model pull |

### 2. Install system tools

**Tesseract OCR**

```powershell
winget install --id UB-Mannheim.TesseractOCR --accept-package-agreements --accept-source-agreements
```

**Poppler** (PDF → image for OCR)

```powershell
winget install --id oschwartz10612.Poppler --accept-package-agreements --accept-source-agreements
```

**LibreOffice** (recommended for legacy `.doc` / `.ppt`)

```powershell
winget install --id TheDocumentFoundation.LibreOffice --accept-package-agreements --accept-source-agreements
```

**Verify** — close and reopen PowerShell, then:

```powershell
tesseract --version
pdftoppm -h
python --version
```

Expected: Python 3.11+ and a Tesseract version string.

If `tesseract` is not found, add `C:\Program Files\Tesseract-OCR` to your user **PATH**, or set `ocr.tesseract_cmd` in `config/default.yaml`.

### 3. Get the project

```powershell
cd $env:USERPROFILE\Desktop
# If delivered as zip, extract to:
# AI-Assisted Data Room File Organizer
cd "AI-Assisted Data Room File Organizer"
```

### 4. Python environment

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[ui]"
```

This installs the CLI, Streamlit UI, and all dependencies from `pyproject.toml`.

For development / running tests:

```powershell
pip install -e ".[ui,dev]"
```

`requirements.txt` lists core runtime packages only (legacy reference). **Do not** rely on `pip install -r requirements.txt` for the UI — use the `[ui]` extra above.

Stop `dataroom ui` before reinstalling, or Windows may lock `dataroom.exe` during `pip install`.

### 5. Download embedding model

```powershell
dataroom download-models
```

Downloads `all-MiniLM-L6-v2` (~90 MB) to the Hugging Face cache. Run once per machine.

If skipped, the model downloads automatically on the first `dataroom run` (you will see a message in the log).

### 6. Configuration

```powershell
copy .env.example .env
notepad .env
```

Minimum for local-only classification:

```env
CLASSIFICATION_MODE=local
REASONING_PROVIDER=local
```

Recommended with local Ollama:

```env
CLASSIFICATION_MODE=hybrid
REASONING_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

Policy (thresholds, guardrails, duplicates) lives in `config/default.yaml` — no secrets there.

### 7. Verify installation

```powershell
dataroom doctor
```

| Status | Meaning |
|--------|---------|
| **PASS** | Ready |
| **WARN** | Optional component missing (may be OK) |
| **FAIL** | Fix before running batches |

All **fail** items must be resolved. Common fixes:

| Check | Fix |
|-------|-----|
| `embedding_model` | `dataroom download-models` |
| `tesseract` | Install Tesseract; restart terminal |
| `poppler` | Install Poppler; restart terminal |
| `libreoffice` | Install LibreOffice (only needed for legacy Office) |
| `ollama` | Install [Ollama](https://ollama.com/); run `ollama pull llama3.2` |

### 8. Optional: Ollama (local LLM)

1. Download and install from [ollama.com](https://ollama.com/)
2. Pull a model:

```powershell
ollama pull llama3.2
```

3. Confirm:

```powershell
ollama list
```

4. Set `.env` as shown in step 6.

### 9. Smoke test

```powershell
dataroom taxonomy
dataroom run "C:\path\to\test\folder" --output-dir output\smoke_test
```

Or launch the UI:

```powershell
dataroom ui
```

Browser opens at `http://localhost:8501`.

### 10. Firewall and corporate networks

| Service | Endpoint | When needed |
|---------|----------|-------------|
| Hugging Face | `huggingface.co` | First embedding model download |
| Ollama | `localhost:11434` | Local Tier 3 only |
| Enterprise gateway | Your `ENTERPRISE_BASE_URL` | If using enterprise provider |

If Hugging Face is blocked, download the model on a connected machine and copy the cache folder, or ask IT to allow `huggingface.co` for one-time setup.

### 11. Updating the tool

```powershell
cd "AI-Assisted Data Room File Organizer"
git pull   # if using git
.venv\Scripts\activate
# Stop dataroom ui first if running (avoids WinError 32 on dataroom.exe)
pip install -e ".[ui]"
dataroom doctor
```

### 12. Uninstall

```powershell
deactivate
Remove-Item -Recurse -Force .venv
```

System tools (Tesseract, Poppler, LibreOffice) are removed separately via Windows Settings → Apps.

## Quick start

```powershell
# CLI — full pipeline
dataroom run "C:\path\to\master\folder" --output-dir output\data_room

# UI — run, review, doctor, outputs (live per-file progress on Run tab)
dataroom ui

# After editing review_queue.xlsx in 00_Admin_and_Index (corrected_folder column)
dataroom rerun output\data_room
```

### Other commands

```powershell
dataroom doctor
dataroom taxonomy
dataroom download-models
```

### Pipeline output

Taxonomy subfolders `01`–`19` for organized document copies, plus **`00_Admin_and_Index/`** for Carl deliverables:

| Location | Files |
|----------|--------|
| `00_Admin_and_Index/` | `manifest.xlsx`, `index.html`, `review_queue.xlsx`, `duplicate_report.xlsx`, `errors_report.xlsx`, `classification_log.xlsx`, `source_authentication_matrix.xlsx` |
| Output root | `run_summary.json`, `processing_log.json`, `run_progress.json` (live UI), `ingestion_cache.json`, `classification_cache.json`, `audit_log.jsonl` |

Original source files are never modified.

### Step-by-step (debugging)

```powershell
dataroom ingest ".\my_folder" --output output\ingestion.json
dataroom classify output\ingestion.json --output output\classification.json --output-dir output\data_room
dataroom organize output\classification.json --output-dir output\data_room
dataroom export output\ingestion.json output\classification.json --output-dir output\data_room
```

## Configuration reference

Copy `.env.example` to `.env` for secrets and classification mode (see **Windows installation → step 6**). Policy lives in `config/default.yaml`.

### Classification modes (`.env`)

| Mode | Description |
|------|-------------|
| `local` | Keywords + embeddings only — Tier 3 never runs |
| `hybrid` | Local first; LLM only for ambiguous docs (recommended) |
| `api` | LLM-assisted for low-confidence cases when a provider is configured |

### Reasoning providers (`.env` → `REASONING_PROVIDER`)

| Value | Description |
|-------|-------------|
| `auto` | Walk `classification.auto_provider_chain` in config (default) |
| `local` | No Tier 3 escalation |
| `openai` | OpenAI API (`OPENAI_API_KEY`) |
| `ollama` | Local Ollama (`OLLAMA_BASE_URL`, `OLLAMA_MODEL`) |
| `enterprise` | OpenAI-compatible gateway (`ENTERPRISE_*` vars) |

## Classification pipeline

1. **Tier 1** — keyword / filename match against taxonomy YAML
2. **Tier 2** — local embeddings (`sentence-transformers` + FAISS)
3. **Tier 3** — optional LLM when local confidence is low

Guardrails control excerpt limits, local-only types (`.dwg`, `.kmz`), provider allow/block lists, and audit logging.

## Supported file types

| Extension | Method |
|-----------|--------|
| `.pdf` | Native text + OCR fallback |
| `.docx`, `.xlsx`, `.pptx` | Native Office parsers |
| `.doc`, `.ppt` | LibreOffice / COM / OCR fallback |
| `.jpg`, `.png`, `.tif` | Tesseract OCR |
| `.txt`, `.eml`, `.msg` | Direct / email parsers |
| `.kmz` | KML placemark parsing (local-only) |
| `.dwg` | Filename/folder context (local-only) |

## Project layout

```
config/default.yaml
taxonomy/real_estate_development.yaml
src/dataroom/
  ingestion/        # scan, extract, OCR, KMZ/DWG
  classification/   # keyword, embeddings, providers
  guardrails/       # escalation policy + audit log
  organizer/        # copy to taxonomy folders
  export/           # manifest, review queue, HTML index, duplicates
  pipeline/         # run, rerun, cache
  doctor/           # environment checks
  ui/               # Streamlit UI
docs/
tests/
```

## Tests

```powershell
pip install -e ".[ui,dev]"
pytest -v
```

See `docs/TESTING.md` for manual QA checklist (run options, duplicates, review/rerun, UI tabs).

## License

Proprietary. All rights reserved.
