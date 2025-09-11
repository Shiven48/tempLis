from typing import Callable, Optional
import logging
from logging.config import dictConfig
from pathlib import Path

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
    
    def _get_gui_middleware_ack_callback(self) -> Callable:
         return self.gui_loggers["gui_middleware_ack_callback"]

    def _get_gui_middleware_nack_callback(self) -> Callable:
         return self.gui_loggers["gui_middleware_nack_callback"]

    def _set_logger(self, logger_name: str, logger_callback: Callable):
        self.gui_loggers[logger_name] = logger_callback

GuiLoggerRegistryInstance = GuiLoggerRegistry()

def register_loggers(
            gui_log: Optional[Callable] = None, 
            error_log: Optional[Callable] = None,
            network_log: Optional[Callable] = None,
            serial_log: Optional[Callable] = None,
            middleware_ack_log: Optional[Callable] = None,
            middleware_nack_log: Optional[Callable] = None
        ):
        GuiLoggerRegistryInstance._set_logger("gui_log_callback", gui_log)
        GuiLoggerRegistryInstance._set_logger("gui_error_callback", error_log)
        GuiLoggerRegistryInstance._set_logger("gui_network_callback", network_log)
        GuiLoggerRegistryInstance._set_logger("gui_serial_callback", serial_log)
        GuiLoggerRegistryInstance._set_logger("gui_middleware_ack_callback", middleware_ack_log)
        GuiLoggerRegistryInstance._set_logger("gui_middleware_nack_callback", middleware_nack_log)

def get_project_root() -> Path:
    """Find project root by looking for packages directory"""
    current_path = Path(__file__).parent
    while current_path.parent != current_path:
        if (current_path / "packages").exists():
            return current_path
        current_path = current_path.parent
    raise RuntimeError("Could not find project root (packages directory)")

# Making a Logs directory
PROJECT_ROOT = get_project_root()
LOGS_DIR = PROJECT_ROOT / "packages" / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

def configure_logging(module_name: str = "middleware"):
    """Configure logging with module-specific files"""
    
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
                "filename": str(LOGS_DIR / f"{module_name}_logs.log"),
            },
        },
        "root": {
            "handlers": ["console", "file"],
            "level": "DEBUG"
        },
    }
    
    dictConfig(LOGGING_CONFIG)
    return logging.getLogger(__name__)

# Default logger for middleware
logger = configure_logging("middleware")
