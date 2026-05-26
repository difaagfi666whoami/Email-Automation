# spec.md — Behavioural Specification

## 1. Trigger

- The script is triggered by macOS `launchd` at **22:05 UTC** (05:05 AM Asia/Jakarta WIB).
- The script may also be run manually via CLI flags for testing (see section 7).

---

## 2. IMAP connection

| Parameter | Value |
|---|---|
| Host | `IMAP_HOST` from `.env` |
| Port | `993` |
| Security | SSL/TLS (not STARTTLS) |
| Username | `IMAP_USER` from `.env` |
| Password | `IMAP_PASS` from `.env` |
| Mailbox | `INBOX` |

Connection must succeed within **10 seconds**, otherwise log error and exit 1.

---

## 3. Email search criteria

An email is **eligible** if ALL of the following are true:

1. Status is **UNSEEN** (not yet read).
2. Subject **starts with** the string `DB Email Alert -` (case-sensitive).
3. Received time, converted to **Asia/Jakarta (WIB, UTC+7)**, falls between
   **05:00:00 and 05:59:59 inclusive**.

If zero emails match: log `INFO: no matching emails found`, exit 0. Do not send
anything to Telegram.

If one or more emails match: process each one in chronological order (oldest first).

---

## 4. Email parsing

For each matched email:

- Extract `From:` header → split into `sender_name` and `sender_email`.
  - If `From` contains a display name: `"Database Mail: TDB-2857 (192.168.28.57)"
    <it2@phillip.com.hk>` → name = `Database Mail: TDB-2857 (192.168.28.57)`,
    email = `it2@phillip.com.hk`.
  - If no display name: name = email address.
- Extract `To:` header → list of recipient addresses.
- Extract `Reply-To:` header → single address string.
- Extract `Subject:` header → decoded string (handle encoded words per RFC 2047).
- Extract `Date:` header → parse to `datetime`, convert to Asia/Jakarta.
- Extract body:
  - Prefer `text/html` part if present.
  - Fall back to `text/plain` if no HTML part.
  - If both present, use `text/html` for rendering and discard plain text.
  - If body is empty: use a fallback message `"(no body content)"`.

---

## 5. Image rendering

For each eligible email, produce one PNG file.

### 5.1 Template variables

Pass to `templates/email_view.html`:

| Variable | Type | Example |
|---|---|---|
| `sender_name` | str | `Database Mail: TDB-2857 (192.168.28.57)` |
| `sender_email` | str | `it2@phillip.com.hk` |
| `recipients` | list[str] | `["gmosupport@phillip.com.hk", "b2bteam@phillip.com.hk", ...]` |
| `reply_to` | str | `jacksonleung@phillip.com.hk` |
| `subject` | str | `DB Email Alert - GMO6 GlobalMO6 EOD Process (Prod)` |
| `body_html` | str or None | raw HTML string, or None |
| `body_text` | str | raw plain text string |
| `received_time` | str | `"2026-05-26 05:12:34"` (WIB, pre-formatted) |
| `recipient_preview_count` | int | number of recipients shown before [MORE] badge |

### 5.2 Playwright settings

| Setting | Value |
|---|---|
| Browser | Chromium (headless) |
| Viewport width | `900` px |
| Viewport height | `1080` px (initial; auto-expands for full page) |
| Wait until | `networkidle` |
| Screenshot type | `full_page=True` |
| Format | PNG |

### 5.3 Output path

```
/tmp/email_captures/email_YYYYMMDD_HHMMSS_<slug>.png
```

Where `<slug>` is the subject string lowercased, spaces replaced with `_`,
special characters removed, truncated to 40 characters.

Example: `email_20260526_051234_db_email_alert_gmo6_globalmo6_eod_.png`

Create `/tmp/email_captures/` if it does not exist.

---

## 6. Telegram send

### 6.1 Bot initialisation

- Token from `TELEGRAM_BOT_TOKEN` env var.
- Chat ID from `TELEGRAM_CHAT_ID` env var.
- Use `python-telegram-bot` v20+ async API.
- Initialise once per run, not once per email.

### 6.2 Send behaviour

- Call `bot.send_photo(chat_id=CHAT_ID, photo=open(png_path, 'rb'), caption=caption)`.
- One `send_photo` call per email (one PNG per email).
- Send in chronological order (same order as fetch).
- Wait for each send to complete before proceeding to next.

### 6.3 Caption format

```
📧 {subject}
🕐 {received_time} WIB
📬 {sender_name}
```

Example:
```
📧 DB Email Alert - GMO6 GlobalMO6 EOD Process (Prod)
🕐 2026-05-26 05:12:34 WIB
📬 Database Mail: TDB-2857 (192.168.28.57)
```

---

## 7. Mark as read

- Mark the email as `\Seen` in IMAP **only after** a confirmed successful Telegram send.
- If Telegram send fails: do NOT mark as read. The email will be retried next run.
- Use IMAP UID (not sequence number) for the store command.

---

## 8. CLI flags

| Flag | Behaviour | Marks read? | Sends to Telegram? |
|---|---|---|---|
| (none) | Full run | Yes | Yes |
| `--test-imap` | Connect + print count | No | No |
| `--test-filter` | List matching emails | No | No |
| `--test-render` | Render PNGs, save to /tmp | No | No |
| `--test-send` | Render + send | No | Yes |
| `--dry-run` | Full pipeline | No | Yes |

---

## 9. Logging

- Log file: `logs/email_bot.log` (relative to project root).
- Create `logs/` directory if it does not exist.
- Rotation: max 5 MB per file, keep 3 backups.
- Format: `%(asctime)s %(levelname)-5s [%(name)-16s] %(message)s`
- Date format: `%Y-%m-%d %H:%M:%S` in Asia/Jakarta time.
- Level: `INFO` by default. Set `LOG_LEVEL=DEBUG` in `.env` for verbose output.

### Required log events

| Event | Level | Message |
|---|---|---|
| Script start | INFO | `starting db_email_bot` |
| IMAP connected | INFO | `connected to {host} as {user}` |
| Emails found | INFO | `{n} matching emails found` |
| No emails | INFO | `no matching emails found` |
| Render start | INFO | `rendering: {subject}` |
| Render done | INFO | `rendered: {filename}` |
| Send start | INFO | `sending: {filename}` |
| Send done | INFO | `sent: {filename}` |
| Mark read | INFO | `marked read: {message_id}` |
| IMAP error | ERROR | `IMAP error: {error}` |
| Render error | ERROR | `render error for {subject}: {error}` |
| Telegram error | ERROR | `telegram error for {filename}: {error}` |
| Script done | INFO | `done. {n} emails processed, {m} sent` |

---

## 10. Environment variables

All loaded from `.env` via `python-dotenv`.

| Variable | Required | Example |
|---|---|---|
| `IMAP_HOST` | Yes | `mail.yourdomain.com` |
| `IMAP_USER` | Yes | `user@yourdomain.com` |
| `IMAP_PASS` | Yes | `yourpassword` |
| `IMAP_PORT` | No (default 993) | `993` |
| `IMAP_MAILBOX` | No (default INBOX) | `INBOX` |
| `TELEGRAM_BOT_TOKEN` | Yes | `123456:ABC-DEF...` |
| `TELEGRAM_CHAT_ID` | Yes | `987654321` |
| `LOG_LEVEL` | No (default INFO) | `DEBUG` |
| `RECIPIENT_PREVIEW_COUNT` | No (default 3) | `3` |

---

## 11. Failure modes and recovery

| Failure | Behaviour |
|---|---|
| IMAP connect timeout | Log ERROR, exit 1 |
| IMAP auth failure | Log ERROR (no password in log), exit 1 |
| No matching emails | Log INFO, exit 0 |
| Playwright not installed | Log ERROR with install command, exit 1 |
| Render failure (one email) | Log ERROR, skip email, continue to next |
| Telegram send failure (one email) | Log ERROR, do NOT mark read, continue |
| All sends fail | Log ERROR, exit 1 |
| Partial success | Log summary of successes vs failures, exit 0 |

---

## 12. .gitignore requirements

Must include:
```
.env
logs/
__pycache__/
*.pyc
/tmp/
.DS_Store
```
