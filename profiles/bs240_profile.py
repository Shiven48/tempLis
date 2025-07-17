"""
BS240 Analyzer Profile
"""
from .base_profile import BaseProfile

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
    
    def format_result_for_api(self, result_record) -> dict:
        """Format result record for remote API"""
        if not result_record:
            return {}
        
        # Extract key fields based on BS240 configuration
        formatted_result = {
            "machine_type": self.get_machine_type(),
            "test_code": getattr(result_record.assay_info, 'assay_number', None),
            "test_name": getattr(result_record.assay_info, 'assay_name', None),
            "result_value": getattr(result_record.result_value, 'measurement_value', None),
            "units": getattr(result_record, 'units', None),
            "reference_range": {
                "low": getattr(result_record.reference_range, 'range_low', None),
                "high": getattr(result_record.reference_range, 'range_high', None)
            },
            "abnormal_flag": getattr(result_record, 'abnormal_flag', None),
            "result_status": getattr(result_record, 'result_status', None),
            "completed_at": getattr(result_record, 'completed_at', None)
        }
        
        return {k: v for k, v in formatted_result.items() if v is not None}