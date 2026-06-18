# Calibration Guide

Short guide for tuning classification without code changes. Use this after a first `dataroom run` to improve folder assignment and reduce manual review.

---

## 1. Adjust confidence thresholds

Edit `config/default.yaml` under `classification:`:

```yaml
classification:
  high_threshold: 0.75    # ≥ this → high confidence, auto-assign
  medium_threshold: 0.50    # ≥ this → medium (assign + flag for review)
                            # < this → low (review queue or Tier 3)
```

| Setting | Effect when **raised** | Effect when **lowered** |
|---------|------------------------|-------------------------|
| `high_threshold` | Fewer auto-assignments; more files hit review or Tier 3 | More files accepted without review |
| `medium_threshold` | More files treated as low confidence | More medium-confidence assignments (assigned but flagged) |

Related guardrail (Tier 3 escalation only):

```yaml
guardrails:
  escalation_confidence_threshold: 0.50   # LLM called only when local score is below this
```

**Workflow:** change values → rerun the same folder → compare `review_queue.csv` and `run_summary.json` (`review_queue_count`).

```powershell
dataroom run "C:\path\to\folder" --output-dir output\calibration_run_2
```

---

## 2. Add or edit taxonomy keywords, then rerun

Taxonomy file: `taxonomy/real_estate_development.yaml`

Each category has:

- `description` — used by Tier 2 embeddings (semantic match)
- `keywords` — used by Tier 1 filename/text match (fast, high precision)

**To improve a file type:**

1. Open the YAML and find the target folder (e.g. `01_Project_Overview`).
2. Add terms that appear in real filenames, placemark names, or document text.
3. Save the file.
4. Rerun `dataroom run` on the same input folder.

No reinstall or cache clear is required. Embedding cache under `output/.cache` is keyed to taxonomy content; it rebuilds when keywords/descriptions change.

**Tips:**

- Add both lowercase and uppercase variants if filenames vary.
- Prefer domain phrases (`site boundary`, `phase i`) over single generic words.
- Use `description` for broader semantic coverage; use `keywords` for obvious matches.

---

## 3. Interpret the review queue and act on it

After each run, open `review_queue.csv` in the output directory. It lists only rows where `needs_review` is true in `manifest.csv`.

| Column | Meaning |
|--------|---------|
| `file_name` | Source document |
| `assigned_folder` | Where the tool placed it (may still be `19_Unclassified_Review_Queue`) |
| `confidence` | `medium` or `low` |
| `score` | Numeric score (0–1) |
| `review_reason` | Why it was flagged |
| `classification_reason` | Method summary (keyword, embedding, ollama, etc.) |
| `supporting_terms` | Keywords that matched, if any |

**Typical actions:**

| Situation | What to do |
|-----------|------------|
| **Correct folder, medium confidence** | Accept placement; optionally lower `high_threshold` if you want fewer flags |
| **Wrong folder, weak keyword hit** | Add keywords to the *correct* category; consider `exclude_if` rules if two categories compete |
| **Wrong folder, embedding won** | Strengthen `description` on the correct category; add distinguishing keywords |
| **Low confidence / review queue** | Add keywords; rerun. If still ambiguous, Tier 3 (Ollama/enterprise) may help in `hybrid` mode |
| **Consistently misclassified type** | Add a dedicated keyword phrase from filename or extracted text (see KMZ example below) |

The full audit trail is in `manifest.csv` (`classification_method`, `classification_basis`, `reasoning_provider`, `extracted_geo_signals` for KMZ).

---

## 4. Worked example: boundary KMZ (`BigPine_600Acre_Boundary.kmz`)

Carl’s sample set includes a KMZ whose placemark text is **“Big Pine 600-Acre Boundary (Conceptual)”**. KMZ files are **local-only** (never sent to an external LLM); classification uses parsed placemarks plus filename.

### Before calibration

Early runs without site/boundary keywords in the taxonomy tended to:

- Assign the file to a **less specific** folder, or
- Leave it in **`19_Unclassified_Review_Queue`** with low embedding confidence,

because Tier 1 did not recognize `boundary`, `acreage`, or `conceptual` as strong project-overview signals.

### Calibration change

Keywords were added to categories **01** and **09** in `taxonomy/real_estate_development.yaml`:

```yaml
# 01_Project_Overview (excerpt)
keywords:
  - boundary
  - acreage
  - site boundary
  - conceptual

# 09_Civil_Engineering_and_Site_Planning (excerpt)
keywords:
  - boundary
  - acreage
  - site boundary
  - conceptual
```

### After calibration (sample run)

| Field | Value |
|-------|--------|
| **File** | `BigPine_600Acre_Boundary.kmz` |
| **Folder** | `01_Project_Overview` |
| **Confidence** | high (0.95) |
| **Method** | keyword |
| **Supporting terms** | `boundary`, `conceptual` |
| **Geo signals** | placemark: Big Pine 600-Acre Boundary (Conceptual) |
| **Review queue** | No |

### Takeaway

1. Inspect `manifest.csv` → `extracted_geo_signals` and `supporting_terms` for KMZ/DWG files.
2. Add missing terms to the **intended** taxonomy category.
3. Rerun once — no code change.

If `01` and `09` both match, the higher keyword score wins; tighten keywords or descriptions if you need a single canonical home for boundary exhibits.

---

## Quick calibration loop

```powershell
dataroom run "C:\path\to\folder" --output-dir output\run_v1
# Edit config/default.yaml and/or taxonomy/real_estate_development.yaml
dataroom run "C:\path\to\folder" --output-dir output\run_v2
# Compare review_queue.csv and review_queue_count in run_summary.json
```

For classify-only iteration (faster after ingestion):

```powershell
dataroom ingest "C:\path\to\folder" --output output\ingestion.json
dataroom classify output\ingestion.json --output-dir output\run_v2 --output output\classification.json
```
