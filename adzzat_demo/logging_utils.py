from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

LOGGER = logging.getLogger("adzzat_demo")
if not LOGGER.handlers:
    logging.basicConfig(level=logging.INFO)


def log_event(event: str, request_id: str, **data: Any) -> None:
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "request_id": request_id,
        **data,
    }
    LOGGER.info(json.dumps(payload, ensure_ascii=False))
