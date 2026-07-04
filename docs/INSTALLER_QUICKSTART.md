# Installer Quick Start — Data Room Organizer

For **Carl's Windows installer** (`AI-Data-Room-Organizer-Setup.exe`). No Python, pip, or winget required.

---

## What you get

One setup file that installs everything:

- Python runtime and all application libraries
- Tesseract OCR, Poppler, LibreOffice
- Pre-cached AI embedding model
- Desktop / Start Menu shortcuts

**Not included:** Ollama (optional local LLM) — see `docs/OLLAMA_SETUP.md`.

---

## Install (3 steps)

### 1. Download and run

1. Download `AI-Data-Room-Organizer-Setup.exe` from the shared cloud folder (~600 MB).
2. Double-click the file.
3. If Windows SmartScreen appears, choose **More info** → **Run anyway** (unsigned installer).
4. Accept the UAC prompt (admin rights required).
5. Use the default install location unless IT requires another drive:

   `C:\Program Files\AI Data Room Organizer\`

6. Optionally check **Create a desktop icon**.
7. Click **Install** and wait for extraction to finish (several minutes).

### 2. Launch the app

After install:

- Open **Start Menu** → **AI Data Room Organizer** → **Data Room Organizer**

Or use the desktop shortcut if you enabled it.

Your browser opens at `http://127.0.0.1:8501` with the Streamlit UI.

**First launch:** a default settings file is created at:

`%APPDATA%\DataRoomOrganizer\.env`

Default mode is **local** (no cloud API calls).

### 3. Verify (optional)

Start Menu → **Data Room Doctor**

A console window runs a health check. Expect **OK** for Python, Tesseract, Poppler, LibreOffice, and the embedding model.

---

## Run your first batch

1. In the UI **Run** tab, set **Input folder** and **Output directory** (use **Browse…**).
2. Click **Run pipeline**.
3. When finished, open the output folder:
   - `00_Admin_and_Index/manifest.xlsx` — full file list
   - `00_Admin_and_Index/index.html` — searchable browser index
   - `00_Admin_and_Index/review_queue.xlsx` — files needing review
   - `run_summary.json` and `processing_log.json` — at the **output root**

See `docs/USER_GUIDE.md` for review, corrections, and rerun workflow.

---

## Settings file location

| Install type | Settings path |
|--------------|---------------|
| **Windows installer** | `%APPDATA%\DataRoomOrganizer\.env` |
| Zip / developer install | Project folder `.env` |

To enable Ollama or OpenAI escalation, edit the AppData `.env` file (see `docs/OLLAMA_SETUP.md`).

Quick open in Notepad:

```powershell
notepad "$env:APPDATA\DataRoomOrganizer\.env"
```

Restart the app after saving changes.

---

## Uninstall

**Windows Settings** → **Apps** → **Installed apps** → **AI Data Room Organizer** → **Uninstall**

User settings in `%APPDATA%\DataRoomOrganizer\` are kept unless you delete that folder manually.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Setup blocked by antivirus | Allow the file; re-download if quarantined |
| Browser does not open | Manually open `http://127.0.0.1:8501` |
| Doctor shows FAIL | Re-run Doctor; if still failing, contact support with a screenshot |
| Legacy `.doc` not reading | LibreOffice is bundled — run Doctor to confirm |
| Slow first classification | Normal; model is pre-cached — no internet needed for embeddings |
| Want local LLM (Ollama) | Follow `docs/OLLAMA_SETUP.md` |

---

## Related documents

- `docs/USER_GUIDE.md` — day-to-day operator workflow
- `docs/OLLAMA_SETUP.md` — connect Ollama after install
- `docs/DEMO.md` — stakeholder demo script
