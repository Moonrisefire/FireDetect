import logging
import json
import sys
import traceback
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """
    Кастомный форматер, который переводит все логи в структурированный JSON.
    """

    def format(self, record):
        log_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger_name": record.name,
            "module": record.module,
            "function": record.funcName,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_record["exception_type"] = record.exc_info[0].__name__
            log_record["exception_message"] = str(record.exc_info[1])
            log_record["traceback"] = "".join(traceback.format_exception(*record.exc_info))

        if hasattr(record, "extra_data"):
            log_record["extra_context"] = record.extra_data

        return json.dumps(log_record, ensure_ascii=False)


def get_logger(name: str = "module", level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(level)

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)

        logger.propagate = False

    return logger