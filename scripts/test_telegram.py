#!/usr/bin/env python3
"""Send a test message to Telegram to verify bot setup."""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.notifiers.telegram import TelegramNotifier


async def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables")
        sys.exit(1)

    notifier = TelegramNotifier(token, chat_id)
    ok = await notifier.send_message(
        "<b>Market Agents Test</b>\n\n"
        "If you see this, your Telegram bot is configured correctly.\n\n"
        "<i>Sent from scripts/test_telegram.py</i>"
    )

    if ok:
        print("Test message sent successfully!")
    else:
        print("Failed to send test message")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
