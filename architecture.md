# architecture.md — System Architecture

## Overview

`db_email_bot` is a single-machine Python automation that runs on macOS.
It has no server, no database, and no web interface.
It is triggered by `launchd` once per day at 05:05 AM WIB.

---

## Component map

```
┌─────────────────────────────────────────────────────────────────┐
│  macOS machine (user's laptop / desktop)                        │
│                                                                 │
│  ┌──────────────┐                                               │
│  │   launchd    │  triggers at 05:05 AM WIB                    │
│  └──────┬───────┘                                               │
│         │ spawns                                                │
│         ▼                                                       │
│  ┌──────────────┐                                               │
│  │   main.py    │  orchestrator — calls modules in order        │
│  └──────┬───────┘                                               │
│         │                                                       │
│    ┌────┴──────────────────────────┐                            │
│    │                               │                            │
│    ▼                               ▼                            │
│  ┌─────────────────┐   ┌─────────────────────┐                 │
│  │  imap_fetcher   │   │   email_renderer    │                 │
│  │                 │   │                     │                 │
│  │ • IMAP connect  │   │ • Jinja2 build HTML │                 │
│  │ • Search UNSEEN │   │ • Playwright launch │                 │
│  │ • Fetch emails  │   │ • Screenshot PNG    │                 │
│  │ • Mark \Seen    │   │ • Save to /tmp/     │                 │
│  └────────┬────────┘   └──────────┬──────────┘                 │
│           │                       │                            │
│           │            ┌──────────▼──────────┐                 │
│           │            │   telegram_sender   │                 │
│           │            │                     │                 │
│           │            │ • Bot init (async)  │                 │
│           │            │ • sendPhoto per PNG │                 │
│           │            │ • Caption format    │                 │
│           │            └─────────────────────┘                 │
│           │                       │                            │
│           └───────────────────────┘                            │
│           mark \Seen only after successful send                 │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  logs/email_bot.log   (rotating, 5MB max, 3 backups)    │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
  ┌─────────────┐               ┌──────────────────┐
  │ IMAP server │               │  Telegram API    │
  │ port 993    │               │  api.telegram.org│
  │ SSL / TLS   │               │  sendPhoto       │
  └─────────────┘               └──────────────────┘
```

---

## Module responsibilities

### main.py
- Entry point and orchestrator only.
- Parses CLI flags (`--test-imap`, `--test-filter`, `--test-render`, `--test-send`,
  `--dry-run`).
- Loads `.env`.
- Calls `imap_fetcher` → `email_renderer` → `telegram_sender` in sequence.
- Handles top-level exception logging.
- Contains no business logic.

### imap_fetcher.py
**Inputs:** IMAP credentials from env.
**Outputs:** list of `EmailMessage` dataclass objects.

Responsibilities:
- Open IMAP SSL connection.
- Search for UNSEEN emails where subject starts with `DB Email Alert -`.
- Filter by received time: 05:00–06:00 Asia/Jakarta (WIB).
- Parse raw RFC 2822 message into structured fields.
- Expose `mark_as_read(uid)` method — called only after confirmed Telegram send.
- Close IMAP connection cleanly.

Does NOT know about rendering or Telegram.

### email_renderer.py
**Inputs:** `EmailMessage` dataclass.
**Outputs:** absolute path to saved PNG file.

Responsibilities:
- Load `templates/email_view.html` Jinja2 template.
- Inject email fields (sender, recipients, subject, body, time) into template.
- Launch headless Chromium via Playwright (async).
- Set viewport to 900px wide.
- Wait for `networkidle`.
- Take full-page screenshot.
- Save PNG to `/tmp/email_captures/email_YYYYMMDD_HHMMSS_<slug>.png`.
- Return the saved file path.

Does NOT know about IMAP or Telegram.

### telegram_sender.py
**Inputs:** list of `(png_path, email_subject, received_time)` tuples.
**Outputs:** list of booleans indicating success per image.

Responsibilities:
- Initialise `python-telegram-bot` async bot with token from env.
- Call `bot.send_photo()` for each PNG.
- Format caption: `📧 {subject}\n🕐 {time} WIB\n📬 {sender_name}`.
- Return success/failure per send (used by main.py to decide mark-as-read).

Does NOT know about IMAP or rendering.

### templates/email_view.html
- Jinja2 template only.
- Renders a static HTML page that mimics the Thunderbird email view.
- Accepts variables: `sender_name`, `sender_email`, `recipients`, `reply_to`,
  `subject`, `body_text`, `received_time`.
- See `spec_template.md` for exact visual requirements.

---

## Data flow (step by step)

```
launchd
  └─▶ main.py
        └─▶ imap_fetcher.connect()
              └─▶ imap_fetcher.fetch_matching()
                    returns [EmailMessage, ...]
              └─▶ for each EmailMessage:
                    email_renderer.render(msg)
                      returns png_path
                    telegram_sender.send(png_path, msg)
                      returns success: bool
                    if success:
                      imap_fetcher.mark_as_read(msg.uid)
        └─▶ imap_fetcher.close()
        └─▶ log summary
```

---

## EmailMessage dataclass

```python
@dataclass
class EmailMessage:
    uid: str                  # IMAP UID (used for mark-as-read)
    message_id: str           # RFC 2822 Message-ID header
    subject: str              # e.g. "DB Email Alert - GMO6 EOD Process (Prod)"
    sender_name: str          # e.g. "Database Mail: TDB-2857 (192.168.28.57)"
    sender_email: str         # e.g. "it2@phillip.com.hk"
    recipients: list[str]     # To: field list
    reply_to: str             # Reply-To: field
    received_time: datetime   # parsed in Asia/Jakarta timezone
    body_text: str            # plain text body (may include CSV-style tables)
    body_html: str | None     # HTML body if present, else None
```

---

## File layout

```
db_email_bot/
├── CLAUDE.md                          ← Claude Code instructions
├── architecture.md                    ← this file
├── spec.md                            ← behaviour specification
├── spec_template.md                   ← HTML template visual specification
├── main.py
├── imap_fetcher.py
├── email_renderer.py
├── telegram_sender.py
├── templates/
│   └── email_view.html
├── scheduler/
│   └── com.dbalert.emailbot.plist
├── logs/                              ← created at runtime
├── .env                               ← not committed
├── .env.example                       ← committed, no real values
├── .gitignore
├── requirements.txt
└── README.md
```

---

## External dependencies

| Service | Protocol | Auth |
|---|---|---|
| IMAP mail server | IMAP over SSL, port 993 | username + password |
| Telegram Bot API | HTTPS REST | Bot token |

No other external services. No database. No message queue.

---

## Timezone handling

All time comparisons use `pytz` with `Asia/Jakarta` (WIB, UTC+7).
The launchd schedule fires at 22:05 UTC = 05:05 WIB.
The fetch window filter checks `05:00 <= received_time_wib <= 06:00`.
All log timestamps are written in WIB for readability.
