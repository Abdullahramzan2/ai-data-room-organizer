# Milestone 3 — Enterprise LLM Plug-in + Calibration

| | |
|---|---|
| **Client** | Carl Quesinberry |
| **Milestone** | Enterprise-ready provider architecture + calibration |
| **Version** | 0.3.0 |
| **Status** | Delivered |

---

## Overview

Milestone 3 makes the classification platform **enterprise-ready** and documents how to **calibrate** it on real data:

1. **Provider registry** — register and resolve reasoning providers via config
2. **OpenAI-compatible enterprise provider** — Aleph Alpha, vLLM, Azure OpenAI, on-prem gateways
3. **Configurable auto chain** — priority order in `config/default.yaml`
4. **Classification mode enforcement** — `local` mode never escalates to Tier 3
5. **Guardrails** — trusted local hosts, provider allow/block lists, remote endpoint detection
6. **CLI / pipeline parity** — `dataroom classify` uses same guardrails and provider setup as `dataroom run`
7. **Error reporting** — `errors_report.csv` for skipped/failed ingestion and organize failures
8. **Calibration guide** — `docs/CALIBRATION.md` (thresholds, taxonomy tuning, review queue, KMZ example)

---

## Before / after (Carl sample data)

Validated on `data/Sample Data` (19 files) with `CLASSIFICATION_MODE=hybrid` and Ollama as Tier 3 provider.

| Metric | Earlier local-only baseline | Milestone 3 hybrid + Ollama |
|--------|----------------------------|-----------------------------|
| Files processed | 19 | 19 |
| Organized successfully | 19 | 19 |
| Review queue | 4 files | **2 files** |
| Tier 3 (LLM) used | No | **Yes** — 2 files classified via Ollama |
| External cloud API | No | No (`api_used_count: 0`; Ollama on localhost) |
| Audit trail | Basic | `audit_log.jsonl` per escalation |
| Failed/skipped reporting | Limited | `errors_report.csv` + manifest `organize_status` |

**Calibration example — `BigPine_600Acre_Boundary.kmz`:**

| | Before taxonomy tuning | After calibration |
|--|------------------------|-------------------|
| Placement | Review queue or weak match | `01_Project_Overview` |
| Confidence | Low / uncertain | **High (0.95)** |
| Method | Embedding guess | **Keyword** (`boundary`, `conceptual`) |
| Change | — | Added `boundary`, `acreage`, `site boundary`, `conceptual` to taxonomy |

**Ambiguous files handled by Ollama (Tier 3):**

- `Data_Center_Reference_Architectures_-_100MW_Blueprint.pdf` → `11_BTM_Generation_BESS_and_Energy`
- `RESO-20180925-21-CCR-East-Campus.pdf` → `04_Zoning_Land_Use_and_Local_Approvals`

See `docs/CALIBRATION.md` for the full KMZ walkthrough and tuning workflow.

---

## Enterprise provider configuration

Copy `.env.example` to `.env` and set:

```env
CLASSIFICATION_MODE=hybrid
REASONING_PROVIDER=enterprise

ENTERPRISE_API_KEY=your-api-key
ENTERPRISE_BASE_URL=https://your-gateway/v1
ENTERPRISE_MODEL=your-model-name
ENTERPRISE_TIMEOUT=120
# Optional JSON headers for custom gateways
ENTERPRISE_EXTRA_HEADERS={"X-Custom-Header": "value"}
```

For auto-selection (enterprise first when configured):

```env
REASONING_PROVIDER=auto
```

Configure chain order in `config/default.yaml`:

```yaml
classification:
  auto_provider_chain:
    - enterprise
    - openai
    - ollama
    - local
```

Local Ollama example:

```env
CLASSIFICATION_MODE=hybrid
REASONING_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

---

## Guardrails

```yaml
guardrails:
  allow_external_api: true
  trusted_local_hosts:
    - localhost
    - 127.0.0.1
    - ::1
  provider_allow_list: []   # empty = all allowed
  provider_block_list: []   # e.g. [openai] to block OpenAI only
```

Remote Ollama URLs and enterprise gateways are treated as **external** unless the host is in `trusted_local_hosts`.

---

## Outputs

| File | Purpose |
|------|---------|
| `manifest.csv` | Full per-file record; includes `organize_status`, `organize_error`, `reasoning_provider` |
| `review_queue.csv` | Subset flagged for human review |
| `errors_report.csv` | Skipped ingestion, failed ingestion, failed organize |
| `audit_log.jsonl` | Tier 3 escalation decisions (provider, excerpt size, local score) |
| `run_summary.json` | Run counts including `review_queue_count`, `errors_report` path |

---

## CLI

```powershell
# Full pipeline (recommended)
dataroom run "C:\path\to\folder" --output-dir output\data_room

# Classify with same guardrails/audit as pipeline
dataroom classify output\ingestion.json --output-dir output\data_room --output output\classification.json
```

---

## Calibration

See **`docs/CALIBRATION.md`** for:

- Confidence thresholds in `config/default.yaml`
- Editing taxonomy keywords and rerunning
- Using `review_queue.csv`
- Boundary KMZ before/after example

---

## Acceptance checklist

| Requirement | Status |
|-------------|--------|
| Provider registry (config-driven) | Yes |
| OpenAI-compatible enterprise provider | Yes |
| Configurable auto provider chain | Yes |
| Guardrails: trusted hosts, allow/block lists | Yes |
| `CLASSIFICATION_MODE=local` blocks Tier 3 | Yes |
| `dataroom classify` matches pipeline guardrails | Yes |
| Ingestion/organize failures in `errors_report.csv` | Yes |
| Calibration guide (`docs/CALIBRATION.md`) | Yes |
| Tests + architecture docs updated | Yes |

---

## Tests

```powershell
pytest -v
```
