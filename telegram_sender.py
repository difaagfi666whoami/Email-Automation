import logging
from pathlib import Path

from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger('telegram_sender')


async def send_photos(
    bot_token: str,
    chat_id: str,
    items: list[tuple[str, str, str, str]],
) -> list[bool]:
    results: list[bool] = []

    async with Bot(token=bot_token) as bot:
        for png_path, subject, received_time, sender_name in items:
            filename = Path(png_path).name
            caption = f'📧 {subject}\n🕐 {received_time} WIB\n📬 {sender_name}'

            logger.info(f'sending: {filename}')
            try:
                with open(png_path, 'rb') as photo:
                    await bot.send_photo(chat_id=chat_id, photo=photo, caption=caption)
                logger.info(f'sent: {filename}')
                results.append(True)
            except TelegramError as exc:
                logger.error(f'telegram error for {filename}: {exc}')
                results.append(False)
            except OSError as exc:
                logger.error(f'telegram error for {filename}: {exc}')
                results.append(False)

    return results
