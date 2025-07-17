"""
Message Processor for handling ASTM/HL7 messages
"""
import logging
from typing import List, Dict, Any, Optional
from profiles.base_profile import BaseProfile
from profile_factory import ProfileFactory

logger = logging.getLogger(__name__)

class MessageProcessor:
    """Process messages based on machine profile"""
    
    def __init__(self, profile):
        self.profile:BaseProfile = profile
        
    def process_message(self, raw_message: str) -> List[Dict[str, Any]]:
        """Process incoming message and return formatted results"""
        try:
            # Parse message using profile
            records = self.profile.parse_message(raw_message)
            
            # Process each record
            processed_results = []
            current_patient = None
            current_order = None
            
            for record in records:
                record_type = self._get_record_type(record)
                
                if record_type == 'header':
                    logger.info(f"Processing header from {self.machine_type}")
                    
                elif record_type == 'patient':
                    current_patient = record
                    logger.info(f"Processing patient: {getattr(record, 'patient_id', 'Unknown')}")
                    
                elif record_type == 'order':
                    current_order = record
                    logger.info(f"Processing order: {getattr(record, 'instrument_id', 'Unknown')}")
                    
                elif record_type == 'result':
                    # Format result for API
                    formatted_result = self.profile.format_result_for_api(record)
                    
                    # Add patient and order context
                    if current_patient:
                        formatted_result.update({
                            "patient_id": getattr(current_patient, 'patient_id', None),
                            "patient_name": self._extract_patient_name(current_patient),
                            "patient_sex": getattr(current_patient, 'patient_sex', None),
                            "patient_age": self._extract_patient_age(current_patient)
                        })
                    
                    if current_order:
                        formatted_result.update({
                            "sample_id": self._extract_sample_id(current_order),
                            "specimen_type": getattr(current_order, 'specimen_type', None),
                            "priority": getattr(current_order, 'priority', None)
                        })
                    
                    processed_results.append(formatted_result)
                    
                elif record_type == 'comment':
                    logger.info(f"Processing comment: {getattr(record, 'comment_text', '')}")
                    
                elif record_type == 'terminator':
                    logger.info("Processing terminator record")
            
            return processed_results
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise
    
    def _get_record_type(self, record) -> str:
        """Determine record type from record instance"""
        record_type_id = getattr(record, 'record_type_id', '')
        
        type_map = {
            'H': 'header',
            'P': 'patient',
            'O': 'order', 
            'R': 'result',
            'C': 'comment',
            'L': 'terminator'
        }
        
        return type_map.get(record_type_id, 'unknown')
    
    def _extract_patient_name(self, patient_record) -> Optional[str]:
        """Extract patient name from patient record"""
        try:
            patient_name = getattr(patient_record, 'patient_name', None)
            if patient_name:
                last_name = getattr(patient_name, 'last_name', '')
                first_name = getattr(patient_name, 'first_name', '')
                return f"{first_name} {last_name}".strip()
        except:
            pass
        return None
    
    def _extract_patient_age(self, patient_record) -> Optional[Dict[str, Any]]:
        """Extract patient age information"""
        try:
            age_info = getattr(patient_record, 'age_info', None)
            if age_info:
                return {
                    "age": getattr(age_info, 'age', None),
                    "age_unit": getattr(age_info, 'age_unit', None),
                    "birth_date": getattr(age_info, 'birth_date', None)
                }
        except:
            pass
        return None
    
    def _extract_sample_id(self, order_record) -> Optional[str]:
        """Extract sample ID from order record"""
        try:
            sample_position = getattr(order_record, 'sample_position', None)
            if sample_position:
                return getattr(sample_position, 'sample_id', None)
        except:
            pass
        return None
    
    def validate_message(self, raw_message: str) -> bool:
        """Validate message format"""
        try:
            records = self.profile.parse_message(raw_message)
            return len(records) > 0
        except Exception as e:
            logger.error(f"Message validation failed: {e}")
            return False
    
    def get_connection_config(self) -> Dict[str, Any]:
        """Get connection configuration for this machine"""
        return self.profile.get_connection_config()
    
    def get_protocol_type(self) -> str:
        """Get protocol type (ASTM/HL7)"""
        return self.profile.get_protocol_type()