#!/usr/bin/env python3
"""Run market agents locally with optional dry-run mode."""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    parser = argparse.ArgumentParser(description="Run market agents locally")
    parser.add_argument(
        "--agent",
        choices=["stock", "crypto"],
        required=True,
        help="Which agent to run",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print message to console instead of sending to Telegram",
    )
    args = parser.parse_args()

    if args.agent == "stock":
        from src.agents.stock_agent import run

        asyncio.run(run(dry_run=args.dry_run))
    else:
        from src.agents.crypto_agent import run

        asyncio.run(run(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
