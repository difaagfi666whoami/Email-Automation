# Claude Code Prompt — Build GUI

Paste this entire prompt into Claude Code.

---

Read `spec_gui.md` fully before writing any code.

Build `gui.py` — a CustomTkinter desktop GUI that wraps the existing
db_email_bot pipeline. Follow every detail in spec_gui.md exactly.

## Rules
- Do NOT modify `main.py`, `imap_fetcher.py`, `email_renderer.py`,
  or `telegram_sender.py`
- `gui.py` is purely additive — it calls the existing modules directly
- All credentials still come from `.env` — GUI only controls filter params
- Pipeline must run in a background thread (GUI stays responsive)
- Log output must stream in real time to the CTkTextbox panel

## Deliver in this order

### 1. Update `requirements.txt`
Add: `customtkinter>=5.2.0`

### 2. Create `gui.py`

Structure:
```
gui.py
├── imports
├── LogHandler class (routes logging to CTkTextbox)
├── App class (CTkTk window)
│   ├── __init__ (build all widgets)
│   ├── load_config()
│   ├── save_config()
│   ├── on_run_clicked() → starts background thread
│   ├── run_pipeline() → runs in thread, calls existing modules
│   ├── append_log(line) → thread-safe GUI update
│   └── on_browse_folder() → folder picker
└── if __name__ == '__main__': App().mainloop()
```

### 3. Create `run_gui.command`

A double-clickable macOS launcher:
```bash
#!/bin/bash
cd "$(dirname "$0")"
python3 gui.py
```
This must work regardless of where the project folder is located.
Use `$(dirname "$0")` not a hardcoded path.

## Key implementation details

### Threading
```python
import threading
import asyncio

def run_pipeline(self):
    # Override module-level constants before running
    import imap_fetcher, email_renderer
    imap_fetcher.SUBJECT_PREFIX = self.subject_var.get()
    imap_fetcher.FETCH_WINDOW_START_HOUR = int(self.start_hour_var.get())
    imap_fetcher.FETCH_WINDOW_END_HOUR = int(self.end_hour_var.get())
    email_renderer.OUTPUT_DIR = Path(self.output_var.get())

    # Run async pipeline
    asyncio.run(self._async_run())
```

### Log capture
```python
class LogHandler(logging.Handler):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def emit(self, record):
        msg = self.format(record)
        self.callback(msg, record.levelname)
```

### Thread-safe GUI update
```python
def append_log(self, line: str, level: str = 'INFO'):
    # Must use self.after(0, ...) — never update tkinter from a thread directly
    self.after(0, self._insert_log, line, level)

def _insert_log(self, line: str, level: str):
    self.log_box.configure(state='normal')
    tag = 'error' if level == 'ERROR' else ('success' if 'sent:' in line else 'normal')
    self.log_box.insert('end', line + '\n')
    self.log_box.see('end')
    self.log_box.configure(state='disabled')
```

### Skip time filter default
```python
# Default ON — user can run at any time
self.skip_filter_var = ctk.BooleanVar(value=True)
```

### Config persistence
```python
CONFIG_PATH = Path(__file__).parent / 'config.json'

def load_config(self):
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {
        "subject_filter": "DB Email Alert -",
        "start_hour": 5,
        "end_hour": 6,
        "skip_time_filter": True,
        "output_dir": str(Path.home() / "Pictures" / "Email Automation")
    }

def save_config(self):
    config = {
        "subject_filter": self.subject_var.get(),
        "start_hour": int(self.start_hour_var.get()),
        "end_hour": int(self.end_hour_var.get()),
        "skip_time_filter": self.skip_filter_var.get(),
        "output_dir": self.output_var.get()
    }
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)
```

## After building, verify these work

1. `pip install customtkinter` → no errors
2. `python3 gui.py` → window opens
3. Fill fields → click Run Now → log streams in real time
4. PNG appears in output folder
5. Telegram receives the photo
6. Close and reopen → settings are remembered from config.json
7. Double-click `run_gui.command` in Finder → GUI opens without terminal
