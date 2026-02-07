"""Allow running agents via python -m src.agents."""

import sys

if __name__ == "__main__":
    print("Use: python -m src.agents.stock_agent or python -m src.agents.crypto_agent")
    sys.exit(1)
