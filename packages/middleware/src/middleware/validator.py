import logging
import time
import os
import yaml
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import ipaddress
from typing import Any, Dict, Optional
from middleware.models import (
    AnalyzerConfig, 
    ErbaMessage, 
    ErbaPatientInfo, 
    ErbaTestResult, 
    ValidationResult
)
from pydantic import ValidationError


class DataValidator:
    def __init__(self, config: AnalyzerConfig):
        self.config = config
        
    def validate_and_create_objects(self, parsed_data: Dict[str, Any]) -> Optional[ErbaMessage]:
        """Validate parsed data against Pydantic models"""
        try:
            erba_message = ErbaMessage(
                patient_info=ErbaPatientInfo(**parsed_data.get('patient_info', {})),
                test_results=[ErbaTestResult(**result) for result in parsed_data.get('test_results', [])],
                timestamp=time.strftime('%Y-%m-%d %H:%M:%S'),
                analyzer_id=self.config.name
            )
            
            return erba_message
            
        except ValidationError as e:
            logging.error(f"Validation error: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected validation error: {e}")
            return None
        
class ConfigurationValidator:
    """Validates analyzer configuration files"""
    
    REQUIRED_FIELDS = {
        'device': str,
        'protocol': str,
        'transport': dict,
        'encoding': str
    }
    
    REQUIRED_TRANSPORT_FIELDS = {
        'mode': str,
        'host': str,
        'port': (int, str)
    }
    
    VALID_PROTOCOLS = ['HL7', 'ASTM', 'HL7-MLLP']
    VALID_TRANSPORT_MODES = ['tcp', 'serial', 'udp']
    VALID_ENCODINGS = ['utf-8', 'ascii', 'latin-1', 'cp1252']
    
    def __init__(self, config_directory: str = "packages/middleware/src/configuration"):
        self.config_directory = Path(config_directory)
        self.validated_configs = {}
    
    def validate_single_config(self, config_path: str) -> ValidationResult:
        """Validate a single configuration file"""
        errors = []
        warnings = []
        config_data = None
        
        try:
            # Check file exists
            if not os.path.exists(config_path):
                errors.append(f"Configuration file not found: {config_path}")
                return ValidationResult(False, errors, warnings)
            
            # Load YAML
            with open(config_path, 'r', encoding='utf-8') as file:
                config_data = yaml.safe_load(file)
            
            if not config_data or not isinstance(config_data, dict):
                errors.append("Configuration file is empty or not a valid YAML dictionary")
                return ValidationResult(False, errors, warnings)
            
            # Validate required fields
            self._validate_required_fields(config_data, errors)
            
            # Validate specific field values
            self._validate_device_name(config_data, errors, warnings)
            self._validate_protocol(config_data, errors, warnings)
            self._validate_transport(config_data, errors, warnings)
            self._validate_encoding(config_data, errors, warnings)
            
            # Additional validations
            self._validate_optional_fields(config_data, warnings)
            
        except yaml.YAMLError as e:
            errors.append(f"YAML parsing error: {str(e)}")
        except Exception as e:
            errors.append(f"Unexpected error validating config: {str(e)}")
        
        is_valid = len(errors) == 0
        return ValidationResult(is_valid, errors, warnings, config_data)
    
    def _validate_required_fields(self, config: Dict[str, Any], errors: List[str]):
        """Validate all required fields are present with correct types"""
        for field, expected_type in self.REQUIRED_FIELDS.items():
            if field not in config:
                errors.append(f"Missing required field: '{field}'")
            elif not isinstance(config[field], expected_type):
                errors.append(f"Field '{field}' must be of type {expected_type.__name__}, got {type(config[field]).__name__}")
    
    def _validate_device_name(self, config: Dict[str, Any], errors: List[str], warnings: List[str]):
        """Validate device name"""
        if 'device' in config:
            device_name = config['device']
            if not device_name or not isinstance(device_name, str):
                errors.append("Device name must be a non-empty string")
            elif len(device_name) > 50:
                warnings.append("Device name is longer than 50 characters")
            elif not device_name.replace(' ', '').replace('_', '').replace('-', '').isalnum():
                warnings.append("Device name contains special characters that may cause issues")
    
    def _validate_protocol(self, config: Dict[str, Any], errors: List[str], warnings: List[str]):
        """Validate protocol field"""
        if 'protocol' in config:
            protocol = config['protocol'].upper() if isinstance(config['protocol'], str) else config['protocol']
            
            if protocol not in self.VALID_PROTOCOLS:
                errors.append(f"Invalid protocol '{config['protocol']}'. Valid options: {', '.join(self.VALID_PROTOCOLS)}")
    
    def _validate_transport(self, config: Dict[str, Any], errors: List[str], warnings: List[str]):
        """Validate transport configuration"""
        if 'transport' not in config:
            return
        
        transport = config['transport']
        
        # Check required transport fields
        for field, expected_type in self.REQUIRED_TRANSPORT_FIELDS.items():
            if field not in transport:
                errors.append(f"Missing required transport field: '{field}'")
            elif isinstance(expected_type, tuple):
                # Multiple allowed types
                if not any(isinstance(transport[field], t) for t in expected_type):
                    type_names = [t.__name__ for t in expected_type]
                    errors.append(f"Transport field '{field}' must be one of types: {', '.join(type_names)}")
            elif not isinstance(transport[field], expected_type):
                errors.append(f"Transport field '{field}' must be of type {expected_type.__name__}")
        
        # Validate specific transport values
        if 'mode' in transport:
            mode = transport['mode'].lower() if isinstance(transport['mode'], str) else transport['mode']
            if mode not in self.VALID_TRANSPORT_MODES:
                errors.append(f"Invalid transport mode '{transport['mode']}'. Valid options: {', '.join(self.VALID_TRANSPORT_MODES)}")
        
        if 'host' in transport:
            self._validate_host(transport['host'], errors, warnings)
        
        if 'port' in transport:
            self._validate_port(transport['port'], errors, warnings)
    
    def _validate_host(self, host: Any, errors: List[str], warnings: List[str]):
        """Validate host/IP address"""
        if not isinstance(host, str) or not host:
            errors.append("Host must be a non-empty string")
            return
        
        # Check if it's a valid IP address
        try:
            ipaddress.ip_address(host)
        except ValueError:
            # Not an IP address, check if it's a valid hostname
            if host.lower() in ['localhost', 'local']:
                warnings.append(f"Host '{host}' should probably be '127.0.0.1' for local connections")
            elif not self._is_valid_hostname(host):
                warnings.append(f"Host '{host}' may not be a valid hostname or IP address")
    
    def _validate_port(self, port: Any, errors: List[str], warnings: List[str]):
        """Validate port number"""
        try:
            port_num = int(port)
            if port_num < 1 or port_num > 65535:
                errors.append(f"Port {port_num} is outside valid range (1-65535)")
            elif port_num < 1024:
                warnings.append(f"Port {port_num} is a privileged port (< 1024) and may require elevated permissions")
            elif port_num in [80, 443, 22, 21, 25]:
                warnings.append(f"Port {port_num} is commonly used by other services")
        except (ValueError, TypeError):
            errors.append(f"Port must be a valid integer, got: {port}")
    
    def _validate_encoding(self, config: Dict[str, Any], errors: List[str], warnings: List[str]):
        """Validate encoding field"""
        if 'encoding' in config:
            encoding = config['encoding'].lower() if isinstance(config['encoding'], str) else config['encoding']
            
            if encoding not in self.VALID_ENCODINGS:
                errors.append(f"Invalid encoding '{config['encoding']}'. Valid options: {', '.join(self.VALID_ENCODINGS)}")
            
            # Check for potential issues
            if encoding == 'ascii':
                warnings.append("ASCII encoding may not handle international characters properly")
    
    def _validate_optional_fields(self, config: Dict[str, Any], warnings: List[str]):
        """Validate optional fields and suggest improvements"""
        
        # Check for recommended optional fields
        recommended_fields = ['timeout', 'retry_attempts', 'buffer_size']
        missing_recommended = [field for field in recommended_fields if field not in config]
        
        if missing_recommended:
            warnings.append(f"Consider adding optional fields: {', '.join(missing_recommended)}")
        
        # Validate timeout if present
        if 'timeout' in config:
            try:
                timeout = float(config['timeout'])
                if timeout <= 0:
                    warnings.append("Timeout should be a positive number")
                elif timeout > 300:
                    warnings.append("Timeout value seems very high (> 5 minutes)")
            except (ValueError, TypeError):
                warnings.append("Timeout should be a numeric value")
        
        # Validate retry_attempts if present
        if 'retry_attempts' in config:
            try:
                retries = int(config['retry_attempts'])
                if retries < 0:
                    warnings.append("Retry attempts should be non-negative")
                elif retries > 10:
                    warnings.append("High retry count may cause long delays")
            except (ValueError, TypeError):
                warnings.append("Retry attempts should be an integer")
    
    def _is_valid_hostname(self, hostname: str) -> bool:
        """Check if hostname follows basic hostname rules"""
        if len(hostname) > 253:
            return False
        
        if hostname.endswith('.'):
            hostname = hostname[:-1]
        
        parts = hostname.split('.')
        for part in parts:
            if len(part) < 1 or len(part) > 63:
                return False
            if not part.replace('-', '').isalnum():
                return False
            if part.startswith('-') or part.endswith('-'):
                return False
        
        return True
    
    def validate_all_configs(self) -> Dict[str, ValidationResult]:
        """Validate all configuration files in the directory"""
        results = {}
        
        if not self.config_directory.exists():
            return {'directory_error': ValidationResult(
                False, 
                [f"Configuration directory does not exist: {self.config_directory}"], 
                []
            )}
        
        yaml_files = list(self.config_directory.glob("*.yaml")) + list(self.config_directory.glob("*.yml"))
        
        if not yaml_files:
            return {'no_configs': ValidationResult(
                False,
                [f"No YAML configuration files found in {self.config_directory}"],
                []
            )}
        
        for config_file in yaml_files:
            config_name = config_file.stem
            results[config_name] = self.validate_single_config(str(config_file))
        
        return results
    
    def get_valid_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get all valid configurations"""
        results = self.validate_all_configs()
        valid_configs = {}
        
        for name, result in results.items():
            if result.is_valid and result.config_data:
                valid_configs[name] = result.config_data
        
        return valid_configs
    
    def validate_analyzer_compatibility(self, analyzer_name: str, protocol_filter: Optional[str] = None) -> ValidationResult:
        """Validate that a specific analyzer configuration is compatible with current setup"""
        results = self.validate_all_configs()
        errors = []
        warnings = []
        config_data = None
        
        # Find matching analyzer config
        matching_configs = []
        for name, result in results.items():
            if result.is_valid and result.config_data:
                if result.config_data.get('device', '').lower() == analyzer_name.lower():
                    matching_configs.append((name, result))
        
        if not matching_configs:
            errors.append(f"No valid configuration found for analyzer '{analyzer_name}'")
            return ValidationResult(False, errors, warnings)
        
        if len(matching_configs) > 1:
            warnings.append(f"Multiple configurations found for analyzer '{analyzer_name}': {[name for name, _ in matching_configs]}")
        
        # Use first matching config
        config_name, result = matching_configs[0]
        config_data = result.config_data
        
        # Apply protocol filter if specified
        if protocol_filter:
            config_protocol = config_data.get('protocol', '').upper()
            if protocol_filter.upper() not in config_protocol:
                errors.append(f"Analyzer '{analyzer_name}' uses protocol '{config_protocol}' but '{protocol_filter}' is required")
                return ValidationResult(False, errors, warnings)
        
        # Additional compatibility checks
        transport = config_data.get('transport', {})
        if transport.get('mode', '').lower() == 'serial':
            warnings.append("Serial communication may require additional setup for network middleware")
        
        return ValidationResult(True, errors, warnings, config_data)

def validate_analyzer_config(analyzer_name: str, config_directory: str = "packages/middleware/src/configuration") -> Tuple[bool, List[str], List[str], Optional[Dict[str, Any]]]:
    """
    Convenience function to validate a specific analyzer configuration
    
    Returns:
        (is_valid, errors, warnings, config_data)
    """
    validator = ConfigurationValidator(config_directory)
    result = validator.validate_analyzer_compatibility(analyzer_name)
    
    return result.is_valid, result.errors, result.warnings, result.config_data

def get_available_analyzers(config_directory: str = "packages/middleware/src/configuration", protocol_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get list of available and valid analyzer configurations
    
    Args:
        config_directory: Path to configuration files
        protocol_filter: Optional protocol filter (e.g., 'HL7', 'ASTM')
    
    Returns:
        List of analyzer info dictionaries
    """
    validator = ConfigurationValidator(config_directory)
    valid_configs = validator.get_valid_configs()
    
    analyzers = []
    for config_name, config_data in valid_configs.items():
        # Apply protocol filter if specified
        if protocol_filter:
            config_protocol = config_data.get('protocol', '').upper()
            if protocol_filter.upper() not in config_protocol:
                continue
        
        analyzer_info = {
            'name': config_data.get('device', config_name),
            'protocol': config_data.get('protocol'),
            'transport_mode': config_data.get('transport', {}).get('mode'),
            'host': config_data.get('transport', {}).get('host'),
            'port': config_data.get('transport', {}).get('port'),
            'config_file': config_name
        }
        analyzers.append(analyzer_info)
    
    return analyzers