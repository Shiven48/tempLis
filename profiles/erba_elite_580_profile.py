"""
ERBA Elite 580 Analyzer Profile
"""
from .base_profile import BaseProfile

class ErbaElite580Profile(BaseProfile):
    """Profile for ERBA Elite 580 analyzer"""
    
    def __init__(self, config_path: str = "config.json"):
        self.machine_type = "ERBA_ELITE_580"
        super().__init__(config_path)
    
    def get_machine_type(self) -> str:
        return "ERBA_ELITE_580"
    
    def get_specific_settings(self) -> dict:
        """ERBA Elite 580 specific settings"""
        return {
            "supports_qc": True,
            "max_samples": 580,
            "supported_tests": [
                "GLU", "BUN", "CREA", "ALT", "AST", 
                "TBIL", "DBIL", "TP", "ALB", "CHOL",
                "TG", "HDL", "LDL", "CK", "LDH"
            ],
            "connection_type": "socket"
        }
    
    def validate_sample_id(self, sample_id: str) -> bool:
        """Validate ERBA sample ID format"""
        # ERBA specific validation
        return len(sample_id) <= 25 and sample_id.replace('-', '').isalnum()
    
    def format_result_for_api(self, result_record) -> dict:
        """Format result record for remote API"""
        if not result_record:
            return {}
        
        # Extract key fields based on ERBA configuration
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
            "completed_at": getattr(result_record, 'completed_at', None),
            "instrument_info": getattr(result_record.instrument_info, 'sender_name', None)
        }
        
        return {k: v for k, v in formatted_result.items() if v is not None}