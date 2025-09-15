"""
Pytest configuration and shared fixtures for HL7 middleware testing
"""
from erba.engine import MiddlewareEngine
import pytest
import asyncio
import sys
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

# Add the src directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from erba import (
    DataHandler,
    HL7Parser, 
    ConfigurableHL7Parser,
    ParserConfig, 
    SegmentsConfig, 
    APIResult, 
    ErbaMessage, 
    ParsingResult
)
from erba.processor import MSHProcessor, OBRProcessor, OBXProcessor
from erba.models import AnalyzerConfig
from erba.constants import ERBA_YAML_PATH


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
def mock_analyzer_config():
    """Mock analyzer configuration"""
    return {
        "name": "test_analyzer",
        "model": "ELite 580", 
        "facility": "Erba",
        "version": "2.3.1"
    }


@pytest.fixture
def mock_parser_config():
    """Mock parser configuration matching actual config structure"""
    return ParserConfig(
        MSH={
            "model": "3",
            "machine": "4",            
            "datetime_of_message": "7",
            "message_id": "10"        
        },
        OBR={
            "requested_timing": "6",    
            "reservation_timing": "7"
        },
        OBX={
            "value_type": "2",
            "test_code": "3-0",        
            "test_name": "3-1",         
            "result_value": "5",       
            "units": "6",
            "reference_range": "7",    
            "flags": "8"               
        }
    )


@pytest.fixture
def mock_segments_config():
    """Mock segments configuration"""
    return SegmentsConfig(
        optional=["1-6"],
        required=["7-36"], 
        findings=["37+"]
    )


@pytest.fixture(scope="function")
def engine_instance(event_loop):
    """Create a fresh MiddlewareEngine instance for testing"""
    asyncio.set_event_loop(event_loop)
    
    with patch('erba.engine.get_api_service') as mock_get_api:
        mock_api_service = AsyncMock()
        mock_api_service.send_analyzer_data.return_value = APIResult(success=True, error=None)
        mock_get_api.return_value = mock_api_service
                
        engine = MiddlewareEngine()
        engine.gui_log_callback = None
        engine.gui_error_callback = None
        engine.gui_network_callback = None
        engine.gui_serial_callback = None
        engine.gui_middleware_ack_callback = None
        engine.gui_middleware_nack_callback = None
                        
        yield engine


@pytest.fixture
def api_test_engine_instance(event_loop):
    """Engine instance specifically for API testing - doesn't mock _send_to_api"""
    asyncio.set_event_loop(event_loop)
    
    engine = MiddlewareEngine()
    engine.gui_log_callback = None
    engine.gui_error_callback = None
    
    yield engine

@pytest.fixture
def mock_api_service():
    """Mock API service for testing"""
    return AsyncMock()


@pytest.fixture
def mock_gui_callbacks():
    """Mock GUI callback functions"""
    return {
        "gui_log": Mock(),
        "gui_error": Mock(),
        "gui_network": Mock(),
        "gui_serial": Mock(),
        "gui_middleware_ack": Mock(),
        "gui_middleware_nack": Mock()
    }


@pytest.fixture
def parser_instance():
    """Create HL7Parser instance with test configuration"""
    with patch('configuration.config_loader.ConfigLoader.load_parser_config') as mock_loader:
        mock_config = ParserConfig(
            MSH={"model": "3", "facility": "4", "datetime_of_message": "7"},
            OBR={"sample_id": "3", "requested_timing": "6", "reservation_timing": "7"},
            OBX={"sequence_number": "1", "value_type": "2", "observation_identifier": "3-1"}
        )
        mock_loader.return_value = mock_config
        return HL7Parser(ERBA_YAML_PATH)


@pytest.fixture
def configurable_parser_instance(mock_parser_config):
    """Create ConfigurableHL7Parser instance"""
    return ConfigurableHL7Parser(mock_parser_config)


@pytest.fixture
def data_handler_instance(mock_analyzer_config):
    """Create DataHandler instance"""
    # Create a mock DataHandler instance without calling the constructor
    handler = Mock(spec=DataHandler)
    
    # Set required attributes
    handler.config = mock_analyzer_config
    handler.yaml_path = "test_path.yaml"
    
    # Create mock parser and validator instances
    mock_parser_instance = Mock()
    mock_validator_instance = Mock()
    
    handler.parser = mock_parser_instance
    handler.validator = mock_validator_instance
    
    # Add the process_data method
    handler.process_data = Mock()
    
    return handler


@pytest.fixture
def mock_api_service():
    """Mock API service"""
    mock_api = AsyncMock()
    mock_api.send_analyzer_data.return_value = APIResult(success=True, error=None)
    return mock_api


@pytest.fixture
def sample_hl7_message():
    """Sample valid HL7 message for testing"""
    return """MSH|^~\\&|ELite 580|Erba|||20250828152838||ORU^R01|test123|P|2.3.1||||||UNICODE
PID|1
PV1|1
OBR|1||TEST001|01001^Automated Count^99MRC||20250828010809|20250828010809|||||||20250828010809||||||||||HM||||||||admin
OBX|1|IS|02001^Take Mode^99MRC||A||||||F
OBX|2|IS|02002^Blood Mode^99MRC||W||||||F
OBX|3|IS|02003^Test Mode^99MRC||CBC+DIFF||||||F
OBX|4|NM|30525-0^Age^LN||||||||F
OBX|5|IS|09001^Remark^99MRC||||||||F
OBX|6|IS|03001^Ref Group^99MRC||General||||||F
OBX|7|NM|6690-2^WBC^LN||6.50|10*3/uL|4.00-10.00|~N|||F
OBX|8|NM|770-8^NEU%^LN||83.4|%|50.0-70.0|H~A|||F
OBX|9|NM|736-9^LYM%^LN||13.6|%|20.0-40.0|L~A|||F
OBX|10|NM|5905-5^MON%^LN||2.7|%|3.0-12.0|L~A|||F
OBX|11|NM|713-8^EOS%^LN||0.1|%|0.5-5.0|L~A|||F
OBX|12|NM|706-2^BAS%^LN||0.2|%|0.0-1.0|~N|||F
OBX|13|NM|751-8^NEU#^LN||5.43|10*3/uL|2.00-7.00|~N|||F
OBX|14|NM|731-0^LYM#^LN||0.88|10*3/uL|0.80-4.00|~N|||F
OBX|15|NM|742-7^MON#^LN||0.17|10*3/uL|0.12-1.20|~N|||F
OBX|16|NM|711-2^EOS#^LN||0.01|10*3/uL|0.02-0.50|L~A|||F
OBX|17|NM|704-7^BAS#^LN||0.01|10*3/uL|0.00-0.10|~N|||F
OBX|18|NM|26477-0^*ALY#^LN||0.00|10*3/uL|0.00-0.20|~N|||F
OBX|19|NM|13046-8^*ALY%^LN||0.0|%|0.0-2.0|~N|||F
OBX|20|NM|11001^*LIC#^99MRC||0.00|10*3/uL|0.00-0.20|~N|||F
OBX|21|NM|11002^*LIC%^99MRC||0.0|%|0.0-2.5|~N|||F
OBX|22|NM|789-8^RBC^LN||3.82|10*6/uL|3.50-5.50|~N|||F
OBX|23|NM|718-7^HGB^LN||11.2|g/dL|11.0-16.0|~N|||F
OBX|24|NM|4544-3^HCT^LN||36.7|%|37.0-54.0|L~A|||F
OBX|25|NM|787-2^MCV^LN||96.2|fL|80.0-100.0|~N|||F
OBX|26|NM|785-6^MCH^LN||29.3|pg|27.0-34.0|~N|||F
OBX|27|NM|786-4^MCHC^LN||30.4|g/dL|32.0-36.0|L~A|||F
OBX|28|NM|788-0^RDW-CV^LN||14.4|%|11.0-16.0|~N|||F
OBX|29|NM|21000-5^RDW-SD^LN||49.2|fL|35.0-56.0|~N|||F
OBX|30|NM|777-3^PLT^LN||92|10*3/uL|100-300|L~A|||F
OBX|31|NM|32623-1^MPV^LN||14.2|fL|6.5-12.0|H~A|||F
OBX|32|NM|32207-3^PDW-SD^LN||25.8|fL|9.0-17.0|H~A|||F
OBX|33|NM|11090^PDW-CV^LN||18.9|%|10.0-17.9|H~A|||F
OBX|34|NM|11003^PCT^99MRC||0.130|%|0.108-0.282|~N|||F
OBX|35|NM|48386-7^P-LCR^LN||55.9|%|11.0-45.0|H~A|||F
OBX|36|NM|34167-7^P-LCC^LN||51|10*9/L|30-90|~N|||F"""


# Helper functions for creating test data
def create_mock_erba_message(sample_id: str = "TEST001") -> ErbaMessage:
    """Create a mock ErbaMessage for testing"""
    return ErbaMessage(
        sample_id=sample_id,
        model="ELite 580",
        facility="Erba",
        datetime_of_message="20250828152838",
        requested_timing="20250828010809",
        reservation_timing="20250828010809",
        test_results=[
            {
                "sequence_number": "7",
                "value_type": "NM",
                "observation_identifier": "6690-2^WBC^LN",
                "observation_value": "6.50",
                "units": "10*3/uL",
                "reference_ranges": "4.00-10.00",
                "abnormal_flags": "~N",
                "observation_result_status": "F"
            }
        ],
        findings=["PLT Abnormal Distribution"]
    )


def create_mock_api_result(success: bool = True, error: str = None) -> APIResult:
    """Create a mock API result"""
    return APIResult(success=success, error=error)


def create_mock_parsing_result(
    has_errors: bool = False,
    error_messages: list = None
) -> ParsingResult:
    """Create a mock parsing result"""
    if has_errors and not error_messages:
        error_messages = ["Test parsing error"]
    
    return ParsingResult(
        message_header={
            "model": "ELite 580",
            "facility": "Erba",
            "datetime_of_message": "20250828152838"
        },
        order_request={
            "sample_id": "TEST001",
            "requested_timing": "20250828010809",
            "reservation_timing": "20250828010809"
        },
        test_results=[
            {
                "sequence_number": "7",
                "observation_value": "6.50"
            }
        ],
        findings=["Test finding"],
        raw_segments=["MSH|test", "OBR|test", "OBX|test"],
        parsing_errors=error_messages or [],
        error=error_messages[0] if error_messages else None
    )