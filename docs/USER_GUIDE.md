# User Guide — Data Room Organizer

Operator guide for Carl Quesinberry and team. For installation, see `docs/INSTALLATION_WINDOWS.md`. For a live walkthrough, see `docs/DEMO.md`.

---

## What this tool does

1. **Scans** a master folder (PDFs, Office files, images, email, KMZ, DWG, etc.)
2. **Extracts** text (native parsers + OCR when needed)
3. **Classifies** each file into taxonomy folders `00`–`19`
4. **Copies** organized copies into an output data room
5. **Exports** manifest, review queue, duplicates report, HTML index, and audit logs

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
| `--rename` / Rename files | Apply taxonomy-based naming (default: preserve original names) |
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
| `audit_log.jsonl` | Tier 3 LLM escalation decisions |

Organized copies live in subfolders `00_…` through `19_…` under the output directory.

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
| **Run** | Execute full pipeline; shows metrics summary when done |
| **Review** | Edit `corrected_folder`, save, rerun |
| **Taxonomy** | View category IDs, folders, keyword counts |
| **Doctor** | Environment check (Python, Tesseract, embedding model, Ollama) |
| **Outputs** | Run summary + list of generated artifacts |

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

Use search/filter boxes in the page to find files by name, folder, or confidence.

---

## Duplicate report

When `duplicates.enabled: true` (default):

- **Exact** — same SHA-256 file hash
- **Near** — high text similarity (configurable threshold)

Review `duplicate_report.csv` before sharing the data room externally. The tool reports duplicates; it does not delete or merge files automatically.

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
| UI shows subprocess error | Expand **Process log**; fix path or run `dataroom doctor` |
| Ollama not used | Start `ollama serve`; set `REASONING_PROVIDER=ollama` in `.env` |
| Review queue empty but files look wrong | Check `manifest.csv` — only medium/low confidence rows appear in review queue |

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
- `docs/CALIBRATION.md` — tuning thresholds and taxonomy
- `docs/MILESTONE_4.md` — milestone delivery summary
