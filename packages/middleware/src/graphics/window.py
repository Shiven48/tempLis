import tkinter as tk
from tkinter import Tk, ttk
from datetime import datetime
import queue

from graphics.logs.log_manager import LoggingManager
from graphics.serial_tab import SerialTab
from graphics.network_tab import NetworkTab
from graphics.logs.logs_tab import InfoLogTab, ErrorLogTab

from erba.constants import host, port
from erba.models import AnalyzerConfig

try:
    import erba as mw_engine
    MIDDLEWARE_AVAILABLE = True
except Exception as e:
    print(f"Warning: Middleware engine not available: {e}")
    import traceback
    traceback.print_exc()
    mw_engine = None
    MIDDLEWARE_AVAILABLE = False

class MiddlewareGUI:

    def __init__(self, root:Tk):
        self.root = root
        self.root.title(string="Analyzer Middleware")
        self.root.geometry(newGeometry="1200x900")
        self.root.configure(bg="#f0f0f0")
        # self.root.configure(bg="#282828")

        # Middleware state variables
        self._current_analyzer = None
        self._middleware_status = "Not Initialized"
        self._server_ready = False
        self._middleware_thread = None
        self._engine_running = False
        
        # Message queue for thread-safe GUI updates
        self.message_queue = queue.Queue()
        
        # Create main container
        main_container = ttk.Frame(root)
        main_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create status bar first
        self.create_status_bar(main_container)
        
        # Create notebook for tabs
        self.logging_manager = LoggingManager()
        self.notebook:ttk.Notebook = ttk.Notebook(main_container)
        
        # Create tab instances
        self.network_tab = NetworkTab(self.notebook, self)
        self.serial_tab = SerialTab(self.notebook, self)
        self.info_logs_tab = InfoLogTab(self.notebook, self)
        self.error_logs_tab = ErrorLogTab(self.notebook, self)
        
        # Add tabs to notebook
        self.notebook.add(self.network_tab.frame, text='Network Communication')
        self.notebook.add(self.serial_tab.frame, text='Serial Communication')
        self.notebook.add(self.info_logs_tab.frame, text='Info logs')
        self.notebook.add(self.error_logs_tab.frame, text='Error logs')
        # self.notebook.pack(expand=True, fill='both', pady=(0, 10))
        self.notebook.pack(expand=True, fill='both')

        self.machine_role = "LIS"

        # Start message queue processor
        self.process_message_queue()
        
        # Log initial startup
        self.log_info("=== ENGINE STARTED ===")
        if MIDDLEWARE_AVAILABLE:
            self.log_info("[Window] Middleware engine available")
        else:
            self.log_info("[Window] Middleware engine not available - limited functionality")
        
        self.log_info("[Window] Ready for analyzer selection...")

    def create_status_bar(self, parent):
        """Create comprehensive status bar"""
        status_frame = ttk.LabelFrame(parent, text="System Status", padding="5")
        # status_frame.pack(side='bottom', fill='x', pady=(10, 0))
        status_frame.pack(side='bottom', fill='x')

        # Create grid layout for status items
        status_grid = ttk.Frame(status_frame)
        status_grid.pack(fill='x')
        
        # Row 1: Middleware and Analyzer Status
        row1 = ttk.Frame(status_grid)
        row1.pack(fill='x', pady=2)
        
        ttk.Label(row1, text="Middleware Status:", font=('Arial', 9, 'bold')).pack(side='left')
        self.middleware_status_label = ttk.Label(row1, text=self._middleware_status, foreground='red')
        self.middleware_status_label.pack(side='left', padx=(5, 20))
        
        ttk.Label(row1, text="Current Analyzer:", font=('Arial', 9, 'bold')).pack(side='left')
        self.current_analyzer_label = ttk.Label(row1, text="None Selected", foreground='gray')
        self.current_analyzer_label.pack(side='left', padx=(5, 20))
        
        ttk.Label(row1, text="Server Status:", font=('Arial', 9, 'bold')).pack(side='left')
        self.server_status_label = ttk.Label(row1, text="Stopped", foreground='red')
        self.server_status_label.pack(side='left', padx=(5, 20))
        
        # Row 2: Control Buttons
        row2 = ttk.Frame(status_grid)
        engine_controls = ttk.Frame(row2)
        engine_controls.pack(side='right', padx=10)
        row2.pack(fill='x', pady=5)

        self.start_engine_btn = ttk.Button(
            engine_controls, 
            text="Start Engine", 
            command=self.start_middleware_engine
        )
        self.start_engine_btn.pack(side='left', padx=2)
        self.start_engine_btn.configure(state=tk.DISABLED)

        
        self.stop_engine_btn = ttk.Button(
            engine_controls, 
            text="Stop Engine", 
            command=self.stop_middleware_engine
        )
        self.stop_engine_btn.pack(side='left', padx=2)
        self.stop_engine_btn.configure(state=tk.DISABLED)
        
        # Test buttons for development
        self.clear_all_logs_btn = ttk.Button(row2, text="Clear All logs", command=self.clear_all_logs)
        self.clear_all_logs_btn.pack(side='left', padx=5)
        
        # Row 3: Quick Stats
        row3 = ttk.Frame(status_grid)
        row3.pack(fill='x', pady=2)
        
        self.processed_messages_label = ttk.Label(row3, text="Messages Processed: 0")
        self.processed_messages_label.pack(side='left', padx=(0, 20))
        
        self.api_status_label = ttk.Label(row3, text="API: Not Connected")
        self.api_status_label.pack(side='left', padx=(0, 20))
        
        self.time_label = ttk.Label(row3, text="")
        self.time_label.pack(side='right')
        self.update_time()
        
    def update_time(self):
        """Update current time display"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=current_time)
        self.root.after(1000, self.update_time)
    
    # logs callbacks
    def log_info(self, message: str):
        """Public, thread-safe method to log a general info message."""
        self.message_queue.put(('info', {'message': message}, None))

    def log_error(self, message: str):
        """Public, thread-safe method to log a global error message."""
        self.message_queue.put(('error', {'message': message}, self.machine_role))

    def log_network_data(self, message: str, tag: str = 'data_in'):
        """Public, thread-safe method to log data to the network tab's window."""
        self.message_queue.put(('network_data', {'message': message, 'tag': tag}, None))

    def log_serial_data(self, message: str, tag: str = 'data_in'):
        """Public, thread-safe method to log data to the serial tab's window."""
        self.message_queue.put(('serial_data', {'message': message, 'tag': tag}, None))

    def log_middleware_ack_data(self, message:str, tag: str = 'data_out'):
        """Public, thread-safe method to log middleware's response to tab's window."""
        self.message_queue.put(('middleware_ack_data', {'message': message, 'tag': tag}, None))

    def log_middleware_nack_data(self, message:str, tag: str = 'error'):
        self.message_queue.put(('middleware_nack_data', {'message': message, 'tag': tag}, None))

    def process_message_queue(self):
        """Processes messages from worker threads and dispatches them to the LoggingManager."""
        try:
            while True:
                msg_type, data, machine_role = self.message_queue.get_nowait()
                
                if msg_type == 'info':
                    self.logging_manager.info(data['message'], machine_role)
                elif msg_type == 'error':
                    self.logging_manager.error(data['message'], machine_role)
                elif msg_type == 'network_data':
                    self.logging_manager.network_data(data['message'], data['tag'], machine_role)
                elif msg_type == 'serial_data':
                    self.logging_manager.serial_data(data['message'], data['tag'], machine_role)
                elif msg_type == 'middleware_ack_data':
                    self.logging_manager.middleware_ack_data(data['message'], data['tag'], machine_role)
                elif msg_type == 'middleware_nack_data':
                    self.logging_manager.middleware_nack_data(data['message'], data['tag'], machine_role)                
                elif msg_type == "status_update":
                    self._update_status_immediate(data)
                    
        except queue.Empty:
            pass
        
        self.root.after(100, self.process_message_queue)

    def clear_all_logs(self):
        """Clears all logs by delegating to the LoggingManager."""
        self.logging_manager.clear_all()
        self.log_info("All log displays have been cleared.")

    def _update_status_immediate(self, status_data):
        """Immediately update status from thread-safe queue"""
        if "server_running" in status_data:
            if status_data["server_running"]:
                self.server_status_label.config(text="Running", foreground='green')
        
        if "server_error" in status_data:
            self.server_status_label.config(text="Error", foreground='red')

    # Init trigger for analyzer change
    def on_analyzer_changed(self, name: str):
        """Enhanced analyzer change handler with engine integration"""
        if name == getattr(self, "_current_analyzer", None):
            return
            
        self._current_analyzer = name
        self.current_analyzer_label.config(text=name, foreground='blue')
        
        self.log_info(f"{'='*3} ANALYZER SELECTION: {name} {'='*3}")
        
        if not MIDDLEWARE_AVAILABLE:
            self.log_error("Middleware engine not available - running in basic mode")
            self.log_info("Note: Full workflow requires middleware engine")
            return
        
        try:
            # === STEP 1-3: Initialize analyzer in engine ===
            self.log_info(f"[WINDOW] Analyzer '{name}' selected from dropdown")
            self.log_info("[WINDOW] Loading YAML configuration...")
            
            # Configure engine
            config:AnalyzerConfig = mw_engine.engine.select_analyzer(name)
            mw_engine.engine.set_analyzer_ready(name)
            
            self.log_info(f"[WINDOW] Loaded config for {config.device} ({config.protocol})")
            self.log_info("[WINDOW] Analyzer marked as ready in shared state")
            
            # Update status (updated when the analyzer is selected)
            self._middleware_status = "Ready"
            self.middleware_status_label.config(text=self._middleware_status, foreground='green')
            self.start_engine_btn.config(state=tk.ACTIVE)
            self.stop_engine_btn.config(state=tk.DISABLED)
            self.network_tab.tcp_status_label.config(text='Click "Start Engine" to connect to the server')

        except Exception as e:
            self.log_error(f"Failed to initialize analyzer: {e}")
            self._middleware_status = "Error"
            self.middleware_status_label.config(text=self._middleware_status, foreground='red')

    def start_middleware_engine(self):
        """Start the middleware engine server"""
        if not MIDDLEWARE_AVAILABLE:
            self.log_error("[Engine] Middleware engine not available")
            return
        
        if self._engine_running:
            self.log_info("[Engine] Engine already running")
            return
            
        if not self._current_analyzer:
            self.log_error("[Engine] Please select an analyzer first")
            return
        
        try:
            self.log_info("[WINDOW] Starting middleware server...")
            self.log_info("[WINDOW] Initializing HL7 MLLP server...")
            
            # Start engine server
            mw_engine.engine.start_server_background(
                host=host,
                port=port,
                gui_log=self.log_info,
                error_log=self.log_error,
                network_log=self.log_network_data,
                serial_log=self.log_serial_data,
                middleware_ack_log=self.log_middleware_ack_data,
                middleware_nack_log=self.log_middleware_nack_data
            )
            
            self._engine_running = True
            self.server_status_label.config(text="Engine Running", foreground='green')
            self.start_engine_btn.config(state=tk.DISABLED)
            self.stop_engine_btn.config(state=tk.ACTIVE)
            self.network_tab.tcp_status_label.config(
                text='Server Started...', 
                foreground="green"
            )


            self.log_info("[WINDOW] HL7 MLLP server started successfully")
            self.log_info("[WINDOW] Server listening on 127.0.0.1:15200")
            self.log_info("=== MIDDLEWARE ENGINE STATUS ===")
            self.log_info("Waiting for analyzer connections...")
            
        except Exception as e:
            self.log_error(f"[Engine] Failed to start: {e}")
            self._engine_running = False

    def stop_middleware_engine(self):
        """Stop the middleware engine"""
        if not self._engine_running:
            return
            
        try:
            if MIDDLEWARE_AVAILABLE:
                mw_engine.engine.stop_server_background()
                
            self._engine_running = False
            self.server_status_label.config(text="Engine Stopped", foreground='red')
            self.start_engine_btn.config(state=tk.ACTIVE)
            self.stop_engine_btn.config(state=tk.DISABLED)
            self.network_tab.tcp_status_label.config(
                text='Server Stopped', 
                foreground="red"
            )
            self.log_info("[Engine] Middleware engine stopped")
            
        except Exception as e:
            self.log_error(f"[Engine] Error stopping: {e}")

    # Callback to remove every window
    def disconnect(self):
        """Handle application closing"""
        try:
            # Stop middleware server
            self.stop_middleware_server()
            
            # Disconnect serial tab
            if hasattr(self, 'serial_tab'):
                self.serial_tab.disconnect()
            
            # Disconnect network tab
            if hasattr(self, 'network_tab'):
                self.network_tab.disconnect_network_connection()
                
        except Exception as e:
            print(f"Error during disconnect: {e}")
        finally:
            self.root.destroy()

if __name__ == "__main__":
    root:Tk = tk.Tk()
    app:MiddlewareGUI = MiddlewareGUI(root)
    
    root.protocol("WM_DELETE_WINDOW", app.disconnect)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        app.disconnect()