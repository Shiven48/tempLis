import yaml
from pathlib import Path
from typing import List, TypeVar, Type, Union
from pydantic import BaseModel, ValidationError

from erba import AnalyzerConfig, ParserConfig, SegmentsConfig, TransportConfig
T = TypeVar('T', bound=BaseModel)

class ConfigLoader:
    """Pydantic-powered configuration loader with validation"""
    
    @staticmethod
    def load_and_validate_config(
        file_name: Union[str, Path], 
        model_class: Type[T]
    ) -> T:
        """Load YAML and validate against Pydantic model"""
        try:
            file_name = Path(file_name)
            
            if not file_name.exists():
                raise FileNotFoundError(f"Configuration file not found: {file_name}")
            
            with open(file_name, 'r', encoding='utf-8') as f:
                raw_data = yaml.safe_load(f)
            
            if raw_data is None:
                raise ValidationError(f"Empty or invalid YAML file: {file_name}")
            
            return model_class.model_validate(raw_data)
            
        except ValidationError as e:
            error_details = []
            for error in e.errors():
                field = " -> ".join(str(loc) for loc in error['loc'])
                message = error['msg']
                error_details.append(f"{field}: {message}")
            
            raise ValidationError(
                f"Configuration validation failed for {file_name}:\n" + 
                "\n".join(f"  - {detail}" for detail in error_details)
            ) from e
        
        except yaml.YAMLError as e:
            raise ValidationError(f"YAML parsing error in {file_name}: {e}") from e
        
        except Exception as e:
            raise ValidationError(f"Unexpected error loading {file_name}: {e}") from e
    
    @staticmethod
    def load_analyzer_config(file_name: Union[str, Path]) -> AnalyzerConfig:
        """Load and validate complete analyzer configuration"""
        return ConfigLoader.load_and_validate_config(file_name, AnalyzerConfig)
    
    @staticmethod
    def load_transport_config(file_name: Union[str, Path]) -> TransportConfig:
        """Load and validate transport configuration only"""
        with open(file_name, 'r', encoding='utf-8') as f:
            raw_data = yaml.safe_load(f)
        
        transport_data = raw_data.get('transport', {})
        return TransportConfig.model_validate(transport_data)
    
    @staticmethod
    def load_parser_config(file_name: Union[str, Path]) -> ParserConfig:
        """Load and validate transport configuration only"""
        with open(file_name, 'r', encoding='utf-8') as f:
            raw_data = yaml.safe_load(f)
        
        parser_data = raw_data.get('parser', {})
        return ParserConfig.model_validate(parser_data) 

    def load_segments_config(file_name: Union[str, Path]) -> SegmentsConfig:
        """Load and validate segments configuration only""" 
        with open(file_name, 'r', encoding='utf-8') as f:
            raw_data = yaml.safe_load(f)
        
        segments_data = raw_data.get('segments', {})
        return SegmentsConfig.model_validate(segments_data)
 
    @staticmethod
    def validate_config_file(file_name: Union[str, Path]) -> tuple[bool, List[str]]:
        """Validate configuration file and return status with errors"""
        try:
            ConfigLoader.load_analyzer_config(file_name)
            return True, []
        except ValidationError as e:
            return False, [str(e)]
        except Exception as e:
            return False, [f"Unexpected validation error: {e}"]
