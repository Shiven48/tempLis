import re
import requests
from erba.constants import CONTROL_CHAR_TO_BYTE, control_map


def parse_input_with_control_chars(self, input_str: str) -> bytes:
        """Converts human-friendly input like "[STX]data[ETX]" into proper ASTM bytes."""
        result = bytearray()
    
        # Replace known escape sequences manually
        input_str = input_str.replace('\\r', '\r').replace('\\n', '\n')
        
        # Find all parts like [STX], data, [ETX]
        tokens = re.split(r'(\[[A-Z]+\])', input_str)
    
        for token in tokens:
            match = re.match(r'\[([A-Z]+)\]', token)
            if match:
                ctrl = match.group(1)
                if ctrl in CONTROL_CHAR_TO_BYTE:
                    result.extend(CONTROL_CHAR_TO_BYTE[ctrl])
            else:
                result.extend(token.encode('latin-1'))
        
        return bytes(result)
    
def pretty_logger(self, bdata: bytes):
    """Format bytes data for pretty logging"""
    output_lines = []
    buffer = []
    in_astm_block = False
    for b in bdata:
        if b in control_map:
            label = control_map[b]
            if label == 'STX':
                # Start capturing ASTM block
                in_astm_block = True
                buffer.append(f"[{label}]")
            elif label == 'ETX':
                buffer.append(f"[{label}]")
                in_astm_block = False
            else:
                # Flush current ASTM block if exists
                if buffer:
                    output_lines.append(''.join(buffer))
                    buffer = []
                output_lines.append(f" - [{label}]")
        elif b == 13:  # \r (CR)
            buffer.append("[CR]")
        elif b == 10:  # \n (LF)
            buffer.append("[LF]")
        else:
            try:
                buffer.append(chr(b))
            except:
                buffer.append(f"[0x{b:02X}]")  # fallback for unknown byte
    if buffer:
        output_lines.append(''.join(buffer))
    return "\n".join(output_lines)

def buffer_to_lines(self, buffer):
    """Convert buffer to readable lines"""
    try:
        return bytes(buffer).decode('latin-1', errors='ignore').replace('\r', '')
    except Exception:
        return repr(buffer)

def send_api_request(self, endpoint, payload):
    """
    Common method to send API requests
    Returns tuple (success: bool, response_data: dict or None, error_message: str or None)
    """
    try:
        self.log_event(f"Sending {payload.get('total_messages', 0)} messages to {endpoint}")
        
        # Send POST request
        response = requests.post(
            endpoint,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            self.log_event(f"Successfully sent data to API. Response: {response.status_code}")
            
            try:
                response_data = response.json()
                return True, response_data, None
            except:
                return True, {'status': response.status_code}, None
                
        else:
            error_msg = f"API request failed with status {response.status_code}: {response.text}"
            self.log_event(error_msg)
            return False, None, f"Failed to send data. Status: {response.status_code}"
            
    except requests.exceptions.Timeout:
        error_msg = "API request timed out"
        self.log_event(error_msg)
        return False, None, "Request timed out. Please check the endpoint URL and try again."
    except requests.exceptions.ConnectionError:
        error_msg = "Failed to connect to API endpoint"
        self.log_event(error_msg)
        return False, None, "Failed to connect to API endpoint. Please check the URL and network connection."
    except Exception as e:
        error_msg = f"Error sending data to API: {str(e)}"
        self.log_event(error_msg)
        return False, None, f"Failed to send data to API: {str(e)}"
