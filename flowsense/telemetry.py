"""Structured JSON logging for FlowSense."""
import json
import logging
import sys


class JsonFormatter(logging.Formatter):
    EXTRA_FIELDS = ("camera_id", "camera", "lane", "event", "frame", "url", "attempt")

    def format(self, record):
        payload = {
            "ts": round(record.created, 3),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key in self.EXTRA_FIELDS:
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, separators=(",", ":"))


def setup_logging(level: str = "INFO", json_output: bool = True) -> logging.Logger:
    logger = logging.getLogger("flowsense")
    logger.setLevel(level.upper())
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter() if json_output else logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    return logger
