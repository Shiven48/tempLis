from pathlib import Path
import hl7
from typing import Dict, List, Any
import logging
from middleware.config_loader import ConfigLoader


def safe_get(segment, index, default=''):
    """Safely extract field from HL7 segment"""
    try:
        return str(segment[index]) if len(segment) > index else default
    except (IndexError, TypeError):
        return default


class ConfigurableHL7Parser:
    """ parsing logic """
    
    def __init__(self, parser_config: Dict[str, Dict[str, int]]):
        """Initialize with parser configuration dictionary"""
        if not parser_config:
            raise ValueError("Parser configuration cannot be empty")
        self.parser_config = parser_config
        
    def parse(self, raw_data: str) -> Dict[str, Any]:
        """Parse HL7 message using configuration"""
        try:
            # Parse HL7 message
            clean_data = raw_data.strip()
            msg = hl7.parse(clean_data)
            
            result = {
                'message_header': {},
                'patient_info': {},
                'order_request': {},
                'test_results': [],
                'raw_segments': [],
                'parsing_errors': []
            }
            
            for segment in msg:
                if len(segment) == 0:
                    continue
                
                segment_type = safe_get(segment, 0)
                
                if segment_type in self.parser_config:
                    try:
                        parsed_segment = self._parse_segment(segment, segment_type)
                        self._store_segment_data(result, segment_type, parsed_segment)
                    except Exception as e:
                        result['parsing_errors'].append(f"Error parsing {segment_type}: {e}")
                
                result['raw_segments'].append(str(segment))
            
            return result
            
        except Exception as e:
            return {
                'error': str(e),
                'raw_data': raw_data,
                'message_header': {},
                'patient_info': {},
                'order_request': {},
                'test_results': [],
                'parsing_errors': [str(e)]
            }
    
    def _parse_segment(self, segment, segment_type: str) -> Dict[str, str]:
        """Parse individual segment using configuration"""
        field_mapping = self.parser_config[segment_type]
        parsed = {}
        
        for field_name, field_index in field_mapping.items():
            value = safe_get(segment, field_index)
            
            # Special handling for OBX fields that contain "CODE^NAME^SYSTEM"
            if segment_type == 'OBX' and field_name in ['test_code', 'test_name', 'patient_name'] and '^' in value:
                parts = value.split('^')
                if field_name == 'test_code':
                    value = parts[0] if parts else value
                elif field_name == 'test_name':
                    value = parts[1] if len(parts) > 1 else value
            elif segment_type == 'PID' and field_name == 'patient_name' and '^' in value:
                parts = value.split('^')
                lastname = parts[0] if len(parts) > 0 else ''
                firstname = parts[1] if len(parts) > 1 else ''
                middle_initial = parts[2] if len(parts) > 2 else ''                
                value = f'{firstname} {middle_initial} {lastname}'.strip()
        
            parsed[field_name] = value

        return parsed
    
    def _store_segment_data(self, result: Dict, segment_type: str, parsed_segment: Dict):
        """Store parsed segment in appropriate result section"""
        if segment_type == 'MSH':
            result['message_header'] = parsed_segment
        elif segment_type == 'PID':
            result['patient_info'] = parsed_segment
        elif segment_type == 'OBR':
            result['order_request'] = parsed_segment
        elif segment_type == 'OBX':
            result['test_results'].append(parsed_segment)


class HL7Parser:
    """Facade that integrates config loading with parsing"""
    
    def __init__(self, yaml_config_path: str = None):
        """Initialize parser with configuration path"""
        self.yaml_config_path = yaml_config_path
        self.core_parser = None
        
        if yaml_config_path:
            self._initialize_parser()
    
    def _initialize_parser(self):
        """Load configuration and initialize core parser"""
        try:
            yaml_path = Path(self.yaml_config_path)
            parser_config = ConfigLoader.load_parser_config(yaml_path)
            
            if not parser_config:
                raise ValueError(f"No 'parser' section found in {self.yaml_config_path}")
            
            self.core_parser = ConfigurableHL7Parser(parser_config)
            logging.info(f"[Parser] Initialized with segments: {list(parser_config.keys())}")
            
        except Exception as e:
            logging.error(f"[Parser] Initialization failed: {e}")
            raise
    
    @staticmethod
    def parse(raw_data: str, yaml_config_path: str = None) -> Dict[str, Any]:
        """Static method for backward compatibility"""
        parser = HL7Parser(yaml_config_path)
        return parser.parse_with_config(raw_data)
    
    def parse_with_config(self, raw_data: str) -> Dict[str, Any]:
        """Parse using initialized configuration"""
        if not self.core_parser:
            raise ValueError("Parser not initialized")
        return self.core_parser.parse(raw_data)
    
    def reload_config(self):
        """Reload configuration from file"""
        if self.yaml_config_path:
            self._initialize_parser()
        else:
            raise ValueError("No config path set for reloading")
    
    def get_available_segments(self) -> List[str]:
        """Get configured segments"""
        return list(self.core_parser.parser_config.keys()) if self.core_parser else []
