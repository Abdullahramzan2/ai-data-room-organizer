# Milestone 1 — Deliverables
## AI-Assisted Data Room File Organizer

| | |
|---|---|
| **Client** | Carl Quesinberry |
| **Milestone** | Project Mobilization — Design / Architecture |
| **Due** | June 12, 2026 |
| **Status** | Delivered |
| **Version** | 0.1.0 |

---

## Overview

Milestone 1 establishes the foundation of the data room organizer: a working repository, configurable taxonomy, a document ingestion pipeline for all required file types, Tesseract OCR for scanned documents, and a technical architecture document.

The tool can scan a master folder, extract text and metadata from supported files, and write structured JSON results. Taxonomy folder definitions are ready for AI-guided classification in the next phase of work.

---

## Deliverables completed

### 1. Repository setup

A complete, installable Python project:

| Item | Location |
|------|----------|
| Application source | `src/dataroom/` |
| Configuration | `config/default.yaml` |
| Dependencies | `requirements.txt`, `pyproject.toml` |
| Install guide | `README.md` |
| Ignore rules | `.gitignore` |
| Unit tests | `tests/` (17 tests, all passing) |

**Install:**

```powershell
cd "AI-Assisted Data Room File Organizer"
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

**CLI commands:**

```powershell
dataroom taxonomy
dataroom ingest "<input_folder>" --output "<output_file>.json"
dataroom ingest "<input_folder>" --no-ocr
```

---

### 2. Taxonomy YAML (folders 00–19)

**File:** `taxonomy/real_estate_development.yaml`

Twenty data room categories from the project specification, each with:

- `id` — category number
- `folder` — data room folder name
- `description` — semantic context for AI classification
- `keywords` — matching terms

| ID | Folder |
|----|--------|
| 00 | `00_Admin_and_Index` |
| 01 | `01_Project_Overview` |
| 02 | `02_Land_Control_and_PSA` |
| 03 | `03_Title_Survey_and_ALTA` |
| 04 | `04_Zoning_Land_Use_and_Local_Approvals` |
| 05 | `05_Environmental_RCRA_BRAC_FOSET` |
| 06 | `06_Wetlands_Streams_USACE` |
| 07 | `07_Floodplain_Drainage_and_Stormwater` |
| 08 | `08_Geotechnical_and_Soils` |
| 09 | `09_Civil_Engineering_and_Site_Planning` |
| 10 | `10_Power_Utility_AEP_SWEPCO` |
| 11 | `11_BTM_Generation_BESS_and_Energy` |
| 12 | `12_Natural_Gas` |
| 13 | `13_Water_and_Wastewater` |
| 14 | `14_Fiber_and_Telecom` |
| 15 | `15_Permitting_FAST41_Federal_State` |
| 16 | `16_Vendors_Proposals_and_Budgets` |
| 17 | `17_Capital_Markets_and_Investor_Materials` |
| 18 | `18_Correspondence` |
| 19 | `19_Unclassified_Review_Queue` |

**Domain flexibility:** To reuse the engine for legal proceedings, project management, or other document sets, create a new YAML file and point `paths.taxonomy_file` in config at it. No code changes required.

---

### 3. Core ingestion module

**Location:** `src/dataroom/ingestion/`

The pipeline scans a master folder and extracts text and metadata from every supported file.

```
Master Folder → Scanner → Router → Extractor → (OCR if needed) → JSON output
```

| Component | Role |
|-----------|------|
| `scanner.py` | Recursively find supported files; collect size and dates |
| `router.py` | Route each file to the correct extractor by extension |
| `pipeline.py` | Orchestrate batch processing |
| `models.py` | Structured results (`ExtractedDocument`, `IngestionResult`) |
| `extractors/` | Per-file-type text extraction |

#### Supported file types

| Extension | Method |
|-----------|--------|
| `.pdf` | Native text (PyMuPDF) + OCR fallback |
| `.docx`, `.xlsx`, `.pptx` | Native Office parsers |
| `.doc` | LibreOffice → DOCX, Word COM, antiword/catdoc, or OCR fallback |
| `.ppt` | LibreOffice → PPTX, PowerPoint COM, or OCR fallback |
| `.xls` | xlrd |
| `.jpg`, `.jpeg`, `.png`, `.tif`, `.tiff` | Tesseract OCR |
| `.txt` | Direct read (multi-encoding) |
| `.eml`, `.msg` | Email parsers |

#### Per-file JSON output fields

| Field | Description |
|-------|-------------|
| `source_path` | Full path to the file processed |
| `file_name`, `extension`, `file_size` | File identity |
| `created_at`, `modified_at` | Filesystem timestamps |
| `page_count` | For PDFs and presentations |
| `text_content` | Native extracted text |
| `ocr_text` | OCR supplement when applied |
| `extraction_method` | `native`, `ocr`, `hybrid`, `failed`, or `skipped` |
| `errors`, `warnings` | Explicit reasons when something fails |

**Note on dates:** `created_at` and `modified_at` are filesystem timestamps for the file at the path processed. On Windows, copying a file into a new folder resets `created_at` to the copy time while `modified_at` preserves the original content date.

---

### 4. Tesseract OCR integration

**Location:** `src/dataroom/ocr/tesseract.py`

- Runs automatically when native PDF text is below 50 characters (configurable)
- Always runs for image files
- Used as last resort for legacy `.doc` / `.ppt` (via PDF conversion)

**Configuration** (`config/default.yaml`):

```yaml
ocr:
  enabled: true
  min_native_text_chars: 50
  language: eng
  pdf_dpi: 300
  tesseract_cmd: null
```

**Host tools required for OCR:**

- Tesseract on system PATH
- Poppler on PATH (for rendering PDF pages before OCR)

If Tesseract is not installed, ingestion continues with native text only and records a warning.

---

### 5. Legacy Office handling (`.doc` and `.ppt`)

**Location:** `src/dataroom/ingestion/extractors/legacy_office.py`

Legacy binary Office files use a multi-step fallback chain. If all methods fail, a clear error lists what was attempted.

**`.doc` order:** LibreOffice → DOCX → Word COM → antiword → catdoc → LibreOffice PDF → OCR

**`.ppt` order:** LibreOffice → PPTX → PowerPoint COM → LibreOffice PDF → OCR

**Configuration** (`config/default.yaml`):

```yaml
legacy_office:
  libreoffice_cmd: null
  enable_com: true
  conversion_timeout: 120
```

---

### 6. Architecture document

**File:** `docs/ARCHITECTURE.md`

Technical architecture of the delivered system: pipeline design, data models, configuration, technology stack, repository layout, and host dependencies.

---

## How to run

### List taxonomy

```powershell
dataroom taxonomy
```

### Ingest a master folder

Input and output paths can be **anywhere on the system** (any drive, absolute or relative path). The input must be an **existing folder** (not a single file). Parent folders for the output file are created automatically.

```powershell
dataroom ingest "D:\Projects\MasterFolder" --output "C:\Reports\ingestion.json"
```

### Run tests

```powershell
pytest -v
```

---

## Host dependencies

| Tool | Purpose |
|------|---------|
| Python 3.11+ | Runtime |
| Tesseract | Scanned PDFs, images, OCR fallback |
| Poppler | PDF page rendering before OCR |
| LibreOffice | Legacy `.doc` / `.ppt` (recommended) |
| Microsoft Office | Optional COM fallback on Windows |

---

## Project structure

```
AI-Assisted Data Room File Organizer/
├── config/default.yaml
├── taxonomy/real_estate_development.yaml
├── src/dataroom/
│   ├── cli.py
│   ├── config.py
│   ├── ingestion/          # scanner, router, pipeline, extractors
│   └── ocr/                # Tesseract integration
├── docs/
│   ├── MILESTONE_1.md      # this document
│   └── ARCHITECTURE.md
├── tests/
├── requirements.txt
├── pyproject.toml
└── README.md
```

**Do not include in source handoff:** `.venv/`, `*.egg-info/`, `__pycache__/`, `.pytest_cache/` — these are auto-generated at install time.

---

## Acceptance checklist

| Project's requirement | Delivered |
|--------------------|-----------|
| Project mobilization / repo setup | Yes |
| Taxonomy YAML with all folders (00–19) | Yes |
| Core ingestion module for all file types | Yes |
| Tesseract OCR integration | Yes |
| Architecture document | Yes |

---

## Document revision history

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | June 2026 | Initial Milestone 1 deliverables document |
