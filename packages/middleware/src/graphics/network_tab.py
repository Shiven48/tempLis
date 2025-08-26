import tkinter as tk
from tkinter import ttk, messagebox
import os
import yaml

from graphics.Logs.logs_widget import TextWidgetLogger, LogWidget

class NetworkTab:

    def __init__(self, parent_notebook, main_app):
        self.parent = parent_notebook
        self.main_app = main_app
        self.frame = ttk.Frame(parent_notebook)
        
        # Connection status variables
        self.tcp_connected = False
        self.tcp_server_socket = None
        self.tcp_client_socket = None
        self.tcp_connection = None
        self.data_buffer = []
        self.reading = False
        self.current_machine_config = None
        self.engine_mode = False
        
        # Setup UI
        self.setup_ui()      
    
    def setup_ui(self):
        # Main container
        main_frame = tk.Frame(self.frame, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- Top Control Frame ---
        top_frame = tk.Frame(main_frame, bg='#e6e6e6', relief=tk.RAISED, bd=2)
        top_frame.pack(fill=tk.X, pady=(0, 10), side=tk.TOP)

        # Network Settings Frame
        settings_frame = tk.Frame(top_frame, bg='#e6e6e6')
        settings_frame.pack(pady=10)
        self.setup_control_frames(settings_frame)

        # Frame for connection buttons (Start/Stop, Connect/Disconnect)
        self.button_frame = tk.Frame(top_frame, bg='#e6e6e6')
        self.button_frame.pack(pady=5)

        # --- Status label ---
        self.tcp_status_label = tk.Label(self.button_frame, text="Select Machine to Configure", bg='#e6e6e6', fg='orange', font=('Arial', 10, 'bold'))
        self.tcp_status_label.pack()

        # --- Middle Log Frames ---
        data_log_frame = ttk.LabelFrame(main_frame, text="Network Data Monitor (HL7/ASTM)")
        data_log_frame.pack(fill='both', expand=True, pady=(0, 10))

        data_log_widget = LogWidget(data_log_frame)
        data_logger = TextWidgetLogger(data_log_widget)
        self.main_app.logging_manager.register('network_data', data_logger)

        # --- Bottom API Frame ---
        # bottom_frame = tk.Frame(main_frame, bg='#e6e6e6', relief=tk.RAISED, bd=2)
        # bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)
        # self.setup_api_frame(bottom_frame)

        # API Controls
        # control_frame = tk.Frame(bottom_frame, bg='#e6e6e6')
        # control_frame.pack(pady=(0, 10))

    # setup frames
    def setup_api_frame(self, bottom_frame):
        api_frame = tk.Frame(bottom_frame, bg='#e6e6e6')
        api_frame.pack(pady=10, fill=tk.X, padx=10)

        # Configure frame
        tk.Label(api_frame, text="API Endpoint:", bg='#e6e6e6', font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        self.network_api_endpoint = tk.Entry(api_frame, width=50, font=('Arial', 9))
        self.network_api_endpoint.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.network_api_endpoint.insert(0, "http://localhost:8000/app/analyzer/parse")
        
        self.network_send_api_btn = tk.Button(api_frame, text="Send to API", command=self.send_network_data_to_api,
                                             bg='#4CAF50', fg='white', font=('Arial', 10, 'bold'), 
                                             relief=tk.RAISED, bd=2, padx=10, state='disabled')
        self.network_send_api_btn.pack(side=tk.LEFT, padx=5)

        self.network_clear_buffer_btn = tk.Button(api_frame, text="Clear Buffer", command=self.clear_network_buffer,
                                                 bg='#f44336', fg='white', font=('Arial', 10, 'bold'), 
                                                 relief=tk.RAISED, bd=2, padx=10)
        self.network_clear_buffer_btn.pack(side=tk.LEFT, padx=5)

        self.network_buffer_status = tk.Label(api_frame, text="Buffer: 0 messages", bg='#e6e6e6', font=('Arial', 9))
        self.network_buffer_status.pack(side=tk.RIGHT, padx=10)

    def setup_control_frames(self, settings_frame):
        # Machine Selection (Primary control)
        tk.Label(settings_frame, text="Machine:", bg='#e6e6e6', font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        self.machine_var = tk.StringVar(value="Select Machine")
        self.analyzer_var = self.machine_var
        machine_options = self.load_machine_options()
        machine_menu = tk.OptionMenu(settings_frame, self.machine_var, *machine_options,
            command=lambda v: (self.on_machine_change(v), self.main_app.on_analyzer_changed(v)))
        machine_menu.configure(bg='white', font=('Arial', 9), relief=tk.RAISED, bd=1)
        machine_menu.pack(side=tk.LEFT, padx=(5, 15))

        # IP Address
        tk.Label(settings_frame, text="IP Address:", bg='#e6e6e6', font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        self.ip_address = tk.Entry(settings_frame, width=15, font=('Arial', 10), state='disabled')
        self.ip_address.pack(side=tk.LEFT, padx=(5, 15))
        self.ip_address.insert(0, "Select Machine First")

        # Port
        tk.Label(settings_frame, text="Port:", bg='#e6e6e6', font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        self.tcp_port = tk.Entry(settings_frame, width=8, font=('Arial', 10), state='disabled')
        self.tcp_port.pack(side=tk.LEFT, padx=(5, 15))
        self.tcp_port.insert(0, "N/A")

        # Mode
        tk.Label(settings_frame, text="Mode:", bg='#e6e6e6', font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        self.connection_type = tk.StringVar(value="TCP Client")
        connection_menu = tk.OptionMenu(settings_frame, self.connection_type, "TCP Server", "TCP Client")
        connection_menu.configure(bg='white', font=('Arial', 9), relief=tk.RAISED, bd=1, state='normal')
        self.connection_menu = connection_menu
        connection_menu.pack(side=tk.LEFT, padx=(5, 15))        

    # Config callbacks
    def load_machine_options(self):
        """Load machine options dynamically from YAML config files, filtering by HL7/TCP protocol"""
        config_dir = "configuration"
        default_machines = ["Select Machine"]

        try:
            if not os.path.isdir(config_dir):
                if hasattr(self, 'main_app') and self.main_app:
                    self.main_app.log_info(
                        f"[Config] Configuration directory not found at {config_dir}, using defaults"
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
                        
                        # Only load machines with HL7 protocol and TCP transport for Network Tab
                        if "HL7" in protocol and transport_mode.lower() == "tcp":
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
                        f"[Config] Loaded {len(machine_names)} HL7 TCP machines from YAML configs"
                    )
                return ["Select Machine"] + machine_names
            else:
                if hasattr(self, 'main_app') and self.main_app:
                    self.main_app.log_info(
                        "[Config] No valid HL7 TCP machines found in configs"
                    )
                return default_machines

        except Exception as e:
            if hasattr(self, 'main_app') and self.main_app:
                self.main_app.log_error(f"[Config Error] Unexpected error: {e}")
            return default_machines

    def on_machine_change(self, selected_machine):
        """Enhanced machine change handler"""
        try:
            self.main_app.log_info(f"[Network] Machine changed → {selected_machine}")

            if selected_machine == "Select Machine":
                self._disable_communication_controls()
                return
            
            if self.engine_mode:
                self.main_app.log_info(f"[Network] Engine Mode: Setting analyzer to {selected_machine}")
                # The main app will handle engine configuration (Change here)
                return
            
            # Apply configuration for selected machine
            if self._apply_machine_configuration(selected_machine):
                self._enable_communication_controls()
            else:
                self._disable_communication_controls()
        except Exception as e:
            self.main_app.log_error(f"[Network] Machine change failed: {e}")
            self._disable_communication_controls()   

    def on_analyzer_change(self, selected_analyzer):
        """Handle analyzer selection changes"""
        try:
            self.main_app.log_info(f"[Network] Analyzer selection changed to: {selected_analyzer}")
            
            # Update connection settings based on analyzer
            if selected_analyzer.lower() == "erba":
                self.ip_address.delete(0, tk.END)
                self.ip_address.insert(0, "192.168.1.100")
                self.tcp_port.delete(0, tk.END)
                self.tcp_port.insert(0, "2575")
                self.connection_type.set("TCP Server")
                self.main_app.log_info("[Network] Configured for Erba analyzer (TCP Server, port 2575)")
            
        except Exception as e:
            self.main_app.log_error(f"[Network] Error changing analyzer: {e}")

    def _apply_machine_configuration(self, machine_name):
        """Apply machine-specific configuration from YAML. Return True if successful."""
        config_dir = "configuration"
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
                            
                            # Validate this is a TCP HL7 device
                            if (transport.get("mode", "").lower() != "tcp" or 
                                "HL7" not in str(config_data.get("protocol", ""))):
                                raise ValueError(f"Machine {machine_name} is not configured for TCP HL7 communication")
                            
                            # Extract configuration
                            host = transport.get("host", "0.0.0.0")
                            port = transport.get("port")

                            if not port:
                                raise ValueError(
                                    f"Invalid config for {machine_name} in {filename}: port missing"
                                )

                            config = {
                                "host": host,
                                "port": str(port),
                                "protocol": config_data.get("protocol"),
                                "encoding": config_data.get("encoding", "utf-8"),
                            }
                            break

            # Fail early if no config found
            if not config:
                raise FileNotFoundError(
                    f"No TCP HL7 configuration found for machine '{machine_name}' in {config_dir}"
                )

            # Apply config to UI
            self.current_machine_config = config
            
            # Update IP address
            self.ip_address.configure(state='normal')
            self.ip_address.delete(0, tk.END)
            self.ip_address.insert(0, config["host"])
            
            # Update port
            self.tcp_port.configure(state='normal')
            self.tcp_port.delete(0, tk.END)
            self.tcp_port.insert(0, config["port"])
            
            # Set connection type based on host (127.0.0.1 loopback)
            # if config["host"] == "127.0.0.1":
            #     self.connection_type.set("TCP Server")
            #     self.tcp_connect_btn.configure(text="Start Server")
            # else:
            #     self.connection_type.set("TCP Client")
            #     self.tcp_connect_btn.configure(text="Connect")

            if hasattr(self.main_app, "log_info"):
                self.main_app.log_info(
                    f"[Network] Config applied for {machine_name}: "
                    f"host={config['host']}, port={config['port']}, "
                    f"protocol={config['protocol']}"
                )
            
            return True

        except Exception as e:
            if hasattr(self.main_app, "log_error"):
                self.main_app.log_error(f"[Config Error] Failed to apply config for {machine_name}: {e}")
            return False 
    
    def _enable_communication_controls(self):
        """Enable communication-related UI controls"""
        self.connection_menu.configure(state="normal")
        self.tcp_status_label.configure(text="Ready to Connect", foreground='green')
    
    def _disable_communication_controls(self):
        """Disable communication-related UI controls"""
        self.ip_address.configure(state='disabled')
        self.tcp_port.configure(state='disabled')
        self.connection_menu.configure(state="disabled")
        
        # Reset UI values
        self.ip_address.delete(0, tk.END)
        self.ip_address.insert(0, "Select Machine First")
        self.tcp_port.delete(0, tk.END)
        self.tcp_port.insert(0, "N/A")
        self.tcp_status_label.pack(side=tk.LEFT, padx=10)

    def update_buffer_status(self):
        """Update buffer status label"""
        buffer_count = len(self.data_buffer)
        self.network_buffer_status.config(text=f"Buffer: {buffer_count} messages")
        
        # Enable API button if there's data
        if buffer_count > 0:
            self.network_send_api_btn.config(state='normal')

    def send_network_data_to_api(self):
        """Send buffered network data to API"""
        if not self.data_buffer:
            messagebox.showwarning("No Data", "No network data available to send")
            return
        
        endpoint = self.network_api_endpoint.get().strip()
        if not endpoint:
            messagebox.showerror("Invalid Endpoint", "Please enter a valid API endpoint")
            return
        
        # Prepare payload
        payload = {
            'source': 'network',
            'connection_info': {
                'ip_address': self.ip_address.get(),
                'port': self.tcp_port.get(),
                'connection_type': self.connection_type.get(),
                'analyzer': self.analyzer_var.get()
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
            messagebox.showinfo("Success", f"Network data sent successfully!\nMessages processed: {processed_count}")
        else:
            messagebox.showerror("API Error", error_message)

    # reset callbacks
    def clear_network_buffer(self):
        """Clear network data buffer"""
        self.data_buffer.clear()
        self.update_buffer_status()
        self.main_app.log_info("[Network] Data buffer cleared")


# import tkinter as tk
# from tkinter import ttk, messagebox
# import os
# import yaml

# from graphics.Logs.logs_widget import TextWidgetLogger, LogWidget

# class NetworkTab:
    
#     def __init__(self, parent_notebook, main_app):
#         self.parent = parent_notebook
#         self.main_app = main_app
        
#         # Get color scheme from main app
#         self.colors = main_app.colors
        
#         # Create main frame with modern styling
#         self.frame = ttk.Frame(parent_notebook, style='TabContent.TFrame')
        
#         # Connection status variables
#         self.tcp_connected = False
#         self.tcp_server_socket = None
#         self.tcp_client_socket = None
#         self.tcp_connection = None
#         self.data_buffer = []
#         self.reading = False
#         self.current_machine_config = None
#         self.engine_mode = False
        
#         # Setup styles for this tab
#         self.setup_tab_styles()
        
#         # Setup UI
#         self.setup_ui()

#     def setup_tab_styles(self):
#         """Setup custom styles for network tab"""
#         style = ttk.Style()
        
#         # Tab content frame
#         style.configure('TabContent.TFrame', 
#                        background=self.colors['bg_primary'])
        
#         # Control panels
#         style.configure('ControlPanel.TLabelframe', 
#                        background=self.colors['bg_secondary'],
#                        borderwidth=1,
#                        relief='solid')
#         style.configure('ControlPanel.TLabelframe.Label', 
#                        background=self.colors['bg_secondary'],
#                        foreground=self.colors['text_primary'],
#                        font=('Segoe UI', 10, 'bold'))
        
#         # Control frame backgrounds
#         style.configure('ControlFrame.TFrame', 
#                        background=self.colors['bg_secondary'])
        
#         # Labels in control panels
#         style.configure('ControlLabel.TLabel', 
#                        background=self.colors['bg_secondary'],
#                        foreground=self.colors['text_primary'],
#                        font=('Segoe UI', 9, 'bold'))
        
#         # Entry widgets
#         style.configure('Modern.TEntry',
#                        fieldbackground=self.colors['bg_tertiary'],
#                        borderwidth=1,
#                        insertcolor=self.colors['text_primary'],
#                        foreground=self.colors['text_primary'])
#         style.map('Modern.TEntry',
#                  focuscolor=[('focus', self.colors['accent_blue'])])
        
#         # ComboBox styling
#         style.configure('Modern.TCombobox',
#                        fieldbackground=self.colors['bg_tertiary'],
#                        borderwidth=1,
#                        foreground=self.colors['text_primary'],
#                        arrowcolor=self.colors['text_secondary'])
#         style.map('Modern.TCombobox',
#                  focuscolor=[('focus', self.colors['accent_blue'])],
#                  selectbackground=[('focus', self.colors['accent_blue'])],
#                  selectforeground=[('focus', self.colors['text_primary'])])

#     def setup_ui(self):
#         """Setup the UI with modern styling"""
#         # Main container with padding
#         main_frame = ttk.Frame(self.frame, style='TabContent.TFrame')
#         main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

#         # --- Top Control Panel ---
#         control_panel = ttk.LabelFrame(main_frame, 
#                                      text="Network Configuration", 
#                                      style='ControlPanel.TLabelframe', 
#                                      padding="15")
#         control_panel.pack(fill=tk.X, pady=(0, 15))

#         # Configuration frame
#         config_frame = ttk.Frame(control_panel, style='ControlFrame.TFrame')
#         config_frame.pack(fill=tk.X, pady=(0, 10))
        
#         self.setup_control_frames(config_frame)

#         # Status and button frame
#         status_frame = ttk.Frame(control_panel, style='ControlFrame.TFrame')
#         status_frame.pack(fill=tk.X)
        
#         # Status label with modern styling
#         self.tcp_status_label = tk.Label(status_frame, 
#                                        text="Select Machine to Configure",
#                                        bg=self.colors['bg_secondary'],
#                                        fg=self.colors['status_warning'],
#                                        font=('Segoe UI', 10, 'bold'))
#         self.tcp_status_label.pack(side=tk.LEFT)

#         # --- Data Monitor Panel ---
#         monitor_panel = ttk.LabelFrame(main_frame, 
#                                      text="Network Data Monitor (HL7/ASTM)", 
#                                      style='ControlPanel.TLabelframe',
#                                      padding="10")
#         monitor_panel.pack(fill='both', expand=True, pady=(0, 15))

#         # Create log widget with dark styling
#         data_log_widget = LogWidget(monitor_panel, 
#                                   bg=self.colors['bg_tertiary'],
#                                   fg=self.colors['text_primary'],
#                                   insertbackground=self.colors['text_primary'],
#                                   selectbackground=self.colors['accent_blue'],
#                                   selectforeground=self.colors['text_primary'])
#         data_logger = TextWidgetLogger(data_log_widget)
#         self.main_app.logging_manager.register('network_data', data_logger)

#         # --- API Control Panel (if needed) ---
#         # Uncomment and modify if you want to add the API panel back
#         # self.setup_api_panel(main_frame)

#     def setup_control_frames(self, parent):
#         """Setup control frames with modern styling"""
#         # First row - Machine and connection settings
#         row1 = ttk.Frame(parent, style='ControlFrame.TFrame')
#         row1.pack(fill=tk.X, pady=(0, 10))
        
#         # Machine Selection
#         machine_frame = ttk.Frame(row1, style='ControlFrame.TFrame')
#         machine_frame.pack(side=tk.LEFT, padx=(0, 20))
        
#         ttk.Label(machine_frame, text="Machine:", 
#                  style='ControlLabel.TLabel').pack(side=tk.LEFT)
        
#         self.machine_var = tk.StringVar(value="Select Machine")
#         self.analyzer_var = self.machine_var
#         machine_options = self.load_machine_options()
        
#         # Create modern combobox instead of OptionMenu
#         self.machine_combo = ttk.Combobox(machine_frame,
#                                         textvariable=self.machine_var,
#                                         values=machine_options,
#                                         state="readonly",
#                                         style='Modern.TCombobox',
#                                         width=20)
#         self.machine_combo.pack(side=tk.LEFT, padx=(10, 0))
#         self.machine_combo.bind('<<ComboboxSelected>>', 
#                               lambda e: self.on_machine_change_event())

#         # Second row - Network settings
#         row2 = ttk.Frame(parent, style='ControlFrame.TFrame')
#         row2.pack(fill=tk.X, pady=(0, 10))
        
#         # IP Address
#         ip_frame = ttk.Frame(row2, style='ControlFrame.TFrame')
#         ip_frame.pack(side=tk.LEFT, padx=(0, 20))
        
#         ttk.Label(ip_frame, text="IP Address:", 
#                  style='ControlLabel.TLabel').pack(side=tk.LEFT)
#         self.ip_address = ttk.Entry(ip_frame, width=15, 
#                                   style='Modern.TEntry', state='disabled')
#         self.ip_address.pack(side=tk.LEFT, padx=(10, 0))
#         self.ip_address.insert(0, "Select Machine First")

#         # Port
#         port_frame = ttk.Frame(row2, style='ControlFrame.TFrame')
#         port_frame.pack(side=tk.LEFT, padx=(0, 20))
        
#         ttk.Label(port_frame, text="Port:", 
#                  style='ControlLabel.TLabel').pack(side=tk.LEFT)
#         self.tcp_port = ttk.Entry(port_frame, width=8, 
#                                 style='Modern.TEntry', state='disabled')
#         self.tcp_port.pack(side=tk.LEFT, padx=(10, 0))
#         self.tcp_port.insert(0, "N/A")

#         # Mode
#         mode_frame = ttk.Frame(row2, style='ControlFrame.TFrame')
#         mode_frame.pack(side=tk.LEFT)
        
#         ttk.Label(mode_frame, text="Mode:", 
#                  style='ControlLabel.TLabel').pack(side=tk.LEFT)
#         self.connection_type = tk.StringVar(value="TCP Client")
#         self.connection_combo = ttk.Combobox(mode_frame,
#                                            textvariable=self.connection_type,
#                                            values=["TCP Server", "TCP Client"],
#                                            state="readonly",
#                                            style='Modern.TCombobox',
#                                            width=12)
#         self.connection_combo.pack(side=tk.LEFT, padx=(10, 0))

#     def setup_api_panel(self, parent):
#         """Setup API control panel with modern styling"""
#         api_panel = ttk.LabelFrame(parent, 
#                                  text="API Controls", 
#                                  style='ControlPanel.TLabelframe',
#                                  padding="15")
#         api_panel.pack(fill=tk.X)

#         # API endpoint frame
#         endpoint_frame = ttk.Frame(api_panel, style='ControlFrame.TFrame')
#         endpoint_frame.pack(fill=tk.X, pady=(0, 10))
        
#         ttk.Label(endpoint_frame, text="API Endpoint:", 
#                  style='ControlLabel.TLabel').pack(side=tk.LEFT)
        
#         self.network_api_endpoint = ttk.Entry(endpoint_frame, 
#                                             style='Modern.TEntry',
#                                             font=('Segoe UI', 9))
#         self.network_api_endpoint.pack(side=tk.LEFT, padx=(10, 10), 
#                                      fill=tk.X, expand=True)
#         self.network_api_endpoint.insert(0, "http://localhost:8000/app/analyzer/parse")
        
#         # API control buttons
#         button_frame = ttk.Frame(api_panel, style='ControlFrame.TFrame')
#         button_frame.pack(fill=tk.X)
        
#         self.network_send_api_btn = ttk.Button(button_frame, 
#                                              text="📤 Send to API", 
#                                              command=self.send_network_data_to_api,
#                                              style='Success.TButton',
#                                              state='disabled')
#         self.network_send_api_btn.pack(side=tk.LEFT, padx=(0, 10))

#         self.network_clear_buffer_btn = ttk.Button(button_frame, 
#                                                  text="🗑 Clear Buffer", 
#                                                  command=self.clear_network_buffer,
#                                                  style='Warning.TButton')
#         self.network_clear_buffer_btn.pack(side=tk.LEFT)
        
#         # Buffer status
#         self.network_buffer_status = ttk.Label(button_frame, 
#                                              text="Buffer: 0 messages",
#                                              background=self.colors['bg_secondary'],
#                                              foreground=self.colors['text_secondary'],
#                                              font=('Segoe UI', 9))
#         self.network_buffer_status.pack(side=tk.RIGHT)

#     def on_machine_change_event(self):
#         """Handle combobox selection event"""
#         selected_machine = self.machine_var.get()
#         self.on_machine_change(selected_machine)
#         self.main_app.on_analyzer_changed(selected_machine)

#     # [Rest of your existing methods remain the same, with enhanced status updates]
    
#     def load_machine_options(self):
#         """Load machine options dynamically from YAML config files, filtering by HL7/TCP protocol"""
#         config_dir = "configuration"
#         default_machines = ["Select Machine"]

#         try:
#             if not os.path.isdir(config_dir):
#                 if hasattr(self, 'main_app') and self.main_app:
#                     self.main_app.log_info(
#                         f"[Config] Configuration directory not found at {config_dir}, using defaults"
#                     )
#                 return default_machines

#             machine_names = []
#             for filename in os.listdir(config_dir):
#                 if not filename.endswith(".yaml"):
#                     continue

#                 filepath = os.path.join(config_dir, filename)
#                 try:
#                     with open(filepath, "r", encoding="utf-8") as f:
#                         config_data = yaml.safe_load(f)

#                     if (
#                         isinstance(config_data, dict)
#                         and "device" in config_data
#                         and "protocol" in config_data
#                         and "transport" in config_data
#                     ):
#                         protocol = str(config_data["protocol"])
#                         transport_mode = str(config_data["transport"].get("mode", ""))
                        
#                         # Only load machines with HL7 protocol and TCP transport for Network Tab
#                         if "HL7" in protocol and transport_mode.lower() == "tcp":
#                             machine_names.append(config_data["device"])
#                     else:
#                         if hasattr(self, 'main_app') and self.main_app:
#                             self.main_app.log_info(
#                                 f"[Config] Missing required keys in {filename}, skipping"
#                             )
#                 except Exception as e:
#                     if hasattr(self, 'main_app') and self.main_app:
#                         self.main_app.log_error(
#                             f"[Config Error] Failed reading {filename}: {e}"
#                         )

#             if machine_names:
#                 if hasattr(self, 'main_app') and self.main_app:
#                     self.main_app.log_info(
#                         f"[Config] Loaded {len(machine_names)} HL7 TCP machines from YAML configs"
#                     )
#                 return ["Select Machine"] + machine_names
#             else:
#                 if hasattr(self, 'main_app') and self.main_app:
#                     self.main_app.log_info(
#                         "[Config] No valid HL7 TCP machines found in configs"
#                     )
#                 return default_machines

#         except Exception as e:
#             if hasattr(self, 'main_app') and self.main_app:
#                 self.main_app.log_error(f"[Config Error] Unexpected error: {e}")
#             return default_machines

#     def on_machine_change(self, selected_machine):
#         """Enhanced machine change handler with better visual feedback"""
#         try:
#             self.main_app.log_info(f"[Network] Machine changed → {selected_machine}")

#             if selected_machine == "Select Machine":
#                 self._disable_communication_controls()
#                 return
            
#             if self.engine_mode:
#                 self.main_app.log_info(f"[Network] Engine Mode: Setting analyzer to {selected_machine}")
#                 return
            
#             # Apply configuration for selected machine
#             if self._apply_machine_configuration(selected_machine):
#                 self._enable_communication_controls()
#             else:
#                 self._disable_communication_controls()
#         except Exception as e:
#             self.main_app.log_error(f"[Network] Machine change failed: {e}")
#             self._disable_communication_controls()

#     def _apply_machine_configuration(self, machine_name):
#         """Apply machine-specific configuration from YAML with enhanced feedback"""
#         config_dir = "configuration"
#         config = None

#         try:
#             if not os.path.isdir(config_dir):
#                 raise FileNotFoundError(f"Config directory not found: {config_dir}")

#             # Look for YAML configs
#             for filename in os.listdir(config_dir):
#                 if filename.endswith(".yaml"):
#                     filepath = os.path.join(config_dir, filename)
#                     with open(filepath, "r", encoding="utf-8") as f:
#                         config_data = yaml.safe_load(f)

#                     if config_data and isinstance(config_data, dict):
#                         if config_data.get("device") == machine_name:
#                             transport = config_data.get("transport", {})
                            
#                             if (transport.get("mode", "").lower() != "tcp" or 
#                                 "HL7" not in str(config_data.get("protocol", ""))):
#                                 raise ValueError(f"Machine {machine_name} is not configured for TCP HL7 communication")
                            
#                             host = transport.get("host", "0.0.0.0")
#                             port = transport.get("port")

#                             if not port:
#                                 raise ValueError(
#                                     f"Invalid config for {machine_name} in {filename}: port missing"
#                                 )

#                             config = {
#                                 "host": host,
#                                 "port": str(port),
#                                 "protocol": config_data.get("protocol"),
#                                 "encoding": config_data.get("encoding", "utf-8"),
#                             }
#                             break

#             if not config:
#                 raise FileNotFoundError(
#                     f"No TCP HL7 configuration found for machine '{machine_name}' in {config_dir}"
#                 )

#             # Apply config to UI with modern styling
#             self.current_machine_config = config
            
#             # Update IP address
#             self.ip_address.configure(state='normal')
#             self.ip_address.delete(0, tk.END)
#             self.ip_address.insert(0, config["host"])
            
#             # Update port
#             self.tcp_port.configure(state='normal')
#             self.tcp_port.delete(0, tk.END)
#             self.tcp_port.insert(0, config["port"])

#             if hasattr(self.main_app, "log_info"):
#                 self.main_app.log_info(
#                     f"[Network] ✓ Config applied for {machine_name}: "
#                     f"host={config['host']}, port={config['port']}, "
#                     f"protocol={config['protocol']}"
#                 )
            
#             return True

#         except Exception as e:
#             if hasattr(self.main_app, "log_error"):
#                 self.main_app.log_error(f"[Config Error] Failed to apply config for {machine_name}: {e}")
#             return False

#     def _enable_communication_controls(self):
#         """Enable communication-related UI controls with modern feedback"""
#         self.connection_combo.configure(state="readonly")
#         self.tcp_status_label.configure(text="✓ Ready to Connect", 
#                                       fg=self.colors['status_success'])

#     def _disable_communication_controls(self):
#         """Disable communication-related UI controls with modern feedback"""
#         self.ip_address.configure(state='disabled')
#         self.tcp_port.configure(state='disabled')
#         self.connection_combo.configure(state="disabled")
        
#         # Reset UI values
#         self.ip_address.delete(0, tk.END)
#         self.ip_address.insert(0, "Select Machine First")
#         self.tcp_port.delete(0, tk.END)
#         self.tcp_port.insert(0, "N/A")
#         self.tcp_status_label.configure(text="⚠ Select Machine to Configure",
#                                       fg=self.colors['status_warning'])

#     def update_buffer_status(self):
#         """Update buffer status label with enhanced styling"""
#         buffer_count = len(self.data_buffer)
#         self.network_buffer_status.config(text=f"Buffer: {buffer_count} messages")
        
#         # Enable API button if there's data
#         if hasattr(self, 'network_send_api_btn') and buffer_count > 0:
#             self.network_send_api_btn.config(state='normal')

#     def send_network_data_to_api(self):
#         """Send buffered network data to API with modern feedback"""
#         if not self.data_buffer:
#             messagebox.showwarning("No Data", "No network data available to send")
#             return
        
#         endpoint = self.network_api_endpoint.get().strip()
#         if not endpoint:
#             messagebox.showerror("Invalid Endpoint", "Please enter a valid API endpoint")
#             return
        
#         # Prepare payload
#         payload = {
#             'source': 'network',
#             'connection_info': {
#                 'ip_address': self.ip_address.get(),
#                 'port': self.tcp_port.get(),
#                 'connection_type': self.connection_type.get(),
#                 'analyzer': self.analyzer_var.get()
#             },
#             'data': self.data_buffer.copy(),
#             'total_messages': len(self.data_buffer)
#         }
        
#         # Send to API using main app's method
#         success, response_data, error_message = self.main_app.send_api_request(endpoint, payload)
        
#         if success:
#             self.data_buffer.clear()
#             self.update_buffer_status()
            
#             processed_count = response_data.get('processed', 'N/A') if response_data else 'N/A'
#             messagebox.showinfo("Success", f"Network data sent successfully!\nMessages processed: {processed_count}")
#         else:
#             messagebox.showerror("API Error", error_message)

#     def clear_network_buffer(self):
#         """Clear network data buffer with enhanced logging"""
#         self.data_buffer.clear()
#         self.update_buffer_status()
#         self.main_app.log_info("[Network] 🗑 Data buffer cleared")

#     # Disconnect method for cleanup
#     def disconnect_network_connection(self):
#         """Cleanup network connections"""
#         try:
#             if self.tcp_connected:
#                 # Add cleanup logic here
#                 self.tcp_connected = False
#                 self.main_app.log_info("[Network] 🔌 Connection closed")
#         except Exception as e:
#             self.main_app.log_error(f"[Network] Error during disconnect: {e}")