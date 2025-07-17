import tkinter as tk
from tkinter import ttk
from datetime import datetime
import threading
import requests
import re

# Import tab classes
from .SerialTab import SerialTab
from .NetworkTab import NetworkTab

# Control characters
ENQ = b'\x05'
ACK = b'\x06'
NAK = b'\x15'
EOT = b'\x04'
STX = b'\x02'
ETX = b'\x03'
CR  = b'\r'
LF  = b'\n'

control_map = {
    0x05: 'ENQ',
    0x06: 'ACK',
    0x15: 'NAK',
    0x04: 'EOT',
    0x02: 'STX',
    0x03: 'ETX',
    0x0D: 'CR',
    0x0A: 'LF',
}

CONTROL_CHAR_TO_BYTE = {
    'ENQ': ENQ,
    'ACK': ACK,
    'NAK': NAK,
    'EOT': EOT,
    'STX': STX,
    'ETX': ETX,
    'CR' : CR,
    'LF' : LF
}

class MiddlewareGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Analyzer Middleware")
        self.root.geometry("900x700")
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(root)
        
        # Create main frame for logs that will be shared
        self.setup_shared_components()
        
        # Create tab instances
        self.serial_tab = SerialTab(self.notebook, self)
        self.network_tab = NetworkTab(self.notebook, self)
        
        # Add tabs to notebook
        self.notebook.add(self.serial_tab.frame, text='Serial Mode')
        self.notebook.add(self.network_tab.frame, text='Network Mode')
        
        self.notebook.pack(expand=1, fill='both', padx=10, pady=10)
        
        # Log initial startup
        self.log_event("Analyzer Middleware started")

    def setup_shared_components(self):
        """Setup components that will be shared between tabs"""
        # These will be used by both tabs for logging
        pass

    def log_event(self, message, msg_type="info"):
        """
        Add a message to the general logs window
        msg_type: 'info', 'sent', 'received', 'timestamp'
        """
        # Safety check: ensure notebook and tabs are initialized
        if not hasattr(self, 'notebook') or not hasattr(self, 'serial_tab'):
            print(f"[INIT LOG] {message}")  # Fallback logging during initialization
            return
            
        try:
            # Get the current active tab and log to its log widget
            current_tab = self.notebook.select()
            current_tab_index = self.notebook.index(current_tab)
            
            timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
            
            if current_tab_index == 0:  # Serial tab
                log_widget = self.serial_tab.log_text
            else:  # Network tab
                log_widget = self.network_tab.log_text
                
            log_widget.insert(tk.END, f"[{timestamp}] ", "timestamp")
            log_widget.insert(tk.END, f"{message}\n", msg_type)
            log_widget.see(tk.END)
        except (AttributeError, tk.TclError):
            # Fallback to console logging if GUI isn't ready
            print(f"[LOG] {message}")

    def log_error(self, error_message, error_type="error"):
        """
        Add an error message to the error logs window
        error_type: 'error', 'warning'
        """
        # Safety check: ensure notebook and tabs are initialized
        if not hasattr(self, 'notebook') or not hasattr(self, 'serial_tab'):
            print(f"[INIT ERROR] {error_message}")  # Fallback logging during initialization
            return
            
        try:
            # Get the current active tab and log to its error widget
            current_tab = self.notebook.select()
            current_tab_index = self.notebook.index(current_tab)
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            if current_tab_index == 0:  # Serial tab
                error_widget = self.serial_tab.error_text
            else:  # Network tab
                error_widget = self.network_tab.error_text
                
            error_widget.insert(tk.END, f"[{timestamp}] ", "timestamp")
            error_widget.insert(tk.END, f"{error_message}\n", error_type)
        except (AttributeError, tk.TclError):
            # Fallback to console logging if GUI isn't ready
            print(f"[ERROR] {error_message}")
        error_widget.see(tk.END)

    def parse_input_with_control_chars(self, input_str: str) -> bytes:
        """
        Converts human-friendly input like "[STX]data[ETX]" into proper ASTM bytes.
        """
        result = bytearray()
    
        # Replace known escape sequences manually
        input_str = input_str.replace('\\r', '\r').replace('\\n', '\n')
        
        # Find all parts like [STX], data, [ETX]
        tokens = re.split(r'(\[[A-Z]+\])', input_str)
    
        for token in tokens:
            match = re.match(r'\[([A-Z]+)\]', token)
            if match:
                ctrl = match.group(1)
                if ctrl in CONTROL_CHAR_TO_BYTE:
                    result.extend(CONTROL_CHAR_TO_BYTE[ctrl])
            else:
                result.extend(token.encode('latin-1'))
        
        return bytes(result)
    
    def pretty_logger(self, bdata: bytes):
        """Format bytes data for pretty logging"""
        output_lines = []
        buffer = []
        in_astm_block = False

        for b in bdata:
            if b in control_map:
                label = control_map[b]

                if label == 'STX':
                    # Start capturing ASTM block
                    in_astm_block = True
                    buffer.append(f"[{label}]")
                elif label == 'ETX':
                    buffer.append(f"[{label}]")
                    in_astm_block = False
                else:
                    # Flush current ASTM block if exists
                    if buffer:
                        output_lines.append(''.join(buffer))
                        buffer = []
                    output_lines.append(f" - [{label}]")
            elif b == 13:  # \r (CR)
                buffer.append("[CR]")
            elif b == 10:  # \n (LF)
                buffer.append("[LF]")
            else:
                try:
                    buffer.append(chr(b))
                except:
                    buffer.append(f"[0x{b:02X}]")  # fallback for unknown byte

        if buffer:
            output_lines.append(''.join(buffer))

        return "\n".join(output_lines)
    
    def buffer_to_lines(self, buffer):
        """Convert buffer to readable lines"""
        try:
            return bytes(buffer).decode('latin-1', errors='ignore').replace('\r', '')
        except Exception:
            return repr(buffer)

    def send_api_request(self, endpoint, payload):
        """
        Common method to send API requests
        Returns tuple (success: bool, response_data: dict or None, error_message: str or None)
        """
        try:
            self.log_event(f"Sending {payload.get('total_messages', 0)} messages to {endpoint}")
            
            # Send POST request
            response = requests.post(
                endpoint,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                self.log_event(f"Successfully sent data to API. Response: {response.status_code}")
                
                try:
                    response_data = response.json()
                    return True, response_data, None
                except:
                    return True, {'status': response.status_code}, None
                    
            else:
                error_msg = f"API request failed with status {response.status_code}: {response.text}"
                self.log_event(error_msg)
                return False, None, f"Failed to send data. Status: {response.status_code}"
                
        except requests.exceptions.Timeout:
            error_msg = "API request timed out"
            self.log_event(error_msg)
            return False, None, "Request timed out. Please check the endpoint URL and try again."
        except requests.exceptions.ConnectionError:
            error_msg = "Failed to connect to API endpoint"
            self.log_event(error_msg)
            return False, None, "Failed to connect to API endpoint. Please check the URL and network connection."
        except Exception as e:
            error_msg = f"Error sending data to API: {str(e)}"
            self.log_event(error_msg)
            return False, None, f"Failed to send data to API: {str(e)}"

    def disconnect(self):
        """Handle application closing"""
        self.serial_tab.disconnect()
        # self.network_tab.disconnect()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MiddlewareGUI(root)
    
    root.protocol("WM_DELETE_WINDOW", app.disconnect)
    
    root.mainloop()