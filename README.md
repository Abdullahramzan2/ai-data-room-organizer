# AI-Assisted Data Room File Organizer

Local tool to ingest, classify, and organize large document batches into a data-room folder structure. Original source files are never modified.

**Current release: v0.4.0** — see `docs/MILESTONE_4.md` (earlier: `docs/MILESTONE_1.md`, `docs/MILESTONE_2.md`, `docs/MILESTONE_3.md`).

| Document | Purpose |
|----------|---------|
| `docs/USER_GUIDE.md` | Day-to-day operator workflow |
| `docs/INSTALLATION_WINDOWS.md` | Full Windows setup |
| `docs/DEMO.md` | Stakeholder demo script |
| `docs/CALIBRATION.md` | Threshold and taxonomy tuning |

## Requirements

- Python 3.11+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) on `PATH`
- [Poppler](https://poppler.freedesktop.org/) on `PATH` (PDF → image for OCR)
- [LibreOffice](https://www.libreoffice.org/) for legacy `.doc` / `.ppt` (recommended)
- Optional: [Ollama](https://ollama.com/) for local Tier 3 LLM escalation

See `docs/INSTALLATION_WINDOWS.md` for winget commands and troubleshooting.

## Installation

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[ui]"
dataroom download-models
copy .env.example .env
dataroom doctor
```

`pip install -e ".[ui]"` installs the CLI, Streamlit UI, and all Python dependencies. Use `pip install -e ".[ui,dev]"` for pytest.

`dataroom download-models` fetches the embedding model (`all-MiniLM-L6-v2`, ~90 MB) once. If skipped, it downloads on the first `dataroom run`.

## Quick start

```powershell
# CLI — full pipeline
dataroom run "C:\path\to\master\folder" --output-dir output\data_room

# UI — run, review, doctor, outputs
dataroom ui

# After editing review_queue.csv (corrected_folder column)
dataroom rerun output\data_room
```

### Other commands

```powershell
dataroom doctor
dataroom taxonomy
dataroom download-models
```

### Pipeline output

Taxonomy subfolders `00`–`19`, plus `manifest.csv`, `manifest.xlsx`, `index.html`, `review_queue.csv`, `duplicate_report.csv`, `errors_report.csv`, `audit_log.jsonl`, `run_summary.json`, and cache files for rerun.

### Step-by-step (debugging)

```powershell
dataroom ingest ".\my_folder" --output output\ingestion.json
dataroom classify output\ingestion.json --output output\classification.json --output-dir output\data_room
dataroom organize output\classification.json --output-dir output\data_room
dataroom export output\ingestion.json output\classification.json --output-dir output\data_room
```

## Configuration

Copy `.env.example` to `.env` for secrets and classification mode. Policy lives in `config/default.yaml`.

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

## License

Proprietary. All rights reserved.
