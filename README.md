# AI-Assisted Data Room File Organizer

Local tool to ingest, classify, and organize large document batches into a data-room folder structure.

**Milestone 2 (v0.2.0)** — full prototype: classify → organize → manifest. See `docs/MILESTONE_2.md`.

## Requirements

- Python 3.11+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) on `PATH`
- [Poppler](https://poppler.freedesktop.org/) on `PATH` (PDF → image for OCR)
- [LibreOffice](https://www.libreoffice.org/) for legacy `.doc` / `.ppt` (recommended)

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

**Output:** taxonomy subfolders `00`–`19`, `manifest.csv`, `review_queue.csv`, `run_summary.json`. Source files are never modified.

### Step-by-step (optional, for debugging)

```powershell
dataroom ingest ".\my_folder" --output output\ingestion.json
dataroom classify output\ingestion.json --output output\classification.json
dataroom organize output\classification.json --output-dir output\data_room
dataroom export output\ingestion.json output\classification.json --output-dir output\data_room
```

## Classification modes

Set in `.env`:

| Mode | Description |
|------|-------------|
| `local` | Keywords + embeddings only |
| `hybrid` | Local first, API for ambiguous docs (default) |
| `api` | API-assisted when key is set |

## Project layout

```
config/default.yaml
taxonomy/real_estate_development.yaml
src/dataroom/
  ingestion/        # M1 — scan, extract, OCR
  classification/   # M2 — keyword, embeddings, optional OpenAI
  organizer/        # M2 — copy to taxonomy folders
  export/           # M2 — manifest + review queue CSV
  pipeline/         # M2 — dataroom run orchestration
  cli.py
docs/MILESTONE_1.md
docs/MILESTONE_2.md
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

## Taxonomy

Edit `taxonomy/real_estate_development.yaml` to change folders, descriptions, and keywords. Swap the YAML file to support other domains (legal, PM, etc.) without code changes.

## License

Proprietary. All rights reserved.
