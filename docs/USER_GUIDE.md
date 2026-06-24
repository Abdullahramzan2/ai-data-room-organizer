# User Guide — Data Room Organizer

Operator guide for Carl Quesinberry and team. For installation, see `docs/INSTALLATION_WINDOWS.md`. For a live walkthrough, see `docs/DEMO.md`.

---

## What this tool does

1. **Scans** a master folder (PDFs, Office files, images, email, KMZ, DWG, etc.)
2. **Extracts** text (native parsers + OCR when needed)
3. **Classifies** each file into taxonomy folders `00`–`19`
4. **Copies** organized copies into an output data room
5. **Exports** manifest, review queue, duplicates report, HTML index, classification log, processing log, and audit logs

**Original source files are never modified or moved.**

---

## Daily workflow

### 1. Prepare

```powershell
.venv\Scripts\activate
dataroom doctor
```

Fix any **fail** items before large batches. Warnings (e.g. LibreOffice missing) may be acceptable if you do not process legacy `.doc` / `.ppt`.

### 2. Run the pipeline

**CLI (recommended for large batches):**

```powershell
dataroom run "D:\Projects\Sample Data" --output-dir output\project_alpha
```

**UI (recommended for review and exploration):**

```powershell
dataroom ui
```

In the sidebar, set **Input folder** and **Output directory** (use **Browse…**), then click **Run pipeline** on the Run tab.

Options:

| Flag / checkbox | Effect |
|-----------------|--------|
| `--rename` / Rename files | Apply standardized naming (see **Rename format** below) |
| `--no-ocr` / Disable OCR | Skip Tesseract (faster; scanned PDFs may have little text) |
| `--no-recursive` / Non-recursive | Only scan top-level files |

### 3. Review results

Open the output folder:

| File | Use |
|------|-----|
| `run_summary.json` | Quick counts (processed, organized, review queue, duplicates) |
| `manifest.csv` / `manifest.xlsx` | Full per-file record — open in Excel |
| `index.html` | Double-click to browse with search (no server needed) |
| `review_queue.csv` | Files needing human attention |
| `duplicate_report.csv` | Exact and near-duplicate pairs |
| `errors_report.csv` | Skipped or failed files |
| `classification_log.csv` | Per-file classification audit trail |
| `processing_log.json` | Run metadata, counts, and timings |
| `audit_log.jsonl` | Tier 3 LLM escalation decisions (API/guardrails only) |

Organized copies live in subfolders `00_…` through `19_…` under the output directory.

**Admin folder (`00_Admin_and_Index/`):** Carl spec admin deliverables are written here — master index (`index.html`), manifest, classification log, review queue, duplicate report, source authentication matrix, errors report, and processing log. Operational caches and `run_summary.json` stay at the output root for the tool; a copy of `run_summary.json` is also placed in folder 00.

---

## Rename format

When **Rename files** is enabled, organized copies use:

`YYYY-MM-DD__CategoryShort__Source__ShortDesc__OriginalFileName.ext`

| Token | Source |
|-------|--------|
| Date | Email header date → `YYYY-MM-DD` in document text → file modified date → `unknown-date` |
| CategoryShort | Taxonomy folder name after the numeric prefix |
| Source | Email `From`, first detected entity, or capitalized phrase in text (max 30 chars) |
| ShortDesc | Email subject or first meaningful text line (max 40 chars) |
| OriginalFileName | Unchanged source filename including extension |

Source and ShortDesc segments are omitted when not detected. Example:

`2024-06-18__Environmental_RCRA_BRAC_FOSET__USACE__Wetland_report__delineation.pdf`

---

### 4. Correct misclassified files

**Option A — UI (Review tab)**

1. Open `dataroom ui` → **Review**
2. Pick **Corrected folder** from the dropdown for each row
3. Click **Save review queue**
4. Click **Rerun with corrections**

**Option B — CSV**

1. Edit `review_queue.csv`
2. Fill `corrected_folder` with a valid folder name (e.g. `04_Zoning_Land_Use_and_Local_Approvals`)
3. Save the file
4. Run:

```powershell
dataroom rerun output\project_alpha
```

Rerun uses cached ingestion/classification — **no re-OCR**, typically completes in seconds.

### 5. Calibrate (optional)

If many files land in review queue or wrong folders:

- Adjust thresholds in `config/default.yaml` — see `docs/CALIBRATION.md`
- Add keywords to `taxonomy/real_estate_development.yaml`
- Rerun on a test output folder before processing production data

---

## Streamlit UI reference

| Tab | Purpose |
|-----|---------|
| **Run** | Execute full pipeline; live per-file progress; run summary with all export paths |
| **Review** | Edit `corrected_folder` (including duplicate-flagged rows), optional rename on rerun, save, rerun |
| **Taxonomy** | View category IDs, folders, keyword counts |
| **Doctor** | Environment check (Python, Tesseract, embedding model, Ollama) |
| **Outputs** | Run summary, manifest preview (snippet/duplicate columns), processing log, admin mirror list, artifact table, HTML index path |

Config path is shown read-only in the sidebar (`config/default.yaml`).

---

## HTML index

`index.html` is a self-contained static page. Open it from Explorer or:

```powershell
start output\project_alpha\index.html
```

**Link modes** (`output.index_link_mode` in config):

| Mode | Links point to |
|------|----------------|
| `original` | Source file path (default — good for shared drives) |
| `organized` | Copy inside the data room output |
| `relative` | Relative path from output folder |

Use search/filter boxes in the page to find files by name, folder, confidence, text snippet, or duplicate status. Filters are available for **Review** and **Duplicates**.

---

## Duplicate report

When `duplicates.enabled: true` (default):

- **Exact** — same SHA-256 file hash
- **Near** — high text similarity (configurable threshold)

Review `duplicate_report.csv` before sharing the data room externally. When `duplicates.flag_for_review` is enabled (default), files in duplicate pairs are also added to `review_queue.csv` with a duplicate reason appended.

The tool reports duplicates within the scanned input batch; it does not delete or merge files automatically, and it does not detect duplicates across separate runs or unrelated folders.

---

## Classification modes

Set in `.env` (copy from `.env.example`):

| Mode | Behavior |
|------|----------|
| `local` | Keywords + embeddings only; no LLM |
| `hybrid` | Local first; LLM for ambiguous files (recommended) |
| `api` | LLM-assisted when provider configured |

Tier 3 providers: `auto`, `local`, `openai`, `ollama`, `enterprise`. See `README.md` for examples.

KMZ and DWG files are always **local-only** — never sent to external APIs.

---

## Troubleshooting

| Symptom | Action |
|---------|--------|
| First run very slow | Run `dataroom download-models` once after install |
| OCR not working | `dataroom doctor` — install Tesseract + Poppler; restart terminal |
| Legacy `.doc` fails | Install LibreOffice; check doctor |
| `rerun` says missing cache | Run full `dataroom run` first on that output folder |
| UI shows subprocess error | Read the error message; fix paths or run `dataroom doctor` |
| Cannot save review queue | Close `review_queue.csv` in Excel or another editor, then retry |
| Ollama not used | Start `ollama serve`; set `REASONING_PROVIDER=ollama` in `.env` |
| Same file in/out of review queue | Tier 3 (Ollama) is non-deterministic for ambiguous docs — see `docs/CALIBRATION.md` |
| Review queue empty but files look wrong | Check `manifest.csv` — only medium/low confidence rows appear in review queue |
| Re-run stacks `_2`, `_3` filenames | Use a fresh output folder for clean demos; rerun does not delete old copies |
| Duplicates not found | Duplicates are within the **input batch only**, not across folders or prior runs |

---

## Command quick reference

```powershell
dataroom run <input_dir> --output-dir <output>
dataroom rerun <output_dir>
dataroom doctor
dataroom download-models
dataroom taxonomy
dataroom ui
```

---

## Related documents

- `docs/INSTALLATION_WINDOWS.md` — setup from scratch
- `docs/DEMO.md` — guided demo for stakeholders
- `docs/TESTING.md` — QA / acceptance checklist
- `docs/CALIBRATION.md` — tuning thresholds and taxonomy
- `docs/MILESTONE_4.md` — milestone delivery summary
