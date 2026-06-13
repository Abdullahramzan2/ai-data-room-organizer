# Milestone 2 — Prototype Deliverables
## AI-Assisted Data Room File Organizer

| | |
|---|---|
| **Client** | Carl Quesinberry |
| **Milestone** | Prototype — Classify, Organize, Manifest |
| **Version** | 0.2.0 |
| **Status** | Delivered |

---

## Overview

Milestone 2 adds a runnable prototype on top of Milestone 1 ingestion:

1. **Hybrid classification** — keywords → local embeddings (FAISS) → optional reasoning provider for low-confidence docs
2. **Model-agnostic reasoning** — swappable providers (local, OpenAI, Ollama) via config
3. **Guardrails** — policy in `config/default.yaml` controls external API use, excerpt limits, and local-only file types
4. **KMZ / DWG support** — dedicated local handlers for geographic and CAD files
5. **Organized folder output** — copy files into taxonomy folders `00`–`19` (originals never modified)
6. **CSV manifest** — one row per file with category, confidence, classification basis, handler signals, and review flags
7. **Review queue** — CSV subset of files flagged for human review
8. **Audit log** — JSONL record of every escalation decision (what was sent, why, which provider)

---

## Quick start

```powershell
cd "AI-Assisted Data Room File Organizer"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
copy .env.example .env

# One command — ingest, classify, organize, export
dataroom run "C:\path\to\your\folder" --output-dir output\data_room
```

**Output:**

```
output\data_room\
├── 00_Admin_and_Index\
├── ...
├── 19_Unclassified_Review_Queue\
├── manifest.csv
├── review_queue.csv
├── audit_log.jsonl
└── run_summary.json
```

---

## CLI commands

| Command | Purpose |
|---------|---------|
| `dataroom run <input_dir> --output-dir <path>` | Full pipeline (recommended) |
| `dataroom ingest <folder> --output file.json` | Extract text only (debug) |
| `dataroom classify ingestion.json --output classification.json` | Classify only |
| `dataroom organize classification.json --output-dir <path>` | Copy to folders |
| `dataroom export ingestion.json classification.json --output-dir <path>` | Write CSVs |

Optional flags: `--rename` (standardized file names), `--no-ocr`, `--no-recursive`

---

## Classification pipeline

### Tier 1 — Keywords
Match file name and extracted text against taxonomy keywords. Strong filename hits (including acronyms such as BRAC, ESA) route directly without dilution from weaker embedding scores.

### Tier 2 — Embeddings
FAISS + `sentence-transformers` compare document excerpts to category descriptions.

### Tier 3 — Reasoning provider
When local confidence is below threshold, escalate to the configured provider:

| Provider | Config value | Behavior |
|----------|--------------|----------|
| Local | `local` | No Tier 3 escalation |
| OpenAI | `openai` | Excerpt-only API call when key is set |
| Ollama | `ollama` | Local LLM via Ollama HTTP API; fails gracefully if server is not running |
| Auto | `auto` | OpenAI if key present, else Ollama if running, else local (**default**) |

Set in `config/default.yaml` (`classification.reasoning_provider`) or `.env` (`REASONING_PROVIDER`).

### Classification modes (`.env`)

| Mode | Behavior |
|------|----------|
| `local` | Keywords + embeddings only — no API calls |
| `hybrid` | Local first; reasoning provider only for ambiguous docs (**default**) |
| `api` | Reasoning provider used for low-confidence cases when available |

```env
CLASSIFICATION_MODE=hybrid
REASONING_PROVIDER=auto
OPENAI_API_KEY=           # optional
OPENAI_MODEL=gpt-4o-mini
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

---

## Guardrails (`config/default.yaml`)

All policy lives in the main config file under `guardrails:`:

| Setting | Purpose |
|---------|---------|
| `allow_external_api` | Block OpenAI calls when `false` |
| `max_external_chars` | Cap text sent externally per file |
| `local_only_extensions` | File types that never escalate (`.dwg`, `.kmz`) |
| `local_only_folders` | Path fragments that force local-only |
| `escalation_confidence_threshold` | Only escalate when local score is below this |
| `max_api_cost_per_run_usd` | Cost cap per pipeline run (`0` = unlimited) |
| `uncertain_action` | Default when still ambiguous: `needs_review` |
| `audit_log_enabled` | Write `audit_log.jsonl` in output dir |

Secrets remain in `.env`; policy in `config/default.yaml`.

---

## File type handlers

| Extension | Handler | Extraction |
|-----------|---------|------------|
| `.pdf`, Office, images, email, `.txt` | `standard` | M1 extractors + OCR |
| `.kmz` | `kmz_parser` | Unzip, parse embedded KML — placemarks, descriptions, coordinates, folders |
| `.dwg` | `dwg_handler` | Filename, parent folder, CAD/document siblings (local-only, never sent externally) |

KMZ parse failures fall back to filename-based classification with `parse_status: failed`.

---

## Confidence routing

| Level | Threshold | Action |
|-------|-----------|--------|
| **High** | ≥ 0.75 | Assign taxonomy folder |
| **Medium** | ≥ 0.50 | Assign folder + flag in review queue |
| **Low** | < 0.50 | Route to `19_Unclassified_Review_Queue` |

---

## Manifest columns (`manifest.csv`)

| Column | Description |
|--------|-------------|
| `file_name`, `original_path`, `output_path` | File identity and destination |
| `category_id`, `category_folder` | Assigned taxonomy folder |
| `confidence`, `score` | Confidence level and numeric score |
| `classification_method`, `classification_reason` | How and why classified |
| `classification_basis` | Combined method + reason summary |
| `supporting_terms`, `entities` | Matched keywords and extracted entities |
| `needs_review`, `needs_review_reason` | Human review flags |
| `extraction_method`, `char_count` | Ingestion result |
| `file_type_handler` | `standard`, `kmz_parser`, or `dwg_handler` |
| `parse_status` | `success`, `partial`, or `failed` |
| `extracted_geo_signals` | KMZ placemark/coordinate signals |
| `extracted_cad_signals` | DWG folder/companion context |
| `reasoning_provider` | `local`, `openai`, or `ollama` |
| `api_used` | Whether an external API was called |

---

## Acceptance checklist

| Requirement | Status |
|-------------|--------|
| Classify documents into taxonomy folders | Yes — `dataroom run` |
| Copy files to organized folder tree | Yes — originals untouched |
| `manifest.csv` with category, confidence, reason | Yes |
| `review_queue.csv` for flagged files | Yes |
| Hybrid local-first + optional API | Yes — `.env` + guardrails |
| Model-agnostic reasoning providers | Yes — OpenAI, Ollama, local |
| Guardrails + audit log for external calls | Yes — `config/default.yaml` |
| KMZ local parsing for classification | Yes |
| DWG local-only classification | Yes |
| Domain-flexible taxonomy YAML | Yes — unchanged from M1 |
| OCR for scanned PDFs and images | Yes — Tesseract + Poppler |

---

## Out of scope (later milestones)

- Static HTML index
- Duplicate detection
- Email chain chronology
- UI

---

## Tests

```powershell
pytest -v
```

48 unit tests covering classification, providers, guardrails, KMZ/DWG handlers, organizer, export, and pipeline.
