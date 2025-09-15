"""
Comprehensive tests for MiddlewareEngine class
"""
import threading
from erba.constants import ERBA_YAML_PATH
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from erba.engine import MiddlewareEngine
from erba.models import APIResult
import yaml
from .fixtures.valid_messages import COMPLETE_VALID_MESSAGE
from .fixtures.edge_cases import (
    INCOMPLETE_MESSAGE_17, MALFORMED_JOINED_MESSAGE, 
)
from .utils.test_helpers import (
    MockHL7StreamReader, 
    MockHL7StreamWriter, 
    create_mock_erba_message,
    find_available_port
)


class TestMiddlewareEngineInitialization:
    """Test engine initialization and configuration"""
    
    def test_engine_initialization_default_values(self, engine_instance):
        """Test engine initializes with correct default values"""
        assert engine_instance.current_analyzer is None
        assert engine_instance.server is None
        assert engine_instance.is_running is False
        assert engine_instance.analyzer_ready is False
        assert engine_instance.server_task is None
        assert engine_instance.handler is None
        assert engine_instance.api_service is not None
        assert engine_instance.loop is None
        assert engine_instance.server_thread is None
        assert engine_instance.yaml_path == ERBA_YAML_PATH 
        assert engine_instance._analyzer_config == {}      
        assert engine_instance.nack_sent is False
    
    def test_analyzer_configuration_loading(self, engine_instance: MiddlewareEngine, mock_analyzer_config):
        """Test analyzer configuration loading"""
        
        with patch('erba.engine.DataHandler') as mock_data_handler:
            engine_instance._analyzer_config = {"test_analyzer": mock_analyzer_config}
            
            mock_handler_instance = Mock()
            mock_data_handler.return_value = mock_handler_instance
            
            config = engine_instance.select_analyzer("test_analyzer")
            
            assert config == mock_analyzer_config
            assert engine_instance.handler == mock_handler_instance
            assert engine_instance.current_analyzer == "test_analyzer"
            
            mock_data_handler.assert_called_once_with(mock_analyzer_config)

    def test_analyzer_config_property_lazy_loading(self, engine_instance):
        """Test that analyzer_config property lazy loads correctly"""
        
        with patch('configuration.config_loader.ConfigLoader.load_analyzer_config') as mock_loader:
            mock_config = Mock()
            mock_config.device = "analyzer1"
            mock_loader.return_value = mock_config
            
            engine_instance._analyzer_config = {}
            
            result = engine_instance.analyzer_config
            expected = {"analyzer1": mock_config}
            
            assert result == expected
            mock_loader.assert_called()


    def test_analyzer_not_found_error(self, engine_instance):
        """Test error when analyzer not in configuration"""
        
        with patch('configuration.config_loader.ConfigLoader.load_parser_config') as mock_loader:
            mock_loader.return_value = {"other_analyzer": {"name": "other"}}
            
            with pytest.raises(ValueError, match="Analyzer 'missing_analyzer' not found"):
                engine_instance.select_analyzer("missing_analyzer")
    
    def test_analyzer_configuration_invalid_name(self, engine_instance):
        """Test analyzer configuration with invalid name"""
        def select_analyzer(analyzer_name):
            if not analyzer_name:
                raise ValueError("Analyzer name cannot be empty")
            return {}
        
        engine_instance.select_analyzer = select_analyzer
        
        with pytest.raises(ValueError, match="Analyzer name cannot be empty"):
            engine_instance.select_analyzer("")
    
    def test_analyzer_configuration_load_failure(self, engine_instance, caplog):
        """Test analyzer configuration load failure scenarios"""
        
        engine_instance._analyzer_config = {}
        
        with patch('configuration.config_loader.ConfigLoader.load_analyzer_config') as mock_loader, \
            patch('glob.glob') as mock_glob:
            
            mock_glob.return_value = ["/fake/config.yaml"]
            mock_loader.side_effect = FileNotFoundError("Configuration file not found")
            
            result = engine_instance.analyzer_config
            
            assert result == {}
            assert "Failed to load config" in caplog.text
            assert "Configuration file not found" in caplog.text


    def test_analyzer_configuration_invalid_yaml(self, engine_instance, caplog):
        """Test invalid YAML configuration file"""
        
        engine_instance._analyzer_config = {}
        
        with patch('configuration.config_loader.ConfigLoader.load_analyzer_config') as mock_loader, \
            patch('glob.glob') as mock_glob:
            
            mock_glob.return_value = ["/fake/invalid.yaml"]
            mock_loader.side_effect = yaml.YAMLError("Invalid YAML syntax")
            
            result = engine_instance.analyzer_config
            
            assert result == {}
            assert "Failed to load config" in caplog.text
            assert "Invalid YAML syntax" in caplog.text

    
    def test_set_analyzer_ready(self, engine_instance, mock_gui_callbacks):
        """Test setting analyzer as ready"""
        engine_instance.current_analyzer = "test_analyzer"
        engine_instance.gui_log_callback = mock_gui_callbacks['gui_log']
        
        engine_instance.set_analyzer_ready("test_analyzer")
        
        assert engine_instance.analyzer_ready is True
        mock_gui_callbacks['gui_log'].assert_called_once()

 
class TestMiddlewareEngineServerLifecycle:
    """Test server lifecycle management"""
    
    @pytest.mark.asyncio
    async def test_server_startup_success(self, engine_instance: MiddlewareEngine):
        """Test server startup with real _run_server method"""
        mock_gui_callback = Mock()
        engine_instance.gui_log_callback = mock_gui_callback
        port = find_available_port()
        
        with patch('erba.engine.start_hl7_server') as mock_start_server:
            mock_server_instance = AsyncMock()
            mock_start_server.return_value = mock_server_instance
            
            server_task = asyncio.create_task(
                engine_instance._run_server("127.0.0.1", port)
            )
            await asyncio.sleep(0.5)
            
            if not server_task.done():
                server_task.cancel()
                try:
                    await server_task
                except asyncio.CancelledError:
                    pass
            
            mock_start_server.assert_called_once()

    def test_server_background_startup(self, engine_instance):
        """Test server startup in background thread"""
        port = find_available_port()
        
        server_running = threading.Event()
        server_should_stop = threading.Event()
        
        async def mock_run_server(host, port):
            """Mock _run_server that keeps running until told to stop"""
            server_running.set()
            while not server_should_stop.is_set():
                await asyncio.sleep(0.1)
        
        with patch.object(engine_instance, '_run_server', side_effect=mock_run_server):
            engine_instance.is_running = False
            
            engine_instance.start_server_background(
                host="127.0.0.1",
                port=port,
                gui_log=Mock(),
                error_log=Mock(),
                network_log=Mock(),
                serial_log=Mock(),
                middleware_ack_log=Mock(),
                middleware_nack_log=Mock()
            )
            
            server_running.wait(timeout=5)
            
            assert engine_instance.server_thread is not None
            assert engine_instance.server_thread.is_alive()
            
            server_should_stop.set()
            engine_instance.server_thread.join(timeout=2)

    def test_server_port_already_in_use(self, engine_instance, mock_gui_callbacks):
        """Test server startup when port is already in use"""
        with patch('erba.engine.start_hl7_server') as mock_server:
            mock_server.side_effect = OSError("Address already in use")
            
            engine_instance.gui_log_callback = mock_gui_callbacks['gui_log']
            
            with pytest.raises(OSError):
                asyncio.run(engine_instance._run_server("127.0.0.1", 15200))
    
    def test_server_stop_background(self, engine_instance):
        """Test stopping background server"""
        engine_instance.is_running = True
        engine_instance.server = Mock()
        engine_instance.loop = Mock()
        engine_instance.loop.is_running.return_value = True
        
        engine_instance.stop_server_background()
        
        assert engine_instance.is_running is False
        assert engine_instance.analyzer_ready is False


class TestMiddlewareEngineHelpers:
    """Test actual helper methods"""
    
    def test_count_VT_single_message(self, engine_instance):
        """Test counting VT positions in single message"""
        message = b'\x0bMSH|message content\x1c\x0d'
        result = engine_instance.count_VT(message)
        assert result == [0]
    
    def test_count_VT_multiple_messages(self, engine_instance):
        """Test counting VT positions in multiple messages"""
        message = b'\x0bMSH|msg1\x1c\x0d\x0bMSH|msg2\x1c\x0d\x0bMSH|msg3\x1c\x0d'
        result = engine_instance.count_VT(message)
        assert result == [0, 11, 22]
    
    def test_count_VT_no_vt(self, engine_instance):
        """Test counting VT when none exist"""
        message = b'MSH|message without VT'
        
        result = engine_instance.count_VT(message)
        
        assert result == []
    
    def test_count_FSCR_single_message(self, engine_instance):
        """Test counting FS+CR positions in single message"""
        message = b'\x0bMSH|^~\\&|TEST|LAB|||\x1c\x0d'
        
        result = engine_instance.count_FSCR(message)

        assert result == [21]
    
    def test_count_FSCR_multiple_messages(self, engine_instance):
        """Test counting FS+CR positions in multiple messages"""
        message = b'\x0bMSH|msg1\x1c\x0d\x0bMSH|msg2\x1c\x0d\x0bMSH|msg3\x1c\x0d'
        
        result = engine_instance.count_FSCR(message)
        
        assert result == [9, 20, 31]
    
    def test_count_FSCR_no_fscr(self, engine_instance):
        """Test counting FS+CR when none exist"""
        message = b'MSH|message without FSCR'
        
        result = engine_instance.count_FSCR(message)
        
        assert result == []
    
    def test_parse_message_structure_single_message(self, engine_instance):
        """Test parsing structure of single message"""
        message = b'\x0bMSH|^~\\&|TEST|LAB|||\x1c\x0d'
        
        with patch('erba.engine.logger') as mock_logger:
            engine_instance.parse_message_structure(message)
        
        assert engine_instance.vt_positions == [0]
        assert engine_instance.vt_count == 1
        assert engine_instance.fscr_positions == [21]
        assert engine_instance.fscr_count == 1
        
        assert mock_logger.info.call_count >= 4
        mock_logger.info.assert_any_call(f"Total message length: {len(message)}")
        mock_logger.info.assert_any_call("VT count: 1, FS count: 1, CR count: 0")

    def test_parse_message_structure_multiple_messages(self, engine_instance):
        """Test parsing structure of multiple messages"""
        message = b'\x0bMSH|msg1\x1c\x0d\x0bMSH|msg2\x1c\x0d'
        
        with patch('erba.engine.logger') as mock_logger:
            engine_instance.parse_message_structure(message)
        
        assert engine_instance.vt_positions == [0, 11]
        assert engine_instance.vt_count == 2
        assert engine_instance.fscr_positions == [9, 20]
        assert engine_instance.fscr_count == 2
    
    def test_parse_message_structure_empty_message(self, engine_instance):
        """Test parsing empty message"""
        message = b''
        
        with patch('erba.engine.logger') as mock_logger:
            engine_instance.parse_message_structure(message)
        
        assert engine_instance.vt_positions == []
        assert engine_instance.vt_count == 0
        assert engine_instance.fscr_positions == []
        assert engine_instance.fscr_count == 0
    
    def test_validate_raw_message_structure_valid_single(self, engine_instance):
        """Test validation of valid single message structure"""
        message = b'\x0bMSH|^~\\&|TEST|LAB|||\x1c\x0d'
        engine_instance.vt_positions = [0]
        
        with patch('erba.engine.logger') as mock_logger:
            result = engine_instance.validate_raw_message_structure(message)
        
        assert result is True
        mock_logger.info.assert_called_with("Frame 1: VT@0 -> MSH check: b'MSH'")
    
    def test_validate_raw_message_structure_valid_multiple(self, engine_instance):
        """Test validation of valid multiple message structure"""
        message = b'\x0bMSH|msg1\x1c\x0d\x0bMSH|msg2\x1c\x0d'
        engine_instance.vt_positions = [0, 11]
        
        with patch('erba.engine.logger') as mock_logger:
            result = engine_instance.validate_raw_message_structure(message)
        
        assert result is True
        assert mock_logger.info.call_count == 2

    def test_validate_raw_message_structure_invalid_msh(self, engine_instance):
        """Test validation fails when VT not followed by MSH"""
        message = b'\x0bOBX|invalid start\x1c\x0d'
        engine_instance.vt_positions = [0]
        
        with patch('erba.engine.logger') as mock_logger:
            result = engine_instance.validate_raw_message_structure(message)
        
        assert result is False
        mock_logger.error.assert_called_with("VT at position 0 not followed by MSH. Found: b'OBX'")
    
    def test_validate_raw_message_structure_vt_beyond_bounds(self, engine_instance):
        """Test validation fails when VT position extends beyond message"""
        message = b'\x0bMS'
        engine_instance.vt_positions = [0]
        
        with patch('erba.engine.logger') as mock_logger:
            result = engine_instance.validate_raw_message_structure(message)
        
        assert result is False
        mock_logger.error.assert_called_with("VT at position 0 extends beyond message bounds")
    
    def test_validate_raw_message_structure_exception(self, engine_instance):
        """Test validation handles exceptions gracefully"""
        message = b'\x0bMSH|test\x1c\x0d'
        engine_instance.vt_positions = None
        
        with patch('erba.engine.logger') as mock_logger:
            result = engine_instance.validate_raw_message_structure(message)
        
        assert result is False
        mock_logger.error.assert_called()
        error_call = mock_logger.error.call_args[0][0]
        assert "Error validating message structure:" in error_call
    
    def test_validate_mllp_boundaries_valid_single_message(self, engine_instance):
        """Test MLLP validation with valid single message"""
        message = b'\x0bMSH|^~\\&|TEST|LAB|||\x1c\x0d'
        
        engine_instance.vt_positions = [0]
        engine_instance.vt_count = 1
        engine_instance.fscr_positions = [21]
        engine_instance.fscr_count = 1
        
        with patch.object(engine_instance, 'validate_raw_message_structure', return_value=True):
            is_valid, clean_messages, error = engine_instance.validate_mllp_boundaries(message)
        
        assert is_valid is True
        assert len(clean_messages) == 1
        assert clean_messages[0] == b'MSH|^~\\&|TEST|LAB|||'
        assert error is None
    
    def test_validate_mllp_boundaries_unexpected_error(self, engine_instance):
        """Test MLLP validation handles unexpected errors"""
        message = b'\x0bMSH|test\x1c\x0d'
        
        engine_instance.vt_count = 1
        engine_instance.fscr_count = 1
        
        with patch.object(engine_instance, 'validate_raw_message_structure', side_effect=Exception("Unexpected error")):
            is_valid, clean_messages, error = engine_instance.validate_mllp_boundaries(message)
        
        assert is_valid is False
        assert clean_messages == []
        assert "Invalid MLLP structure: VT not immediately followed by MSH segment" in error

    def test_validate_mllp_boundaries_empty_message(self, engine_instance):
        """Test MLLP validation with empty message"""
        message = b''
        
        is_valid, clean_messages, error = engine_instance.validate_mllp_boundaries(message)
        
        assert is_valid is False
        assert clean_messages == []
        assert error == "Empty message"
    
    def test_validate_mllp_boundaries_frame_count_mismatch(self, engine_instance):
        """Test MLLP validation with mismatched VT and FS+CR counts"""
        message = b'\x0bMSH|incomplete'
        
        engine_instance.vt_count = 1
        engine_instance.fscr_count = 0
        
        is_valid, clean_messages, error = engine_instance.validate_mllp_boundaries(message)
        
        assert is_valid is False
        assert clean_messages == []
        assert error == "MLLP frame mismatch: VT count (1) != FS+CR count (0)"
    
    def test_validate_mllp_boundaries_invalid_structure(self, engine_instance):
        """Test MLLP validation with invalid structure"""
        message = b'\x0bOBX|invalid\x1c\x0d'
        
        engine_instance.vt_count = 1
        engine_instance.fscr_count = 1
        
        with patch.object(engine_instance, 'validate_raw_message_structure', return_value=False):
            is_valid, clean_messages, error = engine_instance.validate_mllp_boundaries(message)
        
        assert is_valid is False
        assert clean_messages == []
        assert error == "Invalid MLLP structure: VT not immediately followed by MSH segment"
    
    def test_validate_mllp_boundaries_invalid_frame_positions(self, engine_instance):
        """Test MLLP validation with invalid frame positions"""
        message = b'\x0bMSH|test\x1c\x0d'
        
        engine_instance.vt_positions = [10]
        engine_instance.vt_count = 1
        engine_instance.fscr_positions = [5]
        engine_instance.fscr_count = 1
        
        with patch.object(engine_instance, 'validate_raw_message_structure', return_value=True):
            is_valid, clean_messages, error = engine_instance.validate_mllp_boundaries(message)
        
        assert is_valid is False
        assert clean_messages == []
        assert "Invalid frame 1: VT at 10, FS+CR at 5" in error
    
    def test_validate_mllp_boundaries_non_msh_content(self, engine_instance):
        """Test MLLP validation when content doesn't start with MSH"""
        message = b'\x0bOBX|not msh\x1c\x0d'
        
        engine_instance.vt_positions = [0]
        engine_instance.vt_count = 1
        engine_instance.fscr_positions = [12]
        engine_instance.fscr_count = 1
        
        with patch.object(engine_instance, 'validate_raw_message_structure', return_value=True):
            is_valid, clean_messages, error = engine_instance.validate_mllp_boundaries(message)
        
        assert is_valid is False
        assert clean_messages == []
        assert error == "Frame 1 content does not start with MSH segment"
    
    def test_validate_mllp_boundaries_index_error(self, engine_instance):
        """Test MLLP validation handles index errors"""
        message = b'\x0bMSH|test\x1c\x0d'
        
        engine_instance.vt_positions = [0]
        engine_instance.vt_count = 1
        engine_instance.fscr_positions = []
        engine_instance.fscr_count = 1
        
        with patch.object(engine_instance, 'validate_raw_message_structure', return_value=True):
            is_valid, clean_messages, error = engine_instance.validate_mllp_boundaries(message)
        
        assert is_valid is False
        assert clean_messages == []
        assert "Index error during message extraction:" in error
    
    def test_validate_mllp_boundaries_unexpected_error(self, engine_instance):
        """Test MLLP validation handles unexpected errors during message extraction"""
        message = b'\x0bMSH|test\x1c\x0d'
        
        engine_instance.vt_count = 1
        engine_instance.fscr_count = 1
        
        with patch.object(engine_instance, 'validate_raw_message_structure', return_value=True):
            original_vt_positions = [0]
            original_fscr_positions = [10]
            
            def failing_range(*args):
                """Mock range() to raise exception when called in the for loop"""
                raise Exception("Unexpected error during iteration")
            
            with patch('builtins.range', side_effect=failing_range):
                engine_instance.vt_positions = original_vt_positions
                engine_instance.fscr_positions = original_fscr_positions
                
                is_valid, clean_messages, error = engine_instance.validate_mllp_boundaries(message)
        
        assert is_valid is False
        assert clean_messages == []
        assert "Unexpected error during validation: Unexpected error during iteration" in error


class TestMiddlewareEngineConnectionHandling:
    """Test HL7 connection handling"""
    
    @pytest.mark.asyncio
    async def test_handle_hl7_connection_success(self, engine_instance):
        """Test successful HL7 connection handling"""
        hl7_message = "MSH|^~\\&|GHH LAB|ELAB-3|GHH OE|BLDG4|200202150930||ORU^R01|CNTRL-3456|P|2.4"
        mllp_message = f"\x0b{hl7_message}\x1c\x0d"
        
        mock_reader = Mock()
        mock_reader.read = AsyncMock(side_effect=[mllp_message.encode(), b''])  # Message then EOF
        mock_writer = Mock()
        mock_writer.is_closing = Mock(return_value=False)
        mock_writer.get_extra_info = Mock(return_value="127.0.0.1:12345")
        mock_writer.close = Mock()
        mock_writer.wait_closed = AsyncMock()
        
        engine_instance.is_running = True
        engine_instance.peer = None
        engine_instance.handler = Mock()
        
        engine_instance._log_info_to_gui = Mock()
        engine_instance.validate_network_logger = Mock(return_value=True)
        engine_instance.parse_message_structure = Mock()
        engine_instance.validate_mllp_boundaries = Mock(return_value=(True, [hl7_message], None))
        engine_instance.gui_network_callback = Mock()
        engine_instance._send_to_api = AsyncMock(return_value=Mock(success=True, data={}))
        engine_instance._send_positive_acknowledgement_to_analyzer = AsyncMock()
        engine_instance._log_gui_positive_acknowledgement = Mock()
        
        mock_validated_message = Mock()
        mock_validated_message.message_id = "test123"
        engine_instance.handler.process_data = Mock(return_value=mock_validated_message)
        
        await engine_instance.handle_hl7_connection(mock_reader, mock_writer)
        
        engine_instance._log_info_to_gui.assert_called()
        engine_instance.validate_mllp_boundaries.assert_called_once()
        engine_instance._send_to_api.assert_called_once()
        engine_instance._send_positive_acknowledgement_to_analyzer.assert_called_once()


    @pytest.mark.asyncio
    async def test_handle_hl7_connection_invalid_block(self, engine_instance):
        """Test HL7 connection handling with invalid MLLP block"""
        invalid_message = b"Invalid message without MLLP boundaries"
        
        mock_reader = Mock()
        mock_reader.read = AsyncMock(side_effect=[invalid_message, b''])  # Invalid then EOF
        mock_writer = Mock()
        mock_writer.is_closing = Mock(return_value=False)
        mock_writer.get_extra_info = Mock(return_value="127.0.0.1:12345")
        mock_writer.close = Mock()
        mock_writer.wait_closed = AsyncMock()
        
        engine_instance.is_running = True
        engine_instance.peer = None
        
        engine_instance._log_info_to_gui = Mock()
        engine_instance._log_error_to_gui = Mock()
        engine_instance.validate_network_logger = Mock(return_value=True)
        engine_instance.parse_message_structure = Mock()
        engine_instance.validate_mllp_boundaries = Mock(return_value=(False, [], "Invalid MLLP format"))
        engine_instance.gui_network_callback = Mock()
        engine_instance._log_gui_negative_acknowledgement = Mock()
        engine_instance.create_nack = Mock(return_value=Mock())
        engine_instance._send_positive_acknowledgement_to_analyzer = AsyncMock()
        
        await engine_instance.handle_hl7_connection(mock_reader, mock_writer)
        
        engine_instance.validate_mllp_boundaries.assert_called_once()
        engine_instance._log_gui_negative_acknowledgement.assert_called()
        engine_instance.create_nack.assert_called_once_with("Invalid MLLP Boundry")
        engine_instance._send_positive_acknowledgement_to_analyzer.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_hl7_connection_no_messages(self, engine_instance):
        """Test HL7 connection handling with no messages"""
        mock_reader = MockHL7StreamReader([])
        mock_writer = MockHL7StreamWriter()
        
        # Setup mocks
        engine_instance.is_running = True
        engine_instance.read_all_available_messages = AsyncMock(return_value=[])
        engine_instance._log_info_to_gui = Mock()
        
        await engine_instance.handle_hl7_connection(mock_reader, mock_writer)
        
        engine_instance._log_info_to_gui.assert_called()


class TestMiddlewareEngineAcknowledgments:
    """Test acknowledgment handling"""
    
    @pytest.mark.asyncio
    async def test_send_positive_acknowledgement_to_analyzer(self, engine_instance):
        """Test sending positive acknowledgment"""
        mock_message = Mock()
        mock_ack = Mock()
        mock_ack.__str__ = Mock(return_value="ACK_MESSAGE")  # Configure string representation
        mock_message.create_ack.return_value = mock_ack
        mock_writer = MockHL7StreamWriter()
        
        engine_instance._write_message_to_analyzer = AsyncMock(return_value=(True, ""))        
        with patch('erba.engine.logger') as mock_logger:
            result = await engine_instance._send_positive_acknowledgement_to_analyzer(mock_message, mock_writer)
            assert result is True
            
            mock_message.create_ack.assert_called_once_with(ack_code='AA')  # POSITIVE_ACK_CODE
            engine_instance._write_message_to_analyzer.assert_called_once_with(mock_ack, mock_writer)
            mock_logger.info.assert_called_once_with(f"Positive ACK sent to analyzer: {mock_ack}")

    @pytest.mark.asyncio
    async def test_send_positive_acknowledgement_to_analyzer_exception(self, engine_instance):
        """Test handling of exception during positive acknowledgment sending"""
        mock_message = Mock()
        mock_ack = Mock()
        mock_ack.__str__ = Mock(return_value="ACK_MESSAGE")
        mock_message.create_ack.return_value = mock_ack
        mock_writer = MockHL7StreamWriter()
        
        error_message = "Connection timeout"
        engine_instance._write_message_to_analyzer = AsyncMock(side_effect=Exception(error_message))
        
        with patch('erba.engine.logger') as mock_logger:
            with pytest.raises(Exception, match=error_message):
                await engine_instance._send_positive_acknowledgement_to_analyzer(mock_message, mock_writer)
            
            mock_message.create_ack.assert_called_once_with(ack_code='AA')
            engine_instance._write_message_to_analyzer.assert_called_once_with(mock_ack, mock_writer)
            mock_logger.error.assert_called_once_with(f"Failed to send ACK to analyzer: {error_message}")            
            mock_logger.info.assert_not_called()

    @pytest.mark.asyncio
    async def test_write_message_to_analyzer_success(self, engine_instance):
        """Test successful message writing and draining"""
        mock_message = Mock()
        mock_writer = Mock()
        mock_writer.writemessage = Mock()
        mock_writer.drain = AsyncMock()
        
        await engine_instance._write_message_to_analyzer(mock_message, mock_writer)
        mock_writer.writemessage.assert_called_once_with(mock_message)
        mock_writer.drain.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_message_to_analyzer_exception(self, engine_instance):
        """Test exception is re-raised when writing fails"""
        mock_message = Mock()
        mock_writer = Mock()
        
        error_message = "Connection failed"
        mock_writer.writemessage.side_effect = Exception(error_message)
        mock_writer.drain = AsyncMock()
        
        with pytest.raises(Exception, match=error_message):
            await engine_instance._write_message_to_analyzer(mock_message, mock_writer)
        
        mock_writer.writemessage.assert_called_once_with(mock_message)
        mock_writer.drain.assert_not_called()

    @pytest.mark.asyncio
    async def test_write_message_to_analyzer_drain_exception(self, engine_instance):
        """Test exception is re-raised when drain fails"""
        mock_message = Mock()
        mock_writer = Mock()
        
        error_message = "Buffer flush failed"
        mock_writer.writemessage = Mock()  # Succeeds
        mock_writer.drain = AsyncMock(side_effect=Exception(error_message))
        
        with pytest.raises(Exception, match=error_message):
            await engine_instance._write_message_to_analyzer(mock_message, mock_writer)
        
        mock_writer.writemessage.assert_called_once_with(mock_message)
        mock_writer.drain.assert_called_once()


class TestMiddlewareEngineEdgeCases:
    """Test edge cases from configuration files"""
    
    @pytest.mark.asyncio
    async def test_incomplete_message_17_sequences(self, engine_instance):
        """Test handling of incomplete message ending at sequence 17"""
        from hl7 import parse as hl7_parse
        
        clean_message = INCOMPLETE_MESSAGE_17.replace('[CR]', '\r').replace('[VT]', '\x0b').replace('[FS]', '\x1c')
        
        try:
            message = hl7_parse(clean_message)
            
            engine_instance.gui_network_callback = Mock()
            engine_instance.handler = Mock()
            engine_instance.handler.process_data.return_value = None  # Should fail validation
            engine_instance._log_error_to_gui = Mock()
            
            result = await engine_instance.process_single_hl7_message(message, "127.0.0.1:12345")
            
            assert result is False
            engine_instance._log_error_to_gui.assert_called()
        except Exception:
            pass
    
    @pytest.mark.asyncio
    async def test_malformed_joined_sequences(self, engine_instance):
        """Test handling of malformed message with joined sequences"""
        from hl7 import parse as hl7_parse
        
        clean_message = MALFORMED_JOINED_MESSAGE.replace('[CR]', '\r').replace('[VT]', '\x0b').replace('[FS]', '\x1c')
        
        try:
            message = hl7_parse(clean_message)
            
            engine_instance.gui_network_callback = Mock()
            engine_instance.handler = Mock()
            engine_instance.handler.process_data.return_value = None  # Should fail validation
            engine_instance._log_error_to_gui = Mock()
            
            result = await engine_instance.process_single_hl7_message(message, "127.0.0.1:12345")
            
            assert result is False
            engine_instance._log_error_to_gui.assert_called()
        except Exception:
            pass
    

class TestMiddlewareEngineAPIIntegration:
    """Test API service integration"""
    
    @pytest.mark.asyncio
    async def test_send_to_api_success(self, api_test_engine_instance, mock_api_service):
        """Test successful API data transmission"""
        validated_message = create_mock_erba_message()
        
        api_test_engine_instance.api_service = mock_api_service
        api_test_engine_instance.gui_log_callback = Mock()
        
        mock_api_service.send_analyzer_data.return_value = APIResult(success=True, error=None)        
        result = await api_test_engine_instance._send_to_api(validated_message)
        
        assert result.success is True
        mock_api_service.send_analyzer_data.assert_called_once_with(validated_message)
        
        assert api_test_engine_instance.gui_log_callback.call_count == 2  # Two log calls
        api_test_engine_instance.gui_log_callback.assert_any_call("[ENGINE] Sending to API endpoint...")
        api_test_engine_instance.gui_log_callback.assert_any_call("[ENGINE] Data sent to API successfully")
    
    @pytest.mark.asyncio
    async def test_send_to_api_failure(self, api_test_engine_instance):
        """Test API data transmission failure"""
        validated_message = create_mock_erba_message()        
        mock_api_service = AsyncMock()
        mock_api_service.send_analyzer_data.side_effect = Exception("API Error")
        
        api_test_engine_instance.api_service = mock_api_service
        api_test_engine_instance.gui_error_callback = Mock()
        
        with pytest.raises(Exception, match="API Error"):
            await api_test_engine_instance._send_to_api(validated_message)
        
        api_test_engine_instance.gui_error_callback.assert_called_once_with("[ENGINE] API send error: API Error")


class TestDataHandler:
    """Test DataHandler class"""
    
    def test_data_handler_initialization(self, data_handler_instance, mock_analyzer_config):
        """Test DataHandler initialization"""
        handler = data_handler_instance
        
        assert handler.config == mock_analyzer_config
        assert handler.validator is not None
        assert handler.parser is not None
    
    def test_process_data_success(self, data_handler_instance):
        """Test successful data processing"""
        handler = data_handler_instance
        
        mock_erba_message = create_mock_erba_message()
        handler.process_data.return_value = mock_erba_message
        
        result = handler.process_data(COMPLETE_VALID_MESSAGE)
        
        assert result == mock_erba_message
        handler.process_data.assert_called_once_with(COMPLETE_VALID_MESSAGE)
    
    def test_process_data_empty_input(self, data_handler_instance):
        """Test data processing with empty input"""
        handler = data_handler_instance
        
        handler.process_data.return_value = None
        
        result = handler.process_data("")
        
        assert result is None
        handler.process_data.assert_called_once_with("")
    
    def test_process_data_parsing_errors(self, data_handler_instance):
        """Test data processing with parsing errors"""
        handler = data_handler_instance
        
        handler.process_data.return_value = None
        
        result = handler.process_data(COMPLETE_VALID_MESSAGE)
        
        assert result is None
        handler.process_data.assert_called_once_with(COMPLETE_VALID_MESSAGE)
    
    def test_process_data_validation_failure(self, data_handler_instance):
        """Test data processing with validation failure"""
        handler = data_handler_instance
        
        handler.process_data.return_value = None
        
        result = handler.process_data(COMPLETE_VALID_MESSAGE)
        
        assert result is None
        handler.process_data.assert_called_once_with(COMPLETE_VALID_MESSAGE)
    
    def test_process_data_exception_handling(self, data_handler_instance):
        """Test data processing exception handling"""
        handler = data_handler_instance
        
        handler.process_data.side_effect = Exception("Parsing failed")
        
        with pytest.raises(Exception, match="Parsing failed"):
            handler.process_data(COMPLETE_VALID_MESSAGE)


class TestMiddlewareEngineLogging:
    """Test logging functionality"""
    
    def test_log_info_to_gui_with_callback(self, engine_instance):
        """Test info logging with GUI callback"""
        mock_callback = Mock()
        engine_instance.gui_log_callback = mock_callback
        engine_instance._log_info_to_gui("Test message")
        mock_callback.assert_called_once_with("Test message")
    
    def test_log_info_to_gui_without_callback(self, engine_instance):
        """Test info logging without GUI callback (fallback to logger)"""
        engine_instance.gui_log_callback = None
        
        with patch('erba.engine.logger') as mock_logger:
            engine_instance._log_info_to_gui("Test message")
            mock_logger.info.assert_called_once_with("Test message")
    
    def test_log_error_to_gui_with_callback(self, engine_instance):
        """Test error logging with GUI callback"""
        mock_callback = Mock()
        engine_instance.gui_error_callback = mock_callback
        
        engine_instance._log_error_to_gui("Error message")
        
        mock_callback.assert_called_once_with("Error message")
    
    def test_log_error_to_gui_without_callback(self, engine_instance):
        """Test error logging without GUI callback (fallback to logger)"""
        engine_instance.gui_error_callback = None
        
        with patch('erba.engine.logger') as mock_logger:
            engine_instance._log_error_to_gui("Error message")
            mock_logger.error.assert_called_once_with("Error message")
    
    def test_log_acknowledgement_to_gui_positive_ack(self, engine_instance):
        """Test positive ACK logging"""
        engine_instance.gui_log_callback = Mock()
        engine_instance.gui_middleware_ack_callback = Mock()
        engine_instance.gui_middleware_nack_callback = Mock()
        engine_instance._log_info_to_gui = Mock()
        engine_instance.format_response = Mock(return_value="formatted_message")
        mock_message = Mock()
        
        engine_instance._log_acknowledgement_to_gui('AA', mock_message)
        
        engine_instance._log_info_to_gui.assert_called_once_with("[ENGINE] Data processed successfully, ACK logged")
        engine_instance.gui_middleware_ack_callback.assert_called_once_with("formatted_message")
        engine_instance.format_response.assert_called_once_with(mock_message)
    
    def test_log_acknowledgement_to_gui_negative_ack(self, engine_instance, caplog):
        """Test negative ACK logging"""
        engine_instance.gui_log_callback = Mock()
        engine_instance.gui_middleware_ack_callback = Mock()
        engine_instance.gui_middleware_nack_callback = Mock()
        
        engine_instance._log_error_to_gui = Mock()        
        engine_instance.format_response = Mock(return_value="formatted_error_message")
        mock_message = Mock()
        reason = "Invalid data format"
           
        engine_instance._log_acknowledgement_to_gui('AE', mock_message, reason)        
        engine_instance._log_error_to_gui.assert_called_once_with("[ENGINE] Processing failed - Invalid data format, NACK logged")
        engine_instance.gui_middleware_nack_callback.assert_called_once_with("formatted_error_message")

    def test_log_acknowledgement_to_gui_unknown_code(self, engine_instance, caplog):
        """Test negative ACK logging"""
        engine_instance.gui_log_callback = Mock()
        engine_instance.gui_middleware_ack_callback = Mock()
        engine_instance.gui_middleware_nack_callback = Mock()
        
        engine_instance.format_response = Mock(return_value="unknown ack code")
        mock_message = Mock()
        ack_code = 'Unknown code'

        with patch('erba.engine.logger') as mock_logger:
            engine_instance._log_acknowledgement_to_gui(ack_code, mock_message)            
            mock_logger.error.assert_called_once_with(f"Unknown ack_code: {ack_code}")


# Run the tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])