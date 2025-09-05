import asyncio
import datetime
import threading
import time
from typing import Optional, Callable, Tuple

from hl7 import Message
from hl7.mllp import InvalidBlockError
from hl7.mllp import start_hl7_server, HL7StreamReader, HL7StreamWriter

from middleware.config_loader import ConfigLoader
from middleware.logger import GuiLoggerRegistryInstance, register_loggers, logger
from middleware.parser import HL7Parser
from middleware.validator import DataValidator
from middleware.models import APIResult, AnalyzerConfig, ErbaMessage, ParsingResult
from middleware.api import APIService, close_api_service, get_api_service
from constants import ERBA_YAML_PATH, NEGATIVE_ACK_CODE, POSITIVE_ACK_CODE

class DataHandler:
    def __init__(self, config: AnalyzerConfig):
        self.config = config
        self.validator = DataValidator(self.config)
        self.yaml_path = ERBA_YAML_PATH
        self.parser = HL7Parser(self.yaml_path)

    def process_data(self, raw_data: str) -> Optional[ErbaMessage]:
        """
        Process HL7 message through validation, API transmission, and acknowledgement pipeline.
        
        Args:
            raw_data (str): Raw HL7 string message from analyzer to process        
        Returns:
            ProcessingResult: Contains success status, processing stage, API data, error details, and ACK status
            None: This means any of the stage in the pipeline failed. (None will directly signal to send NACK) 
        Raises:
            ConnectionError: When HL7 stream connection is lost during ACK transmission
            ValidationError: When message validation fails due to invalid format
            APIException: When API service is unavailable or returns error
        """
    
        if not raw_data or not raw_data.strip():
            logger.warning(f"Empty or null data provided: {raw_data}")
            return None
    
        try:
            logger.info("Starting data parsing...")
            parsed_data:ParsingResult = self.parser.parse_with_config(raw_data)
            logger.info(f"Parsing completed.")
            
            if not parsed_data:
                logger.error("[Parsing Error] Parsing returned None or empty data. Checking for errors...")
                return None
        
            parsing_errors = parsed_data.parsing_errors
            if parsing_errors:
                logger.error(f"[Parsing Error] Found {len(parsing_errors)} parsing errors:")
                for error in parsing_errors:
                    logger.error(f"{error}")
                parsed_data = None
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

# Analyzer state handlers
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

# Server actions
    async def handle_hl7_connection(self, reader: HL7StreamReader, writer: HL7StreamWriter):
        """Handle HL7 MLLP connections with integrated processing"""
        peer = writer.get_extra_info('peername')
        self._log_info_to_gui(f"[ENGINE] Connection from {peer}")

        try:
            while not writer.is_closing() and self.is_running:
                try:
                    # Read HL7 message from 'HL7StreamReader' instance(Removes MLLP logging)
                    message:Message = await reader.readmessage()
                    
                    self._log_info_to_gui(
                        f"""[ENGINE] HL7 message received from {peer}
                        [ENGINE] Handler processing data..."""
                    )
                    
                    # Log the data to the gui network_tab
                    if self.gui_network_callback:
                        self.gui_network_callback(message)
                    else:
                        self._log_error_to_gui("Network logger not configured properly")
                    
                    # Convert the message to string as we are processing it as a string
                    msg_str:str = str(message)
                    if self.handler:
                        validated_message:ErbaMessage | None = self.handler.process_data(msg_str)                        
                        
                        if validated_message:
                            self._log_info_to_gui("[ENGINE] Data parsed and validated successfully")

                            api_result:APIResult = await self._send_to_api(validated_message)
                            
                            if not api_result.success:
                                self._log_error_to_gui(f"Api Error Cause: {api_result.error}")
                                await self._send_negative_acknowledgement(message, writer)
                                return
                            
                            await self._send_positive_acknowledgement(message, writer)
                            return
                        else:
                            await self._send_negative_acknowledgement(message, writer) 
                            return
                    else:
                        await self._send_negative_acknowledgement(message, writer)
                        return
                except InvalidBlockError as e:
                    self._log_error_to_gui(f"[ENGINE] Invalid HL7 MLLP message block: {str(e)}")
                    await self._send_negative_acknowledgement(message, writer)
                    break
                except asyncio.IncompleteReadError:
                    self._log_error_to_gui(f"[ENGINE] Client {peer} disconnected gracefully")
                    break
                except Exception as e:
                    self._log_error_to_gui(f"[ENGINE] Error processing message from {peer}: {str(e)}")
                    await self._send_negative_acknowledgement(message, writer)
                    break
        finally:
            # Force writer to close(if not closed can lead to security issues)
            if not writer.is_closing():
                writer.close()
                await writer.wait_closed()
            self._log_info_to_gui(f"[ENGINE] Connection with {peer} fully closed")

    async def _send_to_api(self, validated_message: ErbaMessage) -> APIResult:
        """Send validated data to API endpoint and return API result"""
        try:
            if self.gui_log_callback:
                self.gui_log_callback("[ENGINE] Sending to API endpoint...")
            
            api_result:APIResult = await self.api_service.send_analyzer_data(validated_message)
            
            if self.gui_log_callback:
                self.gui_log_callback("[ENGINE] Data sent to API successfully")
                
            return api_result
            
        except Exception as e:
            if self.gui_error_callback:
                self.gui_error_callback(f"[ENGINE] API send error: {e}")
            raise

# ACK & NACK processing
    async def _send_positive_acknowledgement(self, message: Message, writer: HL7StreamWriter):
        ack_sent, errors = await self._send_acknowledgement(
            ack_code=POSITIVE_ACK_CODE, 
            message=message, 
            writer=writer
        )
        self._process_acknowledgement(POSITIVE_ACK_CODE, ack_sent, errors)

    async def _send_negative_acknowledgement(self, message: Message, writer: HL7StreamWriter):
        ack_sent, errors = await self._send_acknowledgement(
            ack_code=NEGATIVE_ACK_CODE, 
            message=message, 
            writer=writer
        )
        self._process_acknowledgement(NEGATIVE_ACK_CODE, ack_sent, errors)

    async def _send_acknowledgement(
            self, 
            ack_code: str, 
            message: Message, 
            writer: HL7StreamWriter
    ) -> Tuple[bool, str]:
        try:
            ack = message.create_ack(ack_code=ack_code)
            writer.writemessage(ack)
            await writer.drain()
            return True, ""
        except Exception as e:
            return False, str(e)

    def _process_acknowledgement(self, ack_code:str, ack_sent: bool, error_msg: str):
        if not ack_sent:
            self.gui_error_callback(f"unable to send acknowledgement to analyzer: {error_msg}")
            return
        
        if not(self.gui_log_callback and self.gui_middleware_ack_callback):
            logger.error("Gui log handlers are not configured properly")
        else:
            if error_msg:
                logger.error(f"Errors: {error_msg}")
        
        if ack_code == 'AA':
            self._log_ack()
        elif ack_code == 'AE':
            self._log_nack()
        else:
            logger.error(f"ack_code: {ack_code} not Valid")

    def _log_ack(self):
        self._log_info_to_gui("[ENGINE] Data sent to API, ACK sent")
        self.gui_middleware_ack_callback(" [ACK] ")  

    def _log_nack(self):
        self._log_info_to_gui("[ENGINE] Data sent to API, NACK sent")
        self.gui_middleware_nack_callback(" [NACK] ")  

# Wrapper on logging messages to gui or server logger(as fallback)
    def _log_info_to_gui(self, msg_str:str):
        if self.gui_log_callback:
            self.gui_log_callback(f"{msg_str}")
        else:
            logger.info(f"{msg_str}")

    def _log_error_to_gui(self, msg_str:str):
        if self.gui_error_callback:
            self.gui_error_callback(f"{msg_str}")
        else:
            logger.error(f"{msg_str}")
    
        # if self.gui_error_callback:
        #     self.gui_error_callback(f"[ENGINE] Invalid HL7 MLLP message block: {e}")
        # else:
        #     logger.error(f"Invalid HL7 MLLP message block")

# Server lifecycle
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

# global methods for knowign engine state
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

# main script to run the server on terminal(Optional as the middleware handles it but good for development)
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
