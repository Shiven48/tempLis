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

default_config = None

def get_default_config():
    """Lazy load default configuration"""
    global default_config
    if default_config is None:
        try:
            from .config_loader import ConfigLoader  # Import only when needed
            default_config = ConfigLoader.load_analyzer_config(DEFAULT_CONFIG_PATH)
        except FileNotFoundError:
            logger.warning(f"Default config file not found: {DEFAULT_CONFIG_PATH}")
            default_config = {}
        except Exception as e:
            logger.error(f"Failed to load default config: {e}")
            default_config = {}
    return default_config

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
