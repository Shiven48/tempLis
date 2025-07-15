from astm.constants import ENCODING, STX, ETX, CR,LF, ETB, REPEAT_SEP, COMPONENT_SEP, RECORD_SEP, CRLF
from config import MAX_FRAME_BODY_SIZE
from utility import setup_logger
import json        
# from ..Records.CommentRecord import ExtendedCommentRecord
# from ..Records.PatientRecord import ExtendedPatientRecord
# from ..Records.ResultRecord import ExtendedResultRecord

log = setup_logger(
    file_path=__file__,
    log_file="logs/core.log",
    separate_levels=True
)

def make_checksum(message: str):
    """Calculates checksum for specified message.

    :param message: ASTM message.
    :type message: bytes

    :returns: Checksum value that is actually byte sized integer in hex base
    :rtype: str
    """
    if not isinstance(message[0], int):
        message = map(ord, message)
    return hex(sum(message) & 0xFF)[2:].upper().zfill(2)

def build_astm_record(message: str) -> bytes:
    """Build proper ASTM message with frame number and checksum"""
    checksum = make_checksum(message + ETX.decode()).encode()
    return STX + message.encode(encoding=ENCODING) + ETX + checksum + CRLF

def build_astm_frames(message: str, chunk_size: int = MAX_FRAME_BODY_SIZE) -> list[bytes]:
    """Break a full ASTM message into correctly framed ASTM protocol-compliant frames"""
    frames = []
    frame_number = 1
    
    for i in range(0, len(message), chunk_size):
        chunk = message[i:i+chunk_size]
        is_last_frame = (i + chunk_size >= len(message))
        
        # Frame structure: STX + frame_number + data + ETX/ETB + checksum + CR + LF
        frame_body = f"{frame_number}{chunk}"
        frame_end = ETX.decode() if is_last_frame else ETB.decode()
        checksum = make_checksum(frame_body + frame_end)
        
        framed = (
            STX +
            frame_body.encode(ENCODING) +
            frame_end.encode() +
            checksum.encode(ENCODING) +
            CR + LF
        )
        frames.append(framed)
        frame_number = 1 if frame_number == 7 else frame_number + 1
    
    return frames

def enhanced_decode(data, encoding=ENCODING):
    """
    Enhanced ASTM decoder that handles:
    1. Single complete messages
    2. Multiple concatenated messages 
    3. Frame sequences that need aggregation
    4. Raw record data
    
    :param data: ASTM data (bytes or list of frame bytes)
    :return: List of decoded records
    """
    if isinstance(data, list):
        return decode_frame_sequence(data, encoding)
    
    if not isinstance(data, bytes):
        raise TypeError('bytes or list expected, got %r' % type(data))
    
    # Count STX occurrences to determine message type
    stx_count = data.count(STX)
    
    if stx_count == 0:
        # No STX - treat as raw record or frame content
        if data[:1].decode().isdigit():
            seq, records = decode_frame(data, encoding)
            return records
        return [decode_record(data, encoding)]
    
    elif stx_count == 1:
        # Single message
        try:
            seq, records, cs = decode_message(data, encoding)
            return records
        except ValueError as valueError:
            raise valueError
    
    else:
        # Multiple messages
        return decode_multiple_messages(data, encoding)

def decode_message(message, encoding):
    """Decode a complete ASTM message."""
    if not isinstance(message, bytes):
        raise TypeError('bytes expected, got %r' % message)

    if not message.startswith(STX):
        raise ValueError('Malformed ASTM message: Must start with STX.')

    # Find ETX or ETB
    frame_end_pos = message.rfind(ETX)
    if frame_end_pos == -1:
        frame_end_pos = message.rfind(ETB)

    if frame_end_pos == -1:
        raise ValueError('Malformed ASTM message: No ETX or ETB found.')

    # Frame content for checksum includes the end character
    frame_for_checksum = message[1:frame_end_pos + 1]
    
    # Extract and verify checksum
    trailer = message[frame_end_pos + 1:]
    cs = trailer.rstrip(CRLF)
    
    if cs:
        ccs = make_checksum(frame_for_checksum).encode()
        if cs != ccs:
            raise ValueError(f'Checksum mismatch: expected {ccs}, but got {cs}')

    # Decode frame content (without ETX/ETB)
    frame_content = frame_for_checksum[:-1]
    seq, records = decode_frame(frame_content, encoding)

    return seq, records, cs.decode(encoding) if cs else None

def decode_frame(frame, encoding):
    """Decode ASTM frame content."""
    if not isinstance(frame, bytes):
        raise TypeError('bytes expected, got %r' % frame)

    # Check for sequence number
    seq_byte = frame[:1]
    if seq_byte.isdigit():
        seq = int(seq_byte.decode('ascii'))
        records_data = frame[1:]
    else:
        seq = None
        records_data = frame

    # Split records by CR and decode each
    return seq, [decode_record(record, encoding)
                 for record in records_data.split(RECORD_SEP) if record]

def decode_record(record, encoding):
    """Decode individual ASTM record."""
    fields = []
    items = record.split(b'|')
    
    for i, item in enumerate(items):
        # Special handling for header delimiters
        if i == 1 and items[0].startswith(b'H') and len(item) in (3, 4):
            delim_chars = "".join([chr(b) for b in item])
            fields.append(delim_chars)
        else:
            if REPEAT_SEP in item:
                item = decode_repeated_component(item, encoding)
            elif COMPONENT_SEP in item:
                item = decode_component(item, encoding)
            else:
                item = item.decode(encoding) if item else None
            fields.append(item if item else None)
    
    return fields



def decode_frame_sequence(frames, encoding=ENCODING):
    """
    Decode a sequence of related frames.
    
    :param frames: List of frame bytes
    :param encoding: Text encoding
    :return: List of decoded records
    """
    # Aggregate frames into single message
    aggregated_message, all_valid = aggregate_frames(frames)
    
    if not all_valid:
        log.warning('Warning: Some frames had checksum errors')
    
    # Decode the aggregated message
    return enhanced_decode(aggregated_message, encoding)

def decode_multiple_messages(data, encoding):
    """Decode multiple concatenated ASTM messages."""
    all_records = []
    messages = split_at_stx(data)
    
    for i, message in enumerate(messages):
        if message:
            try:
                seq, records, cs = decode_message(message, encoding)
                all_records.extend(records)
            except Exception as e:
                log.warning(f"Warning: Failed to decode message {i+1}: {e}")
                continue
    
    return all_records

def split_at_stx(data):
    """Split data at STX boundaries."""
    messages = []
    start = 0
    
    while start < len(data):
        stx_pos = data.find(STX, start)
        if stx_pos == -1:
            break
            
        next_stx = data.find(STX, stx_pos + 1)
        if next_stx == -1:
            message = data[stx_pos:]
        else:
            message = data[stx_pos:next_stx]
        
        if message:
            messages.append(message)
        
        start = next_stx if next_stx != -1 else len(data)
    
    return messages

def decode_component(field, encoding='latin-1'):
    """Decode component-separated field."""
    components = []
    for item in field.split(COMPONENT_SEP):
        if item:
            components.append(item.decode(encoding))
        else:
            components.append(None)
    return components if len(components) > 1 else (components[0] if components else None)

def decode_repeated_component(component, encoding):
    """Decode repeat-separated components."""
    repeats = []
    for item in component.split(REPEAT_SEP):
        if COMPONENT_SEP in item:
            repeats.append(decode_component(item, encoding))
        else:
            repeats.append(item.decode(encoding) if item else None)
    
    return repeats if len(repeats) > 1 else (repeats[0] if repeats else None)

def strip_and_validate_frame(frame_data):
    """
    Strip STX, ETB/ETX, and validate/remove checksum from a single frame.
    
    :param frame_data: Raw frame bytes
    :return: Tuple of (clean_content, is_valid_checksum, is_final_frame)
    """
    if not isinstance(frame_data, bytes):
        raise TypeError('bytes expected, got %r' % frame_data)
    
    if not frame_data.startswith(STX):
        raise ValueError('Frame must start with STX')
    
    # Remove STX
    content = frame_data[1:]
    
    # Find ETX or ETB
    is_final_frame = False
    if content.endswith(CRLF):
        content = content[:-2]  # Remove CRLF
    
    # Check for ETX or ETB and extract checksum
    if ETX in content:
        etx_pos = content.rfind(ETX)
        checksum_part = content[etx_pos + 1:]
        content_for_checksum = content[:etx_pos + 1]  # Include ETX in checksum calc
        content = content[:etx_pos]  # Content without ETX
        is_final_frame = True
    elif ETB in content:
        etb_pos = content.rfind(ETB)
        checksum_part = content[etb_pos + 1:]
        content_for_checksum = content[:etb_pos + 1]  # Include ETB in checksum calc
        content = content[:etb_pos]  # Content without ETB
        is_final_frame = False
    else:
        raise ValueError('Frame must contain ETX or ETB')
    
    # Validate checksum if present
    is_valid_checksum = True
    if checksum_part:
        expected_checksum = make_checksum(content_for_checksum.decode()).encode()
        is_valid_checksum = checksum_part == expected_checksum
        if not is_valid_checksum:
            log.error(f'Checksum mismatch: expected {expected_checksum}, got {checksum_part}')
    
    return content, is_valid_checksum, is_final_frame

def aggregate_frames(frames):
    """
    Aggregate multiple frames into a single ASTM message.
    
    :param frames: List of frame bytes
    :return: Complete ASTM message ready for decode()
    """
    if not frames:
        raise ValueError('No frames provided')
    
    aggregated_content = b''
    all_valid = True
    
    for i, frame in enumerate(frames):
        content, is_valid, is_final = strip_and_validate_frame(frame)
        
        if not is_valid:
            all_valid = False
            log.info(f'Frame {i+1} has invalid checksum')
        
        # Remove sequence number (first character if it's a digit)
        if content and content[:1].isdigit():
            content = content[1:]
        
        aggregated_content += content
        
        # Verify the last frame is marked as final
        if i == len(frames) - 1 and not is_final:
            log.warning('Warning: Last frame should contain ETX, not ETB')
    
    # Create complete ASTM message
    complete_message = STX + b'1' + aggregated_content + ETX
    checksum = make_checksum(b'1' + aggregated_content + ETX).encode()
    final_message = complete_message + checksum + CRLF
    
    return final_message, all_valid

def decode(data, encoding=ENCODING):
    """Common ASTM decoding function that tries to guess which kind of data it
    handles.

    If `data` starts with STX character (``0x02``) than probably it is
    full ASTM message with checksum and other system characters.

    If `data` starts with digit character (``0-9``) than probably it is
    frame of records leading by his sequence number. No checksum is expected
    in this case.

    Otherwise it counts `data` as regular record structure.

    Note, that `data` should be bytes, not unicode string even if you know his
    `encoding`.

    :param data: ASTM data object.
    :type data: bytes

    :param encoding: Data encoding.
    :type encoding: str

    :return: List of ASTM records with unicode data.
    :rtype: list
    """
    if not isinstance(data, bytes):
        raise TypeError('bytes expected, got %r' % data)
    if data.startswith(STX):  # may be decode message \x02...\x03CS\r\n
        seq, records, cs = decode_message(data, encoding)
        return records
    byte = data[:1].decode()
    if byte.isdigit():
        seq, records = decode_frame(data, encoding)
        return records
    return [decode_record(data, encoding)]

# Framing
def build_astm_frames(message: str, chunk_size: int = MAX_FRAME_BODY_SIZE) -> list[bytes]:
    """Break a full ASTM message into correctly framed ASTM protocol-compliant frames"""
    frames = []
    frame_number = 1
    
    for i in range(0, len(message), chunk_size):
        chunk = message[i:i+chunk_size]
        is_last_frame = (i + chunk_size >= len(message))
        
        # Frame structure: STX + frame_number + data + ETX/ETB + checksum + CR + LF
        frame_body = f"{frame_number}{chunk}"
        frame_end = ETX.decode() if is_last_frame else ETB.decode()
        checksum = make_checksum(frame_body + frame_end)
        
        framed = (
            STX +
            frame_body.encode(ENCODING) +
            frame_end.encode() +
            checksum.encode(ENCODING) +
            CR + LF
        )
        frames.append(framed)
        frame_number = 1 if frame_number == 7 else frame_number + 1
    
    return frames

def frame_message_block(records):
    """Frame entire message with STX/ETX and CR line endings"""
    # print(f"Insider records: {records}")
    message_content = '\r'.join(records)
    print(f"message_content: {message_content}")
    return STX + message_content.encode() + ETX + CR + LF

def frame_astm_message(record_groups: list[list[str]]) -> list[bytes]:
    """Join all records from multiple groups into a single ASTM message and frame it."""
    all_records = []
    for group in record_groups:
        all_records.extend(group)
    full_message = '\r'.join(all_records) + '\r'
    return build_astm_frames(full_message)


# Validate the resulting message records(H, P, O, R, C)
def validate_header_fields(decoded_data: list) -> bool:
    """Validate that decoded data has the expected structure for header record"""
    if not decoded_data or len(decoded_data) == 0:
        return False
    
    # Look for header record in the data
    for record in decoded_data:
        if len(record) > 0 and record[0].startswith('H'):
            return True
    
    return False

def validate_comment_fields(decoded_data: list) -> bool:
    """Validate that decoded data has the expected structure for comment record"""
    if not decoded_data or len(decoded_data) == 0:
        return False
    
    # Look for comment record in the data (could be at any position)
    comment_found = False
    for record in decoded_data:
        if len(record) > 0 and record[0].startswith('C'):
            comment_found = True
            break
    
    return comment_found

def validate_patient_fields(decoded_data: list) -> bool:
    """Validate that decoded data has the expected structure for patient record"""
    if not decoded_data or len(decoded_data) == 0:
        return False
    
    # Look for patient record in the data
    for record in decoded_data:
        if len(record) > 0 and record[0].startswith('P'):
            return True
    
    return False

def validate_order_fields(decoded_data: list) -> bool:
    """Validate that decoded data has the expected structure for order record"""
    if not decoded_data or len(decoded_data) == 0:
        return False
    
    # Look for order record in the data
    for record in decoded_data:
        if len(record) > 0 and record[0].startswith('O'):
            return True
    
    return False

def validate_result_fields(decoded_data: list) -> bool:
    """Validate that decoded data has the expected structure for result record"""
    if not decoded_data or len(decoded_data) == 0:
        return False
    
    # Look for result record in the data
    for record in decoded_data:
        if len(record) > 0 and record[0].startswith('R'):
            return True
    
    return False


# return the respective record based on the recordType 
def find_patient_record(decoded_data: list) -> list:
    """Find and return the patient record from decoded data"""
    for record in decoded_data:
        if len(record) > 0 and record[0].startswith('P'):
            return record
        
    return []

def find_order_record(decoded_data: list) -> list:
    """Find and return the order record from decoded data"""
    for record in decoded_data:
        if len(record) > 0 and record[0].startswith('O'):
            return record
    return []

def find_result_record(decoded_data: list) -> list:
    """Find and return the result record from decoded data"""
    for record in decoded_data:
        if len(record) > 0 and record[0].startswith('R'):
            return record
    return []

def find_header_record(decoded_data: list) -> list:
    """Find and return the header record from decoded data"""
    for record in decoded_data:
        if len(record) > 0 and record[0].startswith('H'):
            return record
    return []

def find_comment_record(decoded_data: list) -> list:
    """Find and return the comment record from decoded data"""
    for record in decoded_data:
        if len(record) > 0 and record[0].startswith('C'):
            return record
    return []

# Mapping records to the record object we have defined
def map_header_to_input(inputList: list, headerRecord):
    """Map decoded ASTM data to header record fields with validation"""
    if len(inputList) == 0:
        raise Exception("Input list is empty")
   
    if not validate_header_fields(inputList):
        raise Exception("Invalid header record format")
   
    # Find the header record in the data
    header_data = find_header_record(inputList)
    if not header_data:
        raise Exception("Header record not found in decoded data")
    
    field_names = list(headerRecord._data.keys())    
    
    for i, field_name in enumerate(field_names):
        if i < len(header_data):
            headerRecord._data[field_name] = header_data[i]
        else:
            headerRecord._data[field_name] = ""
    
    return headerRecord

def map_patient_to_input(inputList: list, patientRecord):
    """Map decoded ASTM data to patient record fields with validation"""

    if len(inputList) == 0:
        raise Exception("Input list is empty")
   
    if not validate_patient_fields(inputList):
        raise Exception("Invalid patient record format")
   
    # Find the patient record in the data
    patient_data = find_patient_record(inputList)
    if not patient_data:
        raise Exception("Patient record not found in decoded data")
    
    field_names = list(patientRecord._data.keys())    
    
    for i, field_name in enumerate(field_names):
        if i < len(patient_data):
            patientRecord._data[field_name] = patient_data[i]
        else:
            patientRecord._data[field_name] = ""
    
    return patientRecord

def map_order_to_input(inputList: list, orderRecord):
    """Map decoded ASTM data to order record fields with validation"""
    if len(inputList) == 0:
        raise Exception("Input list is empty")
   
    if not validate_order_fields(inputList):
        raise Exception("Invalid order record format")
   
    # Find the order record in the data
    order_data = find_order_record(inputList)
    if not order_data:
        raise Exception("Order record not found in decoded data")
    
    field_names = list(orderRecord._data.keys())    
    
    for i, field_name in enumerate(field_names):
        if i < len(order_data):
            orderRecord._data[field_name] = order_data[i]
        else:
            orderRecord._data[field_name] = ""
    
    return orderRecord

def map_result_to_input(inputList: list, resultRecord):
    """Map decoded ASTM data to result record fields with validation"""
    if len(inputList) == 0:
        raise Exception("Input list is empty")
   
    if not validate_result_fields(inputList):
        raise Exception("Invalid result record format")
   
    # Find the result record in the data
    result_data = find_result_record(inputList)
    if not result_data:
        raise Exception("Result record not found in decoded data")
    
    field_names = list(resultRecord._data.keys())    
    
    for i, field_name in enumerate(field_names):
        if i < len(result_data):
            resultRecord._data[field_name] = result_data[i]
        else:
            resultRecord._data[field_name] = ""
    
    return resultRecord

def map_comment_to_input(inputList: list, commentRecord):
    """Map decoded ASTM data to comment record fields with validation"""
    if len(inputList) == 0:
        raise Exception("Input list is empty")
   
    if not validate_comment_fields(inputList):
        raise Exception("Invalid comment record format")
   
    # Find the comment record in the data
    comment_data = find_comment_record(inputList)
    if not comment_data:
        raise Exception("Comment record not found in decoded data")
    
    field_names = list(commentRecord._data.keys())    
    
    for i, field_name in enumerate(field_names):
        if i < len(comment_data):
            commentRecord._data[field_name] = comment_data[i]
        else:
            commentRecord._data[field_name] = ""
    
    return commentRecord



# Parsing specific record line
# def parse_astm_patient(analyzer_output: str) -> dict:
#     """Complete function to parse ASTM patient from analyzer output"""
#     try:
#         patient = ExtendedPatientRecord()        
#         byte_astm = buildAstmMessage(message=analyzer_output)     
#         decoded_output_patient = decode(byte_astm)
#         mapped_patient = map_patient_to_input(decoded_output_patient, patient)        
#         patient_json = json.dumps(obj=mapped_patient._data, indent=2)        
        
#         return {
#             'success': True,
#             'data': mapped_patient._data,
#             'json': patient_json
#         }
       
#     except Exception as e:
#         return {
#             'success': False,
#             'error': str(e),
#             'data': None,
#             'json': None
#         }

# def parse_astm_order(analyzer_output: str) -> dict:
#     """Complete function to parse ASTM order from analyzer output"""
#     try:
#         order = ExtendedOrderRecord()        
#         byte_astm = buildAstmMessage(message=analyzer_output)       
#         decoded_output_order = decode(byte_astm)
#         mapped_order = map_order_to_input(decoded_output_order, order)
#         order_json = json.dumps(obj=mapped_order._data, indent=2)        
        
#         return {
#             'success': True,
#             'data': mapped_order._data,
#             'json': order_json
#         }
       
#     except Exception as e:
#         return {
#             'success': False,
#             'error': str(e),
#             'data': None,
#             'json': None
#         }

# def parse_astm_result(analyzer_output: str) -> dict:
#     """Complete function to parse ASTM result from analyzer output"""
#     try:
#         result = ExtendedResultRecord()        
#         byte_astm = buildAstmMessage(message=analyzer_output)    
#         decoded_output_result = decode(byte_astm)
#         mapped_result = map_result_to_input(decoded_output_result, result)      
#         result_json = json.dumps(obj=mapped_result._data, indent=2)        
        
#         return {
#             'success': True,
#             'data': mapped_result._data,
#             'json': result_json
#         }
       
#     except Exception as e:
#         return {
#             'success': False,
#             'error': str(e),
#             'data': None,
#             'json': None
#         }

# def parse_astm_header(analyzer_output: str) -> dict:
#     """Complete function to parse ASTM header from analyzer output"""
#     try:
#         header = ExtraHeaderFields()        
#         byte_astm = buildAstmMessage(message=analyzer_output)   
#         decoded_input_header = decode(byte_astm)
#         mapped_header = map_header_to_input(decoded_input_header, header)        
#         header_json = json.dumps(obj=mapped_header._data, indent=2)        
        
#         return {
#             'success': True,
#             'data': mapped_header._data,
#             'json': header_json
#         }
       
#     except Exception as e:
#         return {
#             'success': False,
#             'error': str(e),
#             'data': None,
#             'json': None
#         }

# def parse_astm_comment(analyzer_output: str) -> dict:
#     """Complete function to parse ASTM comment from analyzer output"""
#     try:
#         comment = ExtendedCommentRecord()        
#         byte_astm = buildAstmMessage(message=analyzer_output)
#         decoded_output_comment = decode(byte_astm)
#         mapped_comment = map_comment_to_input(decoded_output_comment, comment)        
#         comment_json = json.dumps(obj=mapped_comment._data, indent=2)                
#         return {
#             'success': True,
#             'data': mapped_comment._data,
#             'json': comment_json
#         }
        
#     except Exception as e:
#         return {
#             'success': False,
#             'error': str(e),
#             'data': None,
#             'json': None
#         }

# def parse_astm_multi_record(analyzer_output: str) -> dict:
#     """Parse ASTM output that might contain multiple record types"""
#     try:
#         byte_astm = buildAstmMessage(message=analyzer_output)
#         decoded_data = decode(byte_astm)

#         results = {
#             'success': True,
#             'records': {},
#             'errors': [],
#             'record_count': {
#                 'header': 0,
#                 'patient': 0,
#                 'order': 0,
#                 'result': 0,
#                 'comment': 0,
#                 'total': len(decoded_data)
#             }
#         }
        
#         # Parse header if present
#         if validate_header_fields(decoded_data):
#             try:
#                 header = ExtraHeaderFields()
#                 mapped_header = map_header_to_input(decoded_data, header)
#                 results['records']['header'] = {
#                     'data': mapped_header._data,
#                     'json': json.dumps(mapped_header._data, indent=2)
#                 }
#                 results['record_count']['header'] = 1
#             except Exception as e:
#                 results['errors'].append(f"Header parsing error: {str(e)}")
        
#         # Parse patient if present
#         if validate_patient_fields(decoded_data):
#             try:
#                 patient = ExtendedPatientRecord()
#                 mapped_patient = map_patient_to_input(decoded_data, patient)
#                 results['records']['patient'] = {
#                     'data': mapped_patient._data,
#                     'json': json.dumps(mapped_patient._data, indent=2)
#                 }
#                 results['record_count']['patient'] = len(find_all_records_by_type(decoded_data, 'P'))
#             except Exception as e:
#                 results['errors'].append(f"Patient parsing error: {str(e)}")
        
#         # Parse order if present
#         if validate_order_fields(decoded_data):
#             try:
#                 order = ExtendedOrderRecord()
#                 mapped_order = map_order_to_input(decoded_data, order)
#                 results['records']['order'] = {
#                     'data': mapped_order._data,
#                     'json': json.dumps(mapped_order._data, indent=2)
#                 }
#                 results['record_count']['order'] = len(find_all_records_by_type(decoded_data, 'O'))
#             except Exception as e:
#                 results['errors'].append(f"Order parsing error: {str(e)}")
        
#         # Parse result if present
#         if validate_result_fields(decoded_data):
#             try:
#                 result = ExtendedResultRecord()
#                 mapped_result = map_result_to_input(decoded_data, result)
#                 results['records']['result'] = {
#                     'data': mapped_result._data,
#                     'json': json.dumps(mapped_result._data, indent=2)
#                 }
#                 results['record_count']['result'] = len(find_all_records_by_type(decoded_data, 'R'))
#             except Exception as e:
#                 results['errors'].append(f"Result parsing error: {str(e)}")
        
#         # Parse comment if present
#         if validate_comment_fields(decoded_data):
#             try:
#                 comment = ExtendedCommentRecord()
#                 mapped_comment = map_comment_to_input(decoded_data, comment)
#                 results['records']['comment'] = {
#                     'data': mapped_comment._data,
#                     'json': json.dumps(mapped_comment._data, indent=2)
#                 }
#                 results['record_count']['comment'] = len(find_all_records_by_type(decoded_data, 'C'))
#             except Exception as e:
#                 results['errors'].append(f"Comment parsing error: {str(e)}")
        
#         return results
       
#     except Exception as e:
#         return {
#             'success': False,
#             'error': str(e),
#             'records': {},
#             'errors': [],
#             'record_count': {}
#         }

# def parse_astm_complete_transmission(analyzer_output: str) -> dict:
#     """Parse complete ASTM transmission with multiple records of same type"""
#     try:
#         byte_astm = buildAstmMessage(message=analyzer_output)        
#         decoded_data = decode(byte_astm)
        
#         results = {
#             'success': True,
#             'records': {
#                 'headers': [],
#                 'patients': [],
#                 'orders': [],
#                 'results': [],
#                 'comments': []
#             },
#             'errors': [],
#             'summary': {
#                 'total_records': len(decoded_data),
#                 'record_types_found': []
#             }
#         }
        
#         # Process all records
#         for record in decoded_data:
#             if len(record) == 0:
#                 continue
                
#             record_type = record[0][0]  # First character of first field
            
#             try:
#                 if record_type == 'H':
#                     header = ExtraHeaderFields()
#                     # Map this specific record
#                     field_names = list(header._data.keys())
#                     for i, field_name in enumerate(field_names):
#                         if i < len(record):
#                             header._data[field_name] = record[i]
#                         else:
#                             header._data[field_name] = ""
                    
#                     results['records']['headers'].append({
#                         'data': header._data,
#                         'json': json.dumps(header._data, indent=2)
#                     })
                    
#                 elif record_type == 'P':
#                     patient = ExtendedPatientRecord()
#                     field_names = list(patient._data.keys())
#                     for i, field_name in enumerate(field_names):
#                         if i < len(record):
#                             patient._data[field_name] = record[i]
#                         else:
#                             patient._data[field_name] = ""
                    
#                     results['records']['patients'].append({
#                         'data': patient._data,
#                         'json': json.dumps(patient._data, indent=2)
#                     })
                    
#                 elif record_type == 'O':
#                     order = ExtendedOrderRecord()
#                     field_names = list(order._data.keys())
#                     for i, field_name in enumerate(field_names):
#                         if i < len(record):
#                             order._data[field_name] = record[i]
#                         else:
#                             order._data[field_name] = ""
                    
#                     results['records']['orders'].append({
#                         'data': order._data,
#                         'json': json.dumps(order._data, indent=2)
#                     })
                    
#                 elif record_type == 'R':
#                     result_record = ExtendedResultRecord()
#                     field_names = list(result_record._data.keys())
#                     for i, field_name in enumerate(field_names):
#                         if i < len(record):
#                             result_record._data[field_name] = record[i]
#                         else:
#                             result_record._data[field_name] = ""
                    
#                     results['records']['results'].append({
#                         'data': result_record._data,
#                         'json': json.dumps(result_record._data, indent=2)
#                     })
                    
#                 elif record_type == 'C':
#                     comment = ExtendedCommentRecord()
#                     field_names = list(comment._data.keys())
#                     for i, field_name in enumerate(field_names):
#                         if i < len(record):
#                             comment._data[field_name] = record[i]
#                         else:
#                             comment._data[field_name] = ""
                    
#                     results['records']['comments'].append({
#                         'data': comment._data,
#                         'json': json.dumps(comment._data, indent=2)
#                     })
                    
#             except Exception as e:
#                 results['errors'].append(f"Error parsing {record_type} record: {str(e)}")
        
#         # Update summary
#         for record_type, record_list in results['records'].items():
#             if len(record_list) > 0:
#                 results['summary']['record_types_found'].append(f"{record_type}: {len(record_list)}")
        
#         return results
       
#     except Exception as e:
#         return {
#             'success': False,
#             'error': str(e),
#             'records': {},
#             'errors': [],
#             'summary': {}
#         }

# def find_all_records_by_type(decoded_data: list, record_type: str) -> list:
    """Find all records of a specific type from decoded data"""
    matching_records = []
    for record in decoded_data:
        if len(record) > 0 and record[0].startswith(record_type):
            matching_records.append(record)
    return matching_records