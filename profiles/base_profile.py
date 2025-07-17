"""
Base profile class for machine configurations
"""
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from astm.mapping import *

logger = logging.getLogger(__name__)

class BaseProfile(ABC):
    """Base class for machine profiles"""
    
    def __init__(self, machine_type:str, config_path: Optional[str] = None):
        self.machine_type = machine_type
        self.protocol_type = "astm"
        self.connection_config = {}
        self.record_classes = {}
        
        if config_path:
            self.load_config(config_path)
    
    def load_config(self, config_path: str):
        """Load configuration from JSON file"""
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        logger.info('Config loaded Successfully!!')
        machine_config = config.get(self.machine_type, {})
        self.connection_config = machine_config.get('config', {})
        self.protocol_type = machine_config.get('protocol', 'astm')
        
        # Build record classes from config
        records_config = machine_config.get('records', {})
        for record_type, record_config in records_config.items():
            self.record_classes[record_type] = self._build_record_class(
                record_type, record_config.get('fields', [])
            )
            logger.info(f"{record_type} record type built successfully")
    
    def _build_record_class(self, record_name: str, fields_config: list):
        """Build a record class from field configuration"""
        fields = []
        components = {}
        
        for field_cfg in fields_config:
            field = self._build_field_from_config(field_cfg, components)
            if field:
                fields.append(field)
        
        return Record.build(*fields)

    def _build_field_from_config(self, field_cfg: dict, components: dict):
        """Build a field from configuration"""
        field_type = field_cfg.get("type")
        name = field_cfg["name"]
        
        field_map = {
            "constantField": lambda: ConstantField(
                name=name, 
                default=field_cfg.get("default", field_cfg.get("value"))
            ),
            "setField": lambda: SetField(
                name=name, 
                values=field_cfg.get("values", []),
                length=field_cfg.get("length")
            ),
            "textField": lambda: TextField(
                name=name,
                length=field_cfg.get("length")
            ),
            "integerField": lambda: IntegerField(
                name=name,
                length=field_cfg.get("length")
            ),
            "decimalField": lambda: DecimalField(
                name=name,
                length=field_cfg.get("length")
            ),
            "dateTimeField": lambda: DateTimeField(
                name=name
            ),
            "notUsedField": lambda: NotUsedField(name=name),
            "componentField": lambda: self._build_component_field(field_cfg, components),
            "repeatedComponentField": lambda: self._build_repeated_component_field(field_cfg, components)
        }
        
        builder = field_map.get(field_type)
        return builder() if builder else None
    
    def _build_component_field(self, field_cfg: dict, components: dict):
        """Build a component field"""
        component_info = field_cfg.get("component", {})
        component_name = component_info.get("name", f"{field_cfg['name']}_component")
        
        # Build component class if not exists
        if component_name not in components:
            component_fields = []
            for comp_field_cfg in component_info.get("fields", []):
                comp_field = self._build_field_from_config(comp_field_cfg, components)
                if comp_field:
                    component_fields.append(comp_field)
            
            components[component_name] = Component.build(*component_fields)
        
        return ComponentField(components[component_name], name=field_cfg["name"])
    
    def _build_repeated_component_field(self, field_cfg: dict, components: dict):
        """Build a repeated component field"""
        component_info = field_cfg.get("component", {})
        component_name = f"{field_cfg['name']}_repeated_component"
        
        # Build component class
        component_fields = []
        for comp_field_cfg in component_info.get("fields", []):
            comp_field = self._build_field_from_config(comp_field_cfg, components)
            if comp_field:
                component_fields.append(comp_field)
        
        component_class = Component.build(*component_fields)
        return RepeatedComponentField(component_class, name=field_cfg["name"])
    
    @abstractmethod
    def get_machine_type(self) -> str:
        """Return the machine type identifier"""
        pass
    
    def get_protocol_type(self) -> str:
        """Return the protocol type (astm/hl7)"""
        return self.protocol_type
    
    def get_connection_config(self) -> Dict[str, Any]:
        """Return connection configuration"""
        return self.connection_config
    
    def get_record_class(self, record_type: str):
        """Get record class for specific record type"""
        return self.record_classes.get(record_type)
    
    def parse_message(self, message: str):
        """Parse incoming message based on protocol"""
        if self.protocol_type.lower() == "astm":
            return self._parse_astm_message(message)
        elif self.protocol_type.lower() == "hl7":
            return self._parse_hl7_message(message)
        else:
            raise ValueError(f"Unsupported protocol: {self.protocol_type}")
    
    def _parse_astm_message(self, message: str):
        """Parse ASTM message"""
        # Basic ASTM parsing logic
        records = []
        lines = message.strip().split('\n')
        
        for line in lines:
            if not line:
                continue
                
            record_type = line[0].upper()
            record_map = {
                'H': 'header',
                'P': 'patient', 
                'O': 'order',
                'R': 'result',
                'C': 'comment',
                'L': 'terminator'
            }
            
            record_name = record_map.get(record_type)
            if record_name and record_name in self.record_classes:
                # Parse the line into fields
                fields = line.split('|')
                record_class = self.record_classes[record_name]
                
                # Create record instance with parsed data
                # This is a simplified parsing - you'd need more sophisticated logic
                record_data = self._parse_record_fields(fields, record_class)
                records.append(record_class(**record_data))
        
        return records
    
    def _parse_hl7_message(self, message: str):
        """Parse HL7 message - implement based on your HL7 requirements"""
        # Placeholder for HL7 parsing
        raise NotImplementedError("HL7 parsing not implemented yet")
    
    def _parse_record_fields(self, fields: list, record_class) -> dict:
        """Parse record fields based on record class definition"""
        record_data = {}
        
        # This is a simplified field mapping
        # You'd need more sophisticated logic based on your field definitions
        for i, (field_name, field_obj) in enumerate(record_class._fields):
            if i < len(fields) and fields[i]:
                try:
                    # Set the field value, letting the field handle validation
                    record_data[field_name] = fields[i]
                except (ValueError, TypeError) as e:
                    print(f"Error parsing field {field_name}: {e}")
        
        return record_data