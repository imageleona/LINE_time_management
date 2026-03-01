# CLAUDE.md — LINE Time Management Bot

## Project Overview

This is a **LINE Messaging API webhook bot** that lets users track time spent on tasks directly from LINE chat. Active task state is stored locally in a JSON file; completed entries are persisted to a Google Spreadsheet.

---

## Repository Structure

```
.
├── main.py          # FastAPI app — LINE webhook entry point
├── handlers.py      # Command parsing and business logic
├── state.py         # In-process active-task state (JSON file backend)
├── sheets.py        # Google Sheets read/write integration
├── requirements.txt # Pinned Python dependencies
├── .env.example     # Template for required environment variables
└── .gitignore       # Excludes .env, credentials.json, state.json, .venv/
```

**Runtime files (gitignored, created at runtime):**
- `state.json` — tracks each user's currently active task (keyed by LINE `user_id`)
- `credentials.json` — Google service account credentials
- `.env` — actual environment variable values

---

## Architecture

```
LINE Platform
    │  POST /callback
    ▼
main.py  (FastAPI + linebot.v3 WebhookParser)
    │  parse_command() + dispatch()
    ▼
handlers.py  (command logic)
    ├── state.py   (read/write state.json — active task per user)
    └── sheets.py  (Google Sheets API — append or query rows)
```

### Module Responsibilities

| Module | Responsibility |
|---|---|
| `main.py` | Validates LINE webhook signature, routes `MessageEvent`/`TextMessageContent` events, sends reply |
| `handlers.py` | Parses raw text into `(command, argument)`, dispatches to handler functions, formats reply strings |
| `state.py` | Atomic JSON file reads/writes for per-user active task state; uses `os.replace()` for crash safety |
| `sheets.py` | Authenticates with a Google service account; `append_entry()` writes a completed row; `get_today_entries()` scans all rows for today's date and the current user |

---

## Supported Bot Commands

| User sends | Command | Behavior |
|---|---|---|
| `start <task name>` | `start` | Begins tracking; stores task + UTC start time in `state.json` |
| `stop` | `stop` | Calculates duration, writes row to Google Sheets, clears state |
| `status` | `status` | Shows active task name and elapsed minutes |
| `today` | `today` | Reads today's completed entries from Sheets for this user |
| `cancel` | `cancel` | Discards active task without saving |
| anything else | `unknown` | Returns help text listing all commands |

---

## Environment Variables

Defined in `.env` (copy from `.env.example`):

| Variable | Required | Description |
|---|---|---|
| `LINE_CHANNEL_SECRET` | Yes | Used to verify the webhook signature from LINE |
| `LINE_CHANNEL_ACCESS_TOKEN` | Yes | Used to call the LINE Messaging API (reply) |
| `GOOGLE_SPREADSHEET_ID` | Yes | The ID of the target Google Spreadsheet |
| `GOOGLE_CREDENTIALS_FILE` | No | Path to service account JSON; defaults to `credentials.json` |

---

## Google Sheets Schema

The bot reads and writes **`Sheet1`**, columns A–F (1-indexed):

| A | B | C | D | E | F |
|---|---|---|---|---|---|
| Date (`YYYY-MM-DD`) | Start time (`HH:MM:SS`) | End time (`HH:MM:SS`) | Duration (minutes, float) | Task name | LINE user ID |

Row 1 is treated as a header and skipped by `get_today_entries()`.

---

## Development Setup

```bash
# 1. Clone and enter the repo
git clone <repo-url>
cd LINE_time_management

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with real LINE credentials and Google Spreadsheet ID

# 5. Place your Google service account JSON at credentials.json

# 6. Run the server
uvicorn main:app --reload --port 8000
```

To expose the local server to LINE (which requires an HTTPS URL), use a tunnel such as `ngrok http 8000`.

---

## Key Conventions

### State management
- `state.py` always does a **full file read before every write** — there is no in-memory cache. This is intentional for simplicity but means the file is the single source of truth.
- Writes use `tempfile` + `os.replace()` (atomic rename) to avoid partial writes on crash.
- `state.json` maps `user_id → {task, start_time}`. `start_time` is stored as an ISO 8601 string (UTC).

### Time handling
- All times are captured in **UTC** (`datetime.now(timezone.utc)`).
- Display formatting converts to the **local timezone** of the server process via `.astimezone()`.
- Duration is rounded to 1 decimal place for user messages, 2 decimal places in Sheets.

### Error handling
- If writing to Sheets fails during `stop`, the active task is **not cleared** — the user is told to fix the issue and retry. This prevents data loss.
- Invalid LINE signatures raise HTTP 400.

### Dependencies
- All dependencies are **pinned** in `requirements.txt`. Update pins intentionally.
- The `line-bot-sdk` version used is **v3** (`linebot.v3.*`). Do not mix with the legacy v2 API (`linebot.*`).

### No tests yet
- There are no automated tests. When adding tests, prefer `pytest` and mock `sheets.py` at the module boundary to avoid real API calls.

---

## Deployment Notes

- The app is a standard ASGI app (`main:app`) suitable for any uvicorn-compatible host.
- LINE requires the webhook URL to be **HTTPS**. Configure TLS termination at the proxy/platform layer.
- `state.json` is local disk state — it will be lost on container restarts. For production consider replacing `state.py` with a Redis or database backend.
- The Google Sheets client (`_service`, `_creds`) is initialised **at module import time** in `sheets.py`. If `credentials.json` is missing, the process will crash on startup.
