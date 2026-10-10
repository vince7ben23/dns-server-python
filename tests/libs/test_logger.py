import logging
import unittest

from app.libs.logger import LOGGER_NAME, Logger, logger


class TestLogger(unittest.TestCase):
    def test_is_singleton(self):
        self.assertIs(Logger(), Logger())
        self.assertIs(Logger(), logger)

    def test_configured_logging_logger(self):
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, LOGGER_NAME)
        self.assertEqual(logger.level, logging.DEBUG)
        self.assertFalse(logger.propagate)

    def test_handler_added_only_once(self):
        Logger()
        Logger()
        self.assertEqual(len(logger.handlers), 1)


if __name__ == "__main__":
    unittest.main()
