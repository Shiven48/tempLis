import tkinter as tk
from tkinter import scrolledtext
from datetime import datetime
from graphics.Logs.base import LoggerBase

class LogWidget(scrolledtext.ScrolledText):
    """A standardized, themed scrolled text widget for logging."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, wrap=tk.WORD, font=("Consolas", 9), state='normal', **kwargs)
        self.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Configure standard color tags
        self.tag_config("timestamp", foreground="#888888")
        self.tag_config("info", foreground="black")
        self.tag_config("error", foreground="red")
        self.tag_config("data_in", foreground="blue") # For data received
        self.tag_config("data_out", foreground="green") # For data sent

class TextWidgetLogger(LoggerBase):
    """A concrete logger that writes to a specific Tkinter Text/LogWidget."""
    def __init__(self, text_widget: LogWidget):
        self.widget = text_widget

    def log(self, message: str, tag: str = "info"):
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        try:
            self.widget.insert(tk.END, f"{timestamp} ", "timestamp")
            self.widget.insert(tk.END, f"{message}\n", tag)
            self.widget.see(tk.END)
        except tk.TclError:
            print(f"[{tag.upper()}] {timestamp} {message}") # Fallback if UI is gone

    def clear(self):
        try:
            self.widget.delete(1.0, tk.END)
        except tk.TclError:
            pass

