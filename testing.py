# Dynamic record class building and validation test
from Analyzers.Bs240.Astm.Records.HeaderRecord import ConstantField, SetField, TextField, DateTimeField, NotUsedField
from Analyzers.Bs240.Astm.Records.HeaderRecord import Record
import datetime

FIELD_TYPE_MAP = {
    "constantField": ConstantField,
    "setField": SetField,
    "textField": TextField,
    "dateTimeField": DateTimeField,
    "notUsedField": NotUsedField,
}

def build_field_from_config(field_cfg):
    field_type = field_cfg.get("type")
    field_class = FIELD_TYPE_MAP[field_type]
    name = field_cfg["name"]

    if field_type == "constantField":
        return field_class(name=name, default=field_cfg["value"])
    elif field_type == "setField":
        return field_class(name=name, values=field_cfg["values"])
    elif field_type == "textField":
        return field_class(name=name)
    elif field_type == "dateTimeField":
        return field_class(name=name)
    elif field_type == "notUsedField":
        return field_class(name=name)
    elif field_type == "componentField":
        component_info = field_cfg["component"]
        if isinstance(component_info, str):
            component_class = COMPONENT_CLASS_MAP[component_info]
        return ComponentField(component_class, name=field_cfg["name"])
    else:
        raise ValueError(f"Unknown field type: {field_type}")

def build_record_class_from_config(record_name, fields_config):
    fields = [build_field_from_config(fcfg) for fcfg in fields_config]
    return Record.build(*fields)

def toJson(record):
    pass

if __name__ == "__main__":
    # Sample config for testing
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