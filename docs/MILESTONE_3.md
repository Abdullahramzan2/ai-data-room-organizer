# Milestone 3 — Enterprise LLM Plug-in + Calibration

| | |
|---|---|
| **Client** | Carl Quesinberry |
| **Milestone** | Enterprise-ready provider architecture |
| **Version** | 0.3.0 |
| **Status** | Delivered |

---

## Overview

Milestone 3 makes the classification platform **enterprise-ready**:

1. **Provider registry** — register and resolve reasoning providers via config
2. **OpenAI-compatible enterprise provider** — Aleph Alpha, vLLM, Azure OpenAI, on-prem gateways
3. **Configurable auto chain** — priority order in `config/default.yaml`
4. **Classification mode enforcement** — `local` mode never escalates to Tier 3
5. **Guardrails** — trusted local hosts, provider allow/block lists, remote endpoint detection
6. **CLI / pipeline parity** — `dataroom classify` uses same guardrails and provider setup as `dataroom run`
7. **Error reporting** — `errors_report.csv` for skipped/failed ingestion and organize failures

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

## New outputs

| File | Purpose |
|------|---------|
| `errors_report.csv` | Skipped ingestion, failed ingestion, failed organize |
| `manifest.csv` | Added `organize_status`, `organize_error` columns |
| `run_summary.json` | Added `skipped_count`, `ingestion_failed_count`, `organize_failed_count`, `errors_report` |

---

## CLI

```powershell
# Full pipeline (unchanged)
dataroom run "C:\path\to\folder" --output-dir output\data_room

# Classify with same guardrails/audit as pipeline
dataroom classify output\ingestion.json --output-dir output\data_room --output output\classification.json
```

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
| Tests + architecture docs updated | Yes |

---

## Tests

```powershell
pytest -v
```
