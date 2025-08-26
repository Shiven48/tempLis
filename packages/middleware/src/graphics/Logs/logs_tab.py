from tkinter import ttk
from graphics.Logs.logs_widget import LogWidget, TextWidgetLogger


class InfoLogTab:
    def __init__(self, parent_notebook, main_app):
        self.frame = ttk.Frame(parent_notebook)
        
        log_widget = LogWidget(self.frame)
        
        logger = TextWidgetLogger(log_widget)
        main_app.logging_manager.register('global_info', logger)

class ErrorLogTab:
    def __init__(self, parent_notebook, main_app):
        self.frame = ttk.Frame(parent_notebook)
        
        log_widget = LogWidget(self.frame)
        
        logger = TextWidgetLogger(log_widget)
        main_app.logging_manager.register('global_error', logger)
