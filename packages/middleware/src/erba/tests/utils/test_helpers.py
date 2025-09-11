"""
Test utility functions for HL7 middleware testing
"""
import asyncio
import socket
from typing import List, Dict, Any, Optional
from unittest.mock import Mock, AsyncMock
from hl7 import Message, parse as hl7_parse
from hl7.mllp import HL7StreamReader, HL7StreamWriter

from erba.models import ErbaMessage, APIResult, ParsingResult


def create_mock_hl7_message(message_str: str) -> Message:
    """Create a mock HL7 message from string"""
    try:
        return hl7_parse(message_str.replace('\n', '\r'))
    except Exception as e:
        raise ValueError(f"Failed to create HL7 message: {e}")


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


def create_mock_api_result(success: bool = True, error: Optional[str] = None) -> APIResult:
    """Create a mock API result"""
    return APIResult(success=success, error=error)


def create_mock_parsing_result(
    has_errors: bool = False,
    error_messages: Optional[List[str]] = None
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


class MockHL7StreamReader:
    """Mock HL7 stream reader for testing"""
    
    def __init__(self, messages: List[str]):
        self.messages = [hl7_parse(msg.replace('\n', '\r')) for msg in messages]
        self.current_index = 0
    
    async def readmessage(self) -> Optional[Message]:
        """Read next message from mock stream"""
        if self.current_index >= len(self.messages):
            return None
        
        message = self.messages[self.current_index]
        self.current_index += 1
        return message


class MockHL7StreamWriter:
    """Mock HL7 stream writer for testing"""
    
    def __init__(self):
        self.written_messages = []
        self.is_closed = False
        self.peer_info = ('127.0.0.1', 12345)
    
    def writemessage(self, message: Message):
        """Write message to mock stream"""
        self.written_messages.append(message)
    
    async def drain(self):
        """Mock drain operation"""
        pass
    
    def is_closing(self) -> bool:
        """Check if writer is closing"""
        return self.is_closed
    
    def close(self):
        """Close the writer"""
        self.is_closed = True
    
    async def wait_closed(self):
        """Wait for writer to close"""
        pass
    
    def get_extra_info(self, name: str):
        """Get extra info"""
        if name == 'peername':
            return self.peer_info
        return None


def create_mock_server_callbacks() -> Dict[str, Mock]:
    """Create mock server callback functions"""
    return {
        'gui_log': Mock(),
        'gui_error': Mock(),
        'gui_network': Mock(),
        'gui_serial': Mock(),
        'gui_middleware_ack': Mock(),
        'gui_middleware_nack': Mock()
    }


def assert_message_structure(message: Message, expected_segments: List[str]):
    """Assert that message has expected segment structure"""
    actual_segments = [str(segment[0]) for segment in message]
    for expected in expected_segments:
        assert expected in actual_segments, f"Expected segment {expected} not found in message"


def assert_obx_sequence_range(message: Message, min_seq: int, max_seq: int):
    """Assert OBX sequences are in expected range"""
    obx_segments = message.segments('OBX')
    sequences = [int(str(obx[1])) for obx in obx_segments]
    
    for seq in sequences:
        assert min_seq <= seq <= max_seq, f"OBX sequence {seq} outside expected range {min_seq}-{max_seq}"


def extract_obx_sequences(message: Message) -> List[int]:
    """Extract OBX sequence numbers from message"""
    obx_segments = message.segments('OBX')
    return [int(str(obx[1])) for obx in obx_segments]


def count_segments_by_type(message: Message, segment_type: str) -> int:
    """Count segments of specific type in message"""
    return len(message.segments(segment_type))


def validate_datetime_format(datetime_str: str) -> bool:
    """Validate HL7 datetime format (YYYYMMDDHHMMSS)"""
    if not datetime_str or len(datetime_str) != 14:
        return False
    
    try:
        int(datetime_str)
        return True
    except ValueError:
        return False


def create_test_message_with_sequences(sequences: List[int]) -> str:
    """Create test HL7 message with specific OBX sequences"""
    base_message = """MSH|^~\\&|ELite 580|Erba|||20250828152838||ORU^R01|test123|P|2.3.1||||||UNICODE
PID|1
PV1|1
OBR|1||TEST001|01001^Automated Count^99MRC||20250828010809|20250828010809|||||||20250828010809||||||||||HM||||||||admin"""
    
    obx_lines = []
    for seq in sequences:
        value_type = "NM" if 7 <= seq <= 36 else "IS"
        obx_lines.append(f"OBX|{seq}|{value_type}|TEST^Test^LN||TestValue||||||F")
    
    return base_message + '\n' + '\n'.join(obx_lines)


def simulate_network_error():
    """Simulate a network error for testing"""
    raise ConnectionError("Simulated network error")


def simulate_timeout_error():
    """Simulate a timeout error for testing"""
    raise asyncio.TimeoutError("Simulated timeout error")


async def wait_for_condition(condition_func, timeout: float = 5.0, interval: float = 0.1):
    """Wait for a condition to become true with timeout"""
    start_time = asyncio.get_event_loop().time()
    
    while True:
        if condition_func():
            return True
        
        if asyncio.get_event_loop().time() - start_time > timeout:
            return False
        
        await asyncio.sleep(interval)


def find_available_port() -> int:
    """Find an available port for testing"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


class AsyncContextManager:
    """Helper for async context management in tests"""
    
    def __init__(self, async_func):
        self.async_func = async_func
        self.result = None
    
    async def __aenter__(self):
        self.result = await self.async_func()
        return self.result
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


def create_batch_test_messages(count: int) -> List[str]:
    """Create multiple test messages for batch testing"""
    messages = []
    for i in range(count):
        message = f"""MSH|^~\\&|ELite 580|Erba|||20250828152838||ORU^R01|batch{i}|P|2.3.1||||||UNICODE
PID|1
PV1|1
OBR|1||BATCH{i:03d}|01001^Automated Count^99MRC||20250828010809|20250828010809|||||||20250828010809||||||||||HM||||||||admin
OBX|7|NM|6690-2^WBC^LN||{6.50 + i}|10*3/uL|4.00-10.00|~N|||F
OBX|8|NM|770-8^NEU%^LN||{83.4 + i}|%|50.0-70.0|H~A|||F
OBX|9|NM|736-9^LYM%^LN||{13.6 + i}|%|20.0-40.0|L~A|||F
OBX|10|NM|5905-5^MON%^LN||{2.7 + i}|%|3.0-12.0|L~A|||F
OBX|11|NM|713-8^EOS%^LN||{0.1 + i}|%|0.5-5.0|L~A|||F
OBX|12|NM|706-2^BAS%^LN||{0.2 + i}|%|0.0-1.0|~N|||F
OBX|13|NM|751-8^NEU#^LN||{5.43 + i}|10*3/uL|2.00-7.00|~N|||F
OBX|14|NM|731-0^LYM#^LN||{0.88 + i}|10*3/uL|0.80-4.00|~N|||F
OBX|15|NM|742-7^MON#^LN||{0.17 + i}|10*3/uL|0.12-1.20|~N|||F
OBX|16|NM|711-2^EOS#^LN||{0.01 + i}|10*3/uL|0.02-0.50|L~A|||F
OBX|17|NM|704-7^BAS#^LN||{0.01 + i}|10*3/uL|0.00-0.10|~N|||F
OBX|18|NM|26477-0^*ALY#^LN||{0.00 + i}|10*3/uL|0.00-0.20|~N|||F
OBX|19|NM|13046-8^*ALY%^LN||{0.0 + i}|%|0.0-2.0|~N|||F
OBX|20|NM|11001^*LIC#^99MRC||{0.00 + i}|10*3/uL|0.00-0.20|~N|||F
OBX|21|NM|11002^*LIC%^99MRC||{0.0 + i}|%|0.0-2.5|~N|||F
OBX|22|NM|789-8^RBC^LN||{3.82 + i}|10*6/uL|3.50-5.50|~N|||F
OBX|23|NM|718-7^HGB^LN||{11.2 + i}|g/dL|11.0-16.0|~N|||F
OBX|24|NM|4544-3^HCT^LN||{36.7 + i}|%|37.0-54.0|L~A|||F
OBX|25|NM|787-2^MCV^LN||{96.2 + i}|fL|80.0-100.0|~N|||F
OBX|26|NM|785-6^MCH^LN||{29.3 + i}|pg|27.0-34.0|~N|||F
OBX|27|NM|786-4^MCHC^LN||{30.4 + i}|g/dL|32.0-36.0|L~A|||F
OBX|28|NM|788-0^RDW-CV^LN||{14.4 + i}|%|11.0-16.0|~N|||F
OBX|29|NM|21000-5^RDW-SD^LN||{49.2 + i}|fL|35.0-56.0|~N|||F
OBX|30|NM|777-3^PLT^LN||{92 + i}|10*3/uL|100-300|L~A|||F
OBX|31|NM|32623-1^MPV^LN||{14.2 + i}|fL|6.5-12.0|H~A|||F
OBX|32|NM|32207-3^PDW-SD^LN||{25.8 + i}|fL|9.0-17.0|H~A|||F
OBX|33|NM|11090^PDW-CV^LN||{18.9 + i}|%|10.0-17.9|H~A|||F
OBX|34|NM|11003^PCT^99MRC||{0.130 + i}|%|0.108-0.282|~N|||F
OBX|35|NM|48386-7^P-LCR^LN||{55.9 + i}|%|11.0-45.0|H~A|||F
OBX|36|NM|34167-7^P-LCC^LN||{51 + i}|10*9/L|30-90|~N|||F"""
        messages.append(message)
    
    return messages