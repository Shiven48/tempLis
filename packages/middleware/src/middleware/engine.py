import asyncio
import datetime
import threading
import time
from typing import Optional, Callable
from constants import ERBA_YAML_PATH
from hl7 import Message
from hl7.mllp import start_hl7_server, HL7StreamReader, HL7StreamWriter

from middleware.config_loader import ConfigLoader
from middleware.logger import GuiLoggerRegistryInstance, register_loggers, logger
from middleware.parser import HL7Parser
from middleware.validator import DataValidator
from middleware.models import AnalyzerConfig, ErbaMessage
from middleware.api import APIService, close_api_service, get_api_service

class DataHandler:
    def __init__(self, config: AnalyzerConfig):
        self.config = config
        self.validator = DataValidator(self.config)
        self.yaml_path = ERBA_YAML_PATH
        self.parser = HL7Parser(self.yaml_path)

    def process_data(self, raw_data: str) -> Optional[ErbaMessage]:
        """Process raw data through the pipeline with predictable returns and logging"""
    
        if not raw_data or not raw_data.strip():
            logger.error("Empty or null raw_data provided")
            return None
    
        try:
            logger.info("Starting data parsing...")
            parsed_data = self.parser.parse_with_config(raw_data)
            logger.info(f"Parsing completed. Parsed_data keys: {list(parsed_data.keys()) if parsed_data else 'None'}")
            
            if not parsed_data:
                logger.error("Parsing returned None or empty data. Checking for errors...")
                return None
        
            parsing_errors = parsed_data.get('parsing_errors', [])
            if parsing_errors:
                logger.error(f"Found {len(parsing_errors)} parsing errors:")
                for error in parsing_errors:
                    logger.error(f"{error}")
                return None
                
            logger.info("Starting validation and object creation...")
            validated_message:ErbaMessage | None = self.validator.validate_and_create_objects(parsed_data)
        
            # Check validation result
            if validated_message:
                logger.info("Validation successful. Message object created successfully.")
                logger.debug(f"Validated message type: {type(validated_message).__name__}")
                return validated_message
            else:
                logger.warning("Validation failed. No validated message object created.")
                return None
            
        except AttributeError as ae:
            logger.error(f"AttributeError during process_data: {str(ae)} - Check if parser/validator are properly initialized")
            return None
        
        except ValueError as ve:
            logger.error(f"ValueError during process_data: {str(ve)} - Invalid data format or values")
            return None
            
        except Exception as e:
            logger.error(f"Unexpected exception during process_data: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            return None
        
class MiddlewareEngine:
    """
    Production middleware engine with HL7 MLLP server integration
    """
    
    def __init__(self):
        self.current_analyzer = None
        self.server = None
        self.server_task = None
        self.is_running = False
        self.analyzer_ready = False
        self.handler = None
        self.loop = None
        self.server_thread = None
        self.yaml_path = ERBA_YAML_PATH
        self.api_service:APIService = get_api_service()
        
        # Your analyzer configurations
        self.analyzer_config:AnalyzerConfig = {}
        self.gui_loggers = {
            "gui_log_callback": None,
            "gui_error_callback": None,
            "gui_network_callback": None,
            "gui_serial_callback": None,
            "gui_middleware_ack_callback": None,
            "gui_middleware_nack_callback": None
        }

    def select_analyzer(self, analyzer_name: str) -> AnalyzerConfig:
        """Select and configure an analyzer"""
        
        if not analyzer_name:
            raise ValueError("Analyzer name cannot be empty")
    
        if analyzer_name not in self.analyzer_config:
            try:
                self.analyzer_config[analyzer_name] = ConfigLoader.load_analyzer_config(self.yaml_path)
            except Exception as e:
                raise ValueError(f"Failed to load configuration for analyzer '{analyzer_name}': {e}")
    
        config: AnalyzerConfig = self.analyzer_config[analyzer_name]
        self.handler = DataHandler(config)
        return config
        
    def set_analyzer_ready(self, analyzer_name: str):
        """Set analyzer as ready in shared state"""
        if analyzer_name == self.current_analyzer:
            self.analyzer_ready = True
            if self.gui_log_callback:
                self.gui_log_callback(f"[ENGINE] Analyzer {analyzer_name} marked as ready in shared state")
    
    def set_current_analyzer(self, analyzer_name: str):
        """Set the current analyzer"""
        self.current_analyzer = analyzer_name

    async def handle_hl7_connection(self, reader: HL7StreamReader, writer: HL7StreamWriter):
        """Handle HL7 MLLP connections with integrated processing"""
        peer = writer.get_extra_info('peername')
        
        if self.gui_log_callback:
            self.gui_log_callback(f"[ENGINE] Connection from {peer}")

        try:
            while not writer.is_closing() and self.is_running:
                try:
                    # Read HL7 message
                    message:Message = await reader.readmessage()
                    
                    if self.gui_log_callback:
                        self.gui_log_callback(f"[ENGINE] HL7 message received from {peer}")
                        self.gui_log_callback(f"[ENGINE] Handler processing data...")

                    if self.gui_network_callback:
                        self.gui_network_callback(message)
                    
                    msg_str:str = str(message)
                    
                    if self.handler:
                        validated_message:ErbaMessage | None = self.handler.process_data(msg_str)                        
                        if validated_message:
                            if self.gui_log_callback:
                                self.gui_log_callback("[ENGINE] Data parsed and validated successfully")

                            # Step 8: Send to API
                            await self._send_to_api(validated_message)
                            
                            # Send positive ACK
                            ack = message.create_ack(ack_code='AA')
                            writer.writemessage(ack)
                            await writer.drain()
                            
                            if self.gui_log_callback and self.gui_middleware_ack_callback:
                                self.gui_middleware_ack_callback(" [ACK] ")
                                self.gui_log_callback("[ENGINE] Data sent to API, ACK sent")
                        else:
                            nack = message.create_ack(ack_code='AE')
                            writer.writemessage(nack)
                            await writer.drain()
                            
                            if self.gui_log_callback and self.gui_middleware_nack_callback:
                                self.gui_middleware_nack_callback(" [NACK] ")
                                self.gui_log_callback("[ENGINE] Processing failed, NACK sent")
                    else:
                        if self.gui_log_callback:
                            self.gui_error_callback("[ENGINE] No handler configured")
                        
                        nack = message.create_ack(ack_code='AE')
                        writer.writemessage(nack)
                        await writer.drain()

                except asyncio.IncompleteReadError:
                    if self.gui_error_callback:
                        self.gui_error_callback(f"[ENGINE] Client {peer} disconnected gracefully")
                    break

                except Exception as e:
                    if self.gui_error_callback:
                        self.gui_error_callback(f"[ENGINE] Error processing message from {peer}: {e}")
                    
                    if message:
                        nack = message.create_ack(ack_code='AE')
                        writer.writemessage(nack)
                        await writer.drain()
                        if self.gui_log_callback:
                            self.gui_log_callback(f"[ENGINE] NACK sent due to processing error: {e}")
                    break

        finally:
            if not writer.is_closing():
                writer.close()
                await writer.wait_closed()
            if self.gui_log_callback:
                self.gui_log_callback(f"[ENGINE] Connection with {peer} fully closed")

    async def _send_to_api(self, validated_message:ErbaMessage):
        """Send validated data to API endpoint"""
        try:
            if self.gui_log_callback:
                self.gui_log_callback("[ENGINE] Sending to API endpoint...")
            
            await self.api_service.send_analyzer_data(validated_message)

            # For now, simulate API call
            # await asyncio.sleep(0.1)  # Simulate network delay
            
            if self.gui_log_callback:
                self.gui_log_callback("[ENGINE] Data sent to API successfully")
                
        except Exception as e:
            if self.gui_error_callback:
                self.gui_error_callback(f"[ENGINE] API send error: {e}")
            raise

    async def _run_server(self, host: str = "127.0.0.1", port: int = 15200):
        """Run the HL7 MLLP server"""
        try:
            if self.gui_log_callback:
                self.gui_log_callback(f"[ENGINE] Creating HL7 MLLP server on {host}:{port}...")
            
            self.server = await start_hl7_server(
                self.handle_hl7_connection, 
                host=host, 
                port=port
            )
            if self.gui_log_callback:
                self.gui_log_callback(f"[ENGINE] HL7 MLLP server created")
            
            self.is_running = True
            
            if self.gui_log_callback:
                self.gui_log_callback(f"[ENGINE] HL7 MLLP server listening on {host}:{port}")
                self.gui_log_callback("[ENGINE] Event loop started - ready for HL7 connections")
            
            if hasattr(self, 'server_ready'):
                self.server_ready.set()

            async with self.server:
                await self.server.serve_forever()
                
        except OSError as e:
            if "Address already in use" in str(e):
                if self.gui_log_callback:
                    self.gui_log_callback(f"[ENGINE] Port {port} already in use")
            else:
                if self.gui_log_callback:
                    self.gui_log_callback(f"[ENGINE] Network error: {e}")
            raise
        except Exception as e:
            if self.gui_log_callback:
                self.gui_log_callback(f"[ENGINE] Server error: {e}")
            raise
        finally:
            self.is_running = False
            if self.gui_log_callback:
                self.gui_log_callback("[ENGINE] Server stopped")

    def start_server_background(self, 
                                host="127.0.0.1", 
                                port=15200, 
                                gui_log: Optional[Callable] = None, 
                                error_log:Optional[Callable] = None,
                                network_log:Optional[Callable] = None,
                                serial_log:Optional[Callable] = None,
                                middleware_ack_log:Optional[Callable] = None,
                                middleware_nack_log:Optional[Callable] = None
                            ):
        """Start HL7 MLLP server in background thread"""
        register_loggers(
            gui_log, 
            error_log, 
            network_log, 
            serial_log, 
            middleware_ack_log,
            middleware_nack_log)
        
        logger_registry_instance = GuiLoggerRegistryInstance

        self.gui_log_callback = logger_registry_instance._get_gui_log_callback()
        self.gui_error_callback = logger_registry_instance._get_gui_error_callback()
        self.gui_network_callback = logger_registry_instance._get_gui_network_callback()
        self.gui_serial_callback = logger_registry_instance._get_gui_serial_callback()
        self.gui_middleware_ack_callback = logger_registry_instance._get_gui_middleware_ack_callback()
        self.gui_middleware_nack_callback = logger_registry_instance._get_gui_middleware_nack_callback()


        if self.is_running:
            if self.gui_log_callback:
                self.gui_log_callback("[ENGINE] Server already running")
            return
        
        self.server_ready = threading.Event()
        
        def run_server_thread():
            """Run server in dedicated thread with its own event loop"""
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            try:
                self.gui_log_callback("[ENGINE] Server thread started, waiting for initialization...")
                self.loop.run_until_complete(self._run_server(host, port))
            except Exception as e:
                if error_log:
                    self.gui_error_callback(f"[ENGINE] Server thread error: {e}")
            finally:
                if self.loop:
                    self.loop.close()
                    self.gui_log_callback("[ENGINE] Event loop closed")
        
        self.server_thread = threading.Thread(target=run_server_thread, daemon=True)
        self.server_thread.start()
        
        self.gui_log_callback("[ENGINE] Starting server thread...")
        time.sleep(2)
    
    def stop_server_background(self):
        """Stop the HL7 MLLP server"""
        self.is_running = False
        self.analyzer_ready = False
        
        if self.server:
            if self.loop and self.loop.is_running():
                self.loop.call_soon_threadsafe(self.server.close)
        
        if self.gui_log_callback:
            self.gui_log_callback("[ENGINE] Server stopped")

    async def _cleanup_resources(self):
        """Clean up resources when stopping"""
        try:
            await close_api_service()
            if self.gui_log_callback:
                self.gui_log_callback("[ENGINE] API service closed")
        except Exception as e:
            if self.gui_error_callback:
                self.gui_error_callback(f"[ENGINE] Error closing API service: {e}")

engine = MiddlewareEngine()

def is_middleware_ready() -> bool:
    """Check if middleware is ready"""
    return engine.analyzer_ready

def get_server_status() -> dict:
    """Get current server status"""
    return {
        'running': engine.is_running,
        'analyzer_ready': engine.analyzer_ready,
        'current_analyzer': engine.current_analyzer,
        'server_thread_alive': engine.server_thread.is_alive() if engine.server_thread else False
    }

if __name__ == '__main__':
    logger.info("===== Starting Engine =====")    

    def console_log(message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        logger.info(f"[{timestamp}] {message}")
    
    try:
        # Start with console logging
        engine.start_server_background(gui_log=console_log)
        
        print("Server started. Press Ctrl+C to stop...")
        
        # Keep main thread alive
        while True:
            time.sleep(1)
            if not engine.is_running:
                print("Server stopped unexpectedly")
                break
                
    except KeyboardInterrupt:
        print("\n===== Shutting Down =====")
        engine.stop_server_background()
        print("Engine stopped")
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
