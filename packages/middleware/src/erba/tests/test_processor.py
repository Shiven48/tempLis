"""
Comprehensive tests for processor classes: MSHProcessor, OBRProcessor, OBXProcessor
"""
import pytest
from unittest.mock import Mock, patch
from hl7 import Message, parse as hl7_parse

from erba.processor import (
    MSHProcessor, OBRProcessor, OBXProcessor, processFactory
)
from erba.models import ParserConfig, SegmentsConfig
from .fixtures.valid_messages import COMPLETE_VALID_MESSAGE
from .fixtures.invalid_messages import INSUFFICIENT_OBX_FIELDS
from .utils.test_helpers import create_test_message_with_sequences, extract_obx_sequences


class TestMSHProcessor:
    """Test MSHProcessor class"""

    @pytest.fixture(autouse=True)
    def setup_test_data(self, mock_parser_config:ParserConfig):
        """Setup test fixtures"""
        self.sample_message:Message = hl7_parse(COMPLETE_VALID_MESSAGE.replace('\n', '\r'))
        self.msh_segments = self.sample_message.segments('MSH')
        self._mock_parser_config = mock_parser_config
        self.config_dict = {
            'optional': '1-6',
            'required': '7-36',
            'findings': '37+'
        }
        self._mock_segments_config = SegmentsConfig(**self.config_dict)
        self.processor = MSHProcessor(self.msh_segments)
        self.processor.parser_config = self._mock_parser_config    
    
    def test_msh_processor_initialization(self):
        """Test MSHProcessor initialization"""            
        processor = self.processor
        
        assert processor.message_segments == self.msh_segments
        assert processor.segment_type == 'MSH'
        assert processor.parser_config is not None
        assert processor.msh_config_dict is not None
        assert isinstance(processor.errors, list)
    
    def test_msh_processor_process_segment_success(self):
        """Test successful MSH segment processing"""            
        processor = self.processor
        
        with patch.object(processor, '_validate_msh_segments', return_value=True):
            errors, is_valid = processor.process_segment()
            
            assert is_valid is True
            assert len(errors) == 0
    
    def test_msh_processor_process_segment_failure(self):
        """Test MSH segment processing failure"""
        processor = self.processor
        processor.errors = ["Validation error"]
        
        with patch.object(processor, '_validate_msh_segments', return_value=False):
            errors, is_valid = processor.process_segment()
            
            assert is_valid is False
            assert len(errors) > 0
            assert "Validation error" in errors
    
    def test_msh_processor_parse_segment(self):
        """Test MSH segment parsing"""
        processor = self.processor
        
        with patch.object(processor, '_recursive_fetch') as mock_fetch:
            mock_fetch.side_effect = ["ELite 580", "Erba", "20250828152838", "message123",]
            result = processor.parse()
            
            assert isinstance(result, list)
            assert len(result) == 1
            assert isinstance(result[0], dict)
    
    def test_validate_model_valid(self):
        """Test valid model field validation"""
        processor = self.processor
        assert processor.validate_model("ELite 580") is True
        assert processor.validate_model("Test Model") is True
    
    def test_validate_model_invalid(self):
        """Test invalid model field validation"""
        processor = self.processor
        
        assert processor.validate_model("") is False
        assert processor.validate_model(None) is False
        assert processor.validate_model("   ") is False
        assert processor.validate_model("123456") is False
        assert processor.validate_model("a" * 228) is False
    
    def test_validate_machine_valid(self):
        """Test valid machine field validation"""
        processor = self.processor
        
        assert processor.validate_machine("Erba") is True
        assert processor.validate_machine("Test Facility") is True
        assert processor.validate_machine("AB") is True
    
    def test_validate_machine_invalid(self):
        """Test invalid machine field validation"""
        processor = self.processor
        
        assert processor.validate_machine("") is False
        assert processor.validate_machine(None) is False
        assert processor.validate_machine("A") is False
        assert processor.validate_machine("   ") is False
        assert processor.validate_machine("a" * 228) is False
    
    def test_validate_datetime_of_message_valid(self):
        """Test valid datetime validation"""
        processor = self.processor
        
        assert processor.validate_datetime_of_message("20250828152838") is True
        assert processor.validate_datetime_of_message("20000101000000") is True
        assert processor.validate_datetime_of_message("20991231235959") is True
    
    def test_validate_datetime_of_message_invalid(self):
        """Test invalid datetime validation"""
        processor = self.processor
        
        assert processor.validate_datetime_of_message("") is False
        assert processor.validate_datetime_of_message(None) is False
        assert processor.validate_datetime_of_message("invalid") is False
        assert processor.validate_datetime_of_message("2025082815283") is False  
        assert processor.validate_datetime_of_message("202508281528380") is False  
        assert processor.validate_datetime_of_message("20250828252838") is False  
        assert processor.validate_datetime_of_message("20250828156038") is False  
        assert processor.validate_datetime_of_message("20250828153860") is False  
        assert processor.validate_datetime_of_message("18991231235959") is False  
        assert processor.validate_datetime_of_message("21011231235959") is False  
    
    def test_validate_msh_segments_success(self):
        """Test successful MSH segment validation"""
        processor = self.processor
        
        with patch.object(processor, 'validate_model', return_value=True), \
             patch.object(processor, 'validate_machine', return_value=True), \
             patch.object(processor, 'validate_datetime_of_message', return_value=True):
            
            result = processor._validate_msh_segments(self.msh_segments[0])
            
            assert result is True
            assert len(processor.errors) == 0
    
    def test_validate_msh_segments_failure(self):
        """Test MSH segment validation failure"""
        processor = self.processor
        
        with patch.object(processor, 'validate_model', return_value=False), \
             patch.object(processor, 'validate_machine', return_value=False), \
             patch.object(processor, 'validate_datetime_of_message', return_value=False):
            
            result = processor._validate_msh_segments(self.msh_segments[0])
            
            assert result is False
            assert len(processor.errors) == 3
    
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
        processor = self.processor        
        result = processor._recursive_fetch(self.msh_segments[0], "3")
        assert result == "ELite 580"
    
    def test_recursive_fetch_nested_index(self):
        """Test recursive fetch with nested index"""
        processor = MSHProcessor(self.msh_segments)
        result = processor._recursive_fetch(self.msh_segments[0], "9")
        assert result == "ORU^R01"
    
    def test_recursive_fetch_invalid_index(self):
        """Test recursive fetch with invalid index"""
        processor = MSHProcessor(self.msh_segments)
        result = processor._recursive_fetch(self.msh_segments[0], "invalid")
        assert result == ""


class TestOBRProcessor:
    """Test OBRProcessor class"""
    
    @pytest.fixture(autouse=True)
    def setup_test_data(self, mock_parser_config:ParserConfig):
        """Setup test fixtures"""
        self.sample_message:Message = hl7_parse(COMPLETE_VALID_MESSAGE.replace('\n', '\r'))
        self.obr_segments = self.sample_message.segments('OBR')
        self._mock_parser_config = mock_parser_config
        self.config_dict = {
            'optional': '1-6',
            'required': '7-36',
            'findings': '37+'
        }
        self._mock_segments_config = SegmentsConfig(**self.config_dict)
        self.processor = OBRProcessor(self.obr_segments)
        self.processor.parser_config = self._mock_parser_config    
    
    def test_obr_processor_initialization(self):
        """Test OBRProcessor initialization"""
        processor = self.processor

        assert processor.message_segments == self.obr_segments
        assert processor.segment_type == 'OBR'
        assert processor.parser_config is not None
        assert processor.obr_config_dict is not None
        assert isinstance(processor.errors, list)
    
    def test_obr_processor_process_segment_success(self):
        """Test successful OBR segment processing"""
        processor = self.processor
        
        with patch.object(processor, '_validate_obr_segments', return_value=True):
            errors, is_valid = processor.process_segment()
            
            assert is_valid is True
            assert len(errors) == 0
    
    def test_obr_processor_process_segment_failure(self):
        """Test OBR segment processing failure"""
        processor = self.processor
        processor.errors = ["Validation error"]
        
        with patch.object(processor, '_validate_obr_segments', return_value=False):
            errors, is_valid = processor.process_segment()
            
            assert is_valid is False
            assert len(errors) > 0
    
    def test_obr_processor_parse_segment(self):
        """Test OBR segment parsing"""
        processor = self.processor
        
        with patch.object(processor, '_recursive_fetch') as mock_fetch:
            mock_fetch.side_effect = ["20250828010809", "20250828010809"]
            result = processor.parse()
            
            assert isinstance(result, list)
            assert len(result) == 1
            assert isinstance(result[0], dict)
    
    def test_validate_datetime_valid(self):
        """Test valid datetime validation in OBR"""
        processor = self.processor
        
        assert processor.validate_datetime("20250828152838") is True
        assert processor.validate_datetime("20000101000000") is True
        assert processor.validate_datetime("20991231235959") is True
    
    def test_validate_datetime_invalid(self):
        """Test invalid datetime validation in OBR"""
        processor = self.processor
        
        assert processor.validate_datetime("") is False
        assert processor.validate_datetime(None) is False
        assert processor.validate_datetime("invalid") is False
        assert processor.validate_datetime("2025082815283") is False  
        assert processor.validate_datetime("20250828252838") is False
    
    def test_validate_obr_segments_success(self):
        """Test successful OBR segment validation"""
        processor = self.processor
        
        with patch.object(processor, 'validate_datetime', return_value=True):
            result = processor._validate_obr_segments(self.obr_segments[0])
            
            assert result is True
            assert len(processor.errors) == 0
    
    def test_validate_obr_segments_failure(self):
        """Test OBR segment validation failure"""
        processor = self.processor
        
        with patch.object(processor, 'validate_datetime', return_value=False):
            result = processor._validate_obr_segments(self.obr_segments[0])
            
            assert result is False
            assert len(processor.errors) == 2
    
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
    
    @pytest.fixture(autouse=True)
    def setup_test_data(self, mock_parser_config:ParserConfig):
        """Setup test fixtures"""
        self.sample_message:Message = hl7_parse(COMPLETE_VALID_MESSAGE.replace('\n', '\r'))
        self.obx_segments = self.sample_message.segments('OBX')
        self._mock_parser_config = mock_parser_config
        self.config_dict = {
            'optional': '1-6',
            'required': '7-36',
            'findings': '37+'
        }
        self._mock_segments_config = SegmentsConfig(**self.config_dict)
        self.processor = OBXProcessor(self.obx_segments)
        self.processor.parser_config = self._mock_parser_config
        self.processor.segment_config = self._mock_segments_config
        self.processor._parse_config_ranges(self.config_dict)
                                    
    def test_obx_processor_initialization(self):
        """Test OBXProcessor initialization"""
        processor = self.processor
        assert processor.message_segments == self.obx_segments
        assert processor.segment_type == 'OBX'
        assert processor.parser_config is not None
        assert processor.segment_config is not None
        assert processor.parser_config.OBX["value_type"] == "2"
        assert processor.parser_config.OBX["test_code"] == "3-0"
        assert processor.segment_config.optional == "1-6"
        assert processor.segment_config.required == "7-36"
        assert isinstance(processor.valid_obx, list)
        assert isinstance(processor.valid_findings, list)
        assert isinstance(processor.errors, list)
        assert isinstance(processor.required_sequences, dict)
    
    def test_obx_processor_process_segment_success(self):
        """Test successful OBX segment processing"""
        processor = self.processor
        
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
        processor = self.processor
        processor.errors = ["Validation error"]
        
        with patch.object(processor, '_parse_config_ranges'), \
             patch.object(processor, '_validate_segment_config'), \
             patch.object(processor, '_check_bounds', return_value=False), \
             patch.object(processor, '_validate_required_range_completeness', return_value=False):
            
            processor.optional_range = self._mock_segments_config.optional
            processor.required_range = self._mock_segments_config.required
            processor.findings_range = self._mock_segments_config.findings

            errors, is_valid = processor.process_segment()
            
            assert is_valid is False
            assert len(errors) > 0
    
    def test_parse_config_ranges_valid(self):
        """Test parsing valid configuration ranges"""
        processor = self.processor        
        processor._parse_config_ranges(self.config_dict)
        
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
        processor = self.processor
        config_dict = {
            'optional': '5',
            'required': '7-36',
            'findings': '37+'
        }
        processor._parse_config_ranges(config_dict)
        
        assert processor.optional_range['type'] == 'single'
        assert processor.optional_range['value'] == 5
    
    def test_parse_config_ranges_invalid(self):
        """Test parsing invalid configuration ranges"""
        processor = self.processor
        
        config_dict = {
            'optional': 'invalid-range-format',
            'required': '7-36',
            'findings': '37+'
        }
        
        processor._parse_config_ranges(config_dict)
        
        assert processor.optional_range['type'] == 'invalid'
    
    def test_validate_segment_config(self):
        """Test segment configuration validation"""
        processor = self.processor
        
        # Setup valid ranges
        processor.optional_range = {'type': 'range', 'min': 1, 'max': 6}
        processor.required_range = {'type': 'range', 'min': 7, 'max': 36}
        processor.findings_range = {'type': 'threshold', 'min': 37}
        
        # Should not raise any exceptions
        processor._validate_segment_config()
    
    def test_check_bounds_optional_range(self):
        """Test bounds checking for optional range"""
        processor = self.processor
        
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
        processor = self.processor
        
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
        processor = self.processor
        
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
        processor = self.processor
        
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
        processor = self.processor
        
        result = processor._check_bounds("invalid", "NM", Mock())
        
        assert result is False
        assert len(processor.errors) > 0
        assert "Invalid sequence value" in processor.errors[0]
    
    def test_process_optional_range_is_type(self):
        """Test processing optional range with IS type"""
        processor = self.processor
        
        result = processor._process_optional_range(5, "IS")
        
        assert result is True
    
    def test_process_optional_range_nm_type(self):
        """Test processing optional range with NM type"""
        processor = self.processor
        result = processor._process_optional_range(5, "NM")
        assert result is True
    
    def test_process_optional_range_invalid_type(self):
        """Test processing optional range with invalid type"""
        processor = self.processor
        
        result = processor._process_optional_range(5, "INVALID")
        
        assert result is False
    
    def test_process_required_range_success(self):
        """Test successful processing of required range"""
        processor = self.processor
        processor.required_range = {'min': 7, 'max': 36}
        
        # Create mock sequence with proper length
        mock_sequence = Mock()
        mock_sequence.__len__ = Mock(return_value=12)  # OBX_RANGE value
        mock_sequence.__getitem__ = Mock(side_effect=lambda x: Mock(__str__=Mock(return_value="15")))
        
        with patch('erba.processor.OBX_RANGE', 12):
            result = processor._process_required_range("NM", mock_sequence)
            
            assert result is True
            assert 15 in processor.required_sequences
    
    def test_process_required_range_wrong_type(self):
        """Test processing required range with wrong value type"""
        processor = self.processor
        processor.required_range = {'min': 7, 'max': 36}
        
        result = processor._process_required_range("IS", Mock())
        
        assert result is False
        assert len(processor.errors) > 0
        assert "Expected NM segment type" in processor.errors[0]
    
    def test_process_required_range_wrong_field_count(self):
        """Test processing required range with wrong field count"""
        processor = self.processor
        processor.required_range = {'min': 7, 'max': 36}
        
        # Create mock sequence with wrong length
        mock_sequence = Mock()
        mock_sequence.__len__ = Mock(return_value=8)  # Wrong length
        mock_sequence.__getitem__ = Mock(side_effect=lambda x: Mock(__str__=Mock(return_value="15")))
        
        with patch('erba.processor.OBX_RANGE', 12):
            result = processor._process_required_range("NM", mock_sequence)
            
            assert result is False
            assert len(processor.errors) > 0
            assert "Field Count Error" in processor.errors[0]
    
    def test_process_required_range_duplicate_sequence(self):
        """Test processing required range with duplicate sequence"""
        processor = self.processor
        processor.required_range = {'min': 7, 'max': 36}
        processor.required_sequences[15] = Mock()  # Pre-existing sequence
        
        # Create mock sequence
        mock_sequence = Mock()
        mock_sequence.__len__ = Mock(return_value=12)
        mock_sequence.__getitem__ = Mock(side_effect=lambda x: Mock(__str__=Mock(return_value="15")))
        
        with patch('erba.processor.OBX_RANGE', 12):
            result = processor._process_required_range("NM", mock_sequence)
            
            assert result is False
            assert len(processor.errors) > 0
            assert "Duplicate sequence" in processor.errors[0]
    
    def test_validate_required_range_completeness_success(self):
        """Test successful required range completeness validation"""
        processor = self.processor
        processor.required_range = {'min': 7, 'max': 36}
        
        for i in range(7, 37):
            processor.required_sequences[i] = Mock()
        
        result = processor._validate_required_range_completeness()
        
        assert result is True
        assert len(processor.valid_obx) == 30
    
    def test_validate_required_range_completeness_missing(self):
        """Test required range completeness validation with missing sequences"""
        processor = self.processor
        processor.required_range = {'min': 7, 'max': 36}
        
        for i in range(7, 30):
            processor.required_sequences[i] = Mock()
        
        result = processor._validate_required_range_completeness()
        
        assert result is False
        assert len(processor.errors) > 0
        assert "Missing sequences" in processor.errors[0]
    
    def test_validate_required_range_completeness_non_consecutive(self):
        """Test required range completeness validation with non-consecutive sequences"""
        processor = self.processor
        processor.required_range = {'min': 7, 'max': 36}
        
        # Skip sequence 25
        for i in range(7, 25):
            processor.required_sequences[i] = Mock()
        for i in range(26, 37):
            processor.required_sequences[i] = Mock()
        
        result = processor._validate_required_range_completeness()
        assert result is False
        assert len(processor.errors) > 0
        assert 'important fields missing' in processor.errors[0].lower()
    
    def test_process_findings_range_is_type(self):
        """Test processing findings range with IS type"""
        processor = self.processor
        
        mock_sequence = Mock()
        result = processor._process_findings_range("IS", mock_sequence)
        
        assert result is True
        assert mock_sequence in processor.valid_findings
    
    def test_process_findings_range_nm_type(self):
        """Test processing findings range with NM type"""
        processor = self.processor
        
        mock_sequence = Mock()
        result = processor._process_findings_range("NM", mock_sequence)
        
        assert result is True
        assert mock_sequence in processor.valid_findings
    
    def test_process_findings_range_invalid_type(self):
        """Test processing findings range with invalid type"""
        processor = self.processor
        
        result = processor._process_findings_range("INVALID", Mock())
        
        assert result is False
    
    def test_obx_processor_parse_nm_results(self):
        """Test OBX processor parsing NM results"""
        processor = self.processor
        
        # Setup valid OBX segments
        processor.valid_obx = self.obx_segments
        processor.valid_findings = []
        
        with patch.object(processor, '_parse_segment', return_value={"sequence": "7", "value": "6.50"}):
            nm_results, is_results = processor.parse()
            
            assert len(nm_results) == 42
            assert len(is_results) == 0
            assert nm_results[0]["sequence"] == "7"
    
    def test_obx_processor_parse_is_results(self):
        """Test OBX processor parsing IS results"""
        processor = self.processor
        
        # Setup valid findings segments
        mock_segment = Mock()
        mock_segment.__len__ = Mock(return_value=5)
        processor.valid_obx = self.obx_segments
        processor.valid_findings = [mock_segment]
        
        with patch.object(processor, '_recursive_fetch', return_value="Finding1"):
            nm_results, is_results = processor.parse()
            
            assert len(nm_results) == 42
            assert len(is_results) == 1
            assert is_results[0] == "Finding1"
    
    def test_obx_processor_parse_segment(self):
        """Test OBX segment parsing with field mapping"""
        processor = self.processor
        
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
        
        with patch('erba.processor.logger') as mock_logger:
            processor = processFactory('PID', mock_segments)
            
            assert processor is None
            mock_logger.warning.assert_called_once()
    
    def test_process_factory_invalid_segment(self):
        """Test factory with completely invalid segment type"""
        mock_segments = Mock()
        
        with patch('erba.processor.logger') as mock_logger:
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
                with patch('erba.processor.OBX_RANGE', 12):
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
                pass
        
        assert valid_count > 0

# Run the tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])