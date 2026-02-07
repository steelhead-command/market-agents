from datetime import datetime, timezone

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.models.crypto import FearGreedIndex
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

FEAR_GREED_URL = "https://api.alternative.me/fng/"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout)),
    reraise=True,
)
def get_index() -> FearGreedIndex | None:
    """Fetch the current Fear & Greed Index from alternative.me."""
    try:
        resp = requests.get(FEAR_GREED_URL, params={"limit": 1}, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        items = data.get("data", [])
        if not items:
            logger.warning("No Fear & Greed data returned")
            return None

        item = items[0]
        value = int(item["value"])
        label = item["value_classification"]
        ts = int(item.get("timestamp", 0))

        return FearGreedIndex(
            value=value,
            label=label,
            timestamp=datetime.fromtimestamp(ts, tz=timezone.utc) if ts else None,
        )
    except Exception as e:
        logger.error("Failed to fetch Fear & Greed Index: %s", e)
        return None
