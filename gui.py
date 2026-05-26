from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import tkinter as tk
from datetime import date, datetime
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
import pytz
from dotenv import load_dotenv

WIB = pytz.timezone('Asia/Jakarta')

load_dotenv()

ctk.set_appearance_mode('dark')
ctk.set_default_color_theme('blue')

CONFIG_PATH = Path(__file__).parent / 'config.json'
DEFAULT_OUTPUT = str(Path.home() / 'Pictures' / 'Email Automation')


class LogHandler(logging.Handler):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def emit(self, record):
        msg = self.format(record)
        self.callback(msg, record.levelname)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title('db_email_bot')
        self.geometry('520x760')
        self.resizable(False, False)

        config = self.load_config()

        self.subject_var = ctk.StringVar(value=config['subject_filter'])
        self.start_hour_var = ctk.StringVar(value=str(config['start_hour']))
        self.end_hour_var = ctk.StringVar(value=str(config['end_hour']))
        self.skip_filter_var = ctk.BooleanVar(value=config['skip_time_filter'])
        self.include_read_var = ctk.BooleanVar(value=config.get('include_read', False))
        self.date_mode_var = ctk.StringVar(value=config.get('date_mode', 'Today'))
        today_str = datetime.now(WIB).strftime('%Y-%m-%d')
        self.custom_date_var = ctk.StringVar(value=config.get('custom_date', today_str))
        self.output_var = ctk.StringVar(value=config['output_dir'])

        self._build_widgets()
        self._setup_log_handler()
        self._update_time_widgets()
        self._update_date_widgets()

    # ------------------------------------------------------------------
    # Widget construction
    # ------------------------------------------------------------------

    def _build_widgets(self):
        # Title row
        title_frame = ctk.CTkFrame(self, fg_color='transparent')
        title_frame.pack(fill='x', padx=20, pady=(16, 0))
        ctk.CTkLabel(
            title_frame,
            text='📧  db_email_bot',
            font=ctk.CTkFont(size=20, weight='bold'),
        ).pack(side='left')

        # SETTINGS label
        ctk.CTkLabel(
            self,
            text='SETTINGS',
            font=ctk.CTkFont(size=11, weight='bold'),
            text_color='#888888',
        ).pack(anchor='w', padx=20, pady=(14, 4))

        settings_frame = ctk.CTkFrame(self)
        settings_frame.pack(fill='x', padx=20, pady=(0, 8))

        # Subject filter
        ctk.CTkLabel(
            settings_frame,
            text='Subject filter',
            font=ctk.CTkFont(size=12),
        ).pack(anchor='w', padx=12, pady=(12, 2))
        self.subject_entry = ctk.CTkEntry(
            settings_frame,
            textvariable=self.subject_var,
            width=476,
        )
        self.subject_entry.pack(padx=12, pady=(0, 10))

        # Time window
        ctk.CTkLabel(
            settings_frame,
            text='Time window (WIB)',
            font=ctk.CTkFont(size=12),
        ).pack(anchor='w', padx=12, pady=(0, 2))

        time_frame = ctk.CTkFrame(settings_frame, fg_color='transparent')
        time_frame.pack(anchor='w', padx=12, pady=(0, 8))

        hours = [str(h) for h in range(24)]
        ctk.CTkLabel(time_frame, text='From').pack(side='left', padx=(0, 6))
        self.start_hour_menu = ctk.CTkOptionMenu(
            time_frame, values=hours, variable=self.start_hour_var, width=72,
        )
        self.start_hour_menu.pack(side='left')
        ctk.CTkLabel(time_frame, text=': 00     To').pack(side='left', padx=8)
        self.end_hour_menu = ctk.CTkOptionMenu(
            time_frame, values=hours, variable=self.end_hour_var, width=72,
        )
        self.end_hour_menu.pack(side='left')
        ctk.CTkLabel(time_frame, text=': 00').pack(side='left', padx=6)

        # Skip time filter toggle
        self.skip_switch = ctk.CTkSwitch(
            settings_frame,
            text='Skip time filter',
            variable=self.skip_filter_var,
            command=self._update_time_widgets,
        )
        self.skip_switch.pack(anchor='w', padx=12, pady=(0, 4))

        # Include already-read emails toggle
        self.include_read_switch = ctk.CTkSwitch(
            settings_frame,
            text='Include already-read emails',
            variable=self.include_read_var,
        )
        self.include_read_switch.pack(anchor='w', padx=12, pady=(0, 8))

        # Date filter
        ctk.CTkLabel(
            settings_frame,
            text='Date filter',
            font=ctk.CTkFont(size=12),
        ).pack(anchor='w', padx=12, pady=(0, 4))

        date_frame = ctk.CTkFrame(settings_frame, fg_color='transparent')
        date_frame.pack(fill='x', padx=12, pady=(0, 12))

        self.date_seg = ctk.CTkSegmentedButton(
            date_frame,
            values=['Today', 'Custom'],
            variable=self.date_mode_var,
            command=self._update_date_widgets,
            width=160,
        )
        self.date_seg.pack(side='left', padx=(0, 10))

        self.custom_date_entry = ctk.CTkEntry(
            date_frame,
            textvariable=self.custom_date_var,
            placeholder_text='YYYY-MM-DD',
            width=120,
        )
        self.custom_date_entry.pack(side='left')

        # Output folder
        ctk.CTkLabel(
            settings_frame,
            text='Output folder',
            font=ctk.CTkFont(size=12),
        ).pack(anchor='w', padx=12, pady=(0, 2))

        folder_frame = ctk.CTkFrame(settings_frame, fg_color='transparent')
        folder_frame.pack(fill='x', padx=12, pady=(0, 12))
        self.output_entry = ctk.CTkEntry(folder_frame, textvariable=self.output_var)
        self.output_entry.pack(side='left', fill='x', expand=True, padx=(0, 8))
        ctk.CTkButton(
            folder_frame, text='📁', width=36, command=self.on_browse_folder,
        ).pack(side='right')

        # Run Now button
        self.run_button = ctk.CTkButton(
            self,
            text='▶  Run Now',
            height=44,
            font=ctk.CTkFont(size=15, weight='bold'),
            command=self.on_run_clicked,
        )
        self.run_button.pack(fill='x', padx=20, pady=(0, 12))

        # LOG OUTPUT label
        ctk.CTkLabel(
            self,
            text='LOG OUTPUT',
            font=ctk.CTkFont(size=11, weight='bold'),
            text_color='#888888',
        ).pack(anchor='w', padx=20, pady=(4, 4))

        # Log box — tk.Text for native tag/color support
        log_frame = ctk.CTkFrame(self)
        log_frame.pack(fill='both', expand=True, padx=20, pady=(0, 8))

        self.log_box = tk.Text(
            log_frame,
            bg='#1e1e1e',
            fg='#cccccc',
            font=('Courier New', 11),
            state='disabled',
            relief='flat',
            padx=8,
            pady=8,
            wrap='none',
            cursor='arrow',
        )
        scrollbar = tk.Scrollbar(log_frame, command=self.log_box.yview)
        self.log_box.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        self.log_box.pack(side='left', fill='both', expand=True)

        self.log_box.tag_configure('error', foreground='#ff4444')
        self.log_box.tag_configure('success', foreground='#44ff88')

        # Status bar
        status_frame = ctk.CTkFrame(self, fg_color='transparent')
        status_frame.pack(fill='x', padx=20, pady=(0, 16))

        self.status_label = ctk.CTkLabel(
            status_frame,
            text='Ready',
            font=ctk.CTkFont(size=12),
        )
        self.status_label.pack(side='left')

        ctk.CTkButton(
            status_frame,
            text='Clear log',
            width=80,
            height=28,
            command=self._clear_log,
        ).pack(side='right')

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _setup_log_handler(self):
        handler = LogHandler(self.append_log)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)-5s [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M',
        ))
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)

    def append_log(self, line: str, level: str = 'INFO'):
        self.after(0, self._insert_log, line, level)

    def _insert_log(self, line: str, level: str):
        self.log_box.configure(state='normal')
        if level == 'ERROR':
            tag = 'error'
        elif 'sent:' in line:
            tag = 'success'
        else:
            tag = ''
        self.log_box.insert('end', line + '\n', tag)
        self.log_box.see('end')
        self.log_box.configure(state='disabled')

    def _clear_log(self):
        self.log_box.configure(state='normal')
        self.log_box.delete('1.0', 'end')
        self.log_box.configure(state='disabled')
        self.status_label.configure(text='Ready', text_color='#cccccc')

    # ------------------------------------------------------------------
    # Config persistence
    # ------------------------------------------------------------------

    def load_config(self) -> dict:
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH) as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            'subject_filter': 'DB Email Alert -',
            'start_hour': 5,
            'end_hour': 6,
            'skip_time_filter': True,
            'include_read': False,
            'date_mode': 'Today',
            'custom_date': datetime.now(WIB).strftime('%Y-%m-%d'),
            'output_dir': DEFAULT_OUTPUT,
        }

    def save_config(self):
        config = {
            'subject_filter': self.subject_var.get(),
            'start_hour': int(self.start_hour_var.get()),
            'end_hour': int(self.end_hour_var.get()),
            'skip_time_filter': self.skip_filter_var.get(),
            'include_read': self.include_read_var.get(),
            'date_mode': self.date_mode_var.get(),
            'custom_date': self.custom_date_var.get(),
            'output_dir': self.output_var.get(),
        }
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)

    # ------------------------------------------------------------------
    # UI interactions
    # ------------------------------------------------------------------

    def _update_time_widgets(self):
        state = 'disabled' if self.skip_filter_var.get() else 'normal'
        self.start_hour_menu.configure(state=state)
        self.end_hour_menu.configure(state=state)

    def _update_date_widgets(self, *_):
        state = 'normal' if self.date_mode_var.get() == 'Custom' else 'disabled'
        self.custom_date_entry.configure(state=state)

    def on_browse_folder(self):
        current = self.output_var.get() or str(Path.home())
        folder = filedialog.askdirectory(initialdir=current)
        if folder:
            self.output_var.set(folder)

    def on_run_clicked(self):
        if not self.subject_var.get().strip():
            self.append_log('Subject filter must not be empty.', 'ERROR')
            return
        self.save_config()
        self.run_button.configure(state='disabled', text='⏳  Running...')
        self.status_label.configure(text='● Running...', text_color='#aaaaaa')
        thread = threading.Thread(target=self._run_pipeline, daemon=True)
        thread.start()

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------

    def _run_pipeline(self):
        import imap_fetcher
        import email_renderer

        imap_fetcher.SUBJECT_PREFIX = self.subject_var.get()
        imap_fetcher.FETCH_WINDOW_START_HOUR = int(self.start_hour_var.get())
        imap_fetcher.FETCH_WINDOW_END_HOUR = int(self.end_hour_var.get())
        email_renderer.OUTPUT_DIR = Path(self.output_var.get())

        try:
            sent, failed = asyncio.run(self._async_run())
        except Exception as exc:
            logging.getLogger('gui').error(f'pipeline error: {exc}')
            sent, failed = 0, 1

        self.after(0, self._on_run_complete, sent, failed)

    async def _async_run(self) -> tuple[int, int]:
        import imap_fetcher as imap_mod
        import email_renderer as renderer_mod
        import telegram_sender

        logger = logging.getLogger('gui')

        imap_host = os.getenv('IMAP_HOST', '')
        imap_user = os.getenv('IMAP_USER', '')
        imap_pass = os.getenv('IMAP_PASS', '')
        imap_port = int(os.getenv('IMAP_PORT', '993'))
        imap_mailbox = os.getenv('IMAP_MAILBOX', 'INBOX')
        telegram_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
        recipient_preview = int(os.getenv('RECIPIENT_PREVIEW_COUNT', '3'))

        if not all([imap_host, imap_user, imap_pass]):
            logger.error('IMAP credentials missing from .env')
            return 0, 1
        if not all([telegram_token, telegram_chat_id]):
            logger.error('Telegram credentials missing from .env')
            return 0, 1

        logger.info('starting db_email_bot')

        fetcher = imap_mod.IMAPFetcher(imap_host, imap_user, imap_pass, imap_port, imap_mailbox)
        try:
            fetcher.connect()
        except Exception:
            return 0, 1

        skip = self.skip_filter_var.get()
        include_read = self.include_read_var.get()

        filter_date: date | None = None
        if self.date_mode_var.get() == 'Today':
            filter_date = datetime.now(WIB).date()
        else:
            try:
                filter_date = datetime.strptime(self.custom_date_var.get().strip(), '%Y-%m-%d').date()
            except ValueError:
                logger.error(f'Invalid date format: "{self.custom_date_var.get().strip()}" — use YYYY-MM-DD')
                fetcher.close()
                return 0, 1

        logger.info(f'date filter: {filter_date.strftime("%d-%b-%Y")}')

        try:
            messages = fetcher.fetch_matching(
                skip_time_filter=skip,
                include_read=include_read,
                filter_date=filter_date,
            )
        except Exception as exc:
            logger.error(f'IMAP error: {exc}')
            fetcher.close()
            return 0, 1

        if not messages:
            logger.info('no matching emails found')
            fetcher.close()
            return 0, 0

        logger.info(f'{len(messages)} matching emails found')

        sent_count = 0
        failed_count = 0

        for msg in messages:
            try:
                png_path = await renderer_mod.render(msg, recipient_preview)
            except Exception:
                failed_count += 1
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

            if results and results[0]:
                sent_count += 1
                fetcher.mark_as_read(msg.uid, msg.message_id)
            else:
                failed_count += 1

        fetcher.close()
        logger.info(f'done. {len(messages)} emails processed, {sent_count} sent')
        return sent_count, failed_count

    def _on_run_complete(self, sent: int, failed: int):
        self.run_button.configure(state='normal', text='▶  Run Now')
        color = '#44ff88' if failed == 0 else '#ff4444'
        self.status_label.configure(
            text=f'● {sent} sent   ○ {failed} failed',
            text_color=color,
        )


if __name__ == '__main__':
    App().mainloop()
