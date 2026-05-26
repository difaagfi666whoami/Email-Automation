from __future__ import annotations

import email
import email.header
import imaplib
import logging
import socket
from dataclasses import dataclass
from datetime import date, datetime
from email.utils import getaddresses, parseaddr, parsedate_to_datetime

import pytz

logger = logging.getLogger('imap_fetcher')

WIB = pytz.timezone('Asia/Jakarta')
SUBJECT_PREFIX = 'DB Email Alert -'
FETCH_WINDOW_START_HOUR = 5
FETCH_WINDOW_END_HOUR = 6


def _decode_header(value: str) -> str:
    parts = email.header.decode_header(value)
    decoded: list[str] = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or 'utf-8', errors='replace'))
        else:
            decoded.append(part)
    return ''.join(decoded).strip()


def _extract_body(msg: email.message.Message) -> tuple[str, str | None]:
    body_text = ''
    body_html: str | None = None

    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            disposition = str(part.get('Content-Disposition', ''))
            if 'attachment' in disposition:
                continue
            if ct == 'text/html' and body_html is None:
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or 'utf-8'
                body_html = payload.decode(charset, errors='replace')
            elif ct == 'text/plain' and not body_text:
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or 'utf-8'
                body_text = payload.decode(charset, errors='replace')
    else:
        ct = msg.get_content_type()
        payload = msg.get_payload(decode=True)
        charset = msg.get_content_charset() or 'utf-8'
        text = payload.decode(charset, errors='replace') if payload else ''
        if ct == 'text/html':
            body_html = text
        else:
            body_text = text

    if not body_text and not body_html:
        body_text = '(no body content)'

    return body_text, body_html


@dataclass
class EmailMessage:
    uid: str
    message_id: str
    subject: str
    sender_name: str
    sender_email: str
    recipients: list[str]
    reply_to: str
    received_time: datetime
    body_text: str
    body_html: str | None


def parse_raw_email(raw: bytes, uid: str = 'file') -> EmailMessage | None:
    msg = email.message_from_bytes(raw)

    subject = _decode_header(msg.get('Subject', ''))

    date_header = msg.get('Date', '')
    try:
        received_dt = parsedate_to_datetime(date_header)
        received_wib = received_dt.astimezone(WIB)
    except Exception:
        return None

    from_raw = msg.get('From', '')
    display_name, addr = parseaddr(from_raw)
    sender_name = display_name if display_name else addr
    sender_email = addr

    to_raw = msg.get('To', '')
    recipients = [a for _, a in getaddresses([to_raw]) if a]

    reply_to_raw = msg.get('Reply-To', from_raw)
    _, reply_to = parseaddr(reply_to_raw)
    reply_to = reply_to or addr

    message_id = msg.get('Message-ID', uid)
    body_text, body_html = _extract_body(msg)

    return EmailMessage(
        uid=uid,
        message_id=message_id,
        subject=subject,
        sender_name=sender_name,
        sender_email=sender_email,
        recipients=recipients,
        reply_to=reply_to,
        received_time=received_wib,
        body_text=body_text,
        body_html=body_html,
    )


class IMAPFetcher:
    def __init__(
        self,
        host: str,
        user: str,
        password: str,
        port: int = 993,
        mailbox: str = 'INBOX',
    ) -> None:
        self.host = host
        self.user = user
        self._password = password
        self.port = port
        self.mailbox = mailbox
        self._conn: imaplib.IMAP4_SSL | None = None

    def connect(self) -> None:
        try:
            socket.setdefaulttimeout(60)
            self._conn = imaplib.IMAP4_SSL(self.host, self.port)
            self._conn.socket().settimeout(60)
            self._conn.login(self.user, self._password)
            logger.info(f'connected to {self.host} as {self.user}')
        except imaplib.IMAP4.error as exc:
            logger.error(f'IMAP error: {exc}')
            raise
        except socket.timeout:
            logger.error(f'IMAP error: connection to {self.host} timed out after 60s')
            raise

    def get_inbox_count(self) -> int:
        typ, counts = self._conn.select('INBOX', readonly=True)
        if typ == 'OK' and counts[0]:
            return int(counts[0])
        return 0

    def fetch_matching(
        self,
        skip_time_filter: bool = False,
        include_read: bool = False,
        filter_date: date | None = None,
    ) -> list[EmailMessage]:
        self._conn.select(self.mailbox, readonly=False)
        seen_flag = '' if include_read else 'UNSEEN '
        date_flag = f' ON {filter_date.strftime("%d-%b-%Y")}' if filter_date else ''
        search_criteria = f'{seen_flag}SUBJECT "{SUBJECT_PREFIX}"{date_flag}'
        typ, data = self._conn.uid('search', None, search_criteria)
        if typ != 'OK' or not data[0]:
            return []

        uids = data[0].split()
        messages: list[EmailMessage] = []

        for uid in uids:
            typ, msg_data = self._conn.uid('fetch', uid, '(RFC822)')
            if typ != 'OK' or not msg_data or msg_data[0] is None:
                continue

            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            subject = _decode_header(msg.get('Subject', ''))
            if not subject.startswith(SUBJECT_PREFIX):
                continue

            date_header = msg.get('Date', '')
            try:
                received_dt = parsedate_to_datetime(date_header)
                received_wib = received_dt.astimezone(WIB)
            except Exception:
                continue

            if not skip_time_filter:
                if not (FETCH_WINDOW_START_HOUR <= received_wib.hour < FETCH_WINDOW_END_HOUR):
                    continue

            from_raw = msg.get('From', '')
            display_name, addr = parseaddr(from_raw)
            sender_name = display_name if display_name else addr
            sender_email = addr

            to_raw = msg.get('To', '')
            recipients = [a for _, a in getaddresses([to_raw]) if a]

            reply_to_raw = msg.get('Reply-To', from_raw)
            _, reply_to = parseaddr(reply_to_raw)
            reply_to = reply_to or addr

            message_id = msg.get('Message-ID', uid.decode())
            body_text, body_html = _extract_body(msg)

            messages.append(EmailMessage(
                uid=uid.decode(),
                message_id=message_id,
                subject=subject,
                sender_name=sender_name,
                sender_email=sender_email,
                recipients=recipients,
                reply_to=reply_to,
                received_time=received_wib,
                body_text=body_text,
                body_html=body_html,
            ))

        messages.sort(key=lambda m: m.received_time)
        return messages

    def mark_as_read(self, uid: str, message_id: str = '') -> None:
        self._conn.uid('store', uid, '+FLAGS', '\\Seen')
        logger.info(f'marked read: {message_id or uid}')

    def close(self) -> None:
        if self._conn:
            try:
                self._conn.close()
                self._conn.logout()
            except Exception:
                pass
