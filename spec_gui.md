# spec_gui.md — GUI Specification

## Overview

`gui.py` is a CustomTkinter desktop window that wraps the existing pipeline.
It replaces the need to run `python3 main.py --manual` from terminal.
Double-click `gui.py` to launch. No terminal required after setup.

---

## Core behaviour change from CLI

| Before (CLI) | After (GUI) |
|---|---|
| Time filter hardcoded 05:00–06:00 | Configurable via UI, default 05:00–06:00 |
| Subject prefix hardcoded | Configurable via UI, default `DB Email Alert -` |
| Output dir hardcoded | Configurable via UI, persists between runs |
| Run time fixed (launchd or manual) | Run anytime via "Run Now" button |
| Skip filter via `--manual` flag | "Skip time filter" toggle in UI |

---

## Window layout

```
┌──────────────────────────────────────────────┐
│  📧  db_email_bot                            │
├──────────────────────────────────────────────┤
│  SETTINGS                                    │
│                                              │
│  Subject filter                              │
│  ┌────────────────────────────────────────┐  │
│  │ DB Email Alert -                       │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  Time window (WIB)                           │
│  From [05] : 00 AM    To [06] : 00 AM        │
│                                              │
│  ☑ Skip time filter  ← always on by default │
│                                              │
│  Output folder                               │
│  ┌──────────────────────────────────┐ [📁]  │
│  │ /Users/.../Pictures/Email Auto   │       │
│  └──────────────────────────────────┘       │
│                                              │
│  ┌──────────────────────────────────────┐   │
│  │           ▶  Run Now                 │   │
│  └──────────────────────────────────────┘   │
├──────────────────────────────────────────────┤
│  LOG OUTPUT                                  │
│  ┌────────────────────────────────────────┐  │
│  │ 2026-05-26 05:41 INFO starting bot     │  │
│  │ 2026-05-26 05:41 INFO connected to...  │  │
│  │ 2026-05-26 05:41 INFO 3 emails found   │  │
│  │ 2026-05-26 05:41 INFO rendering: DB... │  │
│  │ 2026-05-26 05:41 INFO sent: email_.png │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  Status: ● 3 sent  ○ 0 failed    [Clear log] │
└──────────────────────────────────────────────┘
```

---

## Window properties

| Property | Value |
|---|---|
| Framework | `customtkinter` |
| Theme | `dark` |
| Width | `520px` |
| Height | `680px` |
| Resizable | No |
| Title | `db_email_bot` |

---

## Fields

### Subject filter
- Type: `CTkEntry`
- Default: `DB Email Alert -`
- Passed to `imap_fetcher` as `subject_prefix` override
- Validates: must not be empty

### Start hour / End hour
- Type: `CTkOptionMenu` with values `0` to `23`
- Default: start = `5`, end = `6`
- Passed to `imap_fetcher` as `start_hour` / `end_hour` override
- Only active when "Skip time filter" is OFF

### Skip time filter toggle
- Type: `CTkSwitch`
- Default: **ON** (always skip filter on GUI runs)
- When ON: passes `skip_time_filter=True` to `fetch_matching`
- When OFF: time window fields become active

### Output folder
- Type: `CTkEntry` + `CTkButton` (folder icon)
- Default: loaded from `config.json`, fallback to `~/Pictures/Email Automation`
- Folder picker button opens `tkinter.filedialog.askdirectory`
- Passed to `email_renderer` as `output_dir` override

### Run Now button
- Type: `CTkButton`, accent color
- Triggers the full pipeline in a background thread
- Disabled while a run is in progress
- Re-enabled when run completes

---

## Log output panel

- Type: `CTkTextbox`, read-only, monospace font
- Scrolls automatically to bottom on new lines
- Captures all Python `logging` output in real time
- Colour coding:
  - `INFO` lines → default text colour
  - `ERROR` lines → red (`#ff4444`)
  - `sent:` lines → green (`#44ff88`)

---

## Status bar

Shows summary after each run:
```
● 3 sent   ○ 0 failed        [Clear log]
```
- Green dot for sent count
- Red dot for failed count
- `Clear log` button wipes the log textbox

---

## Settings persistence — `config.json`

Save settings to `config.json` in the project root on every run.
Load on startup.

```json
{
  "subject_filter": "DB Email Alert -",
  "start_hour": 5,
  "end_hour": 6,
  "skip_time_filter": true,
  "output_dir": "/Users/difaagfi/Pictures/Email Automation"
}
```

---

## Threading model

The pipeline MUST run in a background thread, not the main thread.
The GUI must remain responsive during a run.

```python
import threading

def on_run_clicked():
    run_button.configure(state='disabled')
    thread = threading.Thread(target=run_pipeline, daemon=True)
    thread.start()

def run_pipeline():
    # call asyncio.run(main(...)) here
    # post log lines to GUI via gui.after(0, append_log, line)
    ...
```

---

## How GUI overrides existing pipeline

`gui.py` calls the existing modules directly with overrides:

```python
# Override imap_fetcher constants at runtime
imap_fetcher.SUBJECT_PREFIX = subject_filter_value
imap_fetcher.FETCH_WINDOW_START_HOUR = start_hour_value
imap_fetcher.FETCH_WINDOW_END_HOUR = end_hour_value

# Override email_renderer output dir at runtime
email_renderer.OUTPUT_DIR = Path(output_dir_value)

# Pass skip_time_filter=True when toggle is ON
messages = fetcher.fetch_matching(skip_time_filter=True)
```

No changes to `imap_fetcher.py`, `email_renderer.py`, or `main.py`.
`gui.py` is purely additive.

---

## New file: `run_gui.command`

A double-clickable macOS launcher:

```bash
#!/bin/bash
cd /Users/difaagfi/Documents/Project/Email\ Automation
python3 gui.py
```

Set executable: `chmod +x run_gui.command`
User can double-click this from Finder to open the GUI without terminal.

---

## New dependency

Add to `requirements.txt`:
```
customtkinter>=5.2.0
```

---

## What does NOT change

- `main.py` — untouched
- `imap_fetcher.py` — untouched
- `email_renderer.py` — untouched
- `telegram_sender.py` — untouched
- `templates/email_view.html` — untouched
- `.env` — still the source of all credentials
- All CLI flags still work as before
