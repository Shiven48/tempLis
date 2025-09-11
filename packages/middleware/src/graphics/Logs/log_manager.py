from typing import Dict, Optional
from graphics.logs.base import LoggerBase
from graphics.logs.logs_widget import TextWidgetLogger
from configuration.logger import logger as log


class LoggingManager:
    """
    Manages all loggers for the application.
    This class acts as a central dispatcher for all log messages.
    """
    def __init__(self):
        self.loggers:Dict[str, TextWidgetLogger] = {}

    def register(self, name: str, logger: LoggerBase):
        """Registers a new logger under a unique name."""
        self.loggers[name] = logger
        log.info(f"Logger registered: '{name}'")

    def _dispatch(self, name: str, message: str, tag: str, machine_role: Optional[str]):
        """Sends a message to a specific named logger."""
        if name in self.loggers:
            if not machine_role:
                machine_role = ""
            self.loggers[name].log(message, tag, machine_role)
        else:
            log.info(f"[Warning] Logger '{name}' not found for message: {message}")

    def info(self, message: str, machine_role:str):
        self._dispatch('global_info', message, 'info', machine_role)

    def error(self, message: str, machine_role:str):
        self._dispatch('global_error', message, 'error', machine_role)

    def network_data(self, message: str, tag: str = 'data_in', machine_role=None):
        self._dispatch('network_data', message, tag, machine_role)

    def serial_data(self, message: str, tag: str = 'data_in', machine_role=None):
        self._dispatch('serial_data', message, tag, machine_role)

    def middleware_ack_data(self, message: str, tag: str = 'data_in', machine_role=None):
        self._dispatch('middleware_ack_data', message, tag, machine_role)

    def middleware_nack_data(self, message: str, tag: str = 'data_in', machine_role=None):
        self._dispatch('middleware_nack_data', message, tag, machine_role)

    def clear_all(self):
        """Clears all registered loggers."""
        for logger in self.loggers.values():
            logger.clear()