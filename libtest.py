"""
Dynamic record building and validation utilities
"""
import logging
import datetime
from astm.mapping import (
    Record, TextField, ConstantField, SetField, DateTimeField, 
    RepeatedComponentField, NotUsedField, IntegerField, DecimalField
)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)

FIELD_TYPE_MAP = {
    "constantField": ConstantField,
    "setField": SetField,
    "textField": TextField,
    "integerField": IntegerField,
    "decimalField": DecimalField,
    "dateTimeField": DateTimeField,
    "repeatedComponentField": RepeatedComponentField,
    "notUsedField": NotUsedField,
}

def build_field_from_config(field_cfg):
    """Build a field from configuration dictionary"""
    field_type = field_cfg.get("type")
    field_class = FIELD_TYPE_MAP.get(field_type)
    
    if not field_class:
        raise ValueError(f"Unknown field type: {field_type}")
    
    name = field_cfg["name"]
    
    if field_type == "constantField":
        return field_class(name=name, default=field_cfg.get("value", field_cfg.get("default")))
    elif field_type == "setField":
        return field_class(name=name, values=field_cfg["values"])
    elif field_type == "textField":
        return field_class(name=name)
    elif field_type == "integerField":
        return field_class(name=name)
    elif field_type == "decimalField":
        return field_class(name=name)
    elif field_type == "dateTimeField":
        return field_class(name=name)
    elif field_type == "notUsedField":
        return field_class(name=name)
    else:
        return field_class(name=name)

def build_record_class_from_config(record_name, fields_config):
    """Build a record class from field configuration"""
    fields = [build_field_from_config(fcfg) for fcfg in fields_config]
    return Record.build(*fields)

def toJson(record):
    """Convert record to JSON-serializable format"""
    if hasattr(record, '_data'):
        return dict(record._data)
    return {}

# Test server functionality
import asyncio
from astm.server import Server
from astm.constants import ENCODING
from dispatcher import Disp

async def main():
    server = Server(
        host='localhost',
        port=15200,
        dispatcher=Disp,
        timeout=1,
        encoding=ENCODING
    )
    await server.serve_forever()

if __name__ == "__main__":
    # Test dynamic record creation
    print("=== Testing Dynamic Record Creation ===")
    
    fields_config = [
        {"name": "record_type_id", "index": 0, "type": "constantField", "value": "H"},
        {"name": "Processing_Id", "index": 1, "type": "setField", "values": ["PR", "QR", "CR"]},
        {"name": "protocol_version", "index": 2, "type": "textField"},
        {"name": "timestamp", "index": 3, "type": "dateTimeField"},
    ]
    
    # Build the record class
    TestHeaderRecord = build_record_class_from_config("TestHeaderRecord", fields_config)
    
    print("--- Testing with valid data ---")
    try:
        record = TestHeaderRecord(
            record_type_id="H",
            Processing_Id="PR",
            protocol_version="1.0",
            timestamp=datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
        )
        print("Record created successfully:", dict(record._data))
    except Exception as e:
        print("Validation error:", e)
    
    # Start server if requested
    # asyncio.run(main())
