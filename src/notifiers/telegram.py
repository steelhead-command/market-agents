import asyncio
import html

from telegram import Bot
from telegram.constants import ParseMode

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

MAX_MESSAGE_LENGTH = 4096
SECTION_SEPARATOR = "\n\n"


class TelegramNotifier:
    """Send HTML-formatted messages to Telegram with auto-splitting and fallback."""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot = Bot(token=bot_token)
        self.chat_id = chat_id

    async def send_message(self, html_text: str) -> bool:
        """Send an HTML message, auto-splitting on section boundaries if needed.

        Returns True if all parts sent successfully.
        """
        if len(html_text) <= MAX_MESSAGE_LENGTH:
            return await self._send_single(html_text)

        # Split on section boundaries
        parts = self._split_message(html_text)
        all_ok = True
        for i, part in enumerate(parts):
            logger.info("Sending message part %d/%d (%d chars)", i + 1, len(parts), len(part))
            ok = await self._send_single(part)
            if not ok:
                all_ok = False
        return all_ok

    async def _send_single(self, html_text: str) -> bool:
        """Send a single message with HTML parse mode, falling back to plain text."""
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=html_text,
                parse_mode=ParseMode.HTML,
            )
            return True
        except Exception as e:
            logger.error("HTML send failed: %s. Trying plain text fallback.", e)
            return await self._send_plain_text(html_text)

    async def _send_plain_text(self, html_text: str) -> bool:
        """Fallback: strip HTML tags and send as plain text."""
        try:
            # Simple tag stripping
            import re

            plain = re.sub(r"<[^>]+>", "", html_text)
            await self.bot.send_message(chat_id=self.chat_id, text=plain)
            return True
        except Exception as e:
            logger.error("Plain text send also failed: %s", e)
            return False

    async def send_error(self, message: str) -> bool:
        """Send an error notification."""
        error_html = f"<b>Market Agent Error</b>\n\n<code>{escape_html(message)}</code>"
        return await self.send_message(error_html)

    @staticmethod
    def _split_message(text: str) -> list[str]:
        """Split a message at section boundaries to stay under Telegram's limit."""
        sections = text.split(SECTION_SEPARATOR)
        parts: list[str] = []
        current = ""

        for section in sections:
            candidate = current + SECTION_SEPARATOR + section if current else section
            if len(candidate) <= MAX_MESSAGE_LENGTH:
                current = candidate
            else:
                if current:
                    parts.append(current)
                # If a single section exceeds the limit, force-split it
                if len(section) > MAX_MESSAGE_LENGTH:
                    for i in range(0, len(section), MAX_MESSAGE_LENGTH):
                        parts.append(section[i : i + MAX_MESSAGE_LENGTH])
                    current = ""
                else:
                    current = section

        if current:
            parts.append(current)

        return parts


def escape_html(text: str) -> str:
    """Escape HTML special characters. Only <, >, & need escaping for Telegram HTML."""
    return html.escape(text, quote=False)


def send_sync(bot_token: str, chat_id: str, html_text: str) -> bool:
    """Synchronous wrapper for sending a message."""
    notifier = TelegramNotifier(bot_token, chat_id)
    return asyncio.run(notifier.send_message(html_text))
