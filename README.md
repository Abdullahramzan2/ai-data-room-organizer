# AI-Assisted Data Room File Organizer

Local tool to ingest, classify, and organize large document batches into a data-room folder structure with a searchable static index.

**Milestone 1 (June 12)** delivers repo setup, taxonomy YAML, core ingestion, Tesseract OCR integration, and architecture documentation. See `docs/MILESTONE_1.md` for the full deliverables report.

## Requirements

- Python 3.11+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) on system `PATH` (for scanned PDFs and images)
- [Poppler](https://poppler.freedesktop.org/) on `PATH` (for PDF page rendering before OCR)
- [LibreOffice](https://www.libreoffice.org/) for legacy `.doc` and `.ppt` (recommended)
- Optional: Microsoft Office on Windows (COM fallback), or `antiword` / `catdoc` for `.doc`

### Windows setup (Tesseract + Poppler + LibreOffice)

```powershell
# Tesseract (via Chocolatey)
choco install tesseract

# Poppler for Windows — add bin/ to PATH
# https://github.com/oschwartz10612/poppler-windows/releases

# LibreOffice for legacy .doc / .ppt conversion
choco install libreoffice-fresh
```

## Installation

```powershell
cd "AI-Assisted Data Room File Organizer"
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

## Quick start

```powershell
# List taxonomy categories (00–19)
dataroom taxonomy

# Ingest a folder (input and output paths can be anywhere on the system)
dataroom ingest "D:\YourMasterFolder" --output "C:\Reports\ingestion.json"

# Disable OCR for a quick native-text-only pass
dataroom ingest ".\test_input" --no-ocr
```

## Project layout

```
config/default.yaml          # Application settings
taxonomy/
  real_estate_development.yaml   # 20-folder default taxonomy (00–19)
src/dataroom/
  ingestion/                   # File scan, extract, route
  ocr/                         # Tesseract integration
  cli.py                       # CLI entry point
docs/MILESTONE_1.md            # Milestone 1 deliverables (client report)
docs/ARCHITECTURE.md           # Technical architecture
tests/                         # Unit tests
```

## Supported file types (Milestone 1)

| Extension | Method |
|-----------|--------|
| `.pdf` | Native text (PyMuPDF) + OCR fallback |
| `.docx`, `.xlsx`, `.pptx` | Native Office parsers |
| `.doc` | LibreOffice → DOCX, Word COM, antiword/catdoc, or OCR fallback |
| `.xls` | xlrd |
| `.ppt` | LibreOffice → PPTX, PowerPoint COM, or OCR fallback |
| `.jpg`, `.jpeg`, `.png`, `.tif` | Tesseract OCR |
| `.txt` | Direct read |
| `.eml`, `.msg` | Email parsers |

## Taxonomy

Edit `taxonomy/real_estate_development.yaml` (or add a new YAML) to change folder names, descriptions, and keywords. The AI classifier (Milestone 2+) reads descriptions at runtime — swap the file to support legal, PM, or other domains without code changes.

## License

Proprietary. All rights reserved.
