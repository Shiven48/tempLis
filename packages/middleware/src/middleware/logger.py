from typing import Callable, Optional

class GuiLoggerRegistry:
    def __init__(self):
        self.gui_loggers = {}

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

# 
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
