# Demo Script — Data Room Organizer

**Duration:** ~20 minutes  
**Audience:** Carl Quesinberry / stakeholders  
**Version:** 0.5.3  
**Sample data:** 19-file real estate development set (or any folder with mixed PDFs, Office, KMZ)

---

## Before the demo

**Windows installer (Carl):**

1. Start Menu → **Data Room Doctor** — confirm all checks OK
2. Start Menu → **Data Room Organizer**
3. Have sample input folder path ready (e.g. `C:\Users\...\Desktop\Sample Data`)

**Zip / developer install:**

```powershell
cd "AI-Assisted Data Room File Organizer"
.venv\Scripts\activate
dataroom doctor
dataroom download-models
dataroom ui
```

Confirm doctor shows no **fail** items.

---

## Part 1 — Environment check (2 min)

**Say:** *"Before processing thousands of files, the tool validates the machine."*

**Installer:** Start Menu → **Data Room Doctor** (or UI → **Doctor** tab → **Run doctor**)

**Developer:** `dataroom doctor`

**Point out:**

- Python and core libraries
- Tesseract + Poppler for OCR
- Embedding model loaded (Tier 2 classification)
- Ollama reachable (if configured) for ambiguous documents

---

## Part 2 — Taxonomy (2 min)

**Say:** *"Folders 00–19 are defined in YAML — no code changes to adapt domains."*

**UI → Taxonomy tab** (or `dataroom taxonomy` from developer install)

**Highlight:** category ID, folder name, keyword count, review-queue flag for folder `19`.

---

## Part 3 — Full pipeline run (5–8 min)

**Say:** *"One click ingests, classifies, organizes, and exports everything. Originals stay untouched."*

**UI → Run tab:**

1. Set input/output via **Browse…**
2. Click **Run pipeline**
3. Show live status: *Ingesting…* → *Classifying…* → **Pipeline finished.**
4. Show metrics and per-file table updating during the run

**Developer CLI alternative:**

```powershell
dataroom run "C:\Users\user\Desktop\Sample Data" --output-dir output\demo
```

**While waiting, explain:**

- Tier 1 keywords → Tier 2 embeddings → Tier 3 LLM (if hybrid + Ollama)
- KMZ/DWG never leave the machine
- Batch embeddings speed up multi-file runs

**Expected on 19-file sample (local mode):** ~20–40 seconds.

---

## Part 4 — Outputs walkthrough (5 min)

Open `output\demo\00_Admin_and_Index\`:

### Manifest

Open `manifest.xlsx` in Excel.

**Show columns:** file name, assigned folder, confidence, method, reasoning provider, file hash.

### HTML index

Double-click `index.html`.

**Demo:** search for a filename; filter by folder; click a link (opens original or organized copy per config).

### Review queue

Open `review_queue.xlsx`.

**Say:** *"Only uncertain files appear here — not the whole batch."*

### Duplicates

Open `duplicate_report.xlsx`.

**Say:** *"Exact hash matches and near-text duplicates are flagged for analyst review."*

### Organized folders

Browse `output\demo\01_Project_Overview`, etc.

### Run summary (output root)

Open `run_summary.json` at the output root.

**Say:** *"Operational summary stays at the output root — not duplicated in folder 00."*

---

## Part 5 — Correction rerun (3 min)

**Say:** *"Analysts fix folder assignments without re-running OCR."*

**UI path:**

1. **Review** tab
2. Set **Corrected folder** on one flagged row
3. **Save review queue** → **Rerun with corrections**

**CLI path (developer install):**

1. Edit `00_Admin_and_Index/review_queue.xlsx` — set `corrected_folder`
2. `dataroom rerun output\demo`

**Show:** rerun completes in seconds; `run_summary.json` has `"rerun": true`; file appears in corrected folder.

---

## Part 6 — Configuration story (2 min)

**Say:** *"Secrets in .env; policy in YAML."*

**Installer:** open `%APPDATA%\DataRoomOrganizer\.env` in Notepad.

**Developer:** open `.env.example`.

Show classification mode, Ollama, enterprise gateway options.

Open `config/default.yaml` — thresholds, guardrails, duplicate settings, `index_link_mode`.

**Say:** *"Calibration is rerunning with tuned keywords — see CALIBRATION.md."*

---

## Closing talking points

| Point | Detail |
|-------|--------|
| **Local-first** | Ingestion and Tier 2 run on-host; API sends excerpts only |
| **Auditability** | `00_Admin_and_Index/manifest.xlsx`, `audit_log.jsonl`, `errors_report.xlsx` |
| **Scale** | UI for review and ops; full pipeline in one click |
| **No lock-in** | Taxonomy YAML swappable; OpenAI-compatible enterprise gateway |

---

## Troubleshooting during demo

| Issue | Quick fix |
|-------|-----------|
| Doctor embedding fail | Re-run Doctor; reinstall if bundled model missing |
| Run slow | First OCR-heavy batch may take longer; 19-file sample ~20–40 s in local mode |
| UI error loop during run | Upgrade to v0.5.3+ |
| Ollama not used | `CLASSIFICATION_MODE=hybrid` + `ollama serve` running |

---

## Post-demo handoff

Share with Carl:

- `AI-Data-Room-Organizer-Setup.exe`
- `docs/INSTALLER_QUICKSTART.md`
- `docs/USER_GUIDE.md`
- `docs/OLLAMA_SETUP.md` (if hybrid LLM is desired)
