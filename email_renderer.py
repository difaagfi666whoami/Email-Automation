import logging
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright

from imap_fetcher import EmailMessage

logger = logging.getLogger('email_renderer')

TEMPLATE_DIR = Path(__file__).parent / 'templates'
OUTPUT_DIR = Path('/Users/difaagfi/Pictures/Email Automation')


async def render(msg: EmailMessage, recipient_preview_count: int = 3) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=False)
    template = env.get_template('email_view.html')

    received_str = msg.received_time.strftime('%Y-%m-%d %H:%M:%S')

    html_content = template.render(
        sender_name=msg.sender_name,
        sender_email=msg.sender_email,
        recipients=msg.recipients,
        reply_to=msg.reply_to,
        subject=msg.subject,
        body_html=msg.body_html,
        body_text=msg.body_text,
        received_time=received_str,
        recipient_preview_count=recipient_preview_count,
    )

    timestamp = msg.received_time.strftime('%Y%m%d_%H%M%S')
    slug = re.sub(r'[^a-z0-9]', '_', msg.subject.lower())
    slug = re.sub(r'_+', '_', slug).strip('_')[:40]
    filename = f'email_{timestamp}_{slug}.png'
    output_path = str(OUTPUT_DIR / filename)

    logger.info(f'rendering: {msg.subject}')

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={'width': 1080, 'height': 500})
            await page.set_content(html_content, wait_until='networkidle')
            await page.screenshot(path=output_path, full_page=True)
            await browser.close()
    except Exception as exc:
        logger.error(f'render error for {msg.subject}: {exc}')
        raise

    logger.info(f'rendered: {filename}')
    return output_path
