from graphics.Logs.base import LoggerBase
from middleware import logger as log


class LoggingManager:
    """
    Manages all loggers for the application.
    This class acts as a central dispatcher for all log messages.
    """
    def __init__(self):
        self.loggers = {}

    def register(self, name: str, logger: LoggerBase):
        """Registers a new logger under a unique name."""
        self.loggers[name] = logger
        log.info(f"Logger registered: '{name}'")

    def _dispatch(self, name: str, message: str, tag: str):
        """Sends a message to a specific named logger."""
        if name in self.loggers:
            self.loggers[name].log(message, tag)
        else:
            log.info(f"[Warning] Logger '{name}' not found for message: {message}")

    def info(self, message: str):
        self._dispatch('global_info', message, 'info')

    def error(self, message: str):
        self._dispatch('global_error', message, 'error')

    def network_data(self, message: str, tag: str = 'data_in'):
        self._dispatch('network_data', message, tag)

    def serial_data(self, message: str, tag: str = 'data_in'):
        self._dispatch('serial_data', message, tag)

    def clear_all(self):
        """Clears all registered loggers."""
        for logger in self.loggers.values():
            logger.clear()