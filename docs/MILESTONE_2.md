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

1. **Hybrid classification** — keywords → local embeddings (FAISS) → optional OpenAI for low-confidence docs
2. **Organized folder output** — copy files into taxonomy folders `00`–`19` (originals never modified)
3. **CSV manifest** — one row per file with category, confidence, reason, terms, review flag
4. **Review queue** — CSV subset of files flagged for human review

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

## Classification modes (`.env`)

| Mode | Behavior |
|------|----------|
| `local` | Keywords + embeddings only — no API calls |
| `hybrid` | Local first; OpenAI only for ambiguous docs (**default**) |
| `api` | OpenAI used for low-confidence cases when key is set |

```env
CLASSIFICATION_MODE=hybrid
OPENAI_API_KEY=           # optional
OPENAI_MODEL=gpt-4o-mini
```

---

## Confidence routing

| Level | Action |
|-------|--------|
| **High** (≥ 0.75) | Assign taxonomy folder |
| **Medium** (≥ 0.50) | Assign folder + flag in review queue |
| **Low** (< 0.50) | Route to `19_Unclassified_Review_Queue` |

---

## Acceptance checklist

| Requirement | Status |
|-------------|--------|
| Classify documents into taxonomy folders | Yes — `dataroom run` |
| Copy files to organized folder tree | Yes — originals untouched |
| `manifest.csv` with required columns | Yes |
| `review_queue.csv` for flagged files | Yes |
| Hybrid local-first + optional API | Yes — `.env` controlled |
| Domain-flexible taxonomy YAML | Yes — unchanged from M1 |

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
