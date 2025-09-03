from typing import Callable, Optional
import logging
import os
from logging.config import dictConfig

class GuiLoggerRegistry:
    def __init__(self):
        self.gui_loggers = {}
        self.is_registered = False

    def _get_gui_log_callback(self) -> Callable:
        return self.gui_loggers["gui_log_callback"]

    def _get_gui_error_callback(self) -> Callable:
        return self.gui_loggers["gui_error_callback"]

    def _get_gui_network_callback(self) -> Callable:
        return self.gui_loggers["gui_network_callback"]

    def _get_gui_serial_callback(self) -> Callable:
        return self.gui_loggers["gui_serial_callback"]

    def _set_logger(self, logger_name:str, logger_callback: Callable):
        self.gui_loggers[logger_name] = logger_callback

GuiLoggerRegistryInstance = GuiLoggerRegistry()

def register_loggers(
            gui_log: Optional[Callable] = None, 
            error_log:Optional[Callable] = None,
            network_log:Optional[Callable] = None,
            serial_log:Optional[Callable] = None
        ):
        GuiLoggerRegistryInstance._set_logger("gui_log_callback", gui_log)
        GuiLoggerRegistryInstance._set_logger("gui_error_callback", error_log)
        GuiLoggerRegistryInstance._set_logger("gui_network_callback", network_log)
        GuiLoggerRegistryInstance._set_logger("gui_serial_callback", serial_log)


os.makedirs("packages/logs", exist_ok=True)

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "detailed": {
            "format": "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler", 
            "level": "DEBUG",
            "formatter": "detailed",
        },
        "file": {
            "class": "logging.FileHandler",
            "level": "INFO", 
            "formatter": "detailed",
            "filename": "packages/logs/lab_api.log",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "DEBUG"
    },
}

dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)