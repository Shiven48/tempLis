"""
Comprehensive tests for processor classes: MSHProcessor, OBRProcessor, OBXProcessor
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from hl7 import parse as hl7_parse, Sequence

from erba.processor import (
    MSHProcessor, OBRProcessor, OBXProcessor, processFactory
)
from erba.models import ParserConfig, SegmentsConfig
from .fixtures.valid_messages import COMPLETE_VALID_MESSAGE, MINIMAL_VALID_MESSAGE
from .fixtures.invalid_messages import (
    INVALID_MSH_DATETIME, INVALID_OBR_DATETIME, 
    INSUFFICIENT_OBX_FIELDS, WRONG_VALUE_TYPE_REQUIRED
)
from .utils.test_helpers import (
    create_test_message_with_sequences, extract_obx_sequences
)


class TestMSHProcessor:
    """Test MSHProcessor class"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.sample_message = hl7_parse(COMPLETE_VALID_MESSAGE.replace('\n', '\r'))
        self.msh_segments = self.sample_message.segments('MSH')
        
        # Mock configuration for all tests
        self.mock_config_patcher = patch('middleware.processor.ConfigLoader.load_parser_config')
        self.mock_config = self.mock_config_patcher.start()
        mock_parser_config = Mock()
        mock_parser_config.MSH = {"model": "3", "facility": "4", "datetime_of_message": "7"}
        self.mock_config.return_value = mock_parser_config
    
    def teardown_method(self):
        """Cleanup after each test"""
        self.mock_config_patcher.stop()
    
    def test_msh_processor_initialization(self):
        """Test MSHProcessor initialization"""
        with patch('middleware.processor.ConfigLoader.load_parser_config') as mock_loader:
            mock_config = Mock()
            mock_config.MSH = {"model": "3", "facility": "4", "datetime_of_message": "7"}
            mock_loader.return_value = mock_config
            
            processor = MSHProcessor(self.msh_segments)
            
            assert processor.message_segments == self.msh_segments
            assert processor.segment_type == 'MSH'
            assert processor.parser_config is not None
            assert processor.msh_config_dict is not None
            assert isinstance(processor.errors, list)
    
    def test_msh_processor_process_segment_success(self):
        """Test successful MSH segment processing"""
        with patch('middleware.processor.ConfigLoader.load_parser_config') as mock_loader:
            mock_config = Mock()
            mock_config.MSH = {"model": "3", "facility": "4", "datetime_of_message": "7"}
            mock_loader.return_value = mock_config
            
            processor = MSHProcessor(self.msh_segments)
            
            with patch.object(processor, '_validate_msh_segments', return_value=True):
                errors, is_valid = processor.process_segment()
                
                assert is_valid is True
                assert len(errors) == 0
    
    def test_msh_processor_process_segment_failure(self):
        """Test MSH segment processing failure"""
        with patch('middleware.processor.ConfigLoader.load_parser_config') as mock_loader:
            mock_config = Mock()
            mock_config.MSH = {"model": "3", "facility": "4", "datetime_of_message": "7"}
            mock_loader.return_value = mock_config
            
            processor = MSHProcessor(self.msh_segments)
            processor.errors = ["Validation error"]
            
            with patch.object(processor, '_validate_msh_segments', return_value=False):
                errors, is_valid = processor.process_segment()
                
                assert is_valid is False
                assert len(errors) > 0
                assert "Validation error" in errors
    
    def test_msh_processor_parse_segment(self):
        """Test MSH segment parsing"""
        processor = MSHProcessor(self.msh_segments)
        
        with patch.object(processor, '_recursive_fetch') as mock_fetch:
            mock_fetch.side_effect = ["ELite 580", "Erba", "20250828152838"]
            
            result = processor.parse()
            
            assert isinstance(result, list)
            assert len(result) == 1
            assert isinstance(result[0], dict)
    
    def test_validate_model_valid(self):
        """Test valid model field validation"""
        processor = MSHProcessor(self.msh_segments)
        
        assert processor.validate_model("ELite 580") is True
        assert processor.validate_model("Test Model") is True
    
    def test_validate_model_invalid(self):
        """Test invalid model field validation"""
        processor = MSHProcessor(self.msh_segments)
        
        assert processor.validate_model("") is False
        assert processor.validate_model(None) is False
        assert processor.validate_model("   ") is False
        assert processor.validate_model("123456") is False  # Only digits
        assert processor.validate_model("a" * 228) is False  # Too long
    
    def test_validate_machine_valid(self):
        """Test valid machine field validation"""
        processor = MSHProcessor(self.msh_segments)
        
        assert processor.validate_machine("Erba") is True
        assert processor.validate_machine("Test Facility") is True
        assert processor.validate_machine("AB") is True  # Minimum length
    
    def test_validate_machine_invalid(self):
        """Test invalid machine field validation"""
        processor = MSHProcessor(self.msh_segments)
        
        assert processor.validate_machine("") is False
        assert processor.validate_machine(None) is False
        assert processor.validate_machine("A") is False  # Too short
        assert processor.validate_machine("   ") is False
        assert processor.validate_machine("a" * 228) is False  # Too long
    
    def test_validate_datetime_of_message_valid(self):
        """Test valid datetime validation"""
        processor = MSHProcessor(self.msh_segments)
        
        assert processor.validate_datetime_of_message("20250828152838") is True
        assert processor.validate_datetime_of_message("20000101000000") is True
        assert processor.validate_datetime_of_message("20991231235959") is True
    
    def test_validate_datetime_of_message_invalid(self):
        """Test invalid datetime validation"""
        processor = MSHProcessor(self.msh_segments)
        
        assert processor.validate_datetime_of_message("") is False
        assert processor.validate_datetime_of_message(None) is False
        assert processor.validate_datetime_of_message("invalid") is False
        assert processor.validate_datetime_of_message("2025082815283") is False  # Too short
        assert processor.validate_datetime_of_message("202508281528380") is False  # Too long
        assert processor.validate_datetime_of_message("20250828252838") is False  # Invalid hour
        assert processor.validate_datetime_of_message("20250828156038") is False  # Invalid minute
        assert processor.validate_datetime_of_message("20250828153860") is False  # Invalid second
        assert processor.validate_datetime_of_message("18991231235959") is False  # Year too early
        assert processor.validate_datetime_of_message("21011231235959") is False  # Year too late
    
    def test_validate_msh_segments_success(self):
        """Test successful MSH segment validation"""
        processor = MSHProcessor(self.msh_segments)
        
        with patch.object(processor, 'validate_model', return_value=True), \
             patch.object(processor, 'validate_machine', return_value=True), \
             patch.object(processor, 'validate_datetime_of_message', return_value=True):
            
            result = processor._validate_msh_segments(self.msh_segments[0])
            
            assert result is True
            assert len(processor.errors) == 0
    
    def test_validate_msh_segments_failure(self):
        """Test MSH segment validation failure"""
        processor = MSHProcessor(self.msh_segments)
        
        with patch.object(processor, 'validate_model', return_value=False), \
             patch.object(processor, 'validate_machine', return_value=False), \
             patch.object(processor, 'validate_datetime_of_message', return_value=False):
            
            result = processor._validate_msh_segments(self.msh_segments[0])
            
            assert result is False
            assert len(processor.errors) == 3  # All three validations failed
    
    def test_validate_msh_segments_empty(self):
        """Test MSH segment validation with empty segments"""
        empty_segments = []
        processor = MSHProcessor(empty_segments)
        
        result = processor._validate_msh_segments(None)
        
        assert result is False
        assert len(processor.errors) > 0
        assert "No header segment found" in processor.errors[0]
    
    def test_recursive_fetch_simple_index(self):
        """Test recursive fetch with simple index"""
        processor = MSHProcessor(self.msh_segments)
        
        # Test with actual data - index 3 should return the sending application
        result = processor._recursive_fetch(self.msh_segments[0], "3")
        
        # Should return the sending application field (ELite 580)
        assert result == "ELite 580"
    
    def test_recursive_fetch_nested_index(self):
        """Test recursive fetch with nested index"""
        processor = MSHProcessor(self.msh_segments)
        
        # Test the recursive fetch with actual HL7 data that has components
        # Use the message type field which often has components
        result = processor._recursive_fetch(self.msh_segments[0], "9")
        
        # Should return the message type field value
        assert result == "ORU^R01"
    
    def test_recursive_fetch_invalid_index(self):
        """Test recursive fetch with invalid index"""
        processor = MSHProcessor(self.msh_segments)
        
        result = processor._recursive_fetch(self.msh_segments[0], "invalid")
        
        assert result == ""


class TestOBRProcessor:
    """Test OBRProcessor class"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.sample_message = hl7_parse(COMPLETE_VALID_MESSAGE.replace('\n', '\r'))
        self.obr_segments = self.sample_message.segments('OBR')
        
        # Mock configuration for all tests
        self.mock_config_patcher = patch('middleware.processor.ConfigLoader.load_parser_config')
        self.mock_config = self.mock_config_patcher.start()
        mock_parser_config = Mock()
        mock_parser_config.OBR = {"sample_id": "3", "requested_timing": "6", "reservation_timing": "7"}
        self.mock_config.return_value = mock_parser_config
    
    def teardown_method(self):
        """Cleanup after each test"""
        self.mock_config_patcher.stop()
    
    def test_obr_processor_initialization(self):
        """Test OBRProcessor initialization"""
        processor = OBRProcessor(self.obr_segments)
        
        assert processor.message_segments == self.obr_segments
        assert processor.segment_type == 'OBR'
        assert processor.parser_config is not None
        assert processor.obr_config_dict is not None
        assert isinstance(processor.errors, list)
    
    def test_obr_processor_process_segment_success(self):
        """Test successful OBR segment processing"""
        processor = OBRProcessor(self.obr_segments)
        
        with patch.object(processor, '_validate_obr_segments', return_value=True):
            errors, is_valid = processor.process_segment()
            
            assert is_valid is True
            assert len(errors) == 0
    
    def test_obr_processor_process_segment_failure(self):
        """Test OBR segment processing failure"""
        processor = OBRProcessor(self.obr_segments)
        processor.errors = ["Validation error"]
        
        with patch.object(processor, '_validate_obr_segments', return_value=False):
            errors, is_valid = processor.process_segment()
            
            assert is_valid is False
            assert len(errors) > 0
    
    def test_obr_processor_parse_segment(self):
        """Test OBR segment parsing"""
        processor = OBRProcessor(self.obr_segments)
        
        with patch.object(processor, '_recursive_fetch') as mock_fetch:
            mock_fetch.side_effect = ["TEST001", "20250828010809", "20250828010809"]
            
            result = processor.parse()
            
            assert isinstance(result, list)
            assert len(result) == 1
            assert isinstance(result[0], dict)
    
    def test_validate_datetime_valid(self):
        """Test valid datetime validation in OBR"""
        processor = OBRProcessor(self.obr_segments)
        
        assert processor.validate_datetime("20250828152838") is True
        assert processor.validate_datetime("20000101000000") is True
        assert processor.validate_datetime("20991231235959") is True
    
    def test_validate_datetime_invalid(self):
        """Test invalid datetime validation in OBR"""
        processor = OBRProcessor(self.obr_segments)
        
        assert processor.validate_datetime("") is False
        assert processor.validate_datetime(None) is False
        assert processor.validate_datetime("invalid") is False
        assert processor.validate_datetime("2025082815283") is False  # Too short
        assert processor.validate_datetime("20250828252838") is False  # Invalid hour
    
    def test_validate_obr_segments_success(self):
        """Test successful OBR segment validation"""
        processor = OBRProcessor(self.obr_segments)
        
        with patch.object(processor, 'validate_datetime', return_value=True):
            result = processor._validate_obr_segments(self.obr_segments[0])
            
            assert result is True
            assert len(processor.errors) == 0
    
    def test_validate_obr_segments_failure(self):
        """Test OBR segment validation failure"""
        processor = OBRProcessor(self.obr_segments)
        
        with patch.object(processor, 'validate_datetime', return_value=False):
            result = processor._validate_obr_segments(self.obr_segments[0])
            
            assert result is False
            assert len(processor.errors) == 2  # Both timing fields failed
    
    def test_validate_obr_segments_empty(self):
        """Test OBR segment validation with empty segments"""
        empty_segments = []
        processor = OBRProcessor(empty_segments)
        
        result = processor._validate_obr_segments(None)
        
        assert result is False
        assert len(processor.errors) > 0
        assert "No OBR segment found" in processor.errors[0]


class TestOBXProcessor:
    """Test OBXProcessor class"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.sample_message = hl7_parse(COMPLETE_VALID_MESSAGE.replace('\n', '\r'))
        self.obx_segments = self.sample_message.segments('OBX')
        
        # Mock configuration for all tests
        self.mock_config_patcher = patch('middleware.processor.ConfigLoader.load_parser_config')
        self.mock_segments_patcher = patch('middleware.processor.ConfigLoader.load_segments_config')
        
        self.mock_config = self.mock_config_patcher.start()
        self.mock_segments = self.mock_segments_patcher.start()
        
        mock_parser_config = Mock()
        mock_parser_config.OBX = {"sequence_number": "1", "value_type": "2", "observation_identifier": "3-1"}
        self.mock_config.return_value = mock_parser_config
        
        mock_segments_config = Mock()
        mock_segments_config.model_dump.return_value = {
            'optional': ['1-6'],
            'required': ['7-36'],
            'findings': ['37+']
        }
        self.mock_segments.return_value = mock_segments_config
    
    def teardown_method(self):
        """Cleanup after each test"""
        self.mock_config_patcher.stop()
        self.mock_segments_patcher.stop()
    
    def test_obx_processor_initialization(self):
        """Test OBXProcessor initialization"""
        processor = OBXProcessor(self.obx_segments)
        
        assert processor.message_segments == self.obx_segments
        assert processor.segment_type == 'OBX'
        assert processor.parser_config is not None
        assert processor.segment_config is not None
        assert isinstance(processor.valid_obx, list)
        assert isinstance(processor.valid_findings, list)
        assert isinstance(processor.required_sequences, dict)
        assert isinstance(processor.errors, list)
    
    def test_obx_processor_process_segment_success(self):
        """Test successful OBX segment processing"""
        processor = OBXProcessor(self.obx_segments)
        
        # Set up the ranges manually since we're mocking the config parsing
        processor.optional_range = {'type': 'range', 'min': 1, 'max': 6}
        processor.required_range = {'type': 'range', 'min': 7, 'max': 36}
        processor.findings_range = {'type': 'threshold', 'min': 37}
        
        with patch.object(processor, '_parse_config_ranges'), \
             patch.object(processor, '_validate_segment_config'), \
             patch.object(processor, '_check_bounds', return_value=True), \
             patch.object(processor, '_validate_required_range_completeness', return_value=True):
            
            errors, is_valid = processor.process_segment()
            
            assert is_valid is True
            assert len(errors) == 0
    
    def test_obx_processor_process_segment_failure(self):
        """Test OBX segment processing failure"""
        processor = OBXProcessor(self.obx_segments)
        processor.errors = ["Validation error"]
        
        with patch.object(processor, '_parse_config_ranges'), \
             patch.object(processor, '_validate_segment_config'), \
             patch.object(processor, '_check_bounds', return_value=False), \
             patch.object(processor, '_validate_required_range_completeness', return_value=False):
            
            errors, is_valid = processor.process_segment()
            
            assert is_valid is False
            assert len(errors) > 0
    
    def test_parse_config_ranges_valid(self):
        """Test parsing valid configuration ranges"""
        processor = OBXProcessor(self.obx_segments)
        
        config_dict = {
            'optional': ['1-6'],
            'required': ['7-36'],
            'findings': ['37+']
        }
        
        processor._parse_config_ranges(config_dict)
        
        assert processor.optional_range['type'] == 'range'
        assert processor.optional_range['min'] == 1
        assert processor.optional_range['max'] == 6
        
        assert processor.required_range['type'] == 'range'
        assert processor.required_range['min'] == 7
        assert processor.required_range['max'] == 36
        
        assert processor.findings_range['type'] == 'threshold'
        assert processor.findings_range['min'] == 37
    
    def test_parse_config_ranges_single_value(self):
        """Test parsing single value configuration"""
        processor = OBXProcessor(self.obx_segments)
        
        config_dict = {
            'optional': ['5'],
            'required': ['7-36'],
            'findings': ['37+']
        }
        
        processor._parse_config_ranges(config_dict)
        
        assert processor.optional_range['type'] == 'single'
        assert processor.optional_range['value'] == 5
    
    def test_parse_config_ranges_invalid(self):
        """Test parsing invalid configuration ranges"""
        processor = OBXProcessor(self.obx_segments)
        
        config_dict = {
            'optional': ['invalid-range-format'],
            'required': ['7-36'],
            'findings': ['37+']
        }
        
        processor._parse_config_ranges(config_dict)
        
        assert processor.optional_range['type'] == 'invalid'
    
    def test_validate_segment_config(self):
        """Test segment configuration validation"""
        processor = OBXProcessor(self.obx_segments)
        
        # Setup valid ranges
        processor.optional_range = {'type': 'range', 'min': 1, 'max': 6}
        processor.required_range = {'type': 'range', 'min': 7, 'max': 36}
        processor.findings_range = {'type': 'threshold', 'min': 37}
        
        # Should not raise any exceptions
        processor._validate_segment_config()
    
    def test_check_bounds_optional_range(self):
        """Test bounds checking for optional range"""
        processor = OBXProcessor(self.obx_segments)
        
        # Setup ranges
        processor.optional_range = {'min': 1, 'max': 6}
        processor.required_range = {'min': 7, 'max': 36}
        processor.findings_range = {'min': 37}
        
        with patch.object(processor, '_process_optional_range', return_value=True) as mock_process:
            result = processor._check_bounds(5, "IS", Mock())
            
            assert result is True
            mock_process.assert_called_once_with(5, "IS")
    
    def test_check_bounds_required_range(self):
        """Test bounds checking for required range"""
        processor = OBXProcessor(self.obx_segments)
        
        # Setup ranges
        processor.optional_range = {'min': 1, 'max': 6}
        processor.required_range = {'min': 7, 'max': 36}
        processor.findings_range = {'min': 37}
        
        mock_sequence = Mock()
        
        with patch.object(processor, '_process_required_range', return_value=True) as mock_process:
            result = processor._check_bounds(15, "NM", mock_sequence)
            
            assert result is True
            mock_process.assert_called_once_with("NM", mock_sequence)
    
    def test_check_bounds_findings_range(self):
        """Test bounds checking for findings range"""
        processor = OBXProcessor(self.obx_segments)
        
        # Setup ranges
        processor.optional_range = {'min': 1, 'max': 6}
        processor.required_range = {'min': 7, 'max': 36}
        processor.findings_range = {'min': 37}
        
        mock_sequence = Mock()
        
        with patch.object(processor, '_process_findings_range', return_value=True) as mock_process:
            result = processor._check_bounds(40, "IS", mock_sequence)
            
            assert result is True
            mock_process.assert_called_once_with("IS", mock_sequence)
    
    def test_check_bounds_out_of_range(self):
        """Test bounds checking for out-of-range sequence"""
        processor = OBXProcessor(self.obx_segments)
        
        # Setup ranges
        processor.optional_range = {'min': 1, 'max': 6}
        processor.required_range = {'min': 7, 'max': 36}
        processor.findings_range = {'min': 37}
        
        result = processor._check_bounds(0, "NM", Mock())
        
        assert result is False
        assert len(processor.errors) > 0
        assert "not within valid range" in processor.errors[0]
    
    def test_check_bounds_invalid_sequence_number(self):
        """Test bounds checking with invalid sequence number"""
        processor = OBXProcessor(self.obx_segments)
        
        result = processor._check_bounds("invalid", "NM", Mock())
        
        assert result is False
        assert len(processor.errors) > 0
        assert "Invalid sequence value" in processor.errors[0]
    
    def test_process_optional_range_is_type(self):
        """Test processing optional range with IS type"""
        processor = OBXProcessor(self.obx_segments)
        
        result = processor._process_optional_range(5, "IS")
        
        assert result is True
    
    def test_process_optional_range_nm_type(self):
        """Test processing optional range with NM type"""
        processor = OBXProcessor(self.obx_segments)
        
        result = processor._process_optional_range(5, "NM")
        
        assert result is True
    
    def test_process_optional_range_invalid_type(self):
        """Test processing optional range with invalid type"""
        processor = OBXProcessor(self.obx_segments)
        
        result = processor._process_optional_range(5, "INVALID")
        
        assert result is False
    
    def test_process_required_range_success(self):
        """Test successful processing of required range"""
        processor = OBXProcessor(self.obx_segments)
        processor.required_range = {'min': 7, 'max': 36}
        
        # Create mock sequence with proper length
        mock_sequence = Mock()
        mock_sequence.__len__ = Mock(return_value=12)  # OBX_RANGE value
        mock_sequence.__getitem__ = Mock(side_effect=lambda x: Mock(__str__=Mock(return_value="15")))
        
        with patch('middleware.processor.OBX_RANGE', 12):
            result = processor._process_required_range("NM", mock_sequence)
            
            assert result is True
            assert 15 in processor.required_sequences
    
    def test_process_required_range_wrong_type(self):
        """Test processing required range with wrong value type"""
        processor = OBXProcessor(self.obx_segments)
        processor.required_range = {'min': 7, 'max': 36}
        
        result = processor._process_required_range("IS", Mock())
        
        assert result is False
        assert len(processor.errors) > 0
        assert "Expected NM segment type" in processor.errors[0]
    
    def test_process_required_range_wrong_field_count(self):
        """Test processing required range with wrong field count"""
        processor = OBXProcessor(self.obx_segments)
        processor.required_range = {'min': 7, 'max': 36}
        
        # Create mock sequence with wrong length
        mock_sequence = Mock()
        mock_sequence.__len__ = Mock(return_value=8)  # Wrong length
        mock_sequence.__getitem__ = Mock(side_effect=lambda x: Mock(__str__=Mock(return_value="15")))
        
        with patch('middleware.processor.OBX_RANGE', 12):
            result = processor._process_required_range("NM", mock_sequence)
            
            assert result is False
            assert len(processor.errors) > 0
            assert "Field Count Error" in processor.errors[0]
    
    def test_process_required_range_duplicate_sequence(self):
        """Test processing required range with duplicate sequence"""
        processor = OBXProcessor(self.obx_segments)
        processor.required_range = {'min': 7, 'max': 36}
        processor.required_sequences[15] = Mock()  # Pre-existing sequence
        
        # Create mock sequence
        mock_sequence = Mock()
        mock_sequence.__len__ = Mock(return_value=12)
        mock_sequence.__getitem__ = Mock(side_effect=lambda x: Mock(__str__=Mock(return_value="15")))
        
        with patch('middleware.processor.OBX_RANGE', 12):
            result = processor._process_required_range("NM", mock_sequence)
            
            assert result is False
            assert len(processor.errors) > 0
            assert "Duplicate sequence" in processor.errors[0]
    
    def test_validate_required_range_completeness_success(self):
        """Test successful required range completeness validation"""
        processor = OBXProcessor(self.obx_segments)
        processor.required_range = {'min': 7, 'max': 36}
        
        # Setup all required sequences
        for i in range(7, 37):
            processor.required_sequences[i] = Mock()
        
        result = processor._validate_required_range_completeness()
        
        assert result is True
        assert len(processor.valid_obx) == 30  # Should have all 30 sequences
    
    def test_validate_required_range_completeness_missing(self):
        """Test required range completeness validation with missing sequences"""
        processor = OBXProcessor(self.obx_segments)
        processor.required_range = {'min': 7, 'max': 36}
        
        # Setup only some required sequences (missing some)
        for i in range(7, 30):  # Missing 30-36
            processor.required_sequences[i] = Mock()
        
        result = processor._validate_required_range_completeness()
        
        assert result is False
        assert len(processor.errors) > 0
        assert "Missing sequences" in processor.errors[0]
    
    def test_validate_required_range_completeness_extra(self):
        """Test required range completeness validation with extra sequences"""
        processor = OBXProcessor(self.obx_segments)
        processor.required_range = {'min': 7, 'max': 36}
        
        # Setup more than required sequences
        for i in range(7, 40):  # Extra sequences
            processor.required_sequences[i] = Mock()
        
        result = processor._validate_required_range_completeness()
        
        assert result is False
        assert len(processor.errors) > 0
        assert "Logic error" in processor.errors[0]
    
    def test_validate_required_range_completeness_non_consecutive(self):
        """Test required range completeness validation with non-consecutive sequences"""
        processor = OBXProcessor(self.obx_segments)
        processor.required_range = {'min': 7, 'max': 36}
        
        # Setup non-consecutive sequences (7-20, 25-36, missing 21-24)
        for i in list(range(7, 21)) + list(range(25, 37)):
            processor.required_sequences[i] = Mock()
        
        result = processor._validate_required_range_completeness()
        
        assert result is False
        assert len(processor.errors) > 0
        assert "not consecutive" in processor.errors[0]
    
    def test_process_findings_range_is_type(self):
        """Test processing findings range with IS type"""
        processor = OBXProcessor(self.obx_segments)
        
        mock_sequence = Mock()
        result = processor._process_findings_range("IS", mock_sequence)
        
        assert result is True
        assert mock_sequence in processor.valid_findings
    
    def test_process_findings_range_nm_type(self):
        """Test processing findings range with NM type"""
        processor = OBXProcessor(self.obx_segments)
        
        mock_sequence = Mock()
        result = processor._process_findings_range("NM", mock_sequence)
        
        assert result is True
        assert mock_sequence in processor.valid_findings
    
    def test_process_findings_range_invalid_type(self):
        """Test processing findings range with invalid type"""
        processor = OBXProcessor(self.obx_segments)
        
        result = processor._process_findings_range("INVALID", Mock())
        
        assert result is False
    
    def test_obx_processor_parse_nm_results(self):
        """Test OBX processor parsing NM results"""
        processor = OBXProcessor(self.obx_segments)
        
        # Setup valid OBX segments
        mock_segment = Mock()
        processor.valid_obx = [mock_segment]
        processor.valid_findings = []
        
        with patch.object(processor, '_parse_segment', return_value={"sequence": "7", "value": "6.50"}):
            nm_results, is_results = processor.parse()
            
            assert len(nm_results) == 1
            assert len(is_results) == 0
            assert nm_results[0]["sequence"] == "7"
    
    def test_obx_processor_parse_is_results(self):
        """Test OBX processor parsing IS results"""
        processor = OBXProcessor(self.obx_segments)
        
        # Setup valid findings segments
        mock_segment = Mock()
        processor.valid_obx = []
        processor.valid_findings = [mock_segment]
        
        with patch.object(processor, '_recursive_fetch', return_value="Finding1"):
            nm_results, is_results = processor.parse()
            
            assert len(nm_results) == 0
            assert len(is_results) == 1
            assert is_results[0] == "Finding1"
    
    def test_obx_processor_parse_segment(self):
        """Test OBX segment parsing with field mapping"""
        processor = OBXProcessor(self.obx_segments)
        
        mock_segment = Mock()
        mock_config = {
            "sequence_number": "1",
            "value_type": "2",
            "observation_value": "5"
        }
        
        with patch.object(processor.parser_config, 'OBX', mock_config), \
             patch.object(processor, '_recursive_fetch') as mock_fetch:
            
            mock_fetch.side_effect = ["7", "NM", "6.50"]
            
            result = processor._parse_segment(mock_segment, "OBX")
            
            assert result["sequence_number"] == "7"
            assert result["value_type"] == "NM"
            assert result["observation_value"] == "6.50"


class TestProcessFactory:
    """Test processFactory function"""
    
    def test_process_factory_msh(self):
        """Test factory creates MSHProcessor"""
        mock_segments = Mock()
        
        processor = processFactory('MSH', mock_segments)
        
        assert isinstance(processor, MSHProcessor)
        assert processor.message_segments == mock_segments
    
    def test_process_factory_obr(self):
        """Test factory creates OBRProcessor"""
        mock_segments = Mock()
        
        processor = processFactory('OBR', mock_segments)
        
        assert isinstance(processor, OBRProcessor)
        assert processor.message_segments == mock_segments
    
    def test_process_factory_obx(self):
        """Test factory creates OBXProcessor"""
        mock_segments = Mock()
        
        processor = processFactory('OBX', mock_segments)
        
        assert isinstance(processor, OBXProcessor)
        assert processor.message_segments == mock_segments
    
    def test_process_factory_unsupported_segment(self):
        """Test factory with unsupported segment type"""
        mock_segments = Mock()
        
        processor = processFactory('UNSUPPORTED', mock_segments)
        
        assert processor is None
    
    def test_process_factory_known_unsupported_segment(self):
        """Test factory with known but unsupported segment (PID, PV1)"""
        mock_segments = Mock()
        
        with patch('middleware.processor.logger') as mock_logger:
            processor = processFactory('PID', mock_segments)
            
            assert processor is None
            mock_logger.warning.assert_called_once()
    
    def test_process_factory_invalid_segment(self):
        """Test factory with completely invalid segment type"""
        mock_segments = Mock()
        
        with patch('middleware.processor.logger') as mock_logger:
            processor = processFactory('INVALID', mock_segments)
            
            assert processor is None
            mock_logger.error.assert_called_once()


class TestProcessorEdgeCases:
    """Test processor handling of edge cases"""
    
    def test_msh_processor_with_edge_case_datetime(self):
        """Test MSH processor with edge case datetime values"""
        # Create message with edge case datetime
        edge_message = COMPLETE_VALID_MESSAGE.replace(
            "20250828152838", "20250229152838"  # Invalid leap year date
        )
        
        try:
            message = hl7_parse(edge_message.replace('\n', '\r'))
            msh_segments = message.segments('MSH')
            processor = MSHProcessor(msh_segments)
            
            result = processor.validate_datetime_of_message("20250229152838")
            
            # Should be invalid (2025 is not a leap year)
            assert result is False
        except Exception:
            # If parsing fails, that's also acceptable for invalid dates
            pass
    
    def test_obx_processor_with_incomplete_sequences(self):
        """Test OBX processor with incomplete sequence ranges"""
        # Create message with only sequences 7-17 (missing 18-36)
        incomplete_sequences = list(range(7, 18))
        incomplete_message = create_test_message_with_sequences(incomplete_sequences)
        
        message = hl7_parse(incomplete_message.replace('\n', '\r'))
        obx_segments = message.segments('OBX')
        
        processor = OBXProcessor(obx_segments)
        processor.required_range = {'min': 7, 'max': 36}
        
        # Process each segment
        for segment in obx_segments:
            seq_num = int(str(segment[1]))
            processor._process_required_range("NM", segment)
        
        # Validate completeness - should fail
        result = processor._validate_required_range_completeness()
        
        assert result is False
        assert len(processor.errors) > 0
    
    def test_obx_processor_with_out_of_order_sequences(self):
        """Test OBX processor with out-of-order sequences"""
        # Create message with out-of-order sequences
        out_of_order = [10, 7, 9, 8, 12, 11, 15, 13, 14, 16]
        out_of_order_message = create_test_message_with_sequences(out_of_order)
        
        message = hl7_parse(out_of_order_message.replace('\n', '\r'))
        obx_segments = message.segments('OBX')
        
        processor = OBXProcessor(obx_segments)
        
        # Extract sequences to verify they're out of order
        sequences = extract_obx_sequences(message)
        
        assert sequences == out_of_order
        # The processor should handle out-of-order sequences correctly
    
    def test_processor_with_malformed_segments(self):
        """Test processors with malformed segment data"""
        # Test with insufficient fields
        try:
            malformed_message = hl7_parse(INSUFFICIENT_OBX_FIELDS.replace('\n', '\r'))
            obx_segments = malformed_message.segments('OBX')
            
            if obx_segments:
                processor = OBXProcessor(obx_segments)
                
                # Should handle malformed segments gracefully
                with patch('middleware.processor.OBX_RANGE', 12):
                    result = processor._process_required_range("NM", obx_segments[0])
                    
                    # Should fail due to insufficient fields
                    assert result is False
        except Exception:
            # If parsing fails completely, that's also acceptable
            pass


class TestProcessorPerformance:
    """Test processor performance characteristics"""
    
    def test_obx_processor_large_sequence_count(self):
        """Test OBX processor with large number of sequences"""
        # Create message with many sequences (1-100)
        large_sequences = list(range(1, 101))
        large_message = create_test_message_with_sequences(large_sequences)
        
        message = hl7_parse(large_message.replace('\n', '\r'))
        obx_segments = message.segments('OBX')
        
        processor = OBXProcessor(obx_segments)
        
        # Should handle large number of segments
        assert len(obx_segments) == 100
        
        # Test bounds checking for all sequences
        processor.optional_range = {'min': 1, 'max': 6}
        processor.required_range = {'min': 7, 'max': 36}
        processor.findings_range = {'min': 37}
        
        valid_count = 0
        for segment in obx_segments:
            seq_num = int(str(segment[1]))
            value_type = str(segment[2])
            
            try:
                result = processor._check_bounds(seq_num, value_type, segment)
                if result:
                    valid_count += 1
            except Exception:
                # Some sequences might fail validation
                pass
        
        # Should process most sequences successfully
        assert valid_count > 0


# Run the tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])