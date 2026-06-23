# AI-Assisted Data Room File Organizer

Local tool to ingest, classify, and organize large document batches into a data-room folder structure. Original source files are never modified.

**Current release: v0.3.0** — see `docs/MILESTONE_3.md` (earlier: `docs/MILESTONE_1.md`, `docs/MILESTONE_2.md`).

## Requirements

- Python 3.11+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) on `PATH`
- [Poppler](https://poppler.freedesktop.org/) on `PATH` (PDF → image for OCR)
- [LibreOffice](https://www.libreoffice.org/) for legacy `.doc` / `.ppt` (recommended)
- Optional: [Ollama](https://ollama.com/) for local Tier 3 LLM escalation

### Windows system tools

```powershell
winget install --id UB-Mannheim.TesseractOCR --accept-package-agreements --accept-source-agreements
winget install --id oschwartz10612.Poppler --accept-package-agreements --accept-source-agreements
tesseract --version
pdftoppm -h
```

Restart the terminal after installing so `PATH` updates. Optional overrides: `ocr.tesseract_cmd` and `ocr.poppler_path` in `config/default.yaml`.

## Installation

From the project root:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[ui]"
dataroom download-models
copy .env.example .env
dataroom doctor
```

`pip install -e ".[ui]"` installs the CLI, Streamlit UI, and all Python dependencies from `pyproject.toml`. Use `pip install -e ".[ui,dev]"` if you also need pytest.

`dataroom download-models` fetches the embedding model (`all-MiniLM-L6-v2`, ~90 MB) once so the first pipeline run does not wait on Hugging Face. If you skip it, the model downloads automatically on the first `dataroom run`.

## Quick start

### CLI

```powershell
dataroom run "C:\path\to\master\folder" --output-dir output\data_room
```

### UI

```powershell
dataroom ui
```

The UI runs the same pipeline in a background subprocess, with folder browse buttons for input/output, review editing, doctor checks, and output browsing.

### Other commands

```powershell
dataroom doctor      # environment health check
dataroom taxonomy    # list loaded categories
dataroom rerun output\data_room   # after review_queue.csv corrections
```

### Pipeline output

Taxonomy subfolders `00`–`19`, plus:

`manifest.csv`, `manifest.xlsx`, `index.html`, `review_queue.csv`, `duplicate_report.csv`, `errors_report.csv`, `audit_log.jsonl`, `run_summary.json`

### Rerun after review

Set `corrected_folder` in `review_queue.csv`, then:

```powershell
dataroom rerun output\data_room
```

### Step-by-step (debugging)

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

## Classification pipeline

1. **Tier 1** — keyword / filename match against taxonomy YAML
2. **Tier 2** — local embeddings (`sentence-transformers` + FAISS)
3. **Tier 3** — optional LLM (OpenAI, Ollama, or enterprise) when local confidence is low

Guardrails in `config/default.yaml` control excerpt limits, local-only file types (`.dwg`, `.kmz`), provider allow/block lists, and audit logging.

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

Edit `taxonomy/real_estate_development.yaml` to change folders, descriptions, and keywords. Point `config/default.yaml` at a different YAML file to support other domains without code changes.

## Project layout

```
config/default.yaml
taxonomy/real_estate_development.yaml
src/dataroom/
  ingestion/        # scan, extract, OCR, KMZ/DWG handlers
  classification/   # keyword, embeddings, provider registry
  guardrails/       # escalation policy + audit log
  organizer/        # copy to taxonomy folders
  export/           # manifest, review queue, HTML index, duplicates
  pipeline/         # dataroom run orchestration
  ui/               # Streamlit UI
  cli.py
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
