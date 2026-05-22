"""
Structured logging configuration using standard Python logging module.
"""

import logging
import os
import sys

def setup_logging() -> None:
    """Configure standard logging with JSON formatting (prod) or console (dev)."""
    env = os.environ.get("APP_ENV", "development")
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()

    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    # Remove all existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        
    handler = logging.StreamHandler(sys.stdout)
    
    if env == "production":
        # Use a simple JSON formatter for production
        try:
            import json
            class JsonFormatter(logging.Formatter):
                def format(self, record):
                    log_record = {
                        "time": self.formatTime(record, self.datefmt),
                        "level": record.levelname,
                        "name": record.name,
                        "message": record.getMessage()
                    }
                    if record.exc_info:
                        log_record["exc_info"] = self.formatException(record.exc_info)
                    return json.dumps(log_record)
            
            formatter = JsonFormatter()
        except ImportError:
            formatter = logging.Formatter('{"time": "%(asctime)s", "level": "%(levelname)s", "name": "%(name)s", "message": "%(message)s"}')
    else:
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Silence noisy third-party loggers
    for name in ("uvicorn.access", "httpx", "httpcore", "mlflow"):
        logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a standard logger for the given module name."""
    return logging.getLogger(name)
