from middleware.models import AnalyzerConfig, ParserConfig, SegmentsConfig, TransportConfig
import yaml
from pathlib import Path
from typing import List, TypeVar, Type, Union
from pydantic import BaseModel, ValidationError

T = TypeVar('T', bound=BaseModel)

class ConfigLoader:
    """Pydantic-powered configuration loader with validation"""
    
    @staticmethod
    def load_and_validate_config(
        yaml_path: Union[str, Path], 
        model_class: Type[T]
    ) -> T:
        """Load YAML and validate against Pydantic model"""
        try:
            yaml_path = Path(yaml_path)
            
            if not yaml_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {yaml_path}")
            
            with open(yaml_path, 'r', encoding='utf-8') as f:
                raw_data = yaml.safe_load(f)
            
            if raw_data is None:
                raise ValidationError(f"Empty or invalid YAML file: {yaml_path}")
            
            return model_class.model_validate(raw_data)
            
        except ValidationError as e:
            error_details = []
            for error in e.errors():
                field = " -> ".join(str(loc) for loc in error['loc'])
                message = error['msg']
                error_details.append(f"{field}: {message}")
            
            raise ValidationError(
                f"Configuration validation failed for {yaml_path}:\n" + 
                "\n".join(f"  - {detail}" for detail in error_details)
            ) from e
        
        except yaml.YAMLError as e:
            raise ValidationError(f"YAML parsing error in {yaml_path}: {e}") from e
        
        except Exception as e:
            raise ValidationError(f"Unexpected error loading {yaml_path}: {e}") from e
    
    @staticmethod
    def load_analyzer_config(yaml_path: Union[str, Path]) -> AnalyzerConfig:
        """Load and validate complete analyzer configuration"""
        return ConfigLoader.load_and_validate_config(yaml_path, AnalyzerConfig)
    
    @staticmethod
    def load_transport_config(yaml_path: Union[str, Path]) -> TransportConfig:
        """Load and validate transport configuration only"""
        with open(yaml_path, 'r', encoding='utf-8') as f:
            raw_data = yaml.safe_load(f)
        
        transport_data = raw_data.get('transport', {})
        return TransportConfig.model_validate(transport_data)
    
    @staticmethod
    def load_parser_config(yaml_path: Union[str, Path]) -> ParserConfig:
        """Load and validate transport configuration only"""
        with open(yaml_path, 'r', encoding='utf-8') as f:
            raw_data = yaml.safe_load(f)
        
        parser_data = raw_data.get('parser', {})
        return ParserConfig.model_validate(parser_data) 

    def load_segments_config(yaml_path: Union[str, Path]) -> SegmentsConfig:
        """Load and validate segments configuration only""" 
        with open(yaml_path, 'r', encoding='utf-8') as f:
            raw_data = yaml.safe_load(f)
        
        segments_data = raw_data.get('segments', {})
        return SegmentsConfig.model_validate(segments_data)

    
    @staticmethod
    def validate_config_file(yaml_path: Union[str, Path]) -> tuple[bool, List[str]]:
        """Validate configuration file and return status with errors"""
        try:
            ConfigLoader.load_analyzer_config(yaml_path)
            return True, []
        except ValidationError as e:
            return False, [str(e)]
        except Exception as e:
            return False, [f"Unexpected validation error: {e}"]
