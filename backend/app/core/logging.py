import json
import logging
import sys
from typing import Any

from app.core.privacy import redact_mapping


LOGGER_NAME = "careeragent"


def configure_logging() -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    logger.handlers = [
        handler
        for handler in logger.handlers
        if not getattr(getattr(handler, "stream", None), "closed", False)
    ]
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def log_event(event: str, **payload: Any) -> None:
    logger = configure_logging()
    logger.info(
        json.dumps(
            {"event": event, **redact_mapping(payload)},
            default=str,
            sort_keys=True,
        )
    )
