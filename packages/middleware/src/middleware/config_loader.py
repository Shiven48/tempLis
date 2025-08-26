import yaml
import logging
from pathlib import Path
from typing import Dict, Any

class ConfigLoader:
    """Handles all configuration file I/O operations"""
    
    @staticmethod
    def load_yaml_config(yaml_path: Path) -> Dict[str, Any]:
        """Load YAML configuration file"""
        try:
            if yaml_path.exists():
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            else:
                # Create default config if doesn't exist
                default_config = ConfigLoader._create_default_config()
                yaml_path.parent.mkdir(parents=True, exist_ok=True)
                with open(yaml_path, 'w', encoding='utf-8') as f:
                    yaml.dump(default_config, f, default_flow_style=False)
                return default_config
        except Exception as e:
            logging.error(f"Error loading YAML config: {e}")
            return {}
    
    @staticmethod
    def load_parser_config(yaml_path: Path) -> Dict[str, Any]:
        """Extract only parser configuration from YAML"""
        full_config = ConfigLoader.load_yaml_config(yaml_path)
        return full_config.get('parser', {})
    
    @staticmethod
    def _create_default_config() -> Dict[str, Any]:
        """Create default configuration structure"""
        return {
            'analyzer': {
                'name': 'Erba Elite 580',
                'model': 'Elite580',
                'protocol': 'hl7',
                'message_types': ['ORU', 'QRY', 'ACK']
            },
            'parser': {
                'MSH': {'model': 3, 'machine': 4, 'datetime_of_message': 7, 'message_type': 8},
                'PID': {'patient_id': 3, 'patient_name': 5, 'gender': 8, 'birth_date': 7},
                'OBR': {'requested_timing': 6, 'reservation_timing': 7, 'approved_timing': 22},
                'OBX': {'test_code': 3, 'test_name': 3, 'result_value': 5, 'units': 6, 'flags': 8}
            }
        }