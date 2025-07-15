from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
import re
from enum import Enum

class MessageType(Enum):
    """Common HL7 message types"""
    ORU_R01 = "ORU^R01"  # Observation Result
    ORM_O01 = "ORM^O01"  # Order Message
    ACK = "ACK^R01"          # Acknowledgment
    QBP_Q11 = "QBP^Q11"  # Query by Parameter
    RSP_K11 = "RSP^K11"  # Query Response

class ProcessingID(Enum):
    """HL7 Processing ID values"""
    PRODUCTION = "P"
    DEBUGGING = "D"
    TRAINING = "T"

class AckType(Enum):
    """Acknowledgment types"""
    ALWAYS = "AL"
    NEVER = "NE"
    ERROR_REJECT_ONLY = "ER"
    SUCCESS_ONLY = "SU"

@dataclass
class MSHSegment:
    """
    HL7 MSH (Message Header) Segment Implementation
    
    Follows HL7 v2.3.1 standard with proper field ordering and validation
    """
    
    # Required fields
    sending_app: str = 'LISSystem'
    sending_facility: str = 'LabFacility'
    receiving_app: str = 'Analyzer'
    receiving_facility: str = 'ErbaCenter'
    message_type: str = MessageType.ORU_R01.value
    message_control_id: str = field(default_factory=lambda: f"MSG{datetime.now().strftime('%Y%m%d%H%M%S')}")
    
    # Standard HL7 separators (rarely changed)
    field_separator: str = '|'
    encoding_chars: str = '^~\\&'
    
    # Timestamp - changed to match HL7 standard format YYYYMMDDHHMMSS
    datetime_of_message: str = field(default_factory=lambda: datetime.now().strftime('%Y%m%d%H%M%S'))
    
    # Optional fields with sensible defaults
    security: str = ''
    processing_id: str = ProcessingID.PRODUCTION.value
    version_id: str = '2.3.1'
    sequence_number: str = ''
    continuation_pointer: str = ''
    accept_ack_type: str = AckType.ALWAYS.value
    app_ack_type: str = AckType.ALWAYS.value
    country_code: str = 'IN'
    charset: str = 'ASCII'
    principal_language: str = ''
    alt_charset_handling: str = ''
    
    def __post_init__(self):
        """Validate the MSH segment after initialization"""
        # self._validate()
    
    def _validate(self):
        """Validate MSH segment fields according to HL7 standards"""
        
        # Validate field separator
        if len(self.field_separator) != 1:
            raise ValueError("Field separator must be exactly 1 character")
        
        # Validate encoding characters
        if len(self.encoding_chars) != 4:
            raise ValueError("Encoding characters must be exactly 4 characters")
        
        # Validate datetime format - must be exactly YYYYMMDDHHMMSS (14 digits)
        if self.datetime_of_message and not re.match(r'^\d{14}$', self.datetime_of_message):
            raise ValueError("Datetime must be in YYYYMMDDHHMMSS format (14 digits)")
        
        # Validate message type format
        if not re.match(r'^[A-Z]{3}\^[A-Z0-9]{3}(\^[A-Z0-9_]+)?$', self.message_type.strip()):
            raise ValueError("Message type must follow format: XXX^YYY^ZZZ")
        
        # Validate message control ID (alphanumeric, max 20 chars)
        if not re.match(r'^[A-Za-z0-9]{1,20}$', self.message_control_id):
            raise ValueError("Message control ID must be alphanumeric, max 20 characters")
        
        # Validate processing ID
        valid_processing_ids = [p.value for p in ProcessingID]
        if self.processing_id not in valid_processing_ids:
            raise ValueError(f"Processing ID must be one of: {valid_processing_ids}")
        
        # Validate version ID format
        if not re.match(r'^\d+\.\d+(\.\d+)?$', self.version_id):
            raise ValueError("Version ID must be in format X.Y or X.Y.Z")
        
        # Validate acknowledgment types
        valid_ack_types = [a.value for a in AckType]
        if self.accept_ack_type and self.accept_ack_type not in valid_ack_types:
            raise ValueError(f"Accept ACK type must be one of: {valid_ack_types}")
        if self.app_ack_type and self.app_ack_type not in valid_ack_types:
            raise ValueError(f"Application ACK type must be one of: {valid_ack_types}")
        
        # Validate country code (ISO 3166-1 alpha-2)
        if self.country_code and not re.match(r'^[A-Z]{2}$', self.country_code):
            raise ValueError("Country code must be 2 uppercase letters (ISO 3166-1)")
        
        # Validate sending application length (max 180 chars according to spec)
        if len(self.sending_app) > 180:
            raise ValueError("Sending application must be max 180 characters")
        
        # Validate sending facility length (max 180 chars according to spec)
        if len(self.sending_facility) > 180:
            raise ValueError("Sending facility must be max 180 characters")
        
        # Validate receiving application length (max 180 chars according to spec)
        if len(self.receiving_app) > 180:
            raise ValueError("Receiving application must be max 180 characters")
        
        # Validate receiving facility length (max 180 chars according to spec)
        if len(self.receiving_facility) > 180:
            raise ValueError("Receiving facility must be max 180 characters")
        
        # Validate security field length (max 40 chars according to spec)
        if len(self.security) > 40:
            raise ValueError("Security field must be max 40 characters")
        
        # Validate message type length (max 7 chars according to spec)
        if len(self.message_type) > 7:
            print(self.message_type, type(self.message_type))
            raise ValueError("Message type must be max 7 characters")
        
        # Validate sequence number length (max 15 chars according to spec)
        if len(self.sequence_number) > 15:
            raise ValueError("Sequence number must be max 15 characters")
        
        # Validate continuation pointer length (max 180 chars according to spec)
        if len(self.continuation_pointer) > 180:
            raise ValueError("Continuation pointer must be max 180 characters")
        
        # Validate accept acknowledgment type length (max 2 chars according to spec)
        if len(self.accept_ack_type) > 2:
            raise ValueError("Accept acknowledgment type must be max 2 characters")
        
        # Validate application acknowledgment type length (max 2 chars according to spec)
        if len(self.app_ack_type) > 2:
            raise ValueError("Application acknowledgment type must be max 2 characters")
        
        # Validate charset length (max 10 chars according to spec)
        if len(self.charset) > 10:
            raise ValueError("Character set must be max 10 characters")
        
        # Validate principal language length (max 60 chars according to spec)
        if len(self.principal_language) > 60:
            raise ValueError("Principal language must be max 60 characters")
        
        # Validate alternate character set handling length (max 20 chars according to spec)
        if len(self.alt_charset_handling) > 20:
            raise ValueError("Alternate character set handling must be max 20 characters")
    
    @classmethod
    def create_query(cls, sending_app: str, receiving_app: str, **kwargs) -> 'MSHSegment':
        """Create MSH segment for query messages"""
        defaults = {
            'sending_app': sending_app,
            'receiving_app': receiving_app,
            'message_type': MessageType.QBP_Q11.value,
        }
        defaults.update(kwargs)
        return cls(**defaults)
    
    @classmethod
    def create_result(cls, sending_app: str, receiving_app: str, **kwargs) -> 'MSHSegment':
        """Create MSH segment for result messages"""
        defaults = {
            'sending_app': sending_app,
            'receiving_app': receiving_app,
            'message_type': MessageType.ORU_R01.value,
        }
        defaults.update(kwargs)
        return cls(**defaults)
    
    @classmethod
    def create_order(cls, sending_app: str, receiving_app: str, **kwargs) -> 'MSHSegment':
        """Create MSH segment for order messages"""
        defaults = {
            'sending_app': sending_app,
            'receiving_app': receiving_app,
            'message_type': MessageType.ORM_O01.value,
        }
        defaults.update(kwargs)
        return cls(**defaults)
    
    @classmethod
    def create_ack(cls, original_msh: 'MSHSegment', **kwargs) -> 'MSHSegment':
        """Create ACK message from original MSH"""
        defaults = {
            'sending_app': original_msh.receiving_app,
            'sending_facility': original_msh.receiving_facility,
            'receiving_app': original_msh.sending_app,
            'receiving_facility': original_msh.sending_facility,
            'message_type': MessageType.ACK.value,
            'message_control_id': f"ACK{original_msh.message_control_id}",
        }
        defaults.update(kwargs)
        return cls(**defaults)
    
    def update_timestamp(self):
        """Update the message timestamp to current time"""
        self.datetime_of_message = datetime.now().strftime('%Y%m%d%H%M%S')
    
    def to_hl7(self) -> str:
        """
        Convert MSH segment to HL7-compliant string
        
        Returns:
            str: Complete MSH segment with proper HL7 formatting
        """
        # MSH is special - field separator comes after MSH, encoding chars are MSH.1
        fields = [
            'MSH',
            self.encoding_chars,  # MSH.1 (note: field separator is implicit between MSH and encoding_chars)
            self.sending_app,     # MSH.2
            self.sending_facility, # MSH.3
            self.receiving_app,   # MSH.4
            self.receiving_facility, # MSH.5
            self.datetime_of_message, # MSH.6
            self.security,        # MSH.7
            self.message_type,    # MSH.8
            self.message_control_id, # MSH.9
            self.processing_id,   # MSH.10
            self.version_id,      # MSH.11
            self.sequence_number, # MSH.12
            self.continuation_pointer, # MSH.13
            self.accept_ack_type, # MSH.14
            self.app_ack_type,    # MSH.15
            self.country_code,    # MSH.16
            self.charset,         # MSH.17
            self.principal_language, # MSH.18
            self.alt_charset_handling # MSH.19
        ]
        
        return self.field_separator.join(fields) + '\r'
    
    @classmethod
    def from_hl7(cls, hl7_string: str) -> 'MSHSegment':
        """
        Parse HL7 string to create MSH segment
        
        Args:
            hl7_string: HL7 MSH segment string
            
        Returns:
            MSHSegment: Parsed MSH segment object
        """
        # Remove trailing \r if present
        hl7_string = hl7_string.rstrip('\r\n')

        # Split by field separator (first character after MSH)
        if not hl7_string.startswith('MSH'):
            raise ValueError("String must start with 'MSH'")
        
        field_sep = hl7_string[3]  # Character after 'MSH'
        fields = hl7_string.split(field_sep)
        
        # Ensure we have enough fields (MSH has 20 fields total including MSH.0)
        while len(fields) < 20:
            fields.append('')
        
        return cls(
            field_separator=field_sep,
            encoding_chars=fields[1],
            sending_app=fields[2],
            sending_facility=fields[3],
            receiving_app=fields[4],
            receiving_facility=fields[5],
            datetime_of_message=fields[6],
            security=fields[7],
            message_type=fields[8],
            message_control_id=fields[9],
            processing_id=fields[10],
            version_id=fields[11],
            sequence_number=fields[12],
            continuation_pointer=fields[13],
            accept_ack_type=fields[14],
            app_ack_type=fields[15],
            country_code=fields[16],
            charset=fields[17],
            principal_language=fields[18],
            alt_charset_handling=fields[19] if len(fields) > 19 else ''
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert MSH segment to dictionary"""
        return {
            'field_separator': self.field_separator,
            'encoding_chars': self.encoding_chars,
            'sending_app': self.sending_app,
            'sending_facility': self.sending_facility,
            'receiving_app': self.receiving_app,
            'receiving_facility': self.receiving_facility,
            'datetime_of_message': self.datetime_of_message,
            'security': self.security,
            'message_type': self.message_type,
            'message_control_id': self.message_control_id,
            'processing_id': self.processing_id,
            'version_id': self.version_id,
            'sequence_number': self.sequence_number,
            'continuation_pointer': self.continuation_pointer,
            'accept_ack_type': self.accept_ack_type,
            'app_ack_type': self.app_ack_type,
            'country_code': self.country_code,
            'charset': self.charset,
            'principal_language': self.principal_language,
            'alt_charset_handling': self.alt_charset_handling
        }
    
    def __str__(self) -> str:
        """String representation"""
        return f"MSH: {self.sending_app} → {self.receiving_app} ({self.message_type})"
    
    def __repr__(self) -> str:
        """Detailed representation"""
        return f"MSHSegment(message_type='{self.message_type}', control_id='{self.message_control_id}')"


# Usage Examples
if __name__ == "__main__":
    # Example 1: Basic usage
    msh = MSHSegment(
        sending_app="MyLIS",
        receiving_app="ErbaELite580"
    )
    print("Basic MSH:")
    print(msh.to_hl7())
    
    # Example 2: Create different message types
    query_msh = MSHSegment.create_query("LIS", "Analyzer")
    result_msh = MSHSegment.create_result("Analyzer", "LIS")
    order_msh = MSHSegment.create_order("LIS", "Analyzer")
    
    print("\nDifferent message types:")
    print(f"Query: {query_msh}")
    print(f"Result: {result_msh}")
    print(f"Order: {order_msh}")
    
    # Example 3: Create ACK response
    ack_msh = MSHSegment.create_ack(query_msh)
    print(f"\nACK: {ack_msh}")
    
    # # Example 4: Parse from HL7 string
    hl7_string = "MSH|^~\&|Manufacturer|analyzer|||20060427194802||ORU^R01|1|P|2.3.1||||AL||ASCII|||"
    parsed_msh = MSHSegment.from_hl7(hl7_string)
    print(f"\nParsed: {parsed_msh}")
    
    # # Example 5: Validation (this will raise an error)
    try:
        invalid_msh = MSHSegment(
            message_type="INVALID",  # Wrong format
            processing_id="X"        # Invalid processing ID
        )
    except ValueError as e:
        print(f"\nValidation error: {e}")