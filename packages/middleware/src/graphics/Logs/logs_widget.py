import tkinter as tk
from tkinter import scrolledtext
from datetime import datetime
from graphics.logs.base import LoggerBase

class LogWidget(scrolledtext.ScrolledText):
    """A standardized, themed scrolled text widget for logging."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, wrap=tk.WORD, font=("Consolas", 9), state='normal', **kwargs)
        self.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Configure standard color tags
        self.tag_config("timestamp", foreground="#9e9e9e")
        self.tag_config("machine_role", foreground="#9e9e9e")
        self.tag_config("info", foreground="black")
        self.tag_config("error", foreground="#e71818")
        self.tag_config("data_in", foreground="#0d47a1")  
        self.tag_config("data_out", foreground="#1b5e20")  


class TextWidgetLogger(LoggerBase):
    """A concrete logger that writes to a specific Tkinter Text/LogWidget."""
    def __init__(self, text_widget: LogWidget):
        self.widget = text_widget

    def log(self, message: str, tag: str = "info", machine_role:str = "LIS"):
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        machine_role = f"[{machine_role}]" if machine_role else ""
        try:
            self.widget.insert(tk.END, f"{timestamp} ", "timestamp")
            self.widget.insert(tk.END, f"{machine_role} ", "machine_role")
            self.widget.insert(tk.END, f"{message}\n", tag)
            self.widget.see(tk.END)
        except tk.TclError:
            print(f"[{tag.upper()}] {timestamp} {message}")

    def clear(self):
        try:
            self.widget.delete(1.0, tk.END)
        except tk.TclError:
            pass

