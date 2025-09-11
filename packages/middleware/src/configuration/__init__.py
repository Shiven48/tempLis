from pathlib import Path
from .config_loader import ConfigLoader
from .logger import (
    GuiLoggerRegistryInstance, 
    register_loggers, 
    configure_logging,
    logger
)

CONFIG_DIR = Path(__file__).parent
DEFAULT_CONFIG_PATH = CONFIG_DIR / "erba.yaml"

try:
    default_config = ConfigLoader.load_analyzer_config(DEFAULT_CONFIG_PATH)
except FileNotFoundError:
    default_config = {}

__all__ = [
    # configuration utilities
    "ConfigLoader",
    "default_config",
    "CONFIG_DIR",
    "DEFAULT_CONFIG_PATH",

    # logger utilities
    "GuiLoggerRegistryInstance", 
    "register_loggers", 
    "configure_logging",
    "logger"
]
