# Market Agents

Daily market briefings delivered to Telegram via GitHub Actions.

- **Stock Market Agent** — Watchlist technicals + broad market overview (Mon-Fri)
- **Crypto Market Agent** — Portfolio tracking + market overview (daily)

## Setup

### 1. Create a Telegram Bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow the prompts
3. Copy the bot token

### 2. Get Your Chat ID

1. Send any message to your new bot
2. Visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
3. Find `"chat":{"id":YOUR_CHAT_ID}` in the response

### 3. Configure GitHub Secrets

In your repo Settings > Secrets and variables > Actions, add:

| Secret | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Your bot token from BotFather |
| `TELEGRAM_CHAT_ID` | Your chat ID |

### 4. Customize Your Watchlist

Copy the example config and edit:

```bash
cp config/config.example.yaml config/config.yaml
```

Edit `config/config.yaml` with your tickers and coins. This file is gitignored.

For GitHub Actions, the example config is used by default. To customize, either:
- Edit `config/config.example.yaml` directly (committed to repo), or
- Add config content as a GitHub Secret and write it in the workflow

## Local Testing

### Install dependencies

```bash
pip install -r requirements.txt
pip install pytest pytest-mock pytest-asyncio
```

### Dry run (no Telegram needed)

```bash
python scripts/run_local.py --agent stock --dry-run
python scripts/run_local.py --agent crypto --dry-run
```

### Live run (sends to Telegram)

```bash
export TELEGRAM_BOT_TOKEN="your-token"
export TELEGRAM_CHAT_ID="your-chat-id"
python scripts/run_local.py --agent stock
python scripts/run_local.py --agent crypto
```

### Test Telegram connection

```bash
python scripts/test_telegram.py
```

### Run tests

```bash
pytest tests/ -v
```

## Schedule

Both agents run **twice daily** Mon-Fri via GitHub Actions cron — once before the US market opens and once after it closes:

| Agent | Run | UTC | PST (winter) | PDT (summer) |
|---|---|---|---|---|
| Stock | Pre-market | 14:23 | 6:23 AM | 7:23 AM |
| Stock | After close | 21:23 | 1:23 PM | 2:23 PM |
| Crypto | Pre-market | 14:23 | 6:23 AM | 7:23 AM |
| Crypto | After close | 21:23 | 1:23 PM | 2:23 PM |

The off-peak minute (`:23`) avoids GitHub's top-of-hour cron congestion.

You can also trigger manually from the Actions tab using "Run workflow".

### DST Note

The cron runs at fixed UTC times. During Pacific Standard Time (Nov-Mar), the morning run arrives ~6:23 AM and the after-close run at ~1:23 PM. During Pacific Daylight Time (Mar-Nov), they shift to ~7:23 AM and ~2:23 PM.

### Dormancy Warning

GitHub silently disables cron schedules on repos with no activity for 60 days. To prevent this:
- Push a keep-alive commit periodically, or
- Enable GitHub's "keep workflows enabled" setting if available

## Message Format

Each briefing includes:

**Stock Agent:**
- Your watchlist with price, RSI, MACD, SMA, volume analysis, and signal summary
- Market overview (S&P 500, NASDAQ, Dow, Russell 2000)
- Sector performance
- Top movers (gainers/losers)

**Crypto Agent:**
- Your portfolio with price, technicals, and signal summary
- Market overview (total cap, BTC dominance)
- Fear & Greed Index
- Trending coins
- Top 10 by market cap

## Tech Stack

| Component | Choice |
|---|---|
| Stock data | yfinance (free, no API key) |
| Crypto data | CoinGecko API (free tier) |
| Fear & Greed | alternative.me API |
| Technical analysis | Manual pandas implementations |
| Notifications | python-telegram-bot (HTML mode) |
| Scheduling | GitHub Actions cron |
| Config | YAML + environment variables |
| Validation | Pydantic models |

## Project Structure

```
src/
  agents/          # Agent orchestration (stock_agent.py, crypto_agent.py)
  data_sources/    # API clients (yahoo_finance, coingecko, fear_greed)
  analyzers/       # Technical indicators (RSI, MACD, SMA, EMA, volume)
  models/          # Pydantic data models
  notifiers/       # Telegram sender with HTML mode + fallback
  formatters/      # Message builders (HTML formatting)
  utils/           # Config loader, JSON logger
```
