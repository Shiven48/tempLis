import re
from typing import Dict, List, Union
from hl7 import Field, Sequence
from datetime import datetime
from configuration.logger import logger
from erba.abstracts import Processor
from erba.models import ParserConfig, SegmentsConfig
from erba.constants import ERBA_YAML_PATH, OBX_RANGE

class MSHProcessor(Processor):
    def __init__(self, message_sequence: Sequence):
        self.message_segments:Sequence = message_sequence
        self.segment_type = 'MSH'
        self._parser_config: ParserConfig = None
        self._msh_config_dict: Dict = None
        self.errors:List[str] = []

    @property
    def parser_config(self) -> ParserConfig:
        """Lazy load parser config to avoid circular imports"""
        if self._parser_config is None:
            from configuration.config_loader import ConfigLoader
            self._parser_config = ConfigLoader.load_parser_config(ERBA_YAML_PATH)
        return self._parser_config

    @parser_config.setter
    def parser_config(self, value: ParserConfig):
        """Allow setting parser config for testing"""
        self._parser_config = value

    @property
    def msh_config_dict(self) -> Dict:
        """Lazy load MSH config dictionary"""
        if self._msh_config_dict is None:
            self._msh_config_dict = self.parser_config.MSH
        return self._msh_config_dict

    @msh_config_dict.setter
    def msh_config_dict(self, value: Dict):
        """Allow setting msh config dict for testing"""
        self._msh_config_dict = value

    def process_segment(self) -> tuple[List, bool]:
        all_errors = []
        is_valid = self._validate_msh_segments(self.message_segments[0])
        
        if not is_valid:
            all_errors.extend(self.errors)
            self.errors = []

        if all_errors:
            return all_errors, False
        else:
            return [], True
    
    def parse(self) -> Union[List[dict], tuple[dict, dict]]:
        """Parse individual segment using configuration with recursive index handling"""
        parsed = {}
        for field_name, field_index in self.msh_config_dict.items():
            value = self._recursive_fetch(self.message_segments[0], str(field_index))
            parsed[field_name] = value
        
        return [parsed]
    
    def validate_model(self, model: str) -> bool:
        """Validate model field"""
        return (
            bool(model and model.strip()) and  
            len(model.strip()) <= 227 and      
            not model.isdigit()                
        )

    def validate_machine(self, machine: str) -> bool:
        """Validate machine/facility field"""
        return (
            bool(machine and machine.strip()) and  
            len(machine.strip()) <= 227 and        
            len(machine.strip()) >= 2              
        )
    
    def validate_message_id(self, message_id: str) -> bool:
        """Validate message_id field"""
        if not message_id:
            return False
        if not (20 <= len(message_id) <= 35):
            return False
        return True


    def validate_datetime_of_message(self, datetime_str: str) -> bool:
        """Validate HL7 datetime format and logical date"""
        if not datetime_str:
            return False
        
        if not re.match(r'^\d{14}$', datetime_str):
            return False
        
        try:
            dt = datetime.strptime(datetime_str, '%Y%m%d%H%M%S')
            
            return (
                1900 <= dt.year <= 2100 and    
                1 <= dt.month <= 12 and        
                1 <= dt.day <= 31 and          
                0 <= dt.hour <= 23 and         
                0 <= dt.minute <= 59 and       
                0 <= dt.second <= 59           
            )
        except ValueError as e:
            self.errors.append(f"Validation Error in MSH sequence: {e}")
            return False

    def _validate_msh_segments(self, msh_segment:Sequence) -> bool:
        if not self.message_segments:
            self.errors.append(f"No header segment found")
            return False

        msh_segment:list = list(msh_segment)
        model_valid:bool = self.validate_model(str(msh_segment[3]))
        machine_valid = self.validate_machine(str(msh_segment[4]))  
        datetime_valid = self.validate_datetime_of_message(str(msh_segment[7]))
        message_id_valid: bool = self.validate_message_id(str(msh_segment[10]))
        
        if not model_valid:
            self.errors.append(f"Invalid model field: '{msh_segment[3]}'")
        
        if not machine_valid:
            self.errors.append(f"Invalid machine field: '{msh_segment[4]}'")
        
        if not datetime_valid:
            self.errors.append(f"Invalid datetime_of_message field: '{msh_segment[7]}'")

        if not message_id_valid:
            self.errors.append(f"Invalid message_id field: {msh_segment[10]}")
        
        return model_valid and machine_valid and datetime_valid and message_id_valid
    
    
    def _recursive_fetch(self, segment: Union[Sequence, str], index: str):
        """
        Recursive function to process nested indices like '3-1-2'.
        Handles both sequence indexing and HL7 component separation (^).
        """
        if '-' not in index:
            try:
                int_index = int(index)
                value = super().safe_get(segment, int_index)
                return str(value) if value is not None else ''
            except ValueError:
                return ''
        parts = index.split('-', 1)
        try:
            first_index = int(parts[0])
            remaining_index = parts[1]
            
            sub_segment = super().safe_get(segment, first_index, default=None)
            if sub_segment is None:
                return ''
            
            sub_segment = str(sub_segment)
            if isinstance(sub_segment, str) and '^' in sub_segment:
                components = sub_segment.split('^')
                return self._recursive_fetch(components, remaining_index)
            
            if isinstance(sub_segment, (list, tuple)):
                return self._recursive_fetch(sub_segment, remaining_index)
            
            return ''
            
        except ValueError:
            return ''
    

class OBRProcessor(Processor):
    def __init__(self, message_sequence: Sequence) -> tuple[list, bool]:
        self.message_segments:Sequence = message_sequence
        self.segment_type:str = 'OBR'
        self.errors:List[str] = []

        self._parser_config: ParserConfig = None
        self._obr_config_dict: Dict = None

    @property
    def parser_config(self) -> ParserConfig:
        """Lazy load parser config to avoid circular imports"""
        if self._parser_config is None:
            from configuration.config_loader import ConfigLoader
            self._parser_config = ConfigLoader.load_parser_config(ERBA_YAML_PATH)
        return self._parser_config
    
    @parser_config.setter
    def parser_config(self, value: ParserConfig):
        """Allow setting parser config for testing"""
        self._parser_config = value

    @property
    def obr_config_dict(self) -> Dict:
        """Lazy load OBR config dictionary"""
        if self._obr_config_dict is None:  
            self._obr_config_dict = self.parser_config.OBR
        return self._obr_config_dict
    
    @obr_config_dict.setter
    def obr_config_dict(self, value: Dict):
        """Allow setting obr config dict for testing"""
        self._obr_config_dict = value

    def process_segment(self) -> tuple[List, bool]:
        all_errors = []
        is_valid = self._validate_obr_segments(self.message_segments[0])
        
        if not is_valid:
            all_errors.extend(self.errors)
            self.errors = []

        if all_errors:
            return all_errors, False
        else:
            return [], True
        
    def _validate_obr_segments(self, obr_segment:Sequence):
        if not self.message_segments:
            self.errors.append(f"No OBR segment found")
            return False
        
        obr_segment:list = list(obr_segment)
        requested_timing_valid:bool = self.validate_datetime(str(obr_segment[6]))
        reservation_timing_valid:bool = self.validate_datetime(str(obr_segment[7]))

        if not requested_timing_valid:
            self.errors.append(f"Invalid requested_timing field in OBR segment: '{obr_segment[6]}'")
        
        if not reservation_timing_valid:
            self.errors.append(f"Invalid reservation_timing field in OBR segment: '{obr_segment[7]}'")
        
        return requested_timing_valid and reservation_timing_valid

    def validate_datetime(self, datetime_str: str) -> bool:
        """Validate HL7 datetime format and logical date"""        
        if not datetime_str:
            return False
        
        if not re.match(r'^\d{14}$', datetime_str):
            return False
        
        try:
            dt = datetime.strptime(datetime_str, '%Y%m%d%H%M%S')
            
            return (
                1900 <= dt.year <= 2100 and
                1 <= dt.month <= 12 and        
                1 <= dt.day <= 31 and          
                0 <= dt.hour <= 23 and         
                0 <= dt.minute <= 59 and       
                0 <= dt.second <= 59           
            )
        except ValueError:
            return False
    
    def parse(self) -> Union[List[dict], tuple[dict, dict]]:
        """Parse individual segment using configuration with recursive index handling"""
        parsed = {}
        for field_name, field_index in self.obr_config_dict.items():
            value = self._recursive_fetch(self.message_segments[0], str(field_index))
            parsed[field_name] = value
        
        return [parsed]
    
    def _recursive_fetch(self, segment: Union[Sequence, str], index: str):
        """
        Recursive function to process nested indices like '3-1-2'.
        Handles both sequence indexing and HL7 component separation (^).
        """
        if '-' not in index:
            try:
                int_index = int(index)
                value = super().safe_get(segment, int_index)
                return str(value) if value is not None else ''
            except ValueError:
                return ''
        parts = index.split('-', 1)
        try:
            first_index = int(parts[0])
            remaining_index = parts[1]
            
            sub_segment = super().safe_get(segment, first_index, default=None)
            if sub_segment is None:
                return ''
            
            sub_segment = str(sub_segment)
            if isinstance(sub_segment, str) and '^' in sub_segment:
                components = sub_segment.split('^')
                return self._recursive_fetch(components, remaining_index)
            
            if isinstance(sub_segment, (list, tuple)):
                return self._recursive_fetch(sub_segment, remaining_index)
            
            return ''
            
        except ValueError:
            return ''


class OBXProcessor(Processor):
    
    def __init__(self, message_sequence: Sequence):
        self.message_segments:Sequence = message_sequence
        self.segment_type:str = 'OBX'
        self.valid_obx:List[Sequence] = []
        self.valid_findings:List[Sequence] = [] 
        self.required_sequences = {}
        self.errors:List[str] = []

        self.parser_config:ParserConfig = None
        self.segment_config:SegmentsConfig = None


    @property
    def parser_config(self) -> ParserConfig:
        """Lazy load parser config to avoid circular imports"""
        if self._parser_config is None:
            from configuration.config_loader import ConfigLoader
            self._parser_config = ConfigLoader.load_parser_config(ERBA_YAML_PATH)
        return self._parser_config
    
    @parser_config.setter
    def parser_config(self, value: ParserConfig):
        """Allow setting parser config for testing"""
        self._parser_config = value

    @property
    def segment_config(self) -> SegmentsConfig:
        """Lazy load segment config to avoid circular imports"""
        if self._segment_config is None:
            from configuration.config_loader import ConfigLoader
            self._segment_config = ConfigLoader.load_segments_config(ERBA_YAML_PATH)
        return self._segment_config
    
    @segment_config.setter
    def segment_config(self, value: SegmentsConfig):
        """Allow setting segment config for testing"""
        self._segment_config = value
    
    def process_segment(self) -> tuple[List, bool]:
        all_errors = []

        segment_dict: dict[str, str] = self.segment_config.model_dump()
        self._parse_config_ranges(segment_dict)
        self._validate_segment_config()

        logger.info(self.optional_range)
        logger.info(self.required_range)
        logger.info(self.findings_range)
        
        for sequence in self.message_segments:
            current_sequence: Field = sequence[1]
            sequence_type: Field = sequence[2]
            
            is_valid = self._check_bounds(current_sequence, sequence_type, sequence)
            if not is_valid and self.errors:
                all_errors.extend(self.errors)
                self.errors = []
                        
        completeness_valid = self._validate_required_range_completeness()
        if not completeness_valid and self.errors:
            all_errors.extend(self.errors)
            self.errors = []

        if all_errors:
            return all_errors, False
        else:
            return [], True
            
    def _parse_config_ranges(self, config_dict: dict):
        """Parse configuration ranges from config dictionary"""
        parsed = {}
        for key, value in config_dict.items():
            if not value:
                parsed[key] = {'type': 'none'}
                continue
                
            val = value[0] if isinstance(value, list) else value
            
            if '+' in val:
                parsed[key] = {
                    'type': 'threshold', 
                    'min': int(val.replace('+', ''))
                }
            elif '-' in val:
                parts = val.split('-')
                if len(parts) == 2:
                    parsed[key] = {
                        'type': 'range', 
                        'min': int(parts[0]), 
                        'max': int(parts[1])
                    }
                else:
                    parsed[key] = {
                        'type': 'invalid'
                    }
            else:
                try:
                    parsed[key] = {
                        'type': 'single', 
                        'value': int(val)
                    }
                except ValueError:
                    parsed[key] = {'type': 'invalid'}
        
        self.optional_range:dict = parsed.get('optional', {})
        self.required_range:dict = parsed.get('required', {})
        self.findings_range:dict = parsed.get('findings', {})

    def _validate_segment_config(self):
        # optional range(1-6) yaml configuration validation
        if not self.optional_range['type'] == 'range':
            logger.error("[Config Error] The segment validation failed for 'optional' segment config")
        elif len(self.optional_range.keys()) != 3:
            logger.error("[Config Error] The segment validation failed, Expected three keys 'range', 'min' and 'max'")
        logger.info('Optional range configuration validated successfully')

        # required range(7-36) yaml configuration validation
        if not self.required_range['type'] == 'range':
            logger.error("[Config Error] The segment validation failed for 'required' segment config")
        elif len(self.optional_range.keys()) != 3:
            logger.error("[Config Error] The segment validation failed, Expected three keys 'range', 'min' and 'max'")
        logger.info('Required range configuration validated successfully') 

        # findings range(37+) yaml configuration validation
        if not self.findings_range['type'] == 'threshold':
            logger.error("[Config Error] The segment validation failed for required 'findings' segment config")
        elif len(self.findings_range.keys()) != 2:
            logger.error("[Config Error] The segment validation failed, Expected two keys 'threshold' and 'min'")
        logger.info('Findings range configuration validated successfully')

    def _check_bounds(self, current_sequence:Field, sequence_type:Field, sequence:Sequence) -> bool:
        """This receives only one sequence at a time and branches the logic based on the sequence_number"""
        try:
            current_sequence = int(str(current_sequence))
            sequence_type = str(sequence_type)
        except (ValueError, TypeError):
            self.errors.append(f"[Sequence Number Error] Invalid sequence value: {current_sequence}")
            return False
        
        if self.optional_range['min'] <= current_sequence <= self.optional_range['max']:
            return self._process_optional_range(current_sequence, sequence_type)
        elif self.required_range['min'] <= current_sequence <= self.required_range['max']:
            return self._process_required_range(sequence_type, sequence)
        elif current_sequence >= self.findings_range['min']:
            return self._process_findings_range(sequence_type, sequence)
        else:
            self.errors.append(f"[Sequence Number Error] The sequence:{current_sequence} is not within valid range")
            return False
    
    def _process_optional_range(self, current_sequence:int, sequence_type:str) -> bool:
        if sequence_type == 'IS':
            logger.debug(f"Ignoring optional IS sequence {current_sequence}")
            return True
        elif sequence_type == 'NM':
            logger.warning(f"Got NM segment type in range {self.optional_range['min']} - {self.optional_range['max']}")
            return True
        else:
            logger.error(f"[Sequence Error] Got invalid sequence type: {sequence_type}")
            return False

    def _process_required_range(self, value_type: str, sequence: Sequence) -> bool:
        """
        Validates individual sequence and stores it. Complete validation happens later.
        """
    
        if value_type != 'NM':
            self.errors.append(f"[Unexpected Segment Error] Expected NM segment type in range {self.required_range['min']} - {self.required_range['max']}")
            return False
        
        logger.info(f"The length of sequence is: {len(sequence)} -> {sequence}")
    
        if len(sequence) != OBX_RANGE:
            self.errors.append(f"[Field Count Error] In OBX sequence, Expected {OBX_RANGE} fields but got {len(sequence)} at sequence: {int(str(sequence[1]))}")
            return False
    
        try:
            current_sequence: int = int(str(sequence[1]))
        except (ValueError, TypeError, IndexError):
            self.errors.append("[Sequence Number Error] Important fields missing - Could not extract sequence number from sequence")
            return False

        if current_sequence in self.required_sequences:
            self.errors.append(f"[Sequence Number Error] Important fields missing - Duplicate sequence {current_sequence}")
            return False
    
        self.required_sequences[current_sequence] = sequence
        return True

    def _validate_required_range_completeness(self) -> bool:
        """
        Validates that we have exactly 30 consecutive sequences (7-36) after processing all sequences.
        Only adds to valid_obx if all validations pass.
        """
    
        expected_count:int = (self.required_range['max'] - self.required_range['min']) + 1
        expected_range = set(range(self.required_range['min'], self.required_range['max'] + 1))
        actual_sequences = set(self.required_sequences.keys())
        required_found:set = actual_sequences.intersection(expected_range)
    
        if len(required_found) < expected_count:
            missing = expected_range - actual_sequences
            self.errors.append(f"[Sequence Number Error] Important fields missing - Expected {expected_count} sequences (7-36), got {len(required_found)}. Missing sequences: {sorted(missing)}")
            return False
    
        if len(required_found) > expected_count:
            self.errors.append(f"[Sequence Number Error] Important fields missing - Logic error: found {len(required_found)} sequences in range 7-36")
            return False
    
        sorted_sequences = sorted(required_found)
        expected_sequence = sorted(expected_range)
    
        if sorted_sequences != expected_sequence:
            self.errors.append(f"[Sequence Number Error] Important fields missing - Sequences are not consecutive. Expected [7-36], got {sorted_sequences}")
            return False
    
        for seq_num in expected_sequence:
            self.valid_obx.append(self.required_sequences[seq_num])
    
        logger.info(f"Successfully validated all {expected_count} required sequences (7-36)")
        return True

    def _process_findings_range(self,sequence_type:str, sequence:Sequence) -> bool:
        if sequence_type == 'IS':
            self.valid_findings.append(sequence)
            return True
        elif sequence_type == 'NM':
            logger.warning(f"Got NM segment type in range {self.optional_range['min']} - {self.optional_range['max']}")
            self.valid_findings.append(sequence)
            return True
        else:
            logger.error(f"[Sequence Error] Got invalid sequence type: {sequence_type}")
            return False

    def parse(self) -> Union[List[dict], tuple[dict, dict]]:
        parser_config_dict:Dict = self.parser_config.model_dump()
        NM_result:List[Dict] = []
        IS_result:List[Dict] = []

        # NM handling
        for segment in self.valid_obx:
            if len(segment) == 0:
                continue
            
            if self.segment_type in parser_config_dict:
                try:
                    NM_result.append(self._parse_segment(segment, self.segment_type))
                except Exception as e:
                    logger.error(f"[Segment Error] Unexpected Exception: {e}")

        # IS handling
        for segment in self.valid_findings:
            if len(segment) == 0:
                continue
            IS_result.append(self._recursive_fetch(segment, "3-1"))
        return NM_result, IS_result
    
    def _parse_segment(self, segment: Sequence, segment_type: str) -> Dict[str, str]:
        """Parse individual segment using configuration with recursive index handling"""
        yaml_field_mapping = getattr(self.parser_config, segment_type, {})
        parsed = {}

        for field_name, field_index in yaml_field_mapping.items():
            value = self._recursive_fetch(segment, str(field_index))
            parsed[field_name] = value
        
        return parsed


    def _recursive_fetch(self, segment: Union[Sequence, str], index: str):
        """
        Recursive function to process nested indices like '3-1-2'.
        Handles both sequence indexing and HL7 component separation (^).
        """
        if '-' not in index:
            try:
                int_index = int(index)
                value = super().safe_get(segment, int_index)
                return str(value) if value is not None else ''
            except ValueError:
                return ''
        parts = index.split('-', 1)
        try:
            first_index = int(parts[0])
            remaining_index = parts[1]
            
            sub_segment = super().safe_get(segment, first_index, default=None)
            if sub_segment is None:
                return ''
            
            sub_segment = str(sub_segment)
            if isinstance(sub_segment, str) and '^' in sub_segment:
                components = sub_segment.split('^')
                return self._recursive_fetch(components, remaining_index)
            
            if isinstance(sub_segment, (list, tuple)):
                return self._recursive_fetch(sub_segment, remaining_index)
            
            return ''
            
        except ValueError:
            return ''
    
    
def processFactory(segment:str, message_segments:Sequence) -> 'Processor':
        processor: Processor = None
        if segment == 'MSH':
            processor = MSHProcessor(message_segments)
        elif segment == 'OBR':
            processor = OBRProcessor(message_segments)
        elif segment == 'OBX':
            processor = OBXProcessor(message_segments)
        else:
            if segment in ["PV1", "PID"]:
                logger.warning(f"[Processor Error] The segment:{segment} don't have a processor yet try skipping it from yaml")
            else:
                logger.error(f"[Invalid Message Type] The segment:{segment} is not valid")
        return processor