# Installer Quick Start — Data Room Organizer

**Version 0.5.3** — for Carl's Windows installer (`AI-Data-Room-Organizer-Setup.exe`). No Python, pip, or winget required.

---

## What you get

One setup file that installs everything:

- Python runtime and all application libraries
- Tesseract OCR, Poppler, LibreOffice
- Pre-cached AI embedding model
- Start Menu shortcuts (optional desktop icon)

**Not included:** Ollama (optional local LLM) — see `docs/OLLAMA_SETUP.md`.

---

## Install (3 steps)

### 1. Download and run

1. Download `AI-Data-Room-Organizer-Setup.exe` from the shared cloud folder (~600 MB).
2. Double-click the file.
3. If Windows SmartScreen appears, choose **More info** → **Run anyway** (unsigned installer).
4. Accept the installer prompts (no admin required for the default per-user install path):

   `%LOCALAPPDATA%\Programs\AI Data Room Organizer\`

   Do **not** install into a developer `packaging\` folder — that path is for build testing only.

5. Before upgrading or reinstalling, close the UI (Task Manager → end **Data Room Organizer** / related `python.exe` if needed) and wait a few seconds.
6. Optionally check **Create a desktop icon** (shortcut goes to your personal desktop).
7. Click **Install** and wait for extraction to finish (several minutes).

**Upgrading:** Run the new Setup.exe over an existing install — uninstall is not required.

### 2. Launch the app

After install:

- Open **Start Menu** → **AI Data Room Organizer** → **Data Room Organizer**

Or use the desktop shortcut if you enabled it.

Your browser opens at `http://127.0.0.1:8501` with the Streamlit UI.

**First launch:** a default settings file is created at:

`%APPDATA%\DataRoomOrganizer\.env`

Default mode is **local** (no cloud API calls).

Bundled operator docs are also installed at:

`%LOCALAPPDATA%\Programs\AI Data Room Organizer\app\docs\`

### 3. Verify (optional)

Start Menu → **Data Room Doctor**

A console window runs a health check. Expect **OK** for Python, Tesseract, Poppler, LibreOffice, and the embedding model. Press **Enter** to close the window.

---

## Run your first batch

1. In the UI **Run** tab, set **Input folder** and **Output directory** (use **Browse…**).
2. Click **Run pipeline**.
3. Watch the status line update live — e.g. *Ingesting files…*, *Classifying files…*, then **Pipeline finished.**
4. When complete, open the output folder:
   - `00_Admin_and_Index/manifest.xlsx` — full file list
   - `00_Admin_and_Index/index.html` — searchable browser index
   - `00_Admin_and_Index/review_queue.xlsx` — files needing review
   - `run_summary.json` and `processing_log.json` — at the **output root**

On Carl's 19-file sample folder, a typical run completes in **~20–40 seconds** (local mode, OCR enabled).

See `docs/USER_GUIDE.md` for review, corrections, and rerun workflow.

---

## Settings and cache locations

| Item | Path |
|------|------|
| Settings (`.env`) | `%APPDATA%\DataRoomOrganizer\.env` |
| Classification cache | `%APPDATA%\DataRoomOrganizer\cache\` |
| Install directory | `%LOCALAPPDATA%\Programs\AI Data Room Organizer\` |

To add an OpenAI or enterprise API key (or configure Ollama), edit the AppData `.env` file — see **Optional: Add an API key** below.

Quick open in Notepad:

```powershell
notepad "$env:APPDATA\DataRoomOrganizer\.env"
```

Restart the app after saving changes.

---

## Optional: Add an API key (smarter classification)

By default the installer uses **local** mode — keywords and embeddings only, **no API key required** and no cloud calls.

To escalate ambiguous files to a cloud LLM (Tier 3), add a key to your settings file.

### Where to edit

**Windows installer:**

```powershell
notepad "$env:APPDATA\DataRoomOrganizer\.env"
```

**Zip / developer install:** edit `.env` in the project root.

### Option A — OpenAI (simplest cloud setup)

1. Get an API key from [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Add these lines to `.env` (replace `sk-...` with your key):

```env
CLASSIFICATION_MODE=hybrid
REASONING_PROVIDER=openai

OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
```

3. Save the file and **restart** Data Room Organizer.
4. Run **Data Room Doctor** — expect **OK** for enterprise/OpenAI when configured (or run a small test batch).

**Privacy:** Only short document **excerpts** are sent for ambiguous files — never full files. KMZ and DWG stay local-only.

### Option B — Enterprise / private LLM gateway

For Azure OpenAI, vLLM, Aleph Alpha, or any OpenAI-compatible endpoint:

```env
CLASSIFICATION_MODE=hybrid
REASONING_PROVIDER=enterprise

ENTERPRISE_API_KEY=your-api-key
ENTERPRISE_BASE_URL=https://your-gateway.example.com/v1
ENTERPRISE_MODEL=your-model-name
ENTERPRISE_TIMEOUT=120
```

Save, restart the app, then run Doctor to confirm.

### Option C — Local LLM (no API key)

Install **Ollama** on the same PC — no cloud key needed. See `docs/OLLAMA_SETUP.md`.

### Automatic provider selection

To let the tool pick the first available provider:

```env
CLASSIFICATION_MODE=hybrid
REASONING_PROVIDER=auto

OPENAI_API_KEY=sk-your-key-here
# and/or enterprise vars above
# and/or Ollama settings — see OLLAMA_SETUP.md
```

Order with `auto`: enterprise (if configured) → OpenAI (if key set) → Ollama (if running) → local only.

### Verify after changing keys

1. Close the UI completely
2. Start Menu → **Data Room Organizer**
3. **Doctor** tab → **Run doctor** (or Start Menu → **Data Room Doctor**)

If the key is wrong or missing, Doctor reports **FAIL** or **SKIP** for the relevant provider.

---

## Uninstall

**Windows Settings** → **Apps** → **Installed apps** → **AI Data Room Organizer** → **Uninstall**

User settings in `%APPDATA%\DataRoomOrganizer\` are kept unless you delete that folder manually.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Setup "Access is denied" during install | Uncheck desktop icon and retry; close the UI; uninstall any partial copy; reinstall. |
| Doctor window closes instantly | Reinstall with the latest Setup.exe — Doctor waits for **Press Enter** after the report. |
| Browser does not open | Manually open `http://127.0.0.1:8501` |
| Doctor shows FAIL | Re-run Doctor; check API key in `.env` if using hybrid mode |
| Legacy `.doc` not reading | LibreOffice is bundled — run Doctor to confirm |
| Slow first classification | Model is pre-cached — no internet needed for embeddings after install |
| UI status stuck on "Starting…" | Upgrade to v0.5.3 or later |
| Want local LLM (Ollama) | Follow `docs/OLLAMA_SETUP.md` |

---

## Related documents

- `docs/USER_GUIDE.md` — day-to-day operator workflow (**recommended with this guide**)
- `docs/OLLAMA_SETUP.md` — local LLM (no API key)
- `docs/DEMO.md` — stakeholder demo script
