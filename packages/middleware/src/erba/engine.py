import asyncio
import datetime
import threading
import time

from typing import (
    List, 
    Optional, 
    Callable
)

from hl7 import (
    Message, 
    Segment
)

from hl7.parser import parse as hl7_parse

from hl7.mllp import (
    start_hl7_server, 
    HL7StreamReader, 
    HL7StreamWriter
)

from erba import (
    HL7Parser,
    DataValidator,
    APIResult,
    AnalyzerConfig, 
    ErbaMessage, 
    ParsingResult,
    APIService,
    close_api_service, 
    get_api_service
)

from erba.constants import (
    CR, 
    ERBA_YAML_PATH, 
    FS, 
    NEGATIVE_ACK_CODE, 
    POSITIVE_ACK_CODE, 
    VT
)

from configuration.logger import (
    logger, 
    register_loggers, 
    GuiLoggerRegistryInstance
)

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
        
        self._analyzer_config = {}
        self.gui_loggers = {
            "gui_log_callback": None,
            "gui_error_callback": None,
            "gui_network_callback": None,
            "gui_serial_callback": None,
            "gui_middleware_ack_callback": None,
            "gui_middleware_nack_callback": None
        }
        self.nack_sent = False

# Analyzer state handlers
    def select_analyzer(self, analyzer_name: str) -> AnalyzerConfig:
        """Select and configure an analyzer"""
        
        if not analyzer_name:
            raise ValueError("Analyzer name cannot be empty")
        
        if analyzer_name not in self.analyzer_config:
            raise ValueError(f"Analyzer '{analyzer_name}' not found in configuration")
        
        config: AnalyzerConfig = self.analyzer_config[analyzer_name]
        logger.info(f"The analyzer config: {config}")
        
        if config is None:
            raise ValueError(f"Analyzer configuration for '{analyzer_name}' is None")
            
        self.handler = DataHandler(config)
        self.current_analyzer = analyzer_name
        return config
        
    @property
    def analyzer_config(self):
        if not self._analyzer_config:
            from configuration.config_loader import ConfigLoader
            from pathlib import Path
            import glob
            analyzer_configs = {}

            config_dir = Path(self.yaml_path).parent
            config_files = glob.glob(str(config_dir / "*.yaml"))

            for config_file in config_files:
                try:
                    config = ConfigLoader.load_analyzer_config(config_file)
                    device_name = config.device.lower()
                    analyzer_configs[device_name] = config
                    logger.info(f"Loaded analyzer config: {device_name} from {config_file}")
                except Exception as e:
                    logger.warning(f"Failed to load config {config_file}: {e}")
        
            self._analyzer_config = analyzer_configs
        return self._analyzer_config

    @analyzer_config.setter 
    def analyzer_config(self, value):
        self._analyzer_config = value
        
    def set_analyzer_ready(self, analyzer_name: str):
        """Set analyzer as ready in shared state"""
        try:
            if analyzer_name == self.current_analyzer:
                self.analyzer_ready = True
                if self.gui_log_callback:
                    self.gui_log_callback(f"[ENGINE] Analyzer {analyzer_name} marked as ready in shared state")
                else: 
                    self.gui_network_callback(f"Something went wrong")
        except Exception as e:
            logger.info(e)

# Server actions
    async def handle_hl7_connection(self, reader: HL7StreamReader, writer: HL7StreamWriter):
        """Handle HL7 MLLP connections with integrated processing"""
        self.peer = writer.get_extra_info('peername')
        self._log_info_to_gui(f"[ENGINE] Connection from {self.peer}")
        
        # Track ACK state for this connection
        ack_message = None
        should_send_ack = False
        processing_failed = False
        successful_messages = 0

        try:
            while not writer.is_closing() and self.is_running:
                try:
                    if not self.validate_network_logger():
                        break

                    block: bytes = await reader.read()
                    # If there is no more data then break out of loop
                    if not block:
                        break
                        
                    self._log_info_to_gui(f"[ENGINE] HL7 message received from {self.peer} - Handler processing data...")
                    
                    # Validate MLLP boundaries
                    self.parse_message_structure(block)
                    is_valid, clean_messages, error_msg = self.validate_mllp_boundaries(block)
                    
                    if not is_valid:
                        self.gui_network_callback(block)
                        self._log_gui_negative_acknowledgement(message_or_error="", reason=f"MLLP validation failed: {error_msg}")
                        processing_failed = True

                        ack_message = self.create_nack("Invalid MLLP Boundry")
                        should_send_ack = True
                        break
                    
                    batch_success = True
                    for idx, msg in enumerate(clean_messages, 1):
                        try:
                            message: Message = hl7_parse(msg)
                            self.gui_network_callback(message)

                            # In case of batch the standard practice is to send ack for first message
                            # that is what we are doing here
                            if idx == 1:
                                ack_message = message
                                should_send_ack = True

                            # Process message
                            msg_str: str = str(message)
                            if self.handler:
                                validated_message: ErbaMessage | None = self.handler.process_data(msg_str)
                                
                                if validated_message:
                                    self._log_info_to_gui(f"[ENGINE] Message {idx} parsed and validated successfully")
                                    
                                    # Send to API
                                    api_result: APIResult = await self._send_to_api(validated_message)
                                    
                                    if not api_result.success:
                                        self._log_error_to_gui(f"API Error for message {idx}: {api_result.error}")
                                        self._log_gui_negative_acknowledgement(message, f"API failed: {api_result.error}")
                                        batch_success = False
                                        processing_failed = True
                                        break
                                    else:
                                        response_data = api_result.data
                                        if response_data and response_data.get('duplicate', False):
                                            self._log_info_to_gui(f"[ENGINE] Message {idx} (qr_id: {validated_message.message_id}) is duplicate - skipped")
                                        else:
                                            self._log_info_to_gui(f"[ENGINE] Message {idx} (qr_id: {validated_message.message_id}) saved successfully")
                                        successful_messages += 1
                                else:
                                    self._log_error_to_gui(f"[ENGINE] Message {idx} validation failed")
                                    self._log_gui_negative_acknowledgement(message, "Validation failed")
                                    batch_success = False
                                    processing_failed = True
                                    break
                            else:
                                self._log_error_to_gui("[ENGINE] Handler is not configured")
                                self._log_gui_negative_acknowledgement(message, "Handler not configured")
                                batch_success = False
                                processing_failed = True
                                break
                                
                        except Exception as e:
                            self._log_error_to_gui(f"[ENGINE] Error processing message {idx}: {str(e)}")
                            self._log_gui_negative_acknowledgement(message, f"Processing error: {str(e)}")
                            batch_success = False
                            processing_failed = True
                            break
                    
                    # If batch processing completed (success or failure), we're done with this connection
                    if batch_success or processing_failed:
                        break
                        
                except Exception as e:
                    self._log_error_to_gui(f"[ENGINE] Unexpected error in connection loop: {str(e)}")
                    self._log_gui_negative_acknowledgement(
                        ack_message or self.create_nack(f"Connection error: {str(e)}")
                    )
                    processing_failed = True
                    should_send_ack = True
                    break
                    
        except Exception as e:
            self._log_error_to_gui(f"[ENGINE] Fatal connection error: {str(e)}")
            processing_failed = True
            should_send_ack = True
            if not ack_message:
                ack_message = self.create_nack("Unknown Error")
                
        finally:
            if should_send_ack and ack_message:
                try:
                    await self._send_positive_acknowledgement_to_analyzer(ack_message, writer)
                    
                    if not processing_failed and len(clean_messages) == successful_messages:
                        self._log_gui_positive_acknowledgement(ack_message)
                    elif successful_messages == 0:
                        self._log_info_to_gui("[ENGINE] Batch processing failed completely - individual NAKs already logged")
                    else:
                        self._log_info_to_gui(f"[ENGINE] Batch processing completed with mixed results ({successful_messages}/{len(clean_messages)} successful) - individual NAKs already logged for failures")
                except Exception as ack_error:
                    self._log_error_to_gui(f"[ENGINE] Failed to send ACK: {str(ack_error)}")
            
            # Clean up connection
            if not writer.is_closing():
                writer.close()
                await writer.wait_closed()
            self._log_info_to_gui(f"[ENGINE] Connection with {self.peer} fully closed")


    def parse_message_structure(self, raw_message_bytes: bytes):
        """Debug function to understand message structure"""        
        logger.info(f"Total message length: {len(raw_message_bytes)}")
        
        FSCR = FS + CR
        vt_count = raw_message_bytes.count(VT)
        fs_count = raw_message_bytes.count(FS)
        total_cr_count = raw_message_bytes.count(CR)        
        mllp_terminators = raw_message_bytes.count(FSCR)    
        cr_count = total_cr_count - mllp_terminators
        
        logger.info(f"VT count: {vt_count}, FS count: {fs_count}, CR count: {cr_count}")
        
        self.vt_positions = self.count_VT(raw_message_bytes)
        self.vt_count = len(self.vt_positions)
        
        self.fscr_positions = self.count_FSCR(raw_message_bytes)
        self.fscr_count = len(self.fscr_positions)

        logger.info(f"{self.vt_positions} -> {self.vt_count}")
        logger.info(f"{self.fscr_positions} -> {self.fscr_count}")

    def count_VT(self, raw_message: bytes) -> list[int]:
        vt_positions:list = []
        pos = 0

        while True:
            pos = raw_message.find(VT, pos)
            if pos == -1:
                break
            vt_positions.append(pos)
            pos += len(VT)

        return vt_positions

    def count_FSCR(self, raw_message: bytes) -> list[int]:
        fs_cr_positions:list = []
        pos = 0

        while True:
            pos = raw_message.find(FS + CR, pos)            
            if pos == -1:
                break
            fs_cr_positions.append(pos)
            pos += len(VT)

        return fs_cr_positions

    def validate_mllp_boundaries(self, raw_message_bytes: bytes) ->  tuple[bool, List[bytes], Optional[str]]:
        """
        Validates HL7 MLLP message boundaries with comprehensive structure checking:
        - Validates VT/FS+CR count matching
        - Ensures each VT is followed by MSH
        - Handles both single messages and batch messages
        - Extracts clean message content
        
        Args:
            raw_message_bytes (bytes): The raw message bytes from MLLP stream
            
        Returns:
            tuple: (is_valid: bool, clean_messages: List[bytes], error_message: str or None)
        """    
        if not raw_message_bytes:
            return False, [], "Empty message"
    
        if self.vt_count != self.fscr_count:
            return False, [], f"MLLP frame mismatch: VT count ({self.vt_count}) != FS+CR count ({self.fscr_count})"
    
        if not self.validate_raw_message_structure(raw_message_bytes):
            return False, [], "Invalid MLLP structure: VT not immediately followed by MSH segment"
    
        clean_messages = []
    
        try:
            for i in range(len(self.vt_positions)):
                vt_pos = self.vt_positions[i]
                fscr_pos = self.fscr_positions[i]
            
                content_start = vt_pos + 1
                content_end = fscr_pos

                if content_start >= content_end:
                    return False, [], f"Invalid frame {i+1}: VT at {vt_pos}, FS+CR at {fscr_pos}"
            
                message_content:bytes = raw_message_bytes[content_start:content_end]
            
                if not message_content.startswith(b'MSH|'):
                    return False, [], f"Frame {i+1} content does not start with MSH segment"
                clean_messages.append(message_content)
            
            return True, clean_messages, None
        except IndexError as e:
            return False, [], f"Index error during message extraction: {str(e)}"
        except Exception as e:
            return False, [], f"Unexpected error during validation: {str(e)}"

    def validate_raw_message_structure(self, raw_message: bytes) -> bool:
        """
        Validates that each VT position is immediately followed by MSH segment
        
        Args:
            raw_message (bytes): The raw message bytes
            
        Returns:
            bool: True if all VT positions are valid, False otherwise
        """
        try:
            for i, vt_pos in enumerate(self.vt_positions):
                if vt_pos + 4 > len(raw_message):
                    logger.error(f"VT at position {vt_pos} extends beyond message bounds")
                    return False
                
                msh_start = vt_pos + 1
                msh_end = msh_start + 3
                msh_bytes = raw_message[msh_start:msh_end]
                
                logger.info(f"Frame {i+1}: VT@{vt_pos} -> MSH check: {msh_bytes}")
                
                if msh_bytes != b'MSH':
                    logger.error(f"VT at position {vt_pos} not followed by MSH. Found: {msh_bytes}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating message structure: {str(e)}")
            return False

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
    async def _send_positive_acknowledgement_to_analyzer(self, message: Message, writer: HL7StreamWriter):
        """Send positive ACK to analyzer (always AA regardless of internal processing result)"""
        try:
            ack: Message = message.create_ack(ack_code=POSITIVE_ACK_CODE)
            await self._write_message_to_analyzer(ack, writer)
            logger.info(f"Positive ACK sent to analyzer: {ack}")
            return True
        except Exception as e:
            logger.error(f"Failed to send ACK to analyzer: {str(e)}")
            raise

    def _log_gui_positive_acknowledgement(self, message: Message):
        """Log positive acknowledgement to GUI only"""
        try:
            ack: Message = message.create_ack(ack_code=POSITIVE_ACK_CODE)
            self._log_acknowledgement_to_gui(POSITIVE_ACK_CODE, ack)
        except Exception as e:
            logger.error(f"Failed to log GUI ACK: {str(e)}")

    def _log_gui_negative_acknowledgement(self, message_or_error: Message | str, reason: str = "Processing failed"):
        """Log negative acknowledgement to GUI only (never sent to analyzer)"""
        try:
            if isinstance(message_or_error, str):
                nack_message = self.create_nack(reason)
            else:
                nack_message = message_or_error.create_ack(ack_code=NEGATIVE_ACK_CODE)
            
            self._log_acknowledgement_to_gui(NEGATIVE_ACK_CODE, nack_message, reason)
        except Exception as e:
            logger.error(f"Failed to log GUI NACK: {str(e)}")

    def _log_acknowledgement_to_gui(self, ack_code: str, message: Message, reason: str = None):
        """Log acknowledgement message to GUI with proper formatting"""
        if not (self.gui_log_callback and self.gui_middleware_ack_callback):
            logger.error("GUI log handlers are not configured properly")
            return
        
        formatted_msg: str = self.format_response(message)
        if ack_code == POSITIVE_ACK_CODE:  # 'AA'
            self._log_info_to_gui("[ENGINE] Data processed successfully, ACK logged")
            self.gui_middleware_ack_callback(formatted_msg)
        elif ack_code == NEGATIVE_ACK_CODE:  # 'AE'
            reason_msg = f" - {reason}" if reason else ""
            self._log_error_to_gui(f"[ENGINE] Processing failed{reason_msg}, NACK logged")
            self.gui_middleware_nack_callback(formatted_msg)
        else:
            logger.error(f"Unknown ack_code: {ack_code}")

    async def _write_message_to_analyzer(self, response:Message, writer:HL7StreamWriter):
        try:
            writer.writemessage(response)
            await writer.drain()
        except Exception as e:
            raise e

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
    
    def validate_network_logger(self) -> bool:
        if not self.gui_network_callback:
            if self.gui_error_callback:
                self.gui_error_callback("Network logger not configured properly")
                return False
            else:
                logger.error("Network logger not configured properly")
                return False
        return True
    
    def create_nack(self, reason: str) -> Message:
        nack_message:Message = Message()
        msh_segment = Segment(sequence=[
            "MSH",
            "|",
            "",
            "UNKNOWN",
            "",
            datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
            "",
            "ACK", 
            "NAK001",
            "P",
            "2.3.1"
        ])        
        nack_message.append(msh_segment)
        nack_message.append(Segment(sequence=['MSA', 'AR', 'NAK001']))
        nack_message.append(Segment(sequence=[
            'ERR', '', '', '207^Application Internal Error^HL70357', '', '', 'T', str(reason)
        ]))

        return nack_message
    
    def format_response(self, message: Message, indent_chars=" "*12):
        """
        Formats an hl7.Message object as a human-readable string with
        indented segments after the MSH.
        """
        str_msg = str(message)
        segments = str_msg.split('\r')
        if not segments or not segments[0]:
            return ""
        formatted_lines = [segments[0]]
        for segment in segments[1:]:
            if segment:
                formatted_lines.append(indent_chars + segment)
        return '\n'.join(formatted_lines)
    
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
        
        logger.info("Server started. Press Ctrl+C to stop...")
        
        # Keep main thread alive
        while True:
            time.sleep(1)
            if not engine.is_running:
                logger.info("Server stopped unexpectedly")
                break
                
    except KeyboardInterrupt:
        logger.info("\n===== Shutting Down =====")
        engine.stop_server_background()
        logger.info("Engine stopped")
    except Exception as e:
        logger.info(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
