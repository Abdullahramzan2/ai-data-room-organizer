# QA / Acceptance Testing Guide

Checklist for validating **v0.5.3** before delivery or after changes. Run on a Windows machine with the installer (`docs/INSTALLER_QUICKSTART.md`) or zip install (`README.md` → **Windows installation**).

---

## Prerequisites

**Installer:** Start Menu → **Data Room Doctor** — no FAIL items.

**Developer:**

```powershell
.venv\Scripts\activate
dataroom doctor
dataroom download-models
```

Start Ollama if testing hybrid/LLM escalation (`ollama serve`).

---

## 1. Full pipeline (CLI)

**Installer:** use bundled Python from install dir, or run via UI.

**Developer:**

```powershell
dataroom run "C:\path\to\sample\folder" --output-dir output\qa_full
```

| Check | Expected |
|-------|----------|
| Exit code | 0 |
| `run_summary.json` | Output root only | `processed` > 0, paths set |
| Taxonomy folders | `01_…`–`19_…` | Organized document copies |
| Admin folder (`00_Admin_and_Index/`) | Carl deliverables | `manifest.xlsx`, `index.html`, `review_queue.xlsx`, `duplicate_report.xlsx`, `errors_report.xlsx`, `classification_log.xlsx`, `source_authentication_matrix.xlsx` |
| Operational artifacts | Output root | `run_summary.json`, `processing_log.json`, `run_progress.json`, `ingestion_cache.json`, `classification_cache.json`, `audit_log.jsonl` |
| Admin folder | No duplicate of `run_summary.json` | Summary exists only at output root |
| Originals | Source folder unchanged |
| 19-file sample timing | ~20–40 s | Local mode, OCR enabled |

---

## 2. Streamlit UI — Run tab

**Installer:** Start Menu → **Data Room Organizer**

**Developer:** `dataroom ui`

| Check | Expected |
|-------|----------|
| Sidebar | Input/output paths, **Browse…** works |
| Live status | Updates through *Ingesting…* → *Classifying…* → **Pipeline finished.** (not stuck on "Starting…") |
| Progress | **Total files** after scan; per-file table updates live; review queue counter grows |
| Completion | No red Streamlit error loop; final metrics visible |
| Errors | Short error message only on real failure (not flash-then-disappear on success) |

---

## 3. Run options

Use a dedicated output folder per test for clear counts.

### Rename files

| Check | Expected |
|-------|----------|
| Checkbox on | Organized copies use standardized names: `YYYY-MM-DD__CategoryShort__Source__ShortDesc__OriginalName.ext` |
| Checkbox off | Original filenames preserved |

### Disable OCR

| Check | Expected |
|-------|----------|
| `--no-ocr` / checkbox | Faster ingestion; `manifest.xlsx` → `extraction_method` = `native` for text PDFs |

### Non-recursive scan

| Setting | Expected processed |
|---------|-------------------|
| Non-recursive **off** | All supported files in tree |
| Non-recursive **on** | Top-level files only |

---

## 4. Duplicate detection

| Check | Expected |
|-------|----------|
| `duplicate_pair_count` in summary | Matches pairs in input **batch** |
| `duplicate_report.xlsx` | Lists exact (hash) and/or near-text pairs |
| Review queue | Duplicate pairs flagged when `flag_for_review: true` |

---

## 5. Review queue and rerun

1. Run pipeline on a folder that produces review-queue rows.
2. UI → **Review** — set **Corrected folder**; **Save** → **Rerun with corrections**.

| Check | Expected |
|-------|----------|
| Rerun time | Seconds (no re-OCR) |
| `run_summary.json` | `"rerun": true`, `corrections_applied` > 0 |
| Manifest | Corrected rows updated |

---

## 6. Other UI tabs

| Tab | Check |
|-----|-------|
| **Taxonomy** | Categories 00–19 listed with keyword counts |
| **Doctor** | Run doctor → formatted report; pass/fail banner |
| **Outputs** | Run summary, manifest preview, processing log, artifact table |

---

## 7. Installer-specific checks (v0.5.3)

| Check | Expected |
|-------|----------|
| Install path | `%LOCALAPPDATA%\Programs\AI Data Room Organizer\` |
| Settings | `%APPDATA%\DataRoomOrganizer\.env` created on first launch |
| Cache writes | `%APPDATA%\DataRoomOrganizer\cache\` — no Access Denied under Program Files |
| Upgrade | New Setup.exe installs over old version without uninstall |
| Setup.exe size | ~550–620 MB (not ~26 MB) |

---

## 8. Automated tests

```powershell
pip install -e ".[ui,dev]"
pytest -v
```

Key UI suite: `tests/test_ui_progress_display.py` — status message transitions.

---

## 9. Known behaviors (not bugs)

| Behavior | Explanation |
|----------|-------------|
| Ollama picks differ between runs | Tier 3 LLM is non-deterministic |
| Re-run on same output stacks `_2`, `_3` copies | Organizer avoids overwrite |
| `review_queue.xlsx` save fails | File open in Excel — close and retry |
| Full run always re-ingests | Caches used by **`dataroom rerun`**, not full `dataroom run` |

---

## Related docs

- `docs/USER_GUIDE.md` — operator workflow
- `docs/INSTALLER_QUICKSTART.md` — Carl installer guide
- `docs/MILESTONE_5.md` — delivery summary
