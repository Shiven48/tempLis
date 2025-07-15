# import tkinter as tk
# from tkinter import ttk, messagebox, scrolledtext
# from datetime import datetime
# import threading
# import serial
# import socket
# import time
# import requests
# import re

# ENQ = b'\x05'
# ACK = b'\x06'
# NAK = b'\x15'
# EOT = b'\x04'
# STX = b'\x02'
# ETX = b'\x03'
# CR  = b'\r'
# LF  = b'\n'

# control_map = {
#     0x05: 'ENQ',
#     0x06: 'ACK',
#     0x15: 'NAK',
#     0x04: 'EOT',
#     0x02: 'STX',
#     0x03: 'ETX',
#     0x0D: 'CR',
#     0x0A: 'LF',
# }

# CONTROL_CHAR_TO_BYTE = {
#     'ENQ': ENQ,
#     'ACK': ACK,
#     'NAK': NAK,
#     'EOT': EOT,
#     'STX': STX,
#     'ETX': ETX,
#     'CR' : CR,
#     'LF' : LF
# }

# class MiddlewareGUI:

#     def __init__(self, root):
#         self.root = root
#         self.root.title("Analyzer Middleware")
#         self.root.geometry("900x700")
        
#         # Connection status variables
#         self.serial_connected = False
#         self.tcp_connected = False
#         self.serial_connection = None
#         self.tcp_connection = None
        
#         # Data aggregation variables
#         self.serial_data_buffer = []
#         self.network_data_buffer = []
#         self.data_received = False

#         self.net_host = 'localhost'
#         self.net_port = 15200
#         self.sock = None
        
#         # Create notebook for tabs
#         self.notebook = ttk.Notebook(root)
#         self.errors_frame = None
#         self.log_frame = None

#         # Create tabs
#         self.serial_tab = ttk.Frame(self.notebook)
#         self.network_tab = ttk.Frame(self.notebook)
#         self.logs_tab = ttk.Frame(self.notebook)
        
#         # Add tabs to notebook
#         self.notebook.add(self.serial_tab, text='Serial Mode')
#         self.notebook.add(self.network_tab, text='Network Mode')
#         # self.notebook.add(self.logs_tab, text='Logs')
        
#         self.notebook.pack(expand=1, fill='both', padx=10, pady=10)
        
#         # Setup all tabs
#         self.setup_serial_tab()
#         self.setup_network_tab()
#         # self.setup_logs_tab()
    
#         # Log initial startup
#         self.log_event("Analyzer Middleware started")

#     # Setup
#     def setup_serial_tab(self):
#         # Main container
#         main_frame = tk.Frame(self.serial_tab, bg='#f0f0f0')
#         main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

#         # --- Top Control Frame ---
#         top_frame = tk.Frame(main_frame, bg='#e6e6e6', relief=tk.RAISED, bd=2)
#         top_frame.pack(fill=tk.X, pady=(0, 10))

#         connection_frame = tk.Frame(top_frame, bg='#e6e6e6')
#         connection_frame.pack(pady=10)

#         # Port label
#         tk.Label(connection_frame, text="Port:", bg='#e6e6e6', font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
#         self.serial_port_var = tk.StringVar(value="COM2")
#         tk.Label(connection_frame, textvariable=self.serial_port_var, bg='#e6e6e6', font=('Arial', 10)).pack(side=tk.LEFT, padx=(5, 15))

#         # Baud Rate
#         tk.Label(connection_frame, text="Baud:", bg='#e6e6e6', font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
#         self.baud_var = tk.StringVar(value="9600")
#         baud_menu = tk.OptionMenu(connection_frame, self.baud_var, "9600", "19200", "38400", "57600", "115200")
#         baud_menu.configure(bg='white', font=('Arial', 9))
#         baud_menu.pack(side=tk.LEFT, padx=(5, 15))

#         # Connect Button
#         self.serial_connect_btn = tk.Button(connection_frame, 
#                                             text="Connect", 
#                                             command=self.connect_serial_tab,
#                                             bg='#4CAF50', 
#                                             fg='white', 
#                                             font=('Arial', 10, 'bold'), 
#                                             relief=tk.RAISED, 
#                                             bd=2, 
#                                             padx=15)
#         self.serial_connect_btn.pack(side=tk.LEFT, padx=5)

#         # Disconnect Button
#         self.serial_disconnect_btn = tk.Button(connection_frame, 
#                                                text="Disconnect", 
#                                                command=self.disconnect_serial_tab,
#                                                bg='#f44336', 
#                                                fg='white', 
#                                                font=('Arial', 10, 'bold'), 
#                                                relief=tk.RAISED, 
#                                                bd=2, 
#                                                padx=15)
#         self.serial_disconnect_btn.pack(side=tk.LEFT, padx=5)

#         # Connection Status
#         self.status_label = tk.Label(top_frame, text="Disconnected", bg='#e6e6e6', fg='red', font=('Arial', 10, 'bold'))
#         self.status_label.pack(side=tk.RIGHT, padx=10, pady=5)

#         # --- Middle Log Frames ---
#         middle_frame = tk.Frame(main_frame)
#         middle_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

#         # General Logs
#         self.logs_frame = tk.LabelFrame(middle_frame, text="General Logs", font=('Arial', 11, 'bold'), bg='#f0f0f0')
#         self.logs_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

#         self.log_text = scrolledtext.ScrolledText(self.logs_frame, width=40, height=25,
#             font=('Consolas', 9), bg='white', fg='black', wrap=tk.WORD, relief=tk.SUNKEN, bd=2)
#         self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

#         # Error Logs
#         self.errors_frame = tk.LabelFrame(middle_frame, text="Error Logs", font=('Arial', 11, 'bold'), bg='#f0f0f0')
#         self.errors_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

#         self.error_text = scrolledtext.ScrolledText(self.errors_frame, width=40, height=25,
#             font=('Consolas', 9), bg='#fff8f8', fg='#d32f2f', wrap=tk.WORD, relief=tk.SUNKEN, bd=2)
#         self.error_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

#         # --- Bottom Input + Controls ---
#         bottom_frame = tk.Frame(main_frame, bg='#e6e6e6', relief=tk.RAISED, bd=2)
#         bottom_frame.pack(fill=tk.X, pady=(0, 5))

#         # Message input
#         input_frame = tk.Frame(bottom_frame, bg='#e6e6e6')
#         input_frame.pack(pady=10)

#         tk.Label(input_frame, text="Message:", bg='#e6e6e6', font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=(0, 5))
#         self.input_entry = tk.Entry(input_frame, width=60, font=('Arial', 10), relief=tk.SUNKEN, bd=2)
#         self.input_entry.pack(side=tk.LEFT, padx=5)

#         self.send_btn = tk.Button(input_frame, text="Send", command=self.write_to_socket,
#             bg='#2196F3', fg='white', font=('Arial', 10, 'bold'), relief=tk.RAISED, bd=2, padx=15)
#         self.send_btn.pack(side=tk.LEFT, padx=5)

#         # ENQ Button
#         enq_frame = tk.Frame(bottom_frame, bg='#e6e6e6')
#         enq_frame.pack(pady=(0, 10))

#         self.enq_btn = tk.Button(enq_frame, text="Send ENQ", command=self.send_enq,
#             bg='#FF9800', fg='white', font=('Arial', 10, 'bold'), relief=tk.RAISED, bd=2, padx=20)
#         self.enq_btn.pack()

#         # Control buttons
#         control_frame = tk.Frame(bottom_frame, bg='#e6e6e6')
#         control_frame.pack(pady=(0, 10))

#         self.clear_logs_btn = tk.Button(control_frame, text="Clear Logs", command=self.clear_logs,
#             bg='#9E9E9E', fg='white', font=('Arial', 9), relief=tk.RAISED, bd=2, padx=10)
#         self.clear_logs_btn.pack(side=tk.LEFT, padx=5)

#         self.clear_errors_btn = tk.Button(control_frame, text="Clear Errors", command=self.clear_errors,
#             bg='#9E9E9E', fg='white', font=('Arial', 9), relief=tk.RAISED, bd=2, padx=10)
#         self.clear_errors_btn.pack(side=tk.LEFT, padx=5)

#         # TCP Target Entry
#         # tcp_frame = ttk.LabelFrame(main_frame, text="TCP Server Configuration", padding=10)
#         # tcp_frame.pack(fill='x', pady=(5, 10))

#         # ttk.Label(tcp_frame, text="Host:").grid(row=0, column=0, padx=5, pady=5, sticky='e')
#         # self.tcp_host_entry = ttk.Entry(tcp_frame, width=20)
#         # self.tcp_host_entry.grid(row=0, column=1, padx=5, pady=5)
#         # self.tcp_host_entry.insert(0, "127.0.0.1")

#         # ttk.Label(tcp_frame, text="Port:").grid(row=0, column=2, padx=5, pady=5, sticky='e')
#         # self.tcp_port_entry = ttk.Entry(tcp_frame, width=10)
#         # self.tcp_port_entry.grid(row=0, column=3, padx=5, pady=5)
#         # self.tcp_port_entry.insert(0, "15200")

#         # Keybindings + Tags
#         # self.input_entry.bind('<Return>', lambda event: self.send_text())
#         # self.log_text.tag_configure("timestamp", foreground="#1D1D1D", font=('Consolas', 8))
#         # self.log_text.tag_configure("sent", foreground="#0066CC", font=('Consolas', 9, 'bold'))
#         # self.log_text.tag_configure("received", foreground="#009900", font=('Consolas', 9, 'bold'))
#         # self.error_text.tag_configure("error", foreground="#d32f2f", font=('Consolas', 9, 'bold'))
#         # self.error_text.tag_configure("warning", foreground="#ff9800", font=('Consolas', 9, 'bold'))
#         # self.error_text.tag_configure("timestamp", foreground="#1D1D1D", font=('Consolas', 8))

#     def setup_network_tab(self):
#         # Main frame for network tab
#         main_frame = ttk.Frame(self.network_tab)
#         main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
#         # Connection settings frame
#         settings_frame = ttk.LabelFrame(main_frame, text="Network Connection Settings")
#         settings_frame.pack(fill='x', pady=(0, 10))
        
#         # IP Address setting
#         ttk.Label(settings_frame, text="IP Address:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
#         self.ip_address = ttk.Entry(settings_frame, width=20)
#         self.ip_address.grid(row=0, column=1, padx=5, pady=5)
#         self.ip_address.insert(0, "192.168.1.100")  # Default value
        
#         # Port setting
#         ttk.Label(settings_frame, text="Port:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
#         self.tcp_port = ttk.Entry(settings_frame, width=20)
#         self.tcp_port.grid(row=1, column=1, padx=5, pady=5)
#         self.tcp_port.insert(0, "2575")  # Default HL7 port
        
#         # Connection type
#         ttk.Label(settings_frame, text="Connection Type:").grid(row=2, column=0, sticky='w', padx=5, pady=5)
#         self.connection_type = ttk.Combobox(settings_frame, width=17, values=["TCP Client", "TCP Server"])
#         self.connection_type.grid(row=2, column=1, padx=5, pady=5)
#         self.connection_type.set("TCP Client")  # Default value
        
#         # Connection buttons
#         button_frame = ttk.Frame(settings_frame)
#         button_frame.grid(row=3, column=0, columnspan=4, pady=10)
        
#         self.tcp_connect_btn = ttk.Button(button_frame, text="Connect", command=self.handle_tcp_connection)
#         self.tcp_connect_btn.pack(side='left', padx=5)
        
#         self.tcp_disconnect_btn = ttk.Button(button_frame, text="Disconnect", command=self.disconnect_network_connection, state='disabled')
#         self.tcp_disconnect_btn.pack(side='left', padx=5)
        
#         # Status label
#         self.tcp_status = ttk.Label(button_frame, text="Disconnected", foreground='red')
#         self.tcp_status.pack(side='left', padx=10)
        
#         # API endpoint frame for network
#         api_frame_network = ttk.LabelFrame(main_frame, text="API Endpoint Configuration")
#         api_frame_network.pack(fill='x', pady=(0, 10))
        
#         ttk.Label(api_frame_network, text="API Endpoint:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
#         self.network_api_endpoint = ttk.Entry(api_frame_network, width=40)
#         self.network_api_endpoint.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
#         self.network_api_endpoint.insert(0, "http://localhost:8000/app/analyzer/parse")
        
#         # API send button
#         self.network_send_api_btn = ttk.Button(api_frame_network, text="Send to API", 
#                                              command=self.send_network_data_to_api, state='disabled')
#         self.network_send_api_btn.grid(row=0, column=2, padx=5, pady=5)
        
#         # Clear buffer button
#         self.network_clear_buffer_btn = ttk.Button(api_frame_network, text="Clear Buffer", 
#                                                  command=self.clear_network_buffer)
#         self.network_clear_buffer_btn.grid(row=1, column=0, padx=5, pady=5)
        
#         # Buffer status label
#         self.network_buffer_status = ttk.Label(api_frame_network, text="Buffer: 0 messages")
#         self.network_buffer_status.grid(row=1, column=1, sticky='w', padx=5, pady=5)
        
#         # Configure column weight
#         api_frame_network.columnconfigure(1, weight=1)
        
#         # Monitor frame
#         monitor_frame = ttk.LabelFrame(main_frame, text="Network Data Monitor (ASTM/HL7)")
#         monitor_frame.pack(fill='both', expand=True)
        
#         # Text widget with scrollbar
#         text_frame = ttk.Frame(monitor_frame)
#         text_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
#         self.network_monitor = tk.Text(text_frame, height=15, wrap='word')
#         network_scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=self.network_monitor.yview)
#         self.network_monitor.configure(yscrollcommand=network_scrollbar.set)
        
#         self.network_monitor.pack(side='left', fill='both', expand=True)
#         network_scrollbar.pack(side='right', fill='y')
        
#         # Clear button
#         clear_network_btn = ttk.Button(monitor_frame, text="Clear Monitor", command=lambda: self.network_monitor.delete(1.0, tk.END))
#         clear_network_btn.pack(pady=5)

#     # def setup_logs_tab(self):
#     #     # Main frame for logs tab
#     #     main_frame = ttk.Frame(self.logs_tab)
#     #     main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
#     #     # Logs frame
#     #     logs_frame = ttk.LabelFrame(main_frame, text="System Logs")
#     #     logs_frame.pack(fill='both', expand=True)
        
#     #     # Text widget with scrollbar
#     #     text_frame = ttk.Frame(logs_frame)
#     #     text_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
#     #     self.logs = tk.Text(text_frame, height=20, wrap='word')
#     #     logs_scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=self.logs.yview)
#     #     self.logs.configure(yscrollcommand=logs_scrollbar.set)
        
#     #     self.logs.pack(side='left', fill='both', expand=True)
#     #     logs_scrollbar.pack(side='right', fill='y')
        
#     #     # Control buttons
#     #     button_frame = ttk.Frame(logs_frame)
#     #     button_frame.pack(fill='x', pady=5)
        
#     #     ttk.Button(button_frame, text="Clear Logs", command=self.clear_logs).pack(side='left', padx=5)
#     #     ttk.Button(button_frame, text="Save Logs", command=self.save_logs).pack(side='left', padx=5)


#     # Connect serial and socket
#     def connect_serial_tab(self):
#         if not self.serial_connected:
#             if self.connectSerial():
#                 self.serial_connected = True
#                 self.status_label.config(text="Connected", foreground='green')
#                 self.serial_connect_btn.config(state='disabled')
#                 self.serial_disconnect_btn.config(state='normal')
#                 self.log_event(f"[Analyzer] Connected to {self.ser.port} at {self.ser.baudrate} baud")

#                 if self.connectSocket():
#                     self.reading = True
#                     self.read_thread = threading.Thread(target=self.read_from_socket)
#                     self.read_thread.daemon = True
#                     self.read_thread.start()
#                 else:
#                     self.log_error("[Error] Failed to connect to socket", "error")
#             else:
#                 self.log_error("[Error]: Failed to connect to serial", "error")

#     def connectSerial(self) -> bool:
#         try:
#             serial_port = str(self.serial_port_var.get())
#             serial_baud = int(self.baud_var.get())
        
#             self.log_event(f"[Analyzer] Attempting to connect to Serial Port {serial_port} at {serial_baud} baud...")
#             self.ser = serial.Serial(serial_port, serial_baud, timeout=1)

#             if not self.ser.is_open:
#                 self.log_error("[Error] Failed to connect serial", "error")
#                 return False

#             return True
#         except serial.SerialException as e:
#             self.log_error(f"[Error] {e}", "error")


#     def disconnect_serial_tab(self):
#         pass

#     def connectSocket(self) -> bool:
#         try:
#             sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#             sock.setblocking(True)
#             sock.connect((self.net_host,self.net_port))
#             self.log_event(f"Successfully connected to {self.net_host}:{self.net_port}")
#             self.sock = sock
#             return True
#         except socket.gaierror as e:
#             self.log_error(f"Address-related error connecting to {self.net_host}:{self.net_port} - {e}")
#         except socket.timeout as e:
#             self.log_error(f"Connection to {self.net_host}:{self.net_port} timed out - {e}")
#         except ConnectionRefusedError as e:
#             self.log_error(f"Connection to {self.net_host}:{self.net_port} refused - {e}")
#         except socket.error as e:
#             self.log_error(f"Socket error while connecting to {self.net_host}:{self.net_port} - {e}")
#         except Exception as e:
#             self.log_error(f"Unexpected error during socket connection: {e}")

#     def handle_tcp_connection(self):
#         """Handle TCP connection"""
#         if not self.tcp_connected:
#             try:
#                 ip = self.ip_address.get()
#                 port = int(self.tcp_port.get())
#                 conn_type = self.connection_type.get()
                
#                 self.log_event(f"Attempting to connect to TCP {ip}:{port} as {conn_type}...")
                
#                 # Create socket
#                 self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#                 self.tcp_socket.settimeout(5)
                
#                 if conn_type == "TCP Client":
#                     self.tcp_socket.connect((ip, port))
#                     self.tcp_connection = self.tcp_socket
#                 else:  # TCP Server
#                     self.tcp_socket.bind((ip, port))
#                     self.tcp_socket.listen(1)
#                     self.log_event(f"Waiting for connection on {ip}:{port}...")
#                     self.tcp_connection, addr = self.tcp_socket.accept()
#                     self.log_event(f"Client connected from {addr}")
                
#                 self.tcp_connected = True
#                 self.tcp_status.config(text="Connected", foreground='green')
#                 self.tcp_connect_btn.config(state='disabled')
#                 self.tcp_disconnect_btn.config(state='normal')
                
#                 self.log_event(f"Successfully connected to TCP {ip}:{port}")
                
#                 # Start reading thread
#                 self.tcp_thread = threading.Thread(target=self.read_tcp_data, daemon=True)
#                 self.tcp_thread.start()
                
#             except Exception as e:
#                 self.log_event(f"TCP connection failed: {str(e)}")
#                 messagebox.showerror("Connection Error", f"Failed to connect via TCP: {str(e)}")


#     def connect_network_tab(self):
#         pass

#     def disconnect_disconnect_tab(self):
#         pass


#     # Disconnect serial and socket
#     def disconnect(self):
#         """Handle application closing"""
#         if self.serial_connected:
#             self.disconnect_serial_proxy()
#         if self.tcp_connected:
#             self.disconnect_network_connection()
#         self.root.destroy()

#     def disconnect_serial_setup(self):
#         self.reading = False
#         if self.ser and self.ser.is_open:
#             self.ser.close()
#             self.ser.is_open = False

#             self.status_label.config(text="Disconnected", foreground='red')
#             self.serial_connect_btn.config(state='normal')
#             self.serial_disconnect_btn.config(state='disabled')
            
#             # Disable API button when disconnected
#             # self.serial_send_api_btn.config(state='disabled')
            
#             self.log_event("Closing serial port...")
#             self.log_event("[Analyzer] Serial port disconnected")
    
#     def disconnect_network_connection(self):
#         """Disconnect from TCP"""
#         if self.tcp_connected:
#             self.tcp_connected = False
#             if self.tcp_connection:
#                 self.tcp_connection.close()
#             if hasattr(self, 'tcp_socket'):
#                 self.tcp_socket.close()
            
#             self.tcp_status.config(text="Disconnected", foreground='red')
#             self.tcp_connect_btn.config(state='normal')
#             self.tcp_disconnect_btn.config(state='disabled')
            
#             # Disable API button when disconnected
#             self.network_send_api_btn.config(state='disabled')
            
#             self.log_event("TCP connection disconnected")

#     # def disconnect_serial(self):
#     #     """Disconnect from serial port"""
#     #     if self.serial_connected and self.serial_connection:
#     #         self.serial_connected = False
#     #         self.serial_connection.close()
#     #         self.serial_connection = None
            
#     #         self.serial_status.config(text="Disconnected", foreground='red')
#     #         self.serial_connect_btn.config(state='normal')
#     #         self.serial_disconnect_btn.config(state='disabled')
            
#     #         # Disable API button when disconnected
#     #         self.serial_send_api_btn.config(state='disabled')
            
#     #         self.log_event("Serial connection disconnected")


#     # IO serial and socket
#     def read_serial_data(self):
#         """Read data from serial connection in a separate thread"""
#         while self.serial_connected and self.serial_connection:
#             try:
#                 if self.serial_connection.in_waiting > 0:
#                     data = self.serial_connection.readline().decode('utf-8', errors='ignore')
#                     if data:
#                         # Add to buffer
#                         self.serial_data_buffer.append({
#                             'timestamp': datetime.now().isoformat(),
#                             'data': data.strip()
#                         })
                        
#                         # Update GUI in main thread
#                         self.root.after(0, lambda: self.update_serial_monitor(data))
#                         # Enable API button and update buffer status
#                         self.root.after(0, lambda: self.update_serial_api_status())
#                 time.sleep(0.1)
#             except Exception as e:
#                 self.root.after(0, lambda: self.log_event(f"Serial read error: {str(e)}"))
#                 break

#     def write_to_socket(self):
#         user_input = self.input_entry.get()
#         try:
#             parsed_msg = self.parse_input_with_control_chars(user_input)
#             print("Parsed message bytes:", parsed_msg, repr(parsed_msg))
#             self.sock.sendall(parsed_msg)
#             pretty = self.preetyLogger(parsed_msg)
#             self.log_event(pretty, "send")
#         except (ConnectionAbortedError, BrokenPipeError):
#             self.log_error("[Error] Socket connection aborted. Please reconnect.", "error")
#         except Exception as e:
#             self.log_error(f"[Unexpected Error] {e}", "error")

#     def read_from_socket(self):
#         while self.reading and self.sock:
#             try:
#                 self.sock.settimeout(1.0)
#                 data = self.sock.recv(4096)
            
#                 if data:
#                     # decoded = data.decode(errors='ignore', encoding='latin-1').strip()
#                     for b in data:
#                         if b in control_map:
#                             self.log_event(f"[CONTROL] - {control_map[b]}", "recv")
#                         else:
#                             self.log_event(f"[RECEIVED BYTE] - {chr(b)}", "recv")
#                 else:
#                     self.log_event("[INFO] Socket connection closed by remote", "info")
#                     break
                
#             except socket.timeout:
#                 continue
#             except socket.error as e:
#                 self.log_error(f"[Socket Error] {e}", "error")
#                 break
#             except Exception as e:
#                 self.log_error(f"[Unexpected Error] {e}", "error")
#                 break
            
#             time.sleep(0.3)

#     def read_tcp_data(self):
#         """Read data from TCP connection in a separate thread"""
#         while self.tcp_connected and self.tcp_connection:
#             try:
#                 data = self.tcp_connection.recv(1024).decode('utf-8', errors='ignore')
#                 if data:
#                     # Add to buffer
#                     self.network_data_buffer.append({
#                         'timestamp': datetime.now().isoformat(),
#                         'data': data.strip()
#                     })
                    
#                     # Update GUI in main thread
#                     self.root.after(0, lambda: self.update_network_monitor(data))
#                     # Enable API button and update buffer status
#                     self.root.after(0, lambda: self.update_network_api_status())
#                 else:
#                     # Connection closed by remote
#                     break
#                 time.sleep(0.1)
#             except Exception as e:
#                 self.root.after(0, lambda: self.log_event(f"TCP read error: {str(e)}"))
#                 break
    

#     # Logging
#     def log_event(self, message, msg_type="info"):
#         """
#         Add a message to the general logs window
#         msg_type: 'info', 'sent', 'received', 'timestamp'
#         """
#         timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
#         self.log_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
#         self.log_text.insert(tk.END, f"{message}\n", msg_type)
        
#         # Add to logs tab
#         # self.logs.insert(tk.END, log_message)
#         # self.logs.see(tk.END)
#         self.log_text.see(tk.END)

#     def log_error(self, error_message, error_type="error"):
#         """
#         Add an error message to the error logs window
#         error_type: 'error', 'warning'
#         """
#         import datetime
#         timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        
#         self.error_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
#         self.error_text.insert(tk.END, f"{error_message}\n", error_type)
#         self.error_text.see(tk.END)

#     def clear_logs(self):
#         """Clear all content from the general logs window"""
#         self.log_text.delete(1.0, tk.END)
#         self.log_text.insert(tk.END, "--- General logs cleared ---\n", "info")

#     def clear_errors(self):
#         """Clear all content from the error logs window"""
#         self.error_text.delete(1.0, tk.END)
#         self.error_text.insert(tk.END, "--- Error logs cleared ---\n", "info")

#     def save_logs(self):
#         """Save logs to file"""
#         try:
#             from tkinter import filedialog
#             filename = filedialog.asksaveasfilename(
#                 defaultextension=".txt",
#                 filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
#             )
#             if filename:
#                 with open(filename, 'w') as f:
#                     f.write(self.logs.get(1.0, tk.END))
#                 self.log_event(f"Logs saved to {filename}")
#                 messagebox.showinfo("Success", f"Logs saved to {filename}")
#         except Exception as e:
#             self.log_event(f"Error saving logs: {str(e)}")
#             messagebox.showerror("Error", f"Failed to save logs: {str(e)}")
       

#     # Serial tab related operations
#     def update_serial_monitor(self, data):
#         """Update serial monitor with new data"""
#         timestamp = datetime.now().strftime("[%H:%M:%S]")
#         formatted_data = f"{timestamp} {data}"
#         self.serial_monitor.insert(tk.END, formatted_data)
#         self.serial_monitor.see(tk.END)

#     def update_serial_api_status(self):
#         """Update serial API button status and buffer count"""
#         buffer_count = len(self.serial_data_buffer)
#         self.serial_buffer_status.config(text=f"Buffer: {buffer_count} messages")
        
#         # Enable API button if there's data and connection is active
#         if buffer_count > 0 and self.serial_connected:
#             self.serial_send_api_btn.config(state='normal')

#     def send_serial_data_to_api(self):
#         """Send aggregated serial data to API endpoint"""
#         if not self.serial_data_buffer:
#             messagebox.showwarning("No Data", "No ASTM data available to send")
#             return
        
#         endpoint = self.serial_api_endpoint.get().strip()
#         if not endpoint:
#             messagebox.showerror("Invalid Endpoint", "Please enter a valid API endpoint")
#             return
        
#         try:
#             # Prepare payload
#             payload = {
#                 'source': 'serial',
#                 'connection_info': {
#                     'port': self.serial_port.get(),
#                     'baud_rate': self.baud_rate.get(),
#                     'data_bits': self.data_bits.get(),
#                     'parity': self.parity.get(),
#                     'stop_bits': self.stop_bits.get()
#                 },
#                 'data': self.serial_data_buffer.copy(),
#                 'total_messages': len(self.serial_data_buffer)
#             }
            
#             self.log_event(f"Sending {len(self.serial_data_buffer)} ASTM messages to {endpoint}")
            
#             # Send POST request
#             response = requests.post(
#                 endpoint,
#                 json=payload,
#                 headers={'Content-Type': 'application/json'},
#                 timeout=30
#             )
            
#             if response.status_code == 200:
#                 self.log_event(f"Successfully sent data to API. Response: {response.status_code}")
                
#                 # Clear buffer after successful send
#                 self.serial_data_buffer.clear()
#                 self.update_serial_api_status()
                
#                 # Show success message with response
#                 try:
#                     response_data = response.json()
#                     messagebox.showinfo("Success", f"Data sent successfully!\nMessages processed: {response_data.get('processed', 'N/A')}")
#                 except:
#                     messagebox.showinfo("Success", f"Data sent successfully!\nResponse: {response.status_code}")
                    
#             else:
#                 self.log_event(f"API request failed with status {response.status_code}: {response.text}")
#                 messagebox.showerror("API Error", f"Failed to send data. Status: {response.status_code}")
                
#         except requests.exceptions.Timeout:
#             self.log_event("API request timed out")
#             messagebox.showerror("Timeout Error", "Request timed out. Please check the endpoint URL and try again.")
#         except requests.exceptions.ConnectionError:
#             self.log_event("Failed to connect to API endpoint")
#             messagebox.showerror("Connection Error", "Failed to connect to API endpoint. Please check the URL and network connection.")
#         except Exception as e:
#             self.log_event(f"Error saving logs: {str(e)}")
#             messagebox.showerror("Error", f"Failed to save logs: {str(e)}")

#     def clear_serial_buffer(self):
#         """Clear the serial data buffer"""
#         self.serial_data_buffer.clear()
#         self.update_serial_api_status()
#         self.log_event("Serial data buffer cleared")


#     # Network tab related operations
#     def update_network_monitor(self, data):
#         """Update network monitor with new data"""
#         timestamp = datetime.now().strftime("[%H:%M:%S]")
#         formatted_data = f"{timestamp} {data}\n"
#         self.network_monitor.insert(tk.END, formatted_data)
#         self.network_monitor.see(tk.END)

#     def update_network_api_status(self):
#         """Update network API button status and buffer count"""
#         buffer_count = len(self.network_data_buffer)
#         self.network_buffer_status.config(text=f"Buffer: {buffer_count} messages")
        
#         # Enable API button if there's data and connection is active
#         if buffer_count > 0 and self.tcp_connected:
#             self.network_send_api_btn.config(state='normal')

#     def send_network_data_to_api(self):
#         """Send aggregated network data to API endpoint"""
#         if not self.network_data_buffer:
#             messagebox.showwarning("No Data", "No ASTM data available to send")
#             return
        
#         endpoint = self.network_api_endpoint.get().strip()
#         if not endpoint:
#             messagebox.showerror("Invalid Endpoint", "Please enter a valid API endpoint")
#             return
        
#         try:
#             # Prepare payload
#             payload = {
#                 'source': 'network',
#                 'connection_info': {
#                     'ip_address': self.ip_address.get(),
#                     'port': self.tcp_port.get(),
#                     'connection_type': self.connection_type.get()
#                 },
#                 'data': self.network_data_buffer.copy(),
#                 'total_messages': len(self.network_data_buffer)
#             }
            
#             self.log_event(f"Sending {len(self.network_data_buffer)} ASTM messages to {endpoint}")
            
#             # Send POST request
#             response = requests.post(
#                 endpoint,
#                 json=payload,
#                 headers={'Content-Type': 'application/json'},
#                 timeout=30
#             )
            
#             if response.status_code == 200:
#                 self.log_event(f"Successfully sent data to API. Response: {response.status_code}")
                
#                 # Clear buffer after successful send
#                 self.network_data_buffer.clear()
#                 self.update_network_api_status()
                
#                 # Show success message with response
#                 try:
#                     response_data = response.json()
#                     messagebox.showinfo("Success", f"Data sent successfully!\nMessages processed: {response_data.get('processed', 'N/A')}")
#                 except:
#                     messagebox.showinfo("Success", f"Data sent successfully!\nResponse: {response.status_code}")
                    
#             else:
#                 self.log_event(f"API request failed with status {response.status_code}: {response.text}")
#                 messagebox.showerror("API Error", f"Failed to send data. Status: {response.status_code}")
                
#         except requests.exceptions.Timeout:
#             self.log_event("API request timed out")
#             messagebox.showerror("Timeout Error", "Request timed out. Please check the endpoint URL and try again.")
#         except requests.exceptions.ConnectionError:
#             self.log_event("Failed to connect to API endpoint")
#             messagebox.showerror("Connection Error", "Failed to connect to API endpoint. Please check the URL and network connection.")
#         except Exception as e:
#             self.log_event(f"Error sending data to API: {str(e)}")
#             messagebox.showerror("Error", f"Failed to send data to API: {str(e)}")

#     def clear_network_buffer(self):
#         """Clear the network data buffer"""
#         self.network_data_buffer.clear()
#         self.update_network_api_status()
#         self.log_event("Network data buffer cleared")


#     # utils
#     def parse_input_with_control_chars(self, input_str: str) -> bytes:
#         """
#         Converts human-friendly input like "[STX]data[ETX]" into proper ASTM bytes.
#         """
#         result = bytearray()
    
#         # Replace known escape sequences manually
#         input_str = input_str.replace('\\r', '\r').replace('\\n', '\n')
        
#         # Find all parts like [STX], data, [ETX]
#         tokens = re.split(r'(\[[A-Z]+\])', input_str)
    
#         for token in tokens:
#             match = re.match(r'\[([A-Z]+)\]', token)
#             if match:
#                 ctrl = match.group(1)
#                 if ctrl in CONTROL_CHAR_TO_BYTE:
#                     result.extend(CONTROL_CHAR_TO_BYTE[ctrl])
#             else:
#                 result.extend(token.encode('latin-1'))
        
#         return bytes(result)
    
#     def preetyLogger(self, bdata: bytes):
#         output_lines = []
#         buffer = []
#         in_astm_block = False

#         for b in bdata:
#             if b in control_map:
#                 label = control_map[b]

#                 if label == 'STX':
#                     # Start capturing ASTM block
#                     in_astm_block = True
#                     buffer.append(f"[{label}]")
#                 elif label == 'ETX':
#                     buffer.append(f"[{label}]")
#                     in_astm_block = False
#                 else:
#                     # Flush current ASTM block if exists
#                     if buffer:
#                         output_lines.append(''.join(buffer))
#                         buffer = []
#                     output_lines.append(f" - [{label}]")
#             elif b == 13:  # \r (CR)
#                 buffer.append("[CR]")
#             elif b == 10:  # \n (LF)
#                 buffer.append("[LF]")
#             else:
#                 try:
#                     buffer.append(chr(b))
#                 except:
#                     buffer.append(f"[0x{b:02X}]")  # fallback for unknown byte

#         if buffer:
#             output_lines.append(''.join(buffer))

#         return "\n".join(output_lines)
    
#     def buffer_to_lines(self, buffer):
#         try:
#             return bytes(buffer).decode('latin-1', errors='ignore').replace('\r', '')
#         except Exception:
#             return repr(buffer)

#     def send_enq(self):
#         if self.ser and self.ser.is_open:
#             self.sock.sendall(ENQ)
#             b = 0x05
#             self.log_event(f"[Sent] {control_map[b]}", "send")

# if __name__ == "__main__":
#     root = tk.Tk()
#     app = MiddlewareGUI(root)
    
#     root.protocol("WM_DELETE_WINDOW", app.disconnect)
    
#     root.mainloop()

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