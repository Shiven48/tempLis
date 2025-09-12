import yaml
from pathlib import Path
from typing import List, TypeVar, Type, Union
from pydantic import BaseModel, ValidationError

from erba.models import AnalyzerConfig, ParserConfig, SegmentsConfig, TransportConfig

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
            file_name = Path(file_name).resolve()
            
            if not file_name.exists():
                raise FileNotFoundError(f"Configuration file not found: {file_name}")
            
            with open(file_name, 'r', encoding='utf-8') as f:
                raw_data = yaml.safe_load(f)
            
            if raw_data is None:
                raise ValueError(f"Empty or invalid YAML file: {file_name}")
            
            return model_class.model_validate(raw_data)
            
        except ValidationError as e:
            raise ValueError(f"Invalid configuration in {file_name}: {e}") from e

        except yaml.YAMLError as e:
            raise ValueError(f"YAML syntax error in {file_name}: {e}") from e

        except FileNotFoundError as e:
            raise FileNotFoundError(f"Configuration file not found: {file_name}") from e

        except Exception as e:
            raise RuntimeError(f"Failed to load configuration from {file_name}: {e}") from e

    
    @staticmethod
    def load_analyzer_config(file_name: Union[str, Path]) -> AnalyzerConfig:
        """Load and validate complete analyzer configuration"""
        return ConfigLoader.load_and_validate_config(file_name, AnalyzerConfig)
    
    @staticmethod
    def load_transport_config(file_name: Union[str, Path]) -> TransportConfig:
        """Load transport configuration section"""
        config = ConfigLoader.load_and_validate_config(file_name, AnalyzerConfig)
        transport_data = config.model_dump().get('transport', {})
        return TransportConfig.model_validate(transport_data)
    
    @staticmethod
    def load_parser_config(file_name: Union[str, Path]) -> ParserConfig:
        """Load parser configuration section"""
        config = ConfigLoader.load_and_validate_config(file_name, AnalyzerConfig)
        parser_data = config.model_dump().get('parser', {})
        return ParserConfig.model_validate(parser_data)

    @staticmethod
    def load_segments_config(file_name: Union[str, Path]) -> SegmentsConfig:
        """Load segments configuration section"""
        config = ConfigLoader.load_and_validate_config(file_name, AnalyzerConfig)
        segments_data = config.model_dump().get('segments', {})
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
