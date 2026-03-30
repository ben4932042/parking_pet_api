from typing import Any, Dict, List

from pythonjsonlogger import json


class NestedJsonFormatter(json.JsonFormatter):
    """
    Nested JSON formatter for logging.
    """

    CORE_FIELDS = {"asctime", "levelname", "name", "message"}
    DETAIL_FIELDS = {"pathname", "lineno", "exc_info", "stack_info"}

    def process_log_record(self, log_record: Dict[str, Any]) -> Dict[str, Any]:
        nested = {
            "timestamp": log_record.pop("asctime", None),
            "level": log_record.pop("levelname", None),
            "logger": log_record.pop("name", None),
            "message": log_record.pop("message", None),
            "detail": {},
        }

        for field in self.DETAIL_FIELDS:
            if field in log_record:
                nested["detail"][field] = log_record.pop(field)

        if log_record:
            nested["detail"].update(log_record)

        return nested


def get_silent_logger_config(handlers: List[str]) -> Dict[str, Any]:
    return {
        "handlers": handlers,
        "level": "ERROR",
        "propagate": False,
    }


LOGGING_CONFIG: Dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        # JSON formatter for non-local environments
        "json": {
            "()": NestedJsonFormatter,
            "format": "%(asctime) %(name) %(pathname)s %(lineno)d %(levelname)s %(message)s",
            "json_ensure_ascii": False,
        },
    },
    "handlers": {
        "default": {
            "formatter": "json",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        # default log setting
        "": {
            "handlers": ["default"],
            "level": "DEBUG",
            "propagate": True,
        },
        # specific log setting
        **{
            name: get_silent_logger_config(["default"])
            for name in [
                "uvicorn",
                "uvicorn.error",
                "uvicorn.access",
                "pymongo",
                "asyncio",
                "urllib3.connectionpool",
                "httpcore.http11",
                "httpcore.connection",
            ]
        },
    },
}
