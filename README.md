# db_email_bot

Fetches `DB Email Alert -` emails via IMAP every morning, renders each as a
Thunderbird-style PNG screenshot, and sends it to a Telegram chat.

---

## Requirements

- macOS (tested on macOS 13+)
- Python 3.11+
- An IMAP email account (username + password)
- A Telegram bot token and chat ID

---

## Setup

### 1. Clone and enter the project

```bash
cd db_email_bot
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Install Playwright browser

```bash
playwright install chromium
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in:

```
IMAP_HOST=mail.yourdomain.com
IMAP_PORT=993
IMAP_USER=your@email.com
IMAP_PASS=yourpassword

TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

### 5. Set up your Telegram bot

1. Open Telegram, search for **@BotFather**
2. Send `/newbot` and follow the steps
3. Copy the **Bot Token** → paste into `TELEGRAM_BOT_TOKEN`
4. Send any message to your new bot (e.g. `/start`)
5. Visit in your browser:
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
6. Find `"chat":{"id": 123456789}` → paste into `TELEGRAM_CHAT_ID`

---

## Testing (run in this order)

### Step 1 — Test IMAP connection
```bash
python main.py --test-imap
```
Expected: `✅ Connected to <host> as <user>` and inbox count.

### Step 2 — Test email filter
```bash
python main.py --test-filter
```
Expected: list of matching emails (subject + received time). No images sent.

### Step 3 — Test rendering
```bash
python main.py --test-render
```
Expected: PNG files saved to `/tmp/email_captures/`. Open in Finder to verify
they look like the reference Thunderbird screenshots.

### Step 4 — Test Telegram send
```bash
python main.py --test-send
```
Expected: PNG images arrive in your Telegram chat. Emails NOT marked as read.

### Step 5 — Full dry run
```bash
python main.py --dry-run
```
Expected: full pipeline runs, images sent, emails NOT marked as read. Safe to
repeat.

### Step 6 — Full live run
```bash
python main.py
```
Runs everything, marks emails as read, writes to `logs/email_bot.log`.

---

## Scheduler (launchd)

Install the daily 05:05 AM WIB scheduler:

```bash
cp scheduler/com.dbalert.emailbot.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.dbalert.emailbot.plist
```

Verify it is registered:
```bash
launchctl list | grep dbalert
```

Check logs after the next morning run:
```bash
cat ~/Library/Logs/dbalert_emailbot.log
```

To unload the scheduler:
```bash
launchctl unload ~/Library/LaunchAgents/com.dbalert.emailbot.plist
```

---

## Logs

Runtime logs are written to `logs/email_bot.log` (in the project folder).
The scheduler also writes to `~/Library/Logs/dbalert_emailbot.log`.

---

## Project structure

```
db_email_bot/
├── CLAUDE.md                 Claude Code instructions
├── architecture.md           System design
├── spec.md                   Behaviour specification
├── spec_template.md          HTML template visual spec
├── main.py                   Entry point + orchestrator
├── imap_fetcher.py           IMAP fetch logic
├── email_renderer.py         HTML → PNG via Playwright
├── telegram_sender.py        Telegram bot sender
├── templates/
│   └── email_view.html       Jinja2 email view template
├── scheduler/
│   └── com.dbalert.emailbot.plist
├── logs/                     Created at runtime
├── .env                      Your credentials (not committed)
├── .env.example              Template for .env
├── requirements.txt
└── README.md
```

---

## Troubleshooting

**`playwright install chromium` fails**
→ Make sure you ran `pip install playwright` first.

**IMAP authentication error**
→ Check `IMAP_HOST`, `IMAP_USER`, `IMAP_PASS` in `.env`.
→ Some servers require an app password (not your main account password).

**No emails found**
→ Run `--test-filter` and check the time window. The script only fetches emails
   received between 05:00–06:00 WIB. For testing outside that window, temporarily
   comment out the time filter in `imap_fetcher.py`.

**Telegram bot not responding**
→ Make sure you sent at least one message to the bot before running the script.
→ Check `TELEGRAM_CHAT_ID` is correct (use `getUpdates` endpoint).

**PNG looks wrong**
→ Check `spec_template.md` validation checklist.
→ Run `--test-render` and open the PNG in Finder.
