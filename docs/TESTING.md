# QA / Acceptance Testing Guide

Checklist for validating **v0.4.0** before delivery or after changes. Run on a Windows machine with the full install (`docs/INSTALLATION_WINDOWS.md`).

---

## Prerequisites

```powershell
.venv\Scripts\activate
dataroom doctor
dataroom download-models
```

Doctor should show no **FAIL** items. Start Ollama if testing hybrid/LLM escalation (`ollama serve`).

---

## 1. Full pipeline (CLI)

```powershell
dataroom run "C:\path\to\sample\folder" --output-dir output\qa_full
```

| Check | Expected |
|-------|----------|
| Exit code | 0 |
| `run_summary.json` | `processed` > 0, paths set |
| Taxonomy folders | Copies under `00_…`–`19_…` |
| Artifacts | `manifest.csv`, `manifest.xlsx`, `index.html`, `review_queue.csv`, `duplicate_report.csv`, `errors_report.csv`, `audit_log.jsonl` |
| Caches | `ingestion_cache.json`, `classification_cache.json` |
| Originals | Source folder unchanged |

---

## 2. Streamlit UI — Run tab

```powershell
dataroom ui
```

| Check | Expected |
|-------|----------|
| Sidebar | Input/output paths, Browse works |
| Run pipeline | Completes; **Run summary** metrics (no raw JSON expander) |
| Errors | Short error message if subprocess fails (no process log panel) |

**Tip:** Stop the UI (`Ctrl+C`) before `pip install -e` — otherwise Windows may lock `dataroom.exe`.

---

## 3. Run options

Use a dedicated output folder per test for clear counts.

### Rename files

| Check | Expected |
|-------|----------|
| Checkbox on | Organized copies use taxonomy-based names (may add `_2`, `_3` if re-run on same output) |
| Checkbox off | Original filenames preserved |

### Disable OCR

| Check | Expected |
|-------|----------|
| `--no-ocr` / checkbox | Faster ingestion; `manifest.csv` → `extraction_method` = `native` for text PDFs |
| Classification | Still runs (Ollama/local tiers unchanged) |

### Non-recursive scan

Use a folder with files in subfolders (e.g. Desktop `nonrecursive_test`):

| Setting | Expected processed |
|---------|-------------------|
| Non-recursive **off** | All supported files in tree (e.g. 6) |
| Non-recursive **on** | Top-level files only (e.g. 3) |

---

## 4. Duplicate detection

Use a folder with intentional duplicate pairs (same file copied, or identical content):

| Check | Expected |
|-------|----------|
| `duplicate_pair_count` in summary | Matches pairs in input **batch** |
| `duplicate_report.csv` | Lists exact (hash) and/or near-text pairs |
| Organized output | Duplicates are **reported**, not removed |

**Note:** Duplicates are detected **within a single run’s input batch**, not across unrelated folders or prior runs.

---

## 5. Review queue and rerun

1. Run pipeline on a folder that produces review-queue rows (medium/low confidence).
2. Open UI → **Review** (or edit `review_queue.csv`).
3. Set **Corrected folder** for one or more rows.
4. **Save review queue** (close CSV in Excel first if open).
5. **Rerun with corrections**.

| Check | Expected |
|-------|----------|
| Rerun time | Seconds (no re-OCR) |
| `run_summary.json` | `"rerun": true`, `corrections_applied` > 0 |
| `manifest.csv` | Corrected rows → `manual_correction`, `needs_review` false |
| Review queue count | Drops for corrected rows |
| New copies | Appear in corrected taxonomy folders |

**Note:** Rerun adds new organized copies; it does not delete copies from earlier runs in other folders.

---

## 6. Other UI tabs

| Tab | Check |
|-----|-------|
| **Taxonomy** | Categories 00–19 listed with keyword counts |
| **Doctor** | Run doctor → formatted report; pass/fail banner |
| **Outputs** | Run summary + artifact table when output dir has `run_summary.json` |

---

## 7. Doctor CLI

```powershell
dataroom doctor
dataroom doctor --json
```

Verify embedding model, Tesseract, Poppler, and optional Ollama checks.

---

## 8. Automated tests

```powershell
pip install -e ".[ui,dev]"
pytest -v
```

Expected: **135** tests passing.

---

## 9. Known behaviors (not bugs)

| Behavior | Explanation |
|----------|-------------|
| Ollama picks differ between runs | Tier 3 LLM is non-deterministic; edge-case files may move in/out of review queue |
| Re-run on same output stacks `_2`, `_3` copies | Organizer avoids overwrite; use fresh output folder for clean demos |
| `review_queue.csv` save fails | File open in Excel — close it and retry |
| Full run always re-ingests | Caches used by **`dataroom rerun`**, not by full `dataroom run` |
| UI stop slow after run | Streamlit waits for subprocess; second `Ctrl+C` or close terminal if stuck |

---

## Related docs

- `docs/USER_GUIDE.md` — operator workflow
- `docs/DEMO.md` — stakeholder walkthrough
- `docs/MILESTONE_4.md` — delivery summary
