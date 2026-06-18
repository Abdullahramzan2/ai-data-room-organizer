# AI-Assisted Data Room File Organizer

Local tool to ingest, classify, and organize large document batches into a data-room folder structure.

**Milestone 3 (v0.3.0)** — enterprise-ready provider plug-ins, hardened guardrails, and error reporting. See `docs/MILESTONE_3.md`. Earlier milestones: `docs/MILESTONE_1.md`, `docs/MILESTONE_2.md`.

## Requirements

- Python 3.11+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) on `PATH`
- [Poppler](https://poppler.freedesktop.org/) on `PATH` (PDF → image for OCR)
- [LibreOffice](https://www.libreoffice.org/) for legacy `.doc` / `.ppt` (recommended)
- Optional: [Ollama](https://ollama.com/) for local Tier 3 LLM escalation

### System dependencies (Windows)

Install Tesseract and Poppler before running OCR on PNGs or scanned PDFs. The app auto-detects common install paths; restart your terminal after installing so `PATH` updates.

```powershell
winget install --id UB-Mannheim.TesseractOCR --accept-package-agreements --accept-source-agreements
winget install --id oschwartz10612.Poppler --accept-package-agreements --accept-source-agreements
```

Verify:

```powershell
tesseract --version
pdftoppm -h
```

Optional overrides in `config/default.yaml`: `ocr.tesseract_cmd`, `ocr.poppler_path`.

## Installation

```powershell
cd "AI-Assisted Data Room File Organizer"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
copy .env.example .env
```

## Quick start

```powershell
# Full pipeline — one command
dataroom run "C:\path\to\master\folder" --output-dir output\data_room

# List taxonomy categories
dataroom taxonomy
```

**Output:** taxonomy subfolders `00`–`19`, `manifest.csv`, `review_queue.csv`, `errors_report.csv`, `audit_log.jsonl`, `run_summary.json`. Source files are never modified.

### Step-by-step (optional, for debugging)

```powershell
dataroom ingest ".\my_folder" --output output\ingestion.json
dataroom classify output\ingestion.json --output output\classification.json --output-dir output\data_room
dataroom organize output\classification.json --output-dir output\data_room
dataroom export output\ingestion.json output\classification.json --output-dir output\data_room
```

Use `--output-dir` on `classify` so guardrails and audit logging match the full pipeline.

## Configuration

Copy `.env.example` to `.env` for secrets and classification mode. Policy (guardrails, thresholds, provider chain) lives in `config/default.yaml`.

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

Example — local Ollama:

```env
CLASSIFICATION_MODE=hybrid
REASONING_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

Example — enterprise gateway:

```env
CLASSIFICATION_MODE=hybrid
REASONING_PROVIDER=enterprise
ENTERPRISE_API_KEY=your-api-key
ENTERPRISE_BASE_URL=https://your-gateway/v1
ENTERPRISE_MODEL=your-model-name
```

Auto chain order is configurable in `config/default.yaml` under `classification.auto_provider_chain`.

## Classification pipeline

1. **Tier 1** — keyword / filename match against taxonomy YAML
2. **Tier 2** — local embeddings (`sentence-transformers` + FAISS)
3. **Tier 3** — optional LLM (OpenAI, Ollama, or enterprise) when local confidence is low

Guardrails in `config/default.yaml` control excerpt limits, local-only file types (`.dwg`, `.kmz`), provider allow/block lists, and audit logging.

## Project layout

```
config/default.yaml
taxonomy/real_estate_development.yaml
src/dataroom/
  ingestion/        # scan, extract, OCR, KMZ/DWG handlers
  classification/   # keyword, embeddings, provider registry
  guardrails/       # escalation policy + audit log
  organizer/        # copy to taxonomy folders
  export/           # manifest, review queue, errors report
  pipeline/         # dataroom run orchestration
  settings.py       # .env-backed settings
  cli.py
docs/MILESTONE_1.md
docs/MILESTONE_2.md
docs/MILESTONE_3.md
docs/CALIBRATION.md
docs/ARCHITECTURE.md
tests/
```

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

## Taxonomy

Edit `taxonomy/real_estate_development.yaml` to change folders, descriptions, and keywords. Swap the YAML file to support other domains (legal, PM, etc.) without code changes.

## Tests

```powershell
pytest -v
```

## License

Proprietary. All rights reserved.
