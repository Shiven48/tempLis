import logging
import time
from typing import Dict, Optional, Any
from typing import Any, Dict, Optional
from middleware.logger import logger
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
            
            if not test_results_data:
                logging.warning("No test results found in parsed data")
                return None
            
            message_header = parsed_data['message_header']
            machine:str = message_header['machine']
            model:str = message_header['model']

            erba_message:ErbaMessage = ErbaMessage(
                test_results=[ErbaTestResult(**result) for result in parsed_data.get('test_results', [])],
                timestamp=time.strftime('%Y-%m-%d %H:%M:%S'),
                analyzer_id=self.config.device,
                raw_message=parsed_data["raw_segments"],
                findings=parsed_data['findings'],
                machine=machine,
                model=model
            )
            
            logger.info("Message Validated Successfully")
            return erba_message
            
        except ValidationError as e:
            logging.error(f"Validation error: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected validation error: {e}")
            return None