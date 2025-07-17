# ASTM/HL7 Profile-Based Message Processing System

A flexible, profile-based system for processing ASTM and HL7 messages from different laboratory analyzers. The system dynamically configures itself based on machine type and processes messages according to machine-specific protocols.

## Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Analyzer      │───▶│  Profile-Based   │───▶│  Remote API     │
│  (BS240/ERBA)   │    │     Server       │    │   Integration   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ Machine Profiles │
                    │ • BS240Profile   │
                    │ • ErbaProfile    │
                    │ • CustomProfile  │
                    └──────────────────┘
```

## Key Features

- **Profile-Based Configuration**: Each analyzer has its own profile with specific record structures
- **Dynamic Record Building**: Records are built dynamically from JSON configuration
- **Protocol Support**: ASTM and HL7 message processing
- **Connection Flexibility**: Support for both serial and socket connections
- **Validation Layer**: Built-in field validation using ASTM mapping library
- **API Integration**: Formatted output ready for remote API consumption

## Project Structure

```
├── config.json                 # Machine configurations
├── server.py                   # Main server entry point
├── dispatcher.py               # Message dispatcher
├── message_processor.py        # Core message processing logic
├── profile_factory.py          # Profile creation factory
├── profiles/
│   ├── base_profile.py         # Base profile class
│   ├── bs240_profile.py        # BS240 specific profile
│   └── erba_elite_580_profile.py # ERBA Elite 580 profile
├── mapping.py                  # ASTM field mapping library
├── libtest.py                  # Dynamic record building utilities
└── test_system.py              # System tests
```

## Configuration

### Machine Configuration (config.json)

Each machine type has its own configuration section:

```json
{
  "BS_240": {
    "config": {
      "isSerial": "true",
      "COM": "COM2",
      "baudrate": 9600
    },
    "records": {
      "header": {
        "fields": [
          {
            "name": "record_type_id",
            "type": "constantField", 
            "default": "H"
          }
        ]
      }
    }
  }
}
```

### Field Types Supported

- **constantField**: Fixed values (e.g., record type)
- **textField**: String values with optional length limits
- **integerField**: Numeric integer values
- **decimalField**: Decimal/float values
- **setField**: Predefined set of allowed values
- **dateTimeField**: Date/time values with format validation
- **componentField**: Nested component structures
- **repeatedComponentField**: Arrays of components
- **notUsedField**: Placeholder for unused fields

## Usage

### Starting the Server

```python
# Start server for BS240
python server.py

# Or programmatically
from server import ProfileBasedServer
import asyncio

async def main():
    server = ProfileBasedServer("BS_240")
    await server.start_server()

asyncio.run(main())
```

### Processing Messages

```python
from message_processor import MessageProcessor

# Create processor for specific machine
processor = MessageProcessor("BS_240")

# Process ASTM message
astm_message = """H|\\^&|||BS240^1.0^1|||||||P|1|20240716120000
P|1||PAT001||Doe^John^||19900101|M|||123 Main St||||||||||||
R|1|GLU^Glucose^|120|mg/dL|70-110|H||F|||20240716120500|BS240
L|1|N"""

results = processor.process_message(astm_message)
```

### Creating Custom Profiles

```python
from profiles.base_profile import BaseProfile

class CustomAnalyzerProfile(BaseProfile):
    def __init__(self, config_path="config.json"):
        self.machine_type = "CUSTOM_ANALYZER"
        super().__init__(config_path)
    
    def get_machine_type(self):
        return "CUSTOM_ANALYZER"
    
    def format_result_for_api(self, result_record):
        # Custom formatting logic
        return {"custom_field": "value"}

# Register with factory
from profile_factory import ProfileFactory
ProfileFactory.register_profile("CUSTOM_ANALYZER", CustomAnalyzerProfile)
```

## Message Flow

1. **Server Initialization**: Server loads machine profile based on configuration
2. **Connection Setup**: Establishes serial or socket connection per machine config
3. **Message Reception**: Receives raw ASTM/HL7 messages
4. **Message Parsing**: Profile parses message into structured records
5. **Record Validation**: Fields validated against defined constraints
6. **Data Processing**: Records processed and formatted for API
7. **API Integration**: Formatted data sent to remote API

## API Output Format

The system outputs standardized JSON for API consumption:

```json
{
  "machine_type": "BS_240",
  "test_code": "GLU",
  "test_name": "Glucose",
  "result_value": 120,
  "units": "mg/dL",
  "reference_range": {
    "low": 70,
    "high": 110
  },
  "abnormal_flag": "H",
  "result_status": "F",
  "patient_id": "PAT001",
  "patient_name": "John Doe",
  "sample_id": "SAM001",
  "completed_at": "20240716120500"
}
```

## Testing

Run the test suite to verify system functionality:

```bash
python test_system.py
```

This will test:
- Profile creation and configuration
- Dynamic record building
- Message parsing
- Field validation
- API formatting

## Supported Analyzers

- **BS240**: Biochemistry analyzer with full ASTM support
- **ERBA Elite 580**: High-throughput analyzer with socket connection
- **Custom**: Extensible for additional analyzers

## Adding New Analyzers

1. Create profile class inheriting from `BaseProfile`
2. Add machine configuration to `config.json`
3. Register profile with `ProfileFactory`
4. Implement machine-specific validation and formatting

## Dependencies

- `astm` library for ASTM protocol handling
- `asyncio` for asynchronous server operations
- Standard Python libraries (json, logging, datetime, etc.)

## Error Handling

The system includes comprehensive error handling:
- Connection failures
- Message parsing errors
- Field validation errors
- API communication errors

All errors are logged with appropriate detail for debugging.

## Performance Considerations

- Asynchronous message processing
- Efficient field validation
- Minimal memory footprint
- Configurable timeouts
- Connection pooling for high-throughput scenarios