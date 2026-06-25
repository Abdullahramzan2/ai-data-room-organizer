# Milestone 4 — Production Polish + Operator UI

| | |
|---|---|
| **Client** | Carl Quesinberry |
| **Milestone** | Production-ready exports, operator tooling, and rerun workflow |
| **Version** | 0.4.0 |
| **Status** | Delivered |

---

## Overview

Milestone 4 turns the prototype into an **operator-ready** data room tool: richer exports, duplicate detection, environment diagnostics, correction reruns without re-OCR, and an optional Streamlit UI.

### Delivered capabilities

1. **Pipeline caches** — `ingestion_cache.json` and `classification_cache.json` persisted per output run
2. **Duplicate detection** — SHA-256 exact matches + near-text similarity; `duplicate_report.xlsx` in `00_Admin_and_Index/`
3. **Excel manifest** — `manifest.xlsx` with extended columns (hash, dates, size)
4. **HTML index** — searchable static `index.html` with configurable link modes (`original` | `organized` | `relative`)
5. **Doctor CLI** — `dataroom doctor` environment health checks with fix instructions
6. **Rerun after corrections** — `corrected_folder` column in review queue; `dataroom rerun` re-organizes without re-ingesting
7. **Streamlit UI** — optional `[ui]` extra: run, review, taxonomy, doctor, outputs (`dataroom ui`)
8. **Model setup** — `dataroom download-models` pre-caches the embedding model
9. **Batch embeddings** — faster classification on multi-file runs
10. **Documentation** — user guide, Windows install guide, demo script, QA testing guide (this milestone)

### Post-delivery polish (v0.4.0)

- Streamlit UI shows metrics summary only (no raw JSON / process log panels)
- Review queue save uses atomic write with retries; clear error if CSV is locked (e.g. open in Excel)
- `dataroom download-models` for one-time embedding model cache
- `.streamlit/config.toml` disables file watcher noise on Windows

---

## Before / after (Carl sample data)

Validated on 19-file sample set with hybrid classification and local Ollama Tier 3.

| Capability | Milestone 3 | Milestone 4 |
|------------|-------------|-------------|
| Manifest formats | CSV only | CSV + **Excel** |
| Browse organized files | Folder tree only | **HTML index** with search/filter |
| Duplicate awareness | None | **`duplicate_report.xlsx`** in `00_Admin_and_Index/` |
| Re-run after manual fixes | Full `dataroom run` (re-OCR) | **`dataroom rerun`** from cache |
| Environment validation | Manual | **`dataroom doctor`** |
| Operator interface | CLI only | **Streamlit UI** (optional) |
| First-run model wait | Surprise Hugging Face download | **`dataroom download-models`** + auto-ensure on run |
| UI pipeline stability | N/A | Subprocess runner (isolates heavy work) |

Typical full pipeline time on 19 sample files: **~4 minutes** (includes ingestion, batch embeddings, organize, exports). Rerun after corrections: **seconds** (no re-OCR).

---

## New outputs

Carl deliverables are written under **`00_Admin_and_Index/`** (folder 00 in the taxonomy). Operational files stay at the **output root**.

| File | Location | Purpose |
|------|----------|---------|
| `manifest.xlsx` | `00_Admin_and_Index/` | Excel manifest for analysts |
| `index.html` | `00_Admin_and_Index/` | Static searchable index; open in any browser |
| `duplicate_report.xlsx` | `00_Admin_and_Index/` | Exact and near-duplicate file pairs |
| `review_queue.xlsx` | `00_Admin_and_Index/` | Files flagged for human review |
| `errors_report.xlsx` | `00_Admin_and_Index/` | Skipped or failed files |
| `classification_log.xlsx` | `00_Admin_and_Index/` | Per-file classification audit |
| `processing_log.json` | Output root | Run metadata and timings |
| `source_authentication_matrix.xlsx` | `00_Admin_and_Index/` | Source authentication matrix |
| `ingestion_cache.json` | Output root | Cached ingestion payload for rerun |
| `classification_cache.json` | Output root | Cached classification results for rerun |
| `run_summary.json` | Output root only | Extended summary (counts, paths, rerun flag) |
| `run_progress.json` | Output root | Live UI progress snapshots |
| `audit_log.jsonl` | Output root | Tier 3 LLM audit trail |

---

## Configuration additions (`config/default.yaml`)

```yaml
duplicates:
  enabled: true
  hash_algorithm: sha256
  near_similarity_threshold: 0.92
  min_text_chars_for_near: 100

corrections:
  review_queue_corrected_folder_column: corrected_folder

output:
  manifest_xlsx_file: manifest.xlsx
  duplicate_report_file: duplicate_report.xlsx
  index_html_file: index.html
  index_link_mode: original   # original | organized | relative
  persist_ingestion_cache: true
  ingestion_cache_file: ingestion_cache.json
  classification_cache_file: classification_cache.json
```

---

## CLI commands (new / updated)

```powershell
# Pre-download embedding model (~90 MB, one-time)
dataroom download-models

# Environment health check
dataroom doctor
dataroom doctor --json

# Rerun after editing 00_Admin_and_Index/review_queue.xlsx (corrected_folder column)
dataroom rerun output\data_room

# Launch Streamlit UI (requires pip install -e ".[ui]")
dataroom ui
dataroom ui --port 8502
```

Full pipeline (unchanged entry point):

```powershell
dataroom run "C:\path\to\master\folder" --output-dir output\data_room
```

---

## Review correction workflow

1. Run pipeline → open `00_Admin_and_Index/review_queue.xlsx` or use **Review** tab in UI
2. Set `corrected_folder` to a valid taxonomy folder name (e.g. `01_Project_Overview`)
3. Save the CSV (or click **Save review queue** in UI)
4. Run `dataroom rerun output\data_room` — files move to corrected folders; manifest and index refresh
5. No re-OCR, no re-classification API calls

---

## Streamlit UI

Install with the `[ui]` extra (included in README install flow):

```powershell
pip install -e ".[ui]"
dataroom ui
```

| Tab | Function |
|-----|----------|
| **Run** | Full pipeline with browse buttons; **live progress** (file count, per-file status, review queue counter) |
| **Review** | Edit review queue, save, rerun with corrections |
| **Taxonomy** | Browse loaded categories |
| **Doctor** | Run environment checks |
| **Outputs** | View run summary and artifact list |

The UI invokes `dataroom run` / `dataroom rerun` in a **background subprocess** so Streamlit stays responsive during long batches.

---

## Documentation map

| Document | Audience |
|----------|----------|
| `README.md` | Quick install and command reference |
| `docs/USER_GUIDE.md` | Day-to-day operator workflow |
| `README.md` | Install, commands, and Windows setup |
| `docs/DEMO.md` | Step-by-step demo script |
| `docs/TESTING.md` | QA / acceptance test checklist |
| `docs/CALIBRATION.md` | Threshold and taxonomy tuning (updated for rerun) |
| `docs/ARCHITECTURE.md` | Technical architecture (updated for M4) |

---

## Acceptance checklist

| Requirement | Status |
|-------------|--------|
| Ingestion + classification cache persisted | Yes |
| Duplicate detection (exact + near-text) | Yes |
| Excel manifest export | Yes |
| Static HTML index with search | Yes |
| `dataroom doctor` with actionable fixes | Yes |
| `corrected_folder` + `dataroom rerun` | Yes |
| Streamlit UI (run, review, taxonomy, doctor, outputs) | Yes |
| `dataroom download-models` | Yes |
| Batch embedding classification | Yes |
| User guide + Windows install + demo docs | Yes |
| QA testing guide (`docs/TESTING.md`) | Yes |
| README / architecture / calibration updated | Yes |
| Version bumped to 0.4.0 | Yes |

---

## Tests

```powershell
pip install -e ".[ui,dev]"
pytest -v
```

**140** automated tests covering pipeline, duplicates, rerun, doctor, UI helpers, live progress, HTML index, review queue I/O, model setup, and exports.
