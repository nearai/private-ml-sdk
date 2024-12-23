import logging
from logging.config import dictConfig

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(levelname)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s",
        },
        "uvicorn": {
            "format": "%(asctime)s - %(levelname)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
        "uvicorn_console": {
            "class": "logging.StreamHandler",
            "formatter": "uvicorn",
        },
    },
    "loggers": {
        "uvicorn": {
            "handlers": ["uvicorn_console"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn.error": {
            "handlers": ["uvicorn_console"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn.access": {
            "handlers": ["uvicorn_console"],
            "level": "INFO",
            "propagate": False,
        },
        "app": {  # Custom logger for your application
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# Apply the logging configuration
dictConfig(LOGGING_CONFIG)

log = logging.getLogger("app")
