from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pydantic import BaseModel

@dataclass
class AnalyzerConfig:
    name: str
    protocol: str
    port: int
    yaml_config_path: str
    pydantic_schemas: Dict[str, Any] = field(default_factory=dict)
    host: Optional[str] = "127.0.0.1"

@dataclass
class ValidationResult:
    """Result of configuration validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    config_data: Optional[Dict[str, Any]] = None

class ErbaPatientInfo(BaseModel):
    patient_id: str
    patient_name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    
class ErbaTestResult(BaseModel):
    test_code: str
    test_name: str
    result_value: str
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    flags: Optional[str] = None
    
class ErbaMessage(BaseModel):
    patient_info: ErbaPatientInfo
    test_results: List[ErbaTestResult]
    timestamp: str
    analyzer_id: str