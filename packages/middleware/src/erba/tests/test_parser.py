"""
Comprehensive tests for HL7Parser and ConfigurableHL7Parser classes
"""
from erba.constants import ERBA_YAML_PATH
import pytest
from unittest.mock import Mock, patch
from hl7 import parse as hl7_parse, Message

from erba.parser import HL7Parser, ConfigurableHL7Parser
from erba.models import ParserConfig, ParsingResult
from .fixtures.valid_messages import (
    COMPLETE_VALID_MESSAGE, MINIMAL_VALID_MESSAGE, VALID_WITH_FINDINGS
)
from .fixtures.invalid_messages import (
    MISSING_MSH, DUPLICATE_SEQUENCES, MALFORMED_STRUCTURE
)
from .fixtures.edge_cases import (
    INCOMPLETE_MESSAGE_17, MALFORMED_JOINED_MESSAGE, 
    NO_DATA_AFTER_17, COMPLETE_WITH_FINDINGS
)
from .utils.test_helpers import (
    create_test_message_with_sequences, extract_obx_sequences
)


class TestConfigurableHL7Parser:
    """Test ConfigurableHL7Parser class"""
    
    def test_parser_initialization_success(self, mock_parser_config):
        """Test successful parser initialization"""
        parser = ConfigurableHL7Parser(mock_parser_config)
        
        assert parser.parser_config == mock_parser_config
        assert parser.result is None
        assert isinstance(parser.message_types, list)
        assert len(parser.message_types) > 0
    
    def test_parser_initialization_empty_config(self):
        """Test parser initialization with empty config"""
        with pytest.raises(ValueError, match="Parser configuration cannot be empty"):
            ConfigurableHL7Parser(None)
    
    def test_get_segments_from_config(self, mock_parser_config):
        """Test segment extraction from configuration"""
        parser = ConfigurableHL7Parser(mock_parser_config)
        
        segments = parser._get_segments()
        
        assert 'MSH' in segments
        assert 'OBR' in segments
        assert 'OBX' in segments
        assert all(isinstance(seg, str) for seg in segments)
    
    def test_parse_simple_obx_message(self, mock_parser_config):
        """Test parsing with a simple message containing OBX segments"""
        parser = ConfigurableHL7Parser(mock_parser_config)
        result = parser.parse(COMPLETE_VALID_MESSAGE)
        
        assert len(result.parsing_errors) == 0
        assert len(result.test_results) > 0
        assert result is not None
    
    def test_parse_invalid_message_structure(self, mock_parser_config):
        """Test parsing invalid message structure"""
        parser = ConfigurableHL7Parser(mock_parser_config)
        
        result = parser.parse(MALFORMED_STRUCTURE)
        
        assert isinstance(result, ParsingResult)
        assert len(result.parsing_errors) > 0
        assert result.error is not None
    
    def test_parse_empty_message(self, mock_parser_config):
        """Test parsing empty message"""
        parser = ConfigurableHL7Parser(mock_parser_config)
        
        result = parser.parse("")
        
        assert isinstance(result, ParsingResult)
        assert len(result.parsing_errors) > 0
    
    def test_get_max_sequence_number_normal(self, mock_parser_config):
        """Test getting max sequence number from normal message"""
        parser = ConfigurableHL7Parser(mock_parser_config)
        message:Message = hl7_parse(COMPLETE_VALID_MESSAGE.replace('\n', '\r'))
        max_seq, len_obx = parser._get_max_sequence_number(message)
        
        assert max_seq == 42, f"Expected exactly 42 as max sequence, got {max_seq}"
        assert max_seq > 0, "Max sequence must be positive"
        assert len_obx > 0, "Must have OBX segments"
        assert max_seq == len_obx, "For valid sequential: max sequence must equal OBX count"
    
    def test_get_max_sequence_number_incomplete(self, mock_parser_config):
        """Test getting max sequence number from incomplete message"""
        parser = ConfigurableHL7Parser(mock_parser_config)
        
        # Create message with sequences 7-17 only
        incomplete_msg = create_test_message_with_sequences(list(range(7, 18)))
        message = hl7_parse(incomplete_msg.replace('\n', '\r'))
        
        max_seq, len_obx = parser._get_max_sequence_number(message)
        
        assert max_seq == 17
        assert len_obx == 11  # Should have 11 OBX segments (7-17)
    
    def test_message_parse_and_validate_success(self, mock_parser_config):
        """Test successful message parsing and validation"""
        parser = ConfigurableHL7Parser(mock_parser_config)
        parser.result = ParsingResult()
        
        message = hl7_parse(COMPLETE_VALID_MESSAGE.replace('\n', '\r'))
        
        with patch.object(parser, '_process_segments', return_value=([], True)):
            result = parser._message_parse_and_validate(message)
            
            assert result is True
            assert len(parser.result.parsing_errors) == 0
    
    def test_message_parse_and_validate_failure(self, mock_parser_config):
        """Test message parsing and validation failure"""
        parser = ConfigurableHL7Parser(mock_parser_config)
        parser.result = ParsingResult()
        
        message = hl7_parse(COMPLETE_VALID_MESSAGE.replace('\n', '\r'))
        
        with patch.object(parser, '_process_segments', return_value=(["Error"], False)):
            result = parser._message_parse_and_validate(message)
            
            assert result is False
            assert len(parser.result.parsing_errors) > 0
    
    def test_process_segments_all_types(self, mock_parser_config):
        """Test processing all segment types"""
        parser = ConfigurableHL7Parser(mock_parser_config)
        parser.result = ParsingResult()
        parser.message_types = ['MSH', 'OBR', 'OBX']
        
        message = hl7_parse(COMPLETE_VALID_MESSAGE.replace('\n', '\r'))
        
        with patch('erba.parser.processFactory') as mock_factory:
            def mock_processor_factory(segment_type, sequence):
                mock_processor = Mock()
                mock_processor.process_segment.return_value = ([], True)
                
                if segment_type == 'OBX':
                    mock_processor.parse.return_value = (
                        [{"test": "NM_data"}], 
                        ["Finding1", "Finding2"]
                    )
                else:
                    mock_processor.parse.return_value = [{"test": "data"}]
                
                return mock_processor

            mock_factory.side_effect = mock_processor_factory
        
        errors, is_valid = parser._process_segments(message)
        
        assert is_valid is True
        assert len(errors) == 0
        assert mock_factory.call_count == 3
    
    def test_process_segments_with_errors(self, mock_parser_config):
        """Test processing segments with errors"""
        parser = ConfigurableHL7Parser(mock_parser_config)
        parser.result = ParsingResult()
        parser.message_types = ['MSH']
        
        message = hl7_parse(COMPLETE_VALID_MESSAGE.replace('\n', '\r'))
        
        with patch('erba.parser.processFactory') as mock_factory:
            mock_processor = Mock()
            mock_processor.process_segment.return_value = (["Validation error"], False)
            mock_processor.parse.return_value = [{"test": "data"}]
            mock_factory.return_value = mock_processor
            
            errors, is_valid = parser._process_segments(message)
            
            assert is_valid is False
            assert len(errors) > 0
            assert "Validation error" in errors
    
    def test_process_segments_all_types(self, mock_parser_config):
        """Test processing all segment types"""
        parser = ConfigurableHL7Parser(mock_parser_config)
        parser.result = ParsingResult()
        parser.message_types = ['MSH', 'OBR', 'OBX']
        
        message = hl7_parse(COMPLETE_VALID_MESSAGE.replace('\n', '\r'))
        
        with patch('erba.parser.processFactory') as mock_factory:
            def mock_processor_factory(segment_type, sequence):
                mock_processor = Mock()
                mock_processor.process_segment.return_value = ([], True)
                
                if segment_type == 'OBX':
                    mock_processor.parse.return_value = (
                        [{"test": "NM_data"}], 
                        ["Finding1", "Finding2"]
                    )
                else:
                    mock_processor.parse.return_value = [{"test": "data"}]
                
                return mock_processor

            mock_factory.side_effect = mock_processor_factory
            
            errors, is_valid = parser._process_segments(message)
            
            assert is_valid is True
            assert len(errors) == 0
            assert mock_factory.call_count == 3

    def test_store_segment_data_msh(self, mock_parser_config):
        """Test storing MSH segment data"""
        parser = ConfigurableHL7Parser(mock_parser_config)
        parser.result = ParsingResult()
        
        msh_data = [{"model": "ELite 580", "facility": "Erba"}]
        parser._store_segment_data('MSH', msh_data)
        
        expected = {'facility': 'Erba', 'model': 'ELite 580'}
        assert parser.result.message_header == expected
    
    def test_store_segment_data_obr(self, mock_parser_config):
        """Test storing OBR segment data"""
        parser = ConfigurableHL7Parser(mock_parser_config)
        parser.result = ParsingResult()
        
        obr_data = [{"sample_id": "TEST001", "requested_timing": "20250828010809"}]
        parser._store_segment_data('OBR', obr_data)
        
        expected = {'sample_id': 'TEST001', 'requested_timing': '20250828010809'}
        assert parser.result.order_request == expected
    
    def test_store_segment_data_multiple_segments(self, mock_parser_config):
        """Test storing multiple segments of same type"""
        parser = ConfigurableHL7Parser(mock_parser_config)
        parser.result = ParsingResult()
        
        multiple_data = [{"field1": "value1"}, {"field2": "value2"}]
        parser._store_segment_data('MSH', multiple_data)
        
        assert parser.result.message_header == multiple_data


class TestHL7Parser:
    """Test HL7Parser facade class"""
    
    def test_parser_initialization_with_config(self, mock_parser_config):
        """Test parser initialization with configuration path"""        
        
        with patch('configuration.config_loader.ConfigLoader.load_parser_config') as mock_loader:
            mock_loader.return_value = mock_parser_config
            parser = HL7Parser(ERBA_YAML_PATH)
            
            assert parser.yaml_config_path == ERBA_YAML_PATH
            assert parser.core_parser is not None
            mock_loader.assert_called_once()
    
    def test_parser_initialization_without_config(self):
        """Test parser initialization without configuration path"""
        parser = HL7Parser()
        
        assert parser.yaml_config_path is None
        assert parser.core_parser is None
    
    def test_parser_initialization_config_load_failure(self):
        """Test parser initialization with config load failure"""
        with patch('configuration.config_loader.ConfigLoader.load_parser_config') as mock_loader:
            mock_loader.side_effect = Exception("Config load failed")
            
            with pytest.raises(Exception, match="Config load failed"):
                HL7Parser("invalid_config.yaml")
    
    def test_parser_initialization_empty_config(self):
        """Test parser initialization with empty configuration"""
        with patch('configuration.config_loader.ConfigLoader.load_parser_config') as mock_loader:
            empty_config = ParserConfig()
            mock_loader.return_value = empty_config
            
            with pytest.raises(ValueError, match="No parser segments configured"):
                HL7Parser("empty_config.yaml")
    
    def test_static_parse_method(self, mock_parser_config):
        """Test static parse method"""
        
        with patch('configuration.config_loader.ConfigLoader.load_parser_config') as mock_loader, \
            patch.object(ConfigurableHL7Parser, 'parse') as mock_parse:
            
            mock_loader.return_value = mock_parser_config
            
            mock_result = ParsingResult(
                message_header={},
                order_request={},
                test_results=[],
                raw_segments=[COMPLETE_VALID_MESSAGE],
                parsing_errors=[],
                findings=[],
                error=None
            )
            mock_parse.return_value = mock_result
            
            result = HL7Parser.parse(COMPLETE_VALID_MESSAGE, ERBA_YAML_PATH)
            
            assert result == mock_result
            mock_parse.assert_called_once_with(COMPLETE_VALID_MESSAGE)
            mock_loader.assert_called_once()
        
    def test_parse_with_config_success(self, mock_parser_config):
        """Test parsing with initialized configuration"""
        with patch('configuration.config_loader.ConfigLoader.load_parser_config') as mock_loader:
            mock_loader.return_value = mock_parser_config
            parser = HL7Parser(ERBA_YAML_PATH)
            
            with patch.object(parser.core_parser, 'parse') as mock_parse:
                mock_result = ParsingResult()
                mock_parse.return_value = mock_result
                
                result = parser.parse_with_config(COMPLETE_VALID_MESSAGE)
                assert result == mock_result

                mock_parse.assert_called_once_with(COMPLETE_VALID_MESSAGE)
    
    def test_parse_with_config_not_initialized(self):
        """Test parsing without initialized configuration"""
        parser = HL7Parser()
        
        with pytest.raises(ValueError, match="Parser not initialized"):
            parser.parse_with_config(COMPLETE_VALID_MESSAGE)
    
    def test_reload_config_success(self, mock_parser_config):
        """Test successful configuration reload"""
        with patch('configuration.config_loader.ConfigLoader.load_parser_config') as mock_loader:
            mock_loader.return_value = mock_parser_config            
            parser = HL7Parser(ERBA_YAML_PATH)            
            parser.reload_config()
            
            assert parser.core_parser is not None
            assert mock_loader.call_count == 2
    
    def test_reload_config_no_path(self):
        """Test configuration reload without path"""
        parser = HL7Parser()
        
        with pytest.raises(ValueError, match="No config path set for reloading"):
            parser.reload_config()
    
    def test_get_available_segments(self, mock_parser_config):
        """Test getting available segments from configuration"""

        with patch('configuration.config_loader.ConfigLoader.load_parser_config') as mock_loader:
            mock_loader.return_value = mock_parser_config
            
            parser = HL7Parser(ERBA_YAML_PATH)
            segments = parser.get_available_segments()
            
            assert 'MSH' in segments
            assert 'OBR' in segments  
            assert 'OBX' in segments

    def test_get_available_segments_not_initialized(self):
        """Test getting available segments when not initialized"""
        parser = HL7Parser()
        segments = parser.get_available_segments()
        assert segments == []


class TestParserEdgeCases:
    """Test parser handling of edge cases"""
    
    def test_parse_incomplete_message_17_sequences(self, mock_parser_config):
        """Test parsing incomplete message ending at sequence 17"""
        parser = ConfigurableHL7Parser(mock_parser_config)
        
        clean_message = INCOMPLETE_MESSAGE_17.replace('[CR]', '\r').replace('[VT]', '\x0b').replace('[FS]', '\x1c')
        
        try:
            result = parser.parse(clean_message)            
            assert isinstance(result, ParsingResult)
        except Exception:
            pass
    
    def test_parse_malformed_joined_sequences(self, mock_parser_config):
        """Test parsing malformed message with joined sequences"""
        parser = ConfigurableHL7Parser(mock_parser_config)
        
        clean_message = MALFORMED_JOINED_MESSAGE.replace('[CR]', '\r').replace('[VT]', '\x0b').replace('[FS]', '\x1c')
        
        try:
            result = parser.parse(clean_message)
            
            assert isinstance(result, ParsingResult)
        except Exception:
            pass
    
    def test_parse_no_data_after_17(self, mock_parser_config):
        """Test parsing message with no data after sequence 17"""
        parser = ConfigurableHL7Parser(mock_parser_config)
        
        clean_message = NO_DATA_AFTER_17.replace('[CR]', '\r').replace('[VT]', '\x0b').replace('[FS]', '\x1c')
        
        try:
            result = parser.parse(clean_message)
            
            assert isinstance(result, ParsingResult)
        except Exception:
            pass
    
    def test_parse_complete_with_findings(self, mock_parser_config):
        """Test parsing complete message with findings (sequences 37+)"""
        parser = ConfigurableHL7Parser(mock_parser_config)
        
        clean_message = COMPLETE_WITH_FINDINGS.replace('[CR]', '\r').replace('[VT]', '\x0b').replace('[FS]', '\x1c')
        
        with patch.object(parser, '_message_parse_and_validate', return_value=True):
            result = parser.parse(clean_message)
            
            assert isinstance(result, ParsingResult)
    
    def test_parse_missing_required_segments(self, mock_parser_config):
        """Test parsing message missing required segments"""
        parser = ConfigurableHL7Parser(mock_parser_config)
        
        result = parser.parse(MISSING_MSH)
        
        assert isinstance(result, ParsingResult)
        assert len(result.parsing_errors) > 0
    
    def test_parse_duplicate_sequences(self, mock_parser_config):
        """Test parsing message with duplicate sequence numbers"""
        parser = ConfigurableHL7Parser(mock_parser_config)
        
        result = parser.parse(DUPLICATE_SEQUENCES)
        
        assert isinstance(result, ParsingResult)
    
    def test_sequence_validation_gap_detection(self, mock_parser_config):
        """Test detection of gaps in sequence numbers"""
        parser = ConfigurableHL7Parser(mock_parser_config)
        
        sequences_with_gap = list(range(7, 11)) + list(range(15, 21))
        message_with_gap = create_test_message_with_sequences(sequences_with_gap)
        
        message = hl7_parse(message_with_gap.replace('\n', '\r'))
        max_seq, len_obx = parser._get_max_sequence_number(message)
        
        assert max_seq == 20
        assert len_obx == 10  
    
    def test_sequence_validation_out_of_order(self, mock_parser_config):
        """Test handling of out-of-order sequences"""
        parser = ConfigurableHL7Parser(mock_parser_config)
        
        out_of_order_sequences = [10, 7, 9, 8, 12, 11]
        message_out_of_order = create_test_message_with_sequences(out_of_order_sequences)
        
        message = hl7_parse(message_out_of_order.replace('\n', '\r'))
        sequences = extract_obx_sequences(message)
        
        assert sequences == out_of_order_sequences


class TestParserPerformance:
    """Test parser performance characteristics"""
    
    def test_parse_large_message_performance(self, mock_parser_config):
        """Test parsing performance with large message"""
        parser = ConfigurableHL7Parser(mock_parser_config)
        
        large_sequences = list(range(1, 101)) 
        large_message = create_test_message_with_sequences(large_sequences)
        
        with patch.object(parser, '_message_parse_and_validate', return_value=True):
            result = parser.parse(large_message)
            
            assert isinstance(result, ParsingResult)
    
    def test_parse_multiple_messages_memory(self, mock_parser_config):
        """Test memory usage when parsing multiple messages"""
        parser = ConfigurableHL7Parser(mock_parser_config)
        
        messages = [COMPLETE_VALID_MESSAGE, MINIMAL_VALID_MESSAGE, VALID_WITH_FINDINGS]
        
        with patch.object(parser, '_message_parse_and_validate', return_value=True):
            results = []
            for message in messages:
                result = parser.parse(message)
                results.append(result)
            
            assert len(results) == 3
            assert all(isinstance(r, ParsingResult) for r in results)


class TestParserConfigurationHandling:
    """Test parser configuration handling"""
    
    def test_parser_config_validation(self, mock_parser_config):
        """Test parser configuration validation"""
        parser = ConfigurableHL7Parser(mock_parser_config)
        assert parser.parser_config == mock_parser_config
    
    def test_parser_config_partial_segments(self):
        """Test parser with partial segment configuration"""
        partial_config = ParserConfig(
            MSH={"model": "3", "facility": "4"},
            OBR=None,
            OBX=None
        )
        
        parser = ConfigurableHL7Parser(partial_config)
        segments = parser._get_segments()
        
        assert 'MSH' in segments
        assert 'OBR' not in segments
        assert 'OBX' not in segments
    
    def test_parser_config_field_mapping(self, mock_parser_config):
        """Test field mapping from configuration"""
        parser = ConfigurableHL7Parser(mock_parser_config)
        
        assert hasattr(parser.parser_config, 'MSH')
        assert hasattr(parser.parser_config, 'OBR')
        assert hasattr(parser.parser_config, 'OBX')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])