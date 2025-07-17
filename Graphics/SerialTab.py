import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime
import threading
import serial
import socket
import time
import json
import os

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

class SerialTab:
    def __init__(self, parent, main_app):
        self.parent = parent
        self.main_app = main_app
        self.frame = ttk.Frame(parent)
        
        # Connection status variables
        self.serial_connected = False
        self.serial_connection = None
        self.socket_connected = False
        self.socket_connection = None
        
        # Data buffer
        self.data_buffer = []
        self.reading = False
        
        # Socket configuration
        self.net_host = 'localhost'
        self.net_port = 15200
        
        # Setup UI
        self.setup_ui()
        
    def load_machine_options(self):
        """Load machine options from AnalyzerConfig.json with error handling and fallback"""
        # Default machine list as fallback
        default_machines = ["BS240", "Abbott", "Snibe", "ErbaElite580"]
        
        try:
            # Construct path to configuration file
            config_path = os.path.join("Configuration", "AnalyzerConfig.json")
            
            # Check if file exists
            if not os.path.exists(config_path):
                if hasattr(self, 'main_app') and self.main_app:
                    self.main_app.log_event(f"[Config] Configuration file not found at {config_path}, using default machines")
                return default_machines
            
            # Read and parse JSON file
            with open(config_path, 'r', encoding='utf-8') as file:
                config_data = json.load(file)
            
            # Extract machine names from configuration
            if isinstance(config_data, dict):
                machine_names = list(config_data.keys())
                if machine_names:
                    if hasattr(self, 'main_app') and self.main_app:
                        self.main_app.log_event(f"[Config] Loaded {len(machine_names)} machines from configuration")
                    return machine_names
                else:
                    if hasattr(self, 'main_app') and self.main_app:
                        self.main_app.log_event("[Config] Configuration file is empty, using default machines")
                    return default_machines
            else:
                if hasattr(self, 'main_app') and self.main_app:
                    self.main_app.log_event("[Config] Invalid configuration format, using default machines")
                return default_machines
                
        except json.JSONDecodeError as e:
            if hasattr(self, 'main_app') and self.main_app:
                self.main_app.log_error(f"[Config Error] Invalid JSON in configuration file: {e}")
            return default_machines
        except FileNotFoundError:
            if hasattr(self, 'main_app') and self.main_app:
                self.main_app.log_event("[Config] Configuration file not found, using default machines")
            return default_machines
        except PermissionError:
            if hasattr(self, 'main_app') and self.main_app:
                self.main_app.log_error("[Config Error] Permission denied reading configuration file")
            return default_machines
        except Exception as e:
            if hasattr(self, 'main_app') and self.main_app:
                self.main_app.log_error(f"[Config Error] Unexpected error loading configuration: {e}")
            return default_machines
    
    def on_machine_change(self, selected_machine):
        """Handle machine selection changes with logging and future configuration integration"""
        try:
            # Log the machine selection change
            if hasattr(self, 'main_app') and self.main_app:
                self.main_app.log_event(f"[Machine] Selection changed to: {selected_machine}")
            
            # Store the current selection for persistence during session
            # This ensures the selection is maintained as per requirement 2.1
            current_selection = self.machine_var.get()
            if current_selection != selected_machine:
                self.machine_var.set(selected_machine)
            
            # Prepare structure for future configuration integration
            # This method is designed to be extended when machine-specific
            # configurations need to be loaded and applied
            self._prepare_machine_configuration(selected_machine)
            
        except Exception as e:
            # Error handling for any issues during machine selection
            if hasattr(self, 'main_app') and self.main_app:
                self.main_app.log_error(f"[Machine Error] Failed to change machine selection: {e}")
    
    def _prepare_machine_configuration(self, machine_name):
        """Prepare machine-specific configuration for future integration"""
        # This method is structured to accommodate future machine-specific
        # configuration loading as per the design document
        # Currently logs the preparation step and maintains extensibility
        
        try:
            if hasattr(self, 'main_app') and self.main_app:
                self.main_app.log_event(f"[Machine Config] Preparing configuration for {machine_name}")
            
            # Future implementation will include:
            # - Loading machine-specific settings from AnalyzerConfig.json
            # - Applying machine-specific communication parameters
            # - Updating UI elements based on machine capabilities
            # - Setting machine-specific protocol handlers
            
            # For now, this maintains the structure for future extensibility
            # while ensuring the current selection is properly handled
            
        except Exception as e:
            if hasattr(self, 'main_app') and self.main_app:
                self.main_app.log_error(f"[Machine Config Error] Failed to prepare configuration for {machine_name}: {e}")
        
    def setup_ui(self):
        # Main container
        main_frame = tk.Frame(self.frame, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- Top Control Frame ---
        top_frame = tk.Frame(main_frame, bg='#e6e6e6', relief=tk.RAISED, bd=2)
        top_frame.pack(fill=tk.X, pady=(0, 10))

        connection_frame = tk.Frame(top_frame, bg='#e6e6e6')
        connection_frame.pack(pady=10)

        # Port label
        tk.Label(connection_frame, text="Port:", bg='#e6e6e6', font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        self.serial_port_var = tk.StringVar(value="COM2")
        tk.Label(connection_frame, textvariable=self.serial_port_var, bg='#e6e6e6', font=('Arial', 10)).pack(side=tk.LEFT, padx=(5, 15))

        # Baud Rate
        tk.Label(connection_frame, text="Baud:", bg='#e6e6e6', font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        self.baud_var = tk.StringVar(value="9600")
        baud_menu = tk.OptionMenu(connection_frame, self.baud_var, "9600", "19200", "38400", "57600", "115200")
        baud_menu.configure(bg='white', font=('Arial', 9), relief=tk.RAISED, bd=1)
        baud_menu.pack(side=tk.LEFT, padx=(5, 15))

        # Machine selection
        tk.Label(connection_frame, text="Machine:", bg='#e6e6e6', font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        self.machine_var = tk.StringVar(value="BS240")
        machine_options = self.load_machine_options()
        machine_menu = tk.OptionMenu(connection_frame, self.machine_var, *machine_options, command=self.on_machine_change)
        machine_menu.configure(bg='white', font=('Arial', 9), relief=tk.RAISED, bd=1)
        machine_menu.pack(side=tk.LEFT, padx=(5, 15))


        # Connect Button
        self.connect_btn = tk.Button(connection_frame, 
                                    text="Connect", 
                                    command=self.connect,
                                    bg='#4CAF50', 
                                    fg='white', 
                                    font=('Arial', 10, 'bold'), 
                                    relief=tk.RAISED, 
                                    bd=2, 
                                    padx=15)
        self.connect_btn.pack(side=tk.LEFT, padx=5)

        # Disconnect Button
        self.disconnect_btn = tk.Button(connection_frame, 
                                       text="Disconnect", 
                                       command=self.disconnect,
                                       bg='#f44336', 
                                       fg='white', 
                                       font=('Arial', 10, 'bold'), 
                                       relief=tk.RAISED, 
                                       bd=2, 
                                       padx=15)
        self.disconnect_btn.pack(side=tk.LEFT, padx=5)

        # Connection Status
        self.status_label = tk.Label(top_frame, text="Disconnected", bg='#e6e6e6', fg='red', font=('Arial', 10, 'bold'))
        self.status_label.pack(side=tk.RIGHT, padx=10, pady=5)

        # --- Middle Log Frames ---
        middle_frame = tk.Frame(main_frame)
        middle_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # General Logs
        self.logs_frame = tk.LabelFrame(middle_frame, text="General Logs", font=('Arial', 11, 'bold'), bg='#f0f0f0')
        self.logs_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        self.log_text = scrolledtext.ScrolledText(self.logs_frame, width=40, height=25,
            font=('Consolas', 9), bg='white', fg='black', wrap=tk.WORD, relief=tk.SUNKEN, bd=2)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Error Logs
        self.errors_frame = tk.LabelFrame(middle_frame, text="Error Logs", font=('Arial', 11, 'bold'), bg='#f0f0f0')
        self.errors_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        self.error_text = scrolledtext.ScrolledText(self.errors_frame, width=40, height=25,
            font=('Consolas', 9), bg='#fff8f8', fg='#d32f2f', wrap=tk.WORD, relief=tk.SUNKEN, bd=2)
        self.error_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- Bottom Input + Controls ---
        bottom_frame = tk.Frame(main_frame, bg='#e6e6e6', relief=tk.RAISED, bd=2)
        bottom_frame.pack(fill=tk.X, pady=(0, 5))

        # Message input
        input_frame = tk.Frame(bottom_frame, bg='#e6e6e6')
        input_frame.pack(pady=10)

        tk.Label(input_frame, text="Message:", bg='#e6e6e6', font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=(0, 5))
        self.input_entry = tk.Entry(input_frame, width=60, font=('Arial', 10), relief=tk.SUNKEN, bd=2)
        self.input_entry.pack(side=tk.LEFT, padx=5)

        self.send_btn = tk.Button(input_frame, text="Send", command=self.write_to_socket,
            bg='#2196F3', fg='white', font=('Arial', 10, 'bold'), relief=tk.RAISED, bd=2, padx=15)
        self.send_btn.pack(side=tk.LEFT, padx=5)

        # ENQ Button
        enq_frame = tk.Frame(bottom_frame, bg='#e6e6e6')
        enq_frame.pack(pady=(0, 10))

        self.enq_btn = tk.Button(enq_frame, text="Send ENQ", command=self.send_enq,
            bg='#FF9800', fg='white', font=('Arial', 10, 'bold'), relief=tk.RAISED, bd=2, padx=20)
        self.enq_btn.pack()

        # Control buttons
        control_frame = tk.Frame(bottom_frame, bg='#e6e6e6')
        control_frame.pack(pady=(0, 10))

        self.clear_logs_btn = tk.Button(control_frame, text="Clear Logs", command=self.clear_logs,
            bg='#9E9E9E', fg='white', font=('Arial', 9), relief=tk.RAISED, bd=2, padx=10)
        self.clear_logs_btn.pack(side=tk.LEFT, padx=5)

        self.clear_errors_btn = tk.Button(control_frame, text="Clear Errors", command=self.clear_errors,
            bg='#9E9E9E', fg='white', font=('Arial', 9), relief=tk.RAISED, bd=2, padx=10)
        self.clear_errors_btn.pack(side=tk.LEFT, padx=5)

        # API Frame
        api_frame = tk.Frame(bottom_frame, bg='#e6e6e6')
        api_frame.pack(pady=(0, 10))

        tk.Label(api_frame, text="API Endpoint:", bg='#e6e6e6', font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=(0, 5))
        self.api_endpoint = tk.Entry(api_frame, width=40, font=('Arial', 9), relief=tk.SUNKEN, bd=2)
        self.api_endpoint.pack(side=tk.LEFT, padx=5)
        self.api_endpoint.insert(0, "http://localhost:8000/app/analyzer/parse")

        self.send_api_btn = tk.Button(api_frame, text="Send to API", command=self.send_data_to_api,
            bg='#9C27B0', fg='white', font=('Arial', 9), relief=tk.RAISED, bd=2, padx=10, state='disabled')
        self.send_api_btn.pack(side=tk.LEFT, padx=5)

        # Buffer status
        self.buffer_status = tk.Label(api_frame, text="Buffer: 0 messages", bg='#e6e6e6', font=('Arial', 9))
        self.buffer_status.pack(side=tk.LEFT, padx=10)

    def connect(self):
        """Connect to serial port and socket"""
        if not self.serial_connected:
            if self.connect_serial():
                self.serial_connected = True
                self.status_label.config(text="Serial Connected", foreground='orange')
                self.connect_btn.config(state='disabled')
                self.disconnect_btn.config(state='normal')
                self.main_app.log_event(f"[Serial] Connected to {self.serial_connection.port} at {self.serial_connection.baudrate} baud")

                self.serial_reading = True
                self.serial_thread = threading.Thread(target=self.read_from_serial)
                self.serial_thread.daemon = True
                self.serial_thread.start()

                if self.connect_socket():
                    self.socket_connected = True
                    self.status_label.config(text="Connected", foreground='green')
                    self.reading = True
                    self.read_thread = threading.Thread(target=self.read_from_socket)
                    self.read_thread.daemon = True
                    self.read_thread.start()
                    self.main_app.log_event(f"[Socket] Connected to {self.net_host}:{self.net_port}")
                else:
                    self.main_app.log_error("[Error] Failed to connect to socket")
            else:
                self.main_app.log_error("[Error] Failed to connect to serial port")

    def connect_serial(self) -> bool:
        """Connect to serial port"""
        try:
            serial_port = str(self.serial_port_var.get())
            serial_baud = int(self.baud_var.get())
        
            self.main_app.log_event(f"[Serial] Attempting to connect to {serial_port} at {serial_baud} baud...")
            self.serial_connection = serial.Serial(serial_port, serial_baud, timeout=1)

            if not self.serial_connection.is_open:
                self.main_app.log_error("[Error] Failed to open serial port")
                return False

            return True
        except serial.SerialException as e:
            self.main_app.log_error(f"[Serial Error] {e}")
            return False

    def connect_socket(self) -> bool:
        """Connect to TCP socket"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setblocking(True)
            sock.connect((self.net_host, self.net_port))
            self.socket_connection = sock
            return True
        except socket.gaierror as e:
            self.main_app.log_error(f"Address-related error connecting to {self.net_host}:{self.net_port} - {e}")
            return False
        except socket.timeout as e:
            self.main_app.log_error(f"Connection to {self.net_host}:{self.net_port} timed out - {e}")
            return False
        except ConnectionRefusedError as e:
            self.main_app.log_error(f"Connection to {self.net_host}:{self.net_port} refused - {e}")
            return False
        except socket.error as e:
            self.main_app.log_error(f"Socket error while connecting to {self.net_host}:{self.net_port} - {e}")
            return False
        except Exception as e:
            self.main_app.log_error(f"Unexpected error during socket connection: {e}")
            return False

    def disconnect(self):
        """Disconnect from serial port and socket"""
        self.reading = False
        self.serial_reading = False
        
        if self.socket_connected and self.socket_connection:
            self.socket_connection.close()
            self.socket_connected = False
            self.main_app.log_event("[Socket] Disconnected")
        
        if self.serial_connected and self.serial_connection:
            self.serial_connection.close()
            self.serial_connected = False
            self.main_app.log_event("[Serial] Disconnected")

        self.status_label.config(text="Disconnected", foreground='red')
        self.connect_btn.config(state='normal')
        self.disconnect_btn.config(state='disabled')
        self.send_api_btn.config(state='disabled')

    def write_to_socket(self):
        """Write data to socket"""
        if not self.socket_connected:
            self.main_app.log_error("[Error] Socket not connected")
            return

        user_input = self.input_entry.get()
        if not user_input:
            return

        try:
            parsed_msg = self.main_app.parse_input_with_control_chars(user_input)
            self.socket_connection.sendall(parsed_msg)
            pretty = self.main_app.pretty_logger(parsed_msg)
            self.main_app.log_event(f"[SENT]\n{pretty}")
            self.input_entry.delete(0, tk.END)
        except (ConnectionAbortedError, BrokenPipeError):
            self.main_app.log_error("[Error] Socket connection aborted. Please reconnect.")
        except Exception as e:
            self.main_app.log_error(f"[Unexpected Error] {e}")

    def read_from_socket(self):
        """Read data from socket in separate thread"""
        while self.reading and self.socket_connection:
            try:
                self.socket_connection.settimeout(1.0)
                data = self.socket_connection.recv(4096)
            
                if data:
                    # Add to buffer
                    self.data_buffer.append({
                        'timestamp': datetime.now().isoformat(),
                        'data': data.decode('latin-1', errors='ignore').strip()
                    })
                    
                    # Update buffer status
                    self.parent.after(0, self.update_buffer_status)
                    
                    # Log the data
                    for b in data:
                        if b in control_map:
                            self.main_app.log_event(f"[CONTROL] - {control_map[b]}")
                        else:
                            self.main_app.log_event(f"[RECEIVED BYTE] - {chr(b)}")

                    if self.serial_connected:
                        self.serial_connection.write(data)
                        self.main_app.log_event(f"[LIS → Analyzer] {repr(data)}")
                else:
                    self.main_app.log_event("[INFO] Socket connection closed by remote")
                    self.serial_connected = False
                    self.socket_connected = False

                    self.serial_connection = None
                    self.socket_connection = None
                    
                    self.status_label.config(text="Disconnected", foreground='red')
                    break
                
            except socket.timeout:
                continue
            except socket.error as e:
                self.main_app.log_error(f"[Socket Error] {e}")
                break
            except Exception as e:
                self.main_app.log_error(f"[Unexpected Error] {e}")
                break
            
            time.sleep(0.1)

    def read_from_serial(self):
        """Read data from COM2 (serial) and send it to the middleware socket"""
        while self.serial_reading and self.serial_connection:
            try:
                if self.serial_connection.in_waiting:
                    data = self.serial_connection.read(self.serial_connection.in_waiting)

                    # Optional: log data to GUI
                    self.main_app.log_event(f"[Analyzer] SENT: {data}")

                    # Forward to middleware via socket
                    if self.socket_connected:
                        self.socket_connection.sendall(data)
                        self.main_app.log_event(f"[Forwarded to LIS]: {data}")
            except Exception as e:
                self.main_app.log_error(f"[Serial Read Error] {e}")
                break

            time.sleep(0.1)

    def send_enq(self):
        """Send ENQ command"""
        if self.socket_connected and self.socket_connection:
            self.socket_connection.sendall(ENQ)
            self.main_app.log_event(f"[SENT] ENQ")
        else:
            self.main_app.log_error("[Error] Socket not connected")

    def clear_logs(self):
        """Clear general logs"""
        self.log_text.delete(1.0, tk.END)
        self.log_text.insert(tk.END, "--- General logs cleared ---\n")

    def clear_errors(self):
        """Clear error logs"""
        self.error_text.delete(1.0, tk.END)
        self.error_text.insert(tk.END, "--- Error logs cleared ---\n")

    def update_buffer_status(self):
        """Update buffer status label"""
        buffer_count = len(self.data_buffer)
        self.buffer_status.config(text=f"Buffer: {buffer_count} messages")
        
        # Enable API button if there's data
        if buffer_count > 0:
            self.send_api_btn.config(state='normal')

    def send_data_to_api(self):
        """Send buffered data to API"""
        if not self.data_buffer:
            messagebox.showwarning("No Data", "No data available to send")
            return
        
        endpoint = self.api_endpoint.get().strip()
        if not endpoint:
            messagebox.showerror("Invalid Endpoint", "Please enter a valid API endpoint")
            return
        
        # Prepare payload
        payload = {
            'source': 'serial',
            'connection_info': {
                'port': self.serial_port_var.get(),
                'baud_rate': self.baud_var.get()
            },
            'data': self.data_buffer.copy(),
            'total_messages': len(self.data_buffer)
        }
        
        # Send to API using main app's method
        success, response_data, error_message = self.main_app.send_api_request(endpoint, payload)
        
        if success:
            # Clear buffer after successful send
            self.data_buffer.clear()
            self.update_buffer_status()
            
            # Show success message
            processed_count = response_data.get('processed', 'N/A') if response_data else 'N/A'
            messagebox.showinfo("Success", f"Data sent successfully!\nMessages processed: {processed_count}")
        else:
            messagebox.showerror("API Error", error_message)

    def clear_buffer(self):
        """Clear data buffer"""
        self.data_buffer.clear()
        self.update_buffer_status()
        self.main_app.log_event("Data buffer cleared")