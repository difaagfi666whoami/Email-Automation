# CLAUDE.md — Instructions for Claude Code

This file governs how Claude Code must behave when building, editing, or extending
this project. Read this file before touching any other file.

---

## Project identity

This project is called **db_email_bot**.
Its single purpose: fetch DB alert emails via IMAP, render each as a PNG image that
visually matches a Thunderbird email view, and send that PNG to a Telegram chat via bot.

---

## Hard constraints — never violate these

1. **No hardcoded credentials.** Every secret (IMAP host, user, pass, Telegram token,
   chat ID) must be loaded from `.env` via `python-dotenv`. No exceptions.

2. **No plain-text output to Telegram.** The Telegram message must always be an image
   (sendPhoto). Never sendMessage with raw email content.

3. **No modification of emails beyond marking as read.** Do not delete, move, or archive
   emails. Only set the `\Seen` IMAP flag after a successful send.

4. **No third-party cloud services.** Everything runs locally on the user's macOS machine.
   No AWS, no GCP, no SaaS email parsers.

5. **Python 3.11+ only.** Do not use deprecated APIs or syntax below 3.11.

6. **Async Telegram only.** Use `python-telegram-bot` v20+ with `asyncio`. Do not use
   the legacy synchronous API.

7. **Never import Playwright synchronously.** Always use `async_playwright` from
   `playwright.async_api`.

8. **One file per responsibility.** Do not dump all logic into `main.py`. Each module
   has a single job — see architecture.md.

---

## What Claude Code must do before writing any code

1. Read `CLAUDE.md` (this file).
2. Read `architecture.md` — understand the module boundaries.
3. Read `spec.md` — understand the exact behaviour required.
4. Read `spec_template.md` — understand the exact HTML output required.
5. Only then write or edit code.

---

## Module ownership rules

| File | Owns | Must not |
|---|---|---|
| `main.py` | Orchestration only | Contain business logic |
| `imap_fetcher.py` | IMAP connection, search, fetch, mark-read | Know about rendering or Telegram |
| `email_renderer.py` | HTML template build + Playwright screenshot | Know about IMAP or Telegram |
| `telegram_sender.py` | Telegram bot, sendPhoto | Know about IMAP or rendering |
| `templates/email_view.html` | Jinja2 HTML template | Contain Python logic |

---

## Dependency rules

- Only use libraries listed in `requirements.txt`.
- Do not add new libraries without updating `requirements.txt` and noting the reason
  in a comment.
- Do not use `subprocess` to call external tools as a workaround.

---

## Error handling rules

- IMAP failure → log error, exit cleanly. Do not crash with unhandled exception.
- No matching emails → log `INFO: no matching emails found`, exit 0. Do not send
  anything to Telegram.
- Playwright failure → log error with email subject, skip that email, continue to next.
- Telegram send failure → log error, do not mark email as read (so it will be retried
  next run).
- All errors go to `logs/email_bot.log` via Python `logging` with rotation.

---

## Logging format

```
2026-05-26 05:05:01 INFO  [imap_fetcher]     connected to mail.example.com
2026-05-26 05:05:02 INFO  [imap_fetcher]     3 matching emails found
2026-05-26 05:05:04 INFO  [email_renderer]   rendered: email_20260526_050504_gmo6.png
2026-05-26 05:05:06 INFO  [telegram_sender]  sent: email_20260526_050504_gmo6.png
2026-05-26 05:05:06 INFO  [imap_fetcher]     marked read: <message-id>
```

---

## CLI flags required in main.py

| Flag | Behaviour |
|---|---|
| `(no flag)` | Full live run |
| `--test-imap` | Connect to IMAP, print inbox count, exit |
| `--test-filter` | List matched emails (subject + time), no render, no send |
| `--test-render` | Render matched emails to PNG, save to /tmp/email_captures/, no send |
| `--test-send` | Render + send to Telegram, do NOT mark as read |
| `--dry-run` | Full pipeline, do NOT mark as read |

---

## macOS scheduler

- Use `launchd` via a `.plist` file. Do not use `cron`.
- Scheduled time: **22:05 UTC** (= 05:05 AM Asia/Jakarta WIB, UTC+7).
- `.plist` must use full absolute paths for both the Python interpreter and the script.
- Log stdout and stderr to `~/Library/Logs/dbalert_emailbot.log`.
- File location: `scheduler/com.dbalert.emailbot.plist`.
- Load command: `launchctl load ~/Library/LaunchAgents/com.dbalert.emailbot.plist`.

---

## What Claude Code must never do

- Never guess IMAP behaviour — use only documented `imaplib` API.
- Never assume the email body is HTML. Check content-type first; fall back to plain text.
- Never use `time.sleep` in async code — use `asyncio.sleep`.
- Never leave TODO comments in production code paths.
- Never print credentials to stdout or logs.
- Never write tests that actually send messages to Telegram.
