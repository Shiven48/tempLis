import logging
import time
from typing import Dict, Optional, Any
from typing import Any, Dict, Optional
from middleware.models import (
    AnalyzerConfig, 
    ErbaMessage, 
    ErbaTestResult, 
)
from pydantic import ValidationError


class DataValidator:
    def __init__(self, config: AnalyzerConfig):
        self.config = config
        
    def validate_and_create_objects(self, parsed_data: Dict[str, Any]) -> Optional[ErbaMessage]:
        """Validate parsed data against Pydantic models"""
        try:
            test_results_data = parsed_data.get('test_results', [])
            print(f"DEBUG: test_results_data = {test_results_data}")
            
            if not test_results_data:
                logging.warning("No test results found in parsed data")
                return None

            erba_message = ErbaMessage(
                # patient_info=ErbaPatientInfo(**parsed_data.get('patient_info', {})),
                test_results=[ErbaTestResult(**result) for result in parsed_data.get('test_results', [])],
                timestamp=time.strftime('%Y-%m-%d %H:%M:%S'),
                analyzer_id=self.config.device,
                raw_message=parsed_data["raw_segments"]
            )
            
            return erba_message
            
        except ValidationError as e:
            logging.error(f"Validation error: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected validation error: {e}")
            return None