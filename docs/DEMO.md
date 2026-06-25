# Demo Script — Data Room Organizer

**Duration:** ~20 minutes  
**Audience:** Carl Quesinberry / stakeholders  
**Version:** 0.4.0  
**Sample data:** 19-file real estate development set (or any folder with mixed PDFs, Office, KMZ)

---

## Before the demo

```powershell
cd "AI-Assisted Data Room File Organizer"
.venv\Scripts\activate
dataroom doctor
dataroom download-models
```

Confirm doctor shows no **fail** items. Have sample input folder path ready (e.g. `C:\Users\user\Desktop\Sample Data`).

---

## Part 1 — Environment check (2 min)

**Say:** *"Before processing thousands of files, the tool validates the machine."*

```powershell
dataroom doctor
```

**Point out:**

- Python and core libraries
- Tesseract + Poppler for OCR
- Embedding model loaded (Tier 2 classification)
- Ollama reachable (if configured) for ambiguous documents

**Optional — UI:**

```powershell
dataroom ui
```

Open **Doctor** tab → **Run doctor**.

---

## Part 2 — Taxonomy (2 min)

**Say:** *"Folders 00–19 are defined in YAML — no code changes to adapt domains."*

```powershell
dataroom taxonomy
```

**Or UI → Taxonomy tab.**

**Highlight:** category ID, folder name, keyword count, review-queue flag for folder `19`.

---

## Part 3 — Full pipeline run (5–8 min)

**Say:** *"One command ingests, classifies, organizes, and exports everything. Originals stay untouched."*

```powershell
dataroom run "C:\Users\user\Desktop\Sample Data" --output-dir output\demo
```

**Or UI → Run tab:**

1. Set input/output via Browse
2. Click **Run pipeline**
3. Show **Run summary** metrics when complete (processed, review queue, duplicates, timings)

**While waiting, explain:**

- Tier 1 keywords → Tier 2 embeddings → Tier 3 LLM (if hybrid + Ollama)
- KMZ/DWG never leave the machine
- Batch embeddings speed up multi-file runs

**Expected on 19-file sample:** ~3–5 minutes depending on OCR and LLM.

---

## Part 4 — Outputs walkthrough (5 min)

Open `output\demo\00_Admin_and_Index\`:

### Manifest

```powershell
start output\demo\00_Admin_and_Index\manifest.xlsx
```

**Show columns:** file name, assigned folder, confidence, method, reasoning provider, file hash.

### HTML index

```powershell
start output\demo\00_Admin_and_Index\index.html
```

**Demo:** search for a filename; filter by folder; click a link (opens original or organized copy per config).

### Review queue

```powershell
start output\demo\00_Admin_and_Index\review_queue.xlsx
```

**Say:** *"Only uncertain files appear here — not the whole batch."*

### Duplicates

```powershell
start output\demo\00_Admin_and_Index\duplicate_report.xlsx
```

**Say:** *"Exact hash matches and near-text duplicates are flagged for analyst review."*

### Organized folders

Browse `output\demo\01_Project_Overview`, etc.

**Optional KMZ story** (if sample includes boundary KMZ): show `manifest.xlsx` → `extracted_geo_signals` and keyword classification — see `docs/CALIBRATION.md` §4.

### Run summary (output root)

```powershell
type output\demo\run_summary.json
```

**Say:** *"Operational summary stays at the output root — not duplicated in folder 00."*

---

## Part 5 — Correction rerun (3 min)

**Say:** *"Analysts fix folder assignments without re-running OCR."*

**UI path:**

1. **Review** tab
2. Set **Corrected folder** on one flagged row
3. **Save review queue** → **Rerun with corrections**

**CLI path:**

1. Edit `00_Admin_and_Index/review_queue.xlsx` — set `corrected_folder`
2. `dataroom rerun output\demo`

**Show:** rerun completes in seconds; `run_summary.json` (output root) has `"rerun": true`; file appears in corrected folder.

---

## Part 6 — Configuration story (2 min)

**Say:** *"Secrets in .env; policy in YAML."*

Open `.env.example` — classification mode, Ollama, enterprise gateway.

Open `config/default.yaml` — thresholds, guardrails, duplicate settings, `index_link_mode`.

**Say:** *"Calibration is rerunning with tuned keywords — see CALIBRATION.md."*

---

## Closing talking points

| Point | Detail |
|-------|--------|
| **Local-first** | Ingestion and Tier 2 run on-host; API sends excerpts only |
| **Auditability** | `00_Admin_and_Index/manifest.xlsx`, `audit_log.jsonl`, `errors_report.xlsx` |
| **Scale** | CLI for large batches; UI for review and ops |
| **No lock-in** | Taxonomy YAML swappable; OpenAI-compatible enterprise gateway |

---

## Troubleshooting during demo

| Issue | Quick fix |
|-------|-----------|
| Doctor embedding fail | `dataroom download-models` |
| Run slow | Normal on first OCR-heavy batch; mention cache on rerun |
| UI subprocess error | Show CLI `dataroom run` as fallback; run `dataroom doctor` |
| Ollama not used | `CLASSIFICATION_MODE=hybrid` + `ollama serve` running |

---

## Post-demo handoff

Share:

- `docs/USER_GUIDE.md`
- `docs/INSTALLATION_WINDOWS.md`
- `docs/TESTING.md`
- `docs/MILESTONE_4.md`
- `README.md`
