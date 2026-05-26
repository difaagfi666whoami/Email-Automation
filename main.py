from __future__ import annotations

import argparse
import asyncio
import datetime
import logging
import logging.handlers
import os
import sys
from pathlib import Path

import pytz
from dotenv import load_dotenv

load_dotenv()

WIB = pytz.timezone('Asia/Jakarta')
LOG_DIR = Path(__file__).parent / 'logs'


class _WIBFormatter(logging.Formatter):
    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        dt = datetime.datetime.fromtimestamp(record.created, tz=WIB)
        return dt.strftime(datefmt or '%Y-%m-%d %H:%M:%S')


def setup_logging() -> None:
    LOG_DIR.mkdir(exist_ok=True)
    log_level = getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper(), logging.INFO)

    formatter = _WIBFormatter(
        fmt='%(asctime)s %(levelname)-5s [%(name)-16s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    file_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / 'email_bot.log',
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(log_level)
    root.addHandler(file_handler)
    root.addHandler(console_handler)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='db_email_bot — DB alert email to Telegram')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--test-imap', action='store_true', help='Connect to IMAP and print inbox count')
    group.add_argument('--test-filter', action='store_true', help='List matching emails, no render/send')
    group.add_argument('--test-render', action='store_true', help='Render matched emails to PNG, no send')
    group.add_argument('--test-send', action='store_true', help='Render and send to Telegram, no mark-as-read')
    group.add_argument('--dry-run', action='store_true', help='Full pipeline, do not mark as read')
    group.add_argument('--manual', action='store_true', help='Full pipeline, no time filter, marks as read')
    parser.add_argument('--from-file', metavar='PATH', help='Load a single .eml file instead of fetching from IMAP')
    return parser.parse_args()


async def main() -> None:
    setup_logging()
    logger = logging.getLogger('main')
    args = parse_args()

    imap_host = os.getenv('IMAP_HOST', '')
    imap_user = os.getenv('IMAP_USER', '')
    imap_pass = os.getenv('IMAP_PASS', '')
    imap_port = int(os.getenv('IMAP_PORT', '993'))
    imap_mailbox = os.getenv('IMAP_MAILBOX', 'INBOX')
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
    recipient_preview_count = int(os.getenv('RECIPIENT_PREVIEW_COUNT', '3'))

    if not all([imap_host, imap_user, imap_pass]):
        logger.error('IMAP_HOST, IMAP_USER, IMAP_PASS must be set in .env')
        sys.exit(1)

    needs_telegram = not any([args.test_imap, args.test_filter, args.test_render])
    if needs_telegram and not all([telegram_token, telegram_chat_id]):
        logger.error('TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in .env')
        sys.exit(1)

    logger.info('starting db_email_bot')

    from imap_fetcher import IMAPFetcher, parse_raw_email
    import email_renderer
    import telegram_sender

    fetcher = None

    if args.from_file:
        with open(args.from_file, 'rb') as fh:
            raw = fh.read()
        parsed = parse_raw_email(raw)
        if parsed is None:
            logger.error(f'could not parse email from {args.from_file}')
            sys.exit(1)
        messages = [parsed]
        logger.info(f'1 email loaded from file: {args.from_file}')
    else:
        fetcher = IMAPFetcher(imap_host, imap_user, imap_pass, imap_port, imap_mailbox)
        try:
            fetcher.connect()
        except Exception:
            sys.exit(1)

        if args.test_imap:
            count = fetcher.get_inbox_count()
            print(f'✅ Connected to {imap_host} as {imap_user} — {count} messages in INBOX')
            fetcher.close()
            return

        is_test_mode = any([args.test_filter, args.test_render, args.test_send, args.dry_run, args.manual])

        try:
            messages = fetcher.fetch_matching(skip_time_filter=is_test_mode)
        except Exception as exc:
            logger.error(f'IMAP error: {exc}')
            fetcher.close()
            sys.exit(1)

        if not messages:
            logger.info('no matching emails found')
            fetcher.close()
            return

        logger.info(f'{len(messages)} matching emails found')

        if args.test_filter:
            for msg in messages:
                print(f'  {msg.received_time.strftime("%Y-%m-%d %H:%M:%S")} WIB — {msg.subject}')
            fetcher.close()
            return

    sent_count = 0
    processed_count = 0
    mark_read = not any([args.test_send, args.dry_run, bool(args.from_file)]) or args.manual

    for msg in messages:
        processed_count += 1

        try:
            png_path = await email_renderer.render(msg, recipient_preview_count)
        except Exception:
            continue

        if args.test_render:
            continue

        results = await telegram_sender.send_photos(
            telegram_token,
            telegram_chat_id,
            [(
                png_path,
                msg.subject,
                msg.received_time.strftime('%Y-%m-%d %H:%M:%S'),
                msg.sender_name,
            )],
        )

        success = results[0] if results else False
        if success:
            sent_count += 1
            if mark_read and fetcher:
                fetcher.mark_as_read(msg.uid, msg.message_id)

    if fetcher:
        fetcher.close()

    if args.test_render:
        from email_renderer import OUTPUT_DIR
        print(f'✅ Rendered {processed_count} email(s) to {OUTPUT_DIR}')
        return

    logger.info(f'done. {processed_count} emails processed, {sent_count} sent')

    if processed_count > 0 and sent_count == 0:
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
