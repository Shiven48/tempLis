from pathlib import Path
from hl7 import Message, Sequence, parse
from typing import Dict, List
from erba.abstracts import Processor
from configuration.logger import logger
from erba.models import ParserConfig, ParsingResult
from erba.processor import processFactory

class ConfigurableHL7Parser:
    """ parsing logic """
    
    def __init__(self, parser_config: ParserConfig):
        """Initialize with parser configuration dictionary"""
        if not parser_config:
            raise ValueError("Parser configuration cannot be empty")
        self.parser_config = parser_config
        self.result:ParsingResult = None
        self.message_types:List[str] = self._get_segments()

    def _get_segments(self) -> List[str]:
        configured_segments = [
                key for key, value in self.parser_config.model_dump().items() 
                if value
            ]
        return configured_segments
        
    def parse(self, raw_data: str) -> ParsingResult:
        """Parse HL7 message using configuration"""
        try:
            # Cleaning any previous session data to remove inconsistencies
            self.result = ParsingResult()

            clean_data = raw_data.strip()
            self.result.raw_segments = [clean_data]
            msg:Message = parse(clean_data)

            max_segment_number, len_obx_segments = self._get_max_sequence_number(msg)

            if max_segment_number == 0 or len_obx_segments == 0:
                self.result.parsing_errors.append(f"[Sequence Error] Captured 0 sequences. OBX segments missing")

            if max_segment_number != len_obx_segments:
                self.result.parsing_errors.append(f"[Sequence Error] Captured {len_obx_segments} sequences but the max sequence number is {max_segment_number}, {max_segment_number - len_obx_segments} sequences missing")
            
            if not self._message_parse_and_validate(msg):
                self.result.parsing_errors.append("[Sequence Error] OBX sequence validation failed")
            
            return self.result
        except Exception as e:
            return ParsingResult(
                message_header= {},
                order_request = {},
                test_results= [],
                findings= [],
                raw_segments= raw_data,
                parsing_errors=[str(e)],
                error= str(e),
            )

    def _get_max_sequence_number(self, msg: Message) -> tuple[int, int]:
        obx_segments:Sequence = msg.segments('OBX')
        sequence_numbers:List[int] = []
        
        for obx in obx_segments:
            try:
                sequence_number = int(obx[1][0])
                sequence_numbers.append(sequence_number)
            except (ValueError, IndexError, TypeError) as e:
                logger.warning(f"Invalid sequence number in OBX segment: {e}")
                continue

        if not sequence_numbers:
            return 0, len(obx_segments)
        
        max_segment_number = max(sequence_numbers)
        len_obx_segments = len(obx_segments)

        logger.info(f"{max_segment_number} -> {len_obx_segments}")
        return max_segment_number, len_obx_segments

    def _message_parse_and_validate(self, parsed_message:Message) -> bool:
        """Validate sequences maintain transmission order and follow business rules"""
        try:
            errors, is_valid = self._process_segments(parsed_message)
            if errors:
                self.result.parsing_errors.extend(errors)
            return is_valid
        except Exception as e:
            self.result.parsing_errors.append(f"[Sequence Error] Sequence validation failed: {e}")
            return False

    def _process_segments(self, message_segments: Message) -> tuple[list, bool]:
        """Get valid next sequences based on configuration ranges"""
        all_errors = []
        is_valid = True
        
        for segment_type in self.message_types:
            sequence: Sequence = message_segments.segments(segment_type)
            processor: Processor = processFactory(segment_type, sequence)
            errors, valid = processor.process_segment()
        
            if not valid and errors:
                all_errors.extend(errors)
                is_valid = False

            if segment_type == 'OBX':
                NM_result, IS_result = processor.parse()
                if NM_result:
                    self.result.test_results = NM_result
                if IS_result:
                    self.result.findings = IS_result
                segment_parsing_result = {'NM_results': NM_result, 'IS_results': IS_result}
            else:
                segment_parsing_result = processor.parse()

            self._store_segment_data(segment_type, segment_parsing_result)
        return all_errors, is_valid
    
    def _store_segment_data(self, segment_type: str, parsed_segment: List[Dict]) -> None:
        """Store parsed segment in appropriate result section"""
        if segment_type == 'MSH':
            self.result.message_header = parsed_segment[0] if len(parsed_segment) == 1 else parsed_segment
        elif segment_type == 'OBR':
            self.result.order_request = parsed_segment[0] if len(parsed_segment) == 1 else parsed_segment

class HL7Parser:
    """Facade that integrates config loading with parsing"""
    
    def __init__(self, yaml_config_path: str = None):
        """Initialize parser with configuration path"""
        self.yaml_config_path = yaml_config_path
        self.core_parser = None
        self._parser_config: ParserConfig = None
        
        if yaml_config_path:
            self._initialize_parser()
    
    def _initialize_parser(self):
        """Load configuration and initialize core parser"""
        try:
            self.yaml_path = Path(self.yaml_config_path)
            parser_config = self.parser_config
            
            if not any(parser_config.model_dump().values()):
                raise ValueError(f"[Config Error] No parser segments configured in {self.yaml_config_path}")
            
            self.core_parser = ConfigurableHL7Parser(parser_config)            
        except Exception as e:
            logger.error(f"[Parser Error] Initialization failed: {e}")
            raise

    @property
    def parser_config(self) -> ParserConfig:
        """Lazy load parser configuration"""
        if self._parser_config is None:
            from configuration.config_loader import ConfigLoader
            self._parser_config = ConfigLoader.load_parser_config(self.yaml_path)
        return self._parser_config
    
    @parser_config.setter
    def parser_config(self, value: ParserConfig):
        """Allow setting parser config for testing"""
        self._parser_config = value
    
    @staticmethod
    def parse(raw_data: str, yaml_config_path: str = None) -> ParsingResult:
        """Static method for backward compatibility"""
        parser = HL7Parser(yaml_config_path)
        return parser.parse_with_config(raw_data)
    
    def parse_with_config(self, raw_data: str) -> ParsingResult:
        """Parse using initialized configuration"""
        if not self.core_parser:
            raise ValueError("[Parser Error] Parser not initialized")
        return self.core_parser.parse(raw_data)
    
    def reload_config(self) -> None:
        """Reload configuration from file"""
        if self.yaml_config_path:
            try:
                self._parser_config = None
                parser_config = self.parser_config
            
                if not any(parser_config.model_dump().values()):
                    raise ValueError(f"[Config Error] No parser segments configured in {self.yaml_config_path}")
            
                self.core_parser = ConfigurableHL7Parser(parser_config)
            
            except Exception as e:
                logger.error(f"[Parser Error] Config reload failed: {e}")
                raise
        else:
            raise ValueError("[Config Path Error] No config path set for reloading")
    
    def get_available_segments(self) -> List[str]:
        """Get configured segments"""
        return list(self.core_parser.parser_config.model_dump().keys()) if self.core_parser else []
