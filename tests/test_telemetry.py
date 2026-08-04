import json
import logging

from flowsense.telemetry import JsonFormatter, setup_logging


def test_json_formatter_serializes_extra_fields():
    record = logging.LogRecord("flowsense", logging.INFO, "file.py", 1, "reconnecting", None, None)
    record.camera_id = 30
    record.attempt = 2
    data = json.loads(JsonFormatter().format(record))
    assert data["msg"] == "reconnecting"
    assert data["camera_id"] == 30
    assert data["attempt"] == 2
    assert data["level"] == "INFO"


def test_setup_logging_returns_flowsense_logger():
    logger = setup_logging("DEBUG", json_output=True)
    assert logger.name == "flowsense"
    assert logger.level == logging.DEBUG
    assert len(logger.handlers) == 1


def test_setup_logging_is_idempotent():
    setup_logging()
    logger = setup_logging()
    assert len(logger.handlers) == 1
