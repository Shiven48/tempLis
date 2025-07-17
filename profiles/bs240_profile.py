"""
BS240 Analyzer Profile
"""
from .base_profile import BaseProfile

class ConfigBasedRecordWrapper:
    """Wrapper that uses config to convert list-based records to attribute-accessible objects"""
    
    def __init__(self, record_list, config_fields):
        self.record_list = record_list or []
        self.config_fields = config_fields or []
        self._field_index_map = self._build_field_index_map()
    
    def _build_field_index_map(self):
        """Build a mapping from field names to their indices"""
        field_map = {}
        for field in self.config_fields:
            field_map[field['name']] = field['index']
        return field_map
    
    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
        
        if name in self._field_index_map:
            index = self._field_index_map[name]
            if index < len(self.record_list):
                return self.record_list[index]
        return None

class ConfigBasedComponentWrapper:
    """Wrapper for component fields using config"""
    
    def __init__(self, component_list, component_config):
        self.component_list = component_list or []
        self.component_config = component_config or {}
        self._field_index_map = self._build_field_index_map()
    
    def _build_field_index_map(self):
        """Build a mapping from field names to their indices"""
        field_map = {}
        if 'fields' in self.component_config:
            for field in self.component_config['fields']:
                field_map[field['name']] = field['index']
        return field_map
    
    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
        
        if name in self._field_index_map:
            index = self._field_index_map[name]
            if index < len(self.component_list):
                return self.component_list[index]
        return None

class BS240Profile(BaseProfile):
    """Profile for BS240 analyzer"""
   
    def __init__(self, config_path: str = "config.json"):
        self.machine_type = "BS_240"
        super().__init__(self.machine_type, config_path)
   
    def get_machine_type(self) -> str:
        return "BS_240"
   
    def get_specific_settings(self) -> dict:
        """BS240 specific settings"""
        return {
            "supports_qc": True,
            "max_samples": 240,
            "supported_tests": [
                "GLU", "BUN", "CREA", "ALT", "AST",
                "TBIL", "DBIL", "TP", "ALB", "CHOL"
            ]
        }
   
    def validate_sample_id(self, sample_id: str) -> bool:
        """Validate BS240 sample ID format"""
        # BS240 specific validation
        return len(sample_id) <= 20 and sample_id.isalnum()
    
    def _create_record_from_config(self, result_record, record_type='result'):
        """Create a record wrapper using the config for the specified record type"""
        if not result_record or not hasattr(self, 'config'):
            return None
        
        # Get the config fields for the specified record type
        record_config = self.config.get(record_type, {})
        fields = record_config.get('fields', [])
        
        # Create main record wrapper
        record_wrapper = ConfigBasedRecordWrapper(result_record, fields)
        
        # Create component wrappers for nested fields
        for field in fields:
            if field.get('type') == 'componentField' and 'component' in field:
                field_name = field['name']
                field_index = field['index']
                component_config = field['component']
                
                # Get the component data from the record
                component_data = result_record[field_index] if field_index < len(result_record) else []
                
                # Create component wrapper
                component_wrapper = ConfigBasedComponentWrapper(component_data, component_config)
                
                # Add component as attribute to the main wrapper
                setattr(record_wrapper, field_name, component_wrapper)
        
        return record_wrapper
    
    def _get_field_value(self, result_record, field_path, record_type='result'):
        """
        Get a field value using dot notation path (e.g., 'assay_info.assay_number')
        """
        record = self._create_record_from_config(result_record, record_type)
        if not record:
            return None
        
        # Split the path and traverse
        parts = field_path.split('.')
        current = record
        
        for part in parts:
            current = getattr(current, part, None)
            if current is None:
                return None
        
        return current
   
    def format_result_for_api(self, result_record) -> dict:
        """Format result record for remote API"""
        if not result_record:
            return {}
       
        # Extract key fields based on BS240 configuration
        print(f"Before api format: {result_record}")
        
        # Create record wrapper from config
        record = self._create_record_from_config(result_record, 'result')
        
        if not record:
            # Fallback to manual extraction if config-based approach fails
            assay_info = result_record[2] if len(result_record) > 2 else []
            result_value = result_record[3] if len(result_record) > 3 else []
            reference_range = result_record[5] if len(result_record) > 5 else []
            instrument_info = result_record[13] if len(result_record) > 13 else []
            
            formatted_result = {
                "machine_type": self.get_machine_type(),
                "test_code": assay_info[0] if len(assay_info) > 0 else None,
                "test_name": assay_info[1] if len(assay_info) > 1 else None,
                "result_value": result_value[0] if len(result_value) > 0 else None,
                "units": result_record[4] if len(result_record) > 4 else None,
                "reference_range": {
                    "low": reference_range[1] if len(reference_range) > 1 else None,
                    "high": reference_range[0] if len(reference_range) > 0 else None
                },
                "abnormal_flag": result_record[6] if len(result_record) > 6 else None,
                "result_status": result_record[8] if len(result_record) > 8 else None,
                "completed_at": result_record[11] if len(result_record) > 11 else None
            }
        else:
            # Use config-based approach with getattr as originally intended
            formatted_result = {
                "machine_type": self.get_machine_type(),
                "test_code": getattr(record.assay_info, 'assay_number', None),
                "test_name": getattr(record.assay_info, 'assay_name', None),
                "result_value": getattr(record.result_value, 'measurement_value', None),
                "units": getattr(record, 'units', None),
                "reference_range": {
                    "low": getattr(record.reference_range, 'range_low', None),
                    "high": getattr(record.reference_range, 'range_high', None)
                },
                "abnormal_flag": getattr(record, 'abnormal_flag', None),
                "result_status": getattr(record, 'result_status', None),
                "completed_at": getattr(record, 'completed_at', None)
            }
       
        return {k: v for k, v in formatted_result.items() if v is not None}