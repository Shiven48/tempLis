import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import threading
from graphics.logs.logs_widget import LogWidget, TextWidgetLogger
from graphics.utils import parse_input_with_control_chars, pretty_logger
import serial
import socket
import time
import yaml
import os
from erba.constants import ACK, ENQ, ERBA_YAML_DIRECTORY,NAK 

class SerialTab:

    def __init__(self, parent_notebook, main_app):
        self.parent = parent_notebook
        self.main_app = main_app
        self.frame = ttk.Frame(parent_notebook)
        self.net_host = '127.0.0.1'
        self.net_port = 15200
        
        # Connection status variables
        self.serial_connected = False
        self.serial_connection = None
        self.socket_connected = False
        self.socket_connection = None
        self.data_buffer = []
        self.reading = False
        self.serial_reading = False
        self.current_machine_config = None
        
        # --- Setup UI ---
        self.setup_ui()

    def setup_ui(self):
        # Main container with improved styling
        main_frame = tk.Frame(self.frame, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- Top Control Frame ---
        top_frame = tk.Frame(main_frame, bg='#e6e6e6', relief=tk.RAISED, bd=2)
        top_frame.pack(fill=tk.X, pady=(0, 10), side=tk.TOP)

        connection_frame = tk.Frame(top_frame, bg='#e6e6e6')
        connection_frame.pack(pady=10)

        # Machine Selection
        tk.Label(connection_frame, text="Machine:", bg='#e6e6e6',
                 font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        self.machine_var = tk.StringVar(value="Select Machine")
        machine_options = self.load_machine_options()
        machine_menu = tk.OptionMenu(connection_frame, self.machine_var, *machine_options,
            command=lambda v: (self.on_machine_change(v), self.main_app.on_analyzer_changed(v)))
        machine_menu.configure(bg='white', font=('Arial', 9), relief=tk.RAISED, bd=1)
        machine_menu.pack(side=tk.LEFT, padx=(5, 15))

        # Port selection with COM port detection
        tk.Label(connection_frame, text="Port:", bg='#e6e6e6',
                 font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        self.serial_port_var = tk.StringVar(value="Disabled")

        port_options = ["COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8"]
        self.port_menu = tk.OptionMenu(connection_frame, self.serial_port_var, *port_options)
        self.port_menu.configure(bg='white', font=('Arial', 9), state="disabled")
        self.port_menu.pack(side=tk.LEFT, padx=(5, 15))

        # Baud Rate
        tk.Label(connection_frame, text="Baud:", bg='#e6e6e6',
                 font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        self.baud_var = tk.StringVar(value="Disabled")
        self.baud_menu = tk.OptionMenu(connection_frame, self.baud_var, "")
        self.baud_menu.configure(bg='white', font=('Arial', 9), state="disabled")
        self.baud_menu.pack(side=tk.LEFT, padx=(5, 15))

        # Connection buttons
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
        data_log_frame = ttk.LabelFrame(main_frame, text="Serial Data Monitor (ASTM)")
        data_log_frame.pack(fill='both', expand=True, pady=(0, 10))
        data_log_widget = LogWidget(data_log_frame)
        data_logger = TextWidgetLogger(data_log_widget)
        self.main_app.logging_manager.register('serial_data', data_logger)

        # Bottom Input + Controls
        bottom_frame = tk.Frame(main_frame, bg='#e6e6e6', relief=tk.RAISED, bd=2)
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)

        # Message input section
        input_frame = tk.Frame(bottom_frame, bg='#e6e6e6')
        input_frame.pack(pady=10)
        
        tk.Label(input_frame, text="Message:", bg='#e6e6e6', font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=(0, 5))
        self.input_entry = tk.Entry(input_frame, width=50, font=('Arial', 10), relief=tk.SUNKEN, bd=2)
        self.input_entry.pack(side=tk.LEFT, padx=5)
        
        self.input_entry.bind('<Return>', lambda e: self.write_to_middleware())
        
        self.send_btn = tk.Button(input_frame, text="Send to Middleware", command=self.write_to_middleware,
            bg='#2196F3', fg='white', font=('Arial', 10, 'bold'), relief=tk.RAISED, bd=2, padx=15)
        self.send_btn.pack(side=tk.LEFT, padx=5)

        # Quick action buttons
        quick_frame = tk.Frame(bottom_frame, bg='#e6e6e6')
        quick_frame.pack(pady=(0, 10))

        self.enq_btn = tk.Button(quick_frame, text="Send ENQ", command=self.send_enq,
            bg='#FF9800', fg='white', font=('Arial', 10, 'bold'), relief=tk.RAISED, bd=2, padx=20)
        self.enq_btn.pack(side=tk.LEFT, padx=5)
        
        self.ack_btn = tk.Button(quick_frame, text="Send ACK", command=self.send_ack,
            bg='#4CAF50', fg='white', font=('Arial', 10, 'bold'), relief=tk.RAISED, bd=2, padx=20)
        self.ack_btn.pack(side=tk.LEFT, padx=5)

        self.nak_btn = tk.Button(quick_frame, text="Send NAK", command=self.send_nak,
            bg='#f44336', fg='white', font=('Arial', 10, 'bold'), relief=tk.RAISED, bd=2, padx=20)
        self.nak_btn.pack(side=tk.LEFT, padx=5)

        # Control buttons
        control_frame = tk.Frame(bottom_frame, bg='#e6e6e6')
        control_frame.pack(pady=(0, 10))
        
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

    # Methods for initializing the state of middleware 
    def load_machine_options(self):
        """Load machine options dynamically from YAML config files, filtering by ASTM protocol"""
        config_dir = ERBA_YAML_DIRECTORY
        default_machines = ["Select Machine"]

        try:
            if not os.path.isdir(config_dir):
                if hasattr(self, 'main_app') and self.main_app:
                    self.main_app.log_info(
                        f"[Config] Configuration directory not found at {config_dir}, using defaults for ASTM machines"
                    )
                return default_machines

            machine_names = []
            for filename in os.listdir(config_dir):
                if not filename.endswith(".yaml"):
                    continue

                filepath = os.path.join(config_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        config_data = yaml.safe_load(f)

                    if (
                        isinstance(config_data, dict)
                        and "device" in config_data
                        and "protocol" in config_data
                        and "transport" in config_data
                    ):
                        protocol = str(config_data["protocol"])
                        transport_mode = str(config_data["transport"].get("mode", ""))
                        
                        # Only load machines with ASTM protocol and serial transport for Serial Tab
                        if "ASTM" in protocol and transport_mode.lower() == "serial":
                            machine_names.append(config_data["device"])
                    else:
                        if hasattr(self, 'main_app') and self.main_app:
                            self.main_app.log_info(
                                f"[Config] Missing required keys in {filename}, skipping"
                            )
                except Exception as e:
                    if hasattr(self, 'main_app') and self.main_app:
                        self.main_app.log_error(
                            f"[Config Error] Failed reading {filename}: {e}"
                        )
            if machine_names:
                if hasattr(self, 'main_app') and self.main_app:
                    self.main_app.log_info(
                        f"[Config] Loaded {len(machine_names)} ASTM serial machines from YAML configs"
                    )
                return ["Select Machine"] + machine_names
            else:
                if hasattr(self, 'main_app') and self.main_app:
                    self.main_app.log_info(
                        "[Config] No valid ASTM serial machines found in configs"
                    )
                return default_machines
        except Exception as e:
            if hasattr(self, 'main_app') and self.main_app:
                self.main_app.log_error(f"[Config Error] Unexpected error: {e}")
            return default_machines
        
    def on_machine_change(self, selected_machine):
        """Handle machine selection and enable/disable UI elements based on selection"""
        try:
            if hasattr(self.main_app, "log_event"):
                self.main_app.log_info(f"[Serial] Machine changed → {selected_machine}")

            # If "Select Machine" is chosen, disable all communication controls
            if selected_machine == "Select Machine":
                self._disable_communication_controls()
                self.main_app.log_info("[Serial] Please select a machine to enable communication controls")
                return

            # Apply configuration for selected machine
            if self._apply_machine_configuration(selected_machine):
                self._enable_communication_controls()
            else:
                self._disable_communication_controls()
                self.main_app.log_error(f"[Serial] Failed to configure machine: {selected_machine}")
        except Exception as e:
            if hasattr(self.main_app, "log_error"):
                self.main_app.log_error(f"[Serial] Machine change failed: {e}")
            self._disable_communication_controls()

    def _apply_machine_configuration(self, machine_name):
        """Apply machine-specific configuration from YAML. Return True if successful."""
        config_dir = "packages/middleware/src/configuration"
        config = None

        try:
            # Require config directory
            if not os.path.isdir(config_dir):
                raise FileNotFoundError(f"Config directory not found: {config_dir}")

            # Look for YAML configs
            for filename in os.listdir(config_dir):
                if filename.endswith(".yaml"):
                    filepath = os.path.join(config_dir, filename)
                    with open(filepath, "r", encoding="utf-8") as f:
                        config_data = yaml.safe_load(f)

                    # Match YAML `device` with selected machine
                    if config_data and isinstance(config_data, dict):
                        if config_data.get("device") == machine_name:
                            transport = config_data.get("transport", {})
                            
                            # Validate this is a serial ASTM device
                            if (transport.get("mode", "").lower() != "serial" or 
                                "ASTM" not in str(config_data.get("protocol", ""))):
                                raise ValueError(f"Machine {machine_name} is not configured for serial ASTM communication")
                            
                            # Extract configuration
                            port = transport.get("port")
                            baudrate = transport.get("baudrate")

                            if not port or not baudrate:
                                raise ValueError(
                                    f"Invalid config for {machine_name} in {filename}: port/baudrate missing"
                                )

                            config = {
                                "port": port,
                                "baudrate": str(baudrate),
                                "databits": transport.get("databits", 8),
                                "parity": transport.get("parity", "None"),
                                "stopbits": transport.get("stopbits", 1),
                                "timeout": transport.get("timeout", 10.0),
                                "protocol": config_data.get("protocol"),
                                "encoding": config_data.get("encoding", "latin-1"),
                            }
                            break

            # Fail early if no config found
            if not config:
                raise FileNotFoundError(
                    f"No serial ASTM configuration found for machine '{machine_name}' in {config_dir}"
                )

            # Apply config to UI
            self.current_machine_config = config
            
            # Update port options (show only the configured port)
            self.serial_port_var.set(config["port"])
            self._update_option_menu(self.port_menu, [config["port"]])
            
            # Update baud rate options (show only the configured baud rate)
            self.baud_var.set(config["baudrate"])
            self._update_option_menu(self.baud_menu, [config["baudrate"]])

            if hasattr(self.main_app, "log_event"):
                self.main_app.log_info(
                    f"[Serial] Config applied for {machine_name}: "
                    f"port={config['port']}, baud={config['baudrate']}, "
                    f"protocol={config['protocol']}"
                )
            
            return True

        except Exception as e:
            if hasattr(self.main_app, "log_error"):
                self.main_app.log_error(f"[Config Error] Failed to apply config for {machine_name}: {e}")
            return False

    def _enable_communication_controls(self):
        """Enable communication-related UI controls"""
        self.port_menu.configure(state="normal")
        self.baud_menu.configure(state="normal")
        self.connect_btn.configure(state="normal")
    
    def _disable_communication_controls(self):
        """Disable communication-related UI controls"""
        self.port_menu.configure(state="disabled")
        self.baud_menu.configure(state="disabled")
        self.connect_btn.configure(state="disabled")
        self.serial_port_var.set("Select Machine First")
        self.baud_var.set("Select Machine First")

    # methods for connection handling
    def connect(self):
        """Connect to serial port and middleware"""
        if not self.serial_connected:
            if self.connect_serial():
                self.serial_connected = True
                self.status_label.config(text="Serial Connected", foreground='orange')
                self.connect_btn.config(state='disabled')
                self.disconnect_btn.config(state='normal')
                self.main_app.log_info(f"[Serial] Connected to {self.serial_connection.port} at {self.serial_connection.baudrate} baud")

                # Start serial reading thread
                self.serial_reading = True
                self.serial_thread = threading.Thread(target=self.read_from_serial)
                self.serial_thread.daemon = True
                self.serial_thread.start()

                # Try to connect to middleware
                if self.connect_to_middleware():
                    self.socket_connected = True
                    self.status_label.config(text="Connected to Middleware", foreground='green')
                    
                    # Start middleware communication thread
                    self.reading = True
                    self.read_thread = threading.Thread(target=self.read_from_middleware)
                    self.read_thread.daemon = True
                    self.read_thread.start()
                    
                    self.main_app.log_info(f"[Serial] Connected to middleware at {self.net_host}:{self.net_port}")
                else:
                    self.main_app.log_error("[Serial] Failed to connect to middleware")
            else:
                self.main_app.log_error("[Serial] Failed to connect to serial port")

    def connect_serial(self) -> bool:
        """Connect to serial port"""
        try:
            serial_port = str(self.serial_port_var.get())
            serial_baud = int(self.baud_var.get())
        
            self.main_app.log_info(f"[Serial] Attempting to connect to {serial_port} at {serial_baud} baud...")
            self.serial_connection = serial.Serial(serial_port, serial_baud, timeout=1)

            if not self.serial_connection.is_open:
                self.main_app.log_error("[Serial] Failed to open serial port")
                return False

            return True
        except serial.SerialException as e:
            self.main_app.log_error(f"[Serial Error] {e}")
            return False

    def connect_to_middleware(self) -> bool:
        """Connect to middleware server"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setblocking(True)
            sock.settimeout(5.0)  # 5 second timeout
            sock.connect((self.net_host, self.net_port))
            self.socket_connection = sock
            return True
        except socket.gaierror as e:
            self.main_app.log_error(f"[Serial] Address error connecting to middleware {self.net_host}:{self.net_port} - {e}")
            return False
        except socket.timeout as e:
            self.main_app.log_error(f"[Serial] Connection to middleware {self.net_host}:{self.net_port} timed out - {e}")
            return False
        except ConnectionRefusedError as e:
            self.main_app.log_error(f"[Serial] Connection to middleware {self.net_host}:{self.net_port} refused - {e}")
            self.main_app.log_error("[Serial] Make sure middleware server is running")
            return False
        except socket.error as e:
            self.main_app.log_error(f"[Serial] Socket error connecting to middleware: {e}")
            return False
        except Exception as e:
            self.main_app.log_error(f"[Serial] Unexpected error during middleware connection: {e}")
            return False

    def disconnect(self):
        """Disconnect from serial port and middleware"""
        self.reading = False
        self.serial_reading = False
        
        if self.socket_connected and self.socket_connection:
            self.socket_connection.close()
            self.socket_connected = False
            self.main_app.log_info("[Serial] Disconnected from middleware")
        
        if self.serial_connected and self.serial_connection:
            self.serial_connection.close()
            self.serial_connected = False
            self.main_app.log_info("[Serial] Disconnected from serial port")

        self.status_label.config(text="Disconnected", foreground='red')
        self.connect_btn.config(state='normal')
        self.disconnect_btn.config(state='disabled')
        self.send_api_btn.config(state='disabled')

    # methods to communicate with middleware
    def write_to_middleware(self):
        """Write data to middleware (instead of directly to socket)"""
        if not self.socket_connected:
            self.main_app.log_error("[Serial] Not connected to middleware")
            return

        user_input = self.input_entry.get().strip()
        if not user_input:
            return

        try:
            parsed_msg = parse_input_with_control_chars(user_input)
            self.socket_connection.sendall(parsed_msg)
            pretty = pretty_logger(parsed_msg)
            self.main_app.log_serial_data(f"[Serial → Middleware]\n{pretty}")
            self.input_entry.delete(0, tk.END)
        except (ConnectionAbortedError, BrokenPipeError):
            self.main_app.log_error("[Serial] Middleware connection lost. Please reconnect.")
            self.socket_connected = False
            self.status_label.config(text="Middleware Disconnected", foreground='red')
        except Exception as e:
            self.main_app.log_error(f"[Serial] Send error: {e}")

    def read_from_middleware(self):
        """Read responses from middleware"""
        while self.reading and self.socket_connection:
            try:
                self.socket_connection.settimeout(1.0)
                data = self.socket_connection.recv(4096)
            
                if data:
                    # Add to buffer
                    self.data_buffer.append({
                        'timestamp': datetime.now().isoformat(),
                        'source': 'middleware_response',
                        'data': data.decode('latin-1', errors='ignore').strip()
                    })
                    
                    # Update buffer status
                    self.parent.after(0, self.update_buffer_status)
                    
                    # Log the response
                    self.main_app.log_serial_data(f"[Middleware → Serial] Response received: {len(data)} bytes")
                    pretty = pretty_logger(data)
                    self.main_app.log_serial_data(f"[Middleware Response]\n{pretty}")

                    # Forward to serial port if connected
                    if self.serial_connected and self.serial_connection:
                        self.serial_connection.write(data)
                        self.main_app.log_serial_data(f"[Serial] Forwarded to analyzer: {len(data)} bytes")
                else:
                    self.main_app.log_serial_data("[Serial] Middleware connection closed")
                    self.socket_connected = False
                    self.status_label.config(text="Middleware Disconnected", foreground='red')
                    break
                
            except socket.timeout:
                continue
            except socket.error as e:
                if self.reading:  # Only log if we should be reading
                    self.main_app.log_error(f"[Serial] Middleware read error: {e}")
                break
            except Exception as e:
                self.main_app.log_error(f"[Serial] Unexpected middleware read error: {e}")
                break
            
            time.sleep(0.1)

    def read_from_serial(self):
        """Read data from serial port and forward to middleware"""
        while self.serial_reading and self.serial_connection:
            try:
                if self.serial_connection.in_waiting:
                    data = self.serial_connection.read(self.serial_connection.in_waiting)

                    # Log received data
                    self.main_app.log_serial_data(f"[Analyzer → Serial] Received: {len(data)} bytes")
                    pretty = pretty_logger(data)
                    self.main_app.log_serial_data(f"[From Analyzer]\n{pretty}")

                    # Add to buffer
                    self.data_buffer.append({
                        'timestamp': datetime.now().isoformat(),
                        'source': 'serial_analyzer',
                        'raw_data': data.hex(),
                        'decoded_data': data.decode('latin-1', errors='ignore').strip()
                    })

                    # Update buffer status
                    self.parent.after(0, self.update_buffer_status)

                    # Forward to middleware if connected
                    if self.socket_connected and self.socket_connection:
                        self.socket_connection.sendall(data)
                        self.main_app.log_serial_data(f"[Serial → Middleware] Forwarded: {len(data)} bytes")
                    else:
                        self.main_app.log_error("[Serial] Cannot forward to middleware - not connected")                    
                        
            except Exception as e:
                self.main_app.log_error(f"[Serial] Read error: {e}")
                break
            time.sleep(0.1)

    # methods for development/testing
    def send_enq(self):
        """Send ENQ command"""
        if self.socket_connected and self.socket_connection:
            self.socket_connection.sendall(ENQ)
            self.main_app.log_event("[Serial → Middleware] ENQ sent")
        else:
            self.main_app.log_error("[Serial] Not connected to middleware")

    def send_ack(self):
        """Send ACK command"""
        if self.socket_connected and self.socket_connection:
            self.socket_connection.sendall(ACK)
            self.main_app.log_event("[Serial → Middleware] ACK sent")
        else:
            self.main_app.log_error("[Serial] Not connected to middleware")

    def send_nak(self):
        """Send NAK command"""
        if self.socket_connected and self.socket_connection:
            self.socket_connection.sendall(NAK)
            self.main_app.log_event("[Serial → Middleware] NAK sent")
        else:
            self.main_app.log_error("[Serial] Not connected to middleware")

    # methods for clearing logs and updating buffers
    def update_buffer_status(self):
        """Update buffer status label"""
        buffer_count = len(self.data_buffer)
        self.buffer_status.config(text=f"Buffer: {buffer_count} messages")
        
        # Enable API button if there's data
        if buffer_count > 0:
            self.send_api_btn.config(state='normal')

    def clear_buffer(self):
        """Clear data buffer"""
        self.data_buffer.clear()
        self.update_buffer_status()
        self.main_app.log_event("[Serial] Data buffer cleared")

    # Method to send data to remote api route
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
                'baud_rate': self.baud_var.get(),
                'analyzer': self.machine_var.get()
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
            messagebox.showinfo("Success", f"Serial data sent successfully!\nMessages processed: {processed_count}")
        else:
            messagebox.showerror("API Error", error_message)
