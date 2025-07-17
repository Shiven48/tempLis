from platform import machine
from astm.server import BaseRecordsDispatcher
from message_processor import MessageProcessor
import logging
import json

logger = logging.getLogger(__name__)

class Disp(BaseRecordsDispatcher):
    
    def __init__(self, encoding, machine_type: str = "BS_240", profile=None):
        super(Disp, self).__init__(encoding)
        self.machine_type = machine_type
        self.profile = profile
        self.processor = MessageProcessor(self.profile)
        self.current_session = {
            "header": None,
            "patient": None,
            "order": None,
            "results": []
        } 

    def on_header(self, record):
        logger.info("Header received")
        self.current_session["header"] = record
        print(f"Header from {self.machine_type}:", record)
    
    def on_patient(self, record):
        logger.info("Patient received")
        self.current_session["patient"] = record
        print("Patient received:", record)
    
    def on_order(self, record):
        logger.info("Order received")
        self.current_session["order"] = record
        print("Order received:", record)
    
    def on_result(self, record):
        logger.info("Result received")
        self.current_session["results"].append(record)
        
        # Format result for API
        formatted_result = self.processor.profile.format_result_for_api(record)
        
        # Add context from current session
        if self.current_session["patient"]:
            formatted_result.update({
                "patient_id": getattr(self.current_session["patient"], 'patient_id', None)
            })
        
        if self.current_session["order"]:
            formatted_result.update({
                "sample_id": self._extract_sample_id(self.current_session["order"])
            })
        
        print("Formatted result for API:", json.dumps(formatted_result, indent=2))
        
        # Here you would send to your remote API
        self._send_to_api(formatted_result)
    
    def on_comment(self, record):
        logger.info("Comment received")
        print("Comment received:", record)
    
    def on_terminator(self, record):
        logger.info("Terminator received - session complete")
        print("Session complete. Total results:", len(self.current_session["results"]))
        
        # Reset session
        self.current_session = {
            "header": None,
            "patient": None, 
            "order": None,
            "results": []
        }
    
    def _extract_sample_id(self, order_record):
        """Extract sample ID from order record"""
        try:
            sample_position = getattr(order_record, 'sample_position', None)
            if sample_position:
                return getattr(sample_position, 'sample_id', None)
        except:
            pass
        return None
    
    def _send_to_api(self, formatted_result):
        """Send formatted result to remote API"""
        # Placeholder for API call
        # You would implement your actual API call here
        logger.info(f"Sending to API: {formatted_result}")
        print(f"[API CALL] Would send: {formatted_result}")