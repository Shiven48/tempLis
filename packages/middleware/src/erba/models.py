from dataclasses import dataclass, field
from typing import (
    Dict, 
    Optional, 
    List, 
    Any, 
    Union
)
import warnings
from erba.constants import OBX_RANGE
from erba.enums import (
    TransportMode,
    Protocol
)
from pydantic import (
    BaseModel,
    ConfigDict, 
    Field, 
    field_validator, 
    model_validator
)
import ipaddress

# python dataclasses
@dataclass
class APIResult:
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    status_code: Optional[int] = None
    retry_attempted: bool = False

@dataclass
class ParsingResult:
    message_header: Dict[str, Any] = field(default_factory=dict)
    order_request: Dict[str, Any] = field(default_factory=dict)
    test_results: List[Any] = field(default_factory=list)
    raw_segments: List[str] = field(default_factory=list)
    parsing_errors: List[str] = field(default_factory=list)
    findings: List[Any] = field(default_factory=list)
    error: Optional[str] = None

# pydantic Models for config validation
class TransportConfig(BaseModel):
    mode: TransportMode = Field(default=TransportMode.TCP)
    host: str = Field(default="127.0.0.1", min_length=1)
    port: int = Field(..., ge=1, le=65535)
    
    @field_validator('host')
    @classmethod
    def validate_host(cls, v: str) -> str:
        try:
            ipaddress.ip_address(v)
        except ValueError:
            # Basic hostname validation
            if not v.replace('-', '').replace('.', '').isalnum():
                raise ValueError(f'Invalid hostname format: {v}')
        return v

class ParserConfig(BaseModel):
    """Parser configuration for HL7 segments with flexible field mapping"""
    MSH: Dict[str, Union[int, str]] = Field(default_factory=dict)
    OBR: Optional[Dict[str, Union[int, str]]] = Field(default_factory=dict) 
    OBX: Optional[Dict[str, Union[int, str]]] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")

    @field_validator('OBX')
    @classmethod
    def validate_obx_fields(cls, v):
        """OBX segment cannot have more than 11 fields"""
        if v and len(v) > OBX_RANGE:
            raise ValueError('OBX segment cannot have more than 12 field mappings')
        return v
    
    @field_validator('MSH')
    @classmethod
    def validate_msh_fields(cls, v):
        """MSH segment cannot have more than 18 fields"""
        if v and len(v) > 18:
            raise ValueError('MSH segment cannot have more than 18 field mappings')
        return v
    
    @field_validator('OBR')
    @classmethod
    def validate_obr_fields(cls, v):
        """OBR segment cannot have more than 32 fields"""
        if v and len(v) > 32:
            raise ValueError('OBR segment cannot have more than 32 field mappings')
        return v
    
    
    @field_validator('*')
    @classmethod  
    def validate_field_numbers(cls, v):
        """Ensure field numbers are positive integers"""
        if v:
            for field_name, field_number in v.items():
                if isinstance(field_number, int) and field_number < 1:
                    raise ValueError(f'Field number for {field_name} must be positive, got {field_number}')
                elif isinstance(field_number, int) and field_number > 32:
                    warnings.warn("Segment cannot have more than 32 fields")
        return v
    
    @model_validator(mode='after')
    def validate_required_obx_fields(self):
        """Ensure OBX has minimum required fields for test results"""
        if self.OBX:
            required_obx_fields = {'test_code', 'result_value'}
            obx_fields = set(self.OBX.keys())
            print(f"OBX fields: {obx_fields}")
            missing_fields = required_obx_fields - obx_fields
            if missing_fields:
                warnings.warn(f"OBX missing recommended fields: {missing_fields}")
        return self

class SegmentsConfig(BaseModel):
    """Complete segments configuration with validation"""
    optional: str = Field(..., description="Optional segment range (e.g. '1-6')")
    required: str = Field(..., description="Required segment range (e.g. '7-36')")
    findings: Optional[str] = Field(..., description="Findings (e.g. '37+' or '37-50')")

    @field_validator("optional", "required", "findings", mode="before")
    def validate_range(cls, v):
        if v is None:
            return v
        if not isinstance(v, str):
            raise ValueError("Must be a string like '1-6' or '37+'")
        if not (v.replace("-", "").replace("+", "").isdigit()):
            raise ValueError(f"Invalid format: {v}")
        return v

class AnalyzerConfig(BaseModel):
    """Complete analyzer configuration with validation"""
    device: str = Field(..., min_length=1, max_length=50)
    protocol: Protocol
    transport: TransportConfig
    parser: Optional[ParserConfig] = Field(default_factory=ParserConfig)
    segments: SegmentsConfig = Field(default_factory=SegmentsConfig)
    retry_attempts: Optional[int] = Field(None, ge=0, le=10)
    
    @field_validator('device')
    @classmethod
    def validate_device_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Device name cannot be empty or whitespace")
        return v.strip()
    
    @model_validator(mode='after')
    def validate_config_consistency(self):
        """Cross-field validation"""
        if self.transport.mode == TransportMode.SERIAL and self.transport.host != "127.0.0.1":
            raise ValueError("Serial mode should use localhost/127.0.0.1")
        return self

class ErbaTestResult(BaseModel):
    test_code: str = Field(..., min_length=1)
    test_name: str = Field(..., min_length=1)
    result_value: str
    units: Optional[str] = None
    reference_range: Optional[str] = None
    flags: Optional[str] = None

class ErbaMessage(BaseModel):
    message_id: str = Field(..., min_length=1)
    test_results: List[ErbaTestResult] = Field(..., min_length=1)
    timestamp: str = Field(..., min_length=1)
    analyzer_id: str = Field(..., min_length=1)
    raw_message: List[Any] = Field(default_factory=list)
    findings: Optional[List] = Field(default_factory=list)
    machine: str = Field(min_length=1, default="ERBA")
    model: str = Field(min_length=1, default="ELite 580")