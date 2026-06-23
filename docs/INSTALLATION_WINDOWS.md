# Windows Installation Guide

Step-by-step setup for **AI-Assisted Data Room File Organizer v0.4.0** on Windows 10/11.

---

## 1. Prerequisites

| Requirement | Notes |
|-------------|-------|
| Windows 10 or 11 | 64-bit |
| Python 3.11+ | From [python.org](https://www.python.org/downloads/) — check **Add Python to PATH** during install |
| Git (optional) | For cloning the repository |
| ~2 GB disk | Python venv, PyTorch, embedding model (~90 MB) |
| Internet (first setup) | Hugging Face model download; optional Ollama model pull |

---

## 2. Install system tools

Open **PowerShell** (not CMD) as a normal user.

### Tesseract OCR

```powershell
winget install --id UB-Mannheim.TesseractOCR --accept-package-agreements --accept-source-agreements
```

### Poppler (PDF → image for OCR)

```powershell
winget install --id oschwartz10612.Poppler --accept-package-agreements --accept-source-agreements
```

### LibreOffice (recommended for `.doc` / `.ppt`)

```powershell
winget install --id TheDocumentFoundation.LibreOffice --accept-package-agreements --accept-source-agreements
```

### Verify

Close and reopen PowerShell, then:

```powershell
tesseract --version
pdftoppm -h
python --version
```

Expected: Python 3.11+ and Tesseract version string.

If `tesseract` is not found, add `C:\Program Files\Tesseract-OCR` to your user **PATH**, or set `ocr.tesseract_cmd` in `config/default.yaml`.

---

## 3. Get the project

```powershell
cd $env:USERPROFILE\Desktop
# If delivered as zip, extract to:
# AI-Assisted Data Room File Organizer
cd "AI-Assisted Data Room File Organizer"
```

---

## 4. Python environment

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[ui]"
```

This installs the CLI, Streamlit UI, and all dependencies from `pyproject.toml`.

For development / running tests:

```powershell
pip install -e ".[ui,dev]"
```

---

## 5. Download embedding model

```powershell
dataroom download-models
```

Downloads `all-MiniLM-L6-v2` (~90 MB) to the Hugging Face cache. Run once per machine.

If skipped, the model downloads automatically on the first `dataroom run` (you will see a message in the log).

---

## 6. Configuration

```powershell
copy .env.example .env
notepad .env
```

Minimum for local-only classification:

```env
CLASSIFICATION_MODE=local
REASONING_PROVIDER=local
```

Recommended with local Ollama:

```env
CLASSIFICATION_MODE=hybrid
REASONING_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

Policy (thresholds, guardrails, duplicates) lives in `config/default.yaml` — no secrets there.

---

## 7. Verify installation

```powershell
dataroom doctor
```

| Status | Meaning |
|--------|---------|
| **PASS** | Ready |
| **WARN** | Optional component missing (may be OK) |
| **FAIL** | Fix before running batches |

All **fail** items must be resolved. Common fixes:

| Check | Fix |
|-------|-----|
| `embedding_model` | `dataroom download-models` |
| `tesseract` | Install Tesseract; restart terminal |
| `poppler` | Install Poppler; restart terminal |
| `libreoffice` | Install LibreOffice (only needed for legacy Office) |
| `ollama` | Install [Ollama](https://ollama.com/); run `ollama pull llama3.2` |

---

## 8. Optional: Ollama (local LLM)

1. Download and install from [ollama.com](https://ollama.com/)
2. Pull a model:

```powershell
ollama pull llama3.2
```

3. Confirm:

```powershell
ollama list
```

4. Set `.env` as shown in section 6.

---

## 9. Smoke test

```powershell
dataroom taxonomy
dataroom run "C:\path\to\test\folder" --output-dir output\smoke_test
```

Or launch the UI:

```powershell
dataroom ui
```

Browser opens at `http://localhost:8501`.

---

## 10. Firewall and corporate networks

| Service | Endpoint | When needed |
|---------|----------|-------------|
| Hugging Face | `huggingface.co` | First embedding model download |
| Ollama | `localhost:11434` | Local Tier 3 only |
| Enterprise gateway | Your `ENTERPRISE_BASE_URL` | If using enterprise provider |

If Hugging Face is blocked, download the model on a connected machine and copy the cache folder, or ask IT to allow `huggingface.co` for one-time setup.

---

## 11. Updating the tool

```powershell
cd "AI-Assisted Data Room File Organizer"
git pull   # if using git
.venv\Scripts\activate
# Stop dataroom ui first if running (avoids WinError 32 on dataroom.exe)
pip install -e ".[ui]"
dataroom doctor
```

---

## 12. Uninstall

```powershell
deactivate
Remove-Item -Recurse -Force .venv
```

System tools (Tesseract, Poppler, LibreOffice) are removed separately via Windows Settings → Apps.

---

## Next steps

- `docs/USER_GUIDE.md` — daily operator workflow
- `docs/DEMO.md` — stakeholder demo script
- `docs/TESTING.md` — QA / acceptance checklist
- `README.md` — command reference
