import logging
import sys

LOGGER_NAME = "dns_server"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


class Logger:
    """Process-wide singleton wrapper around a configured `logging.Logger`."""

    _instance: logging.Logger | None = None

    def __new__(cls) -> logging.Logger:
        if cls._instance is None:
            logger = logging.getLogger(LOGGER_NAME)
            logger.setLevel(logging.DEBUG)

            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(logging.Formatter(LOG_FORMAT))
            logger.addHandler(handler)
            logger.propagate = False

            cls._instance = logger
        return cls._instance


logger = Logger()
