import logging
import time
from typing import List, Optional, Any
from typing import Any, Optional
from pydantic import ValidationError

from constants import cbc_parameters
from middleware.logger import logger
from middleware.models import (
    AnalyzerConfig, 
    ErbaMessage, 
    ErbaTestResult,
    ParsingResult, 
)


class DataValidator:
    def __init__(self, config: AnalyzerConfig):
        self.config = config
        
    def validate_and_create_objects(self, parsed_data: ParsingResult) -> Optional[ErbaMessage]:
        """Validate parsed data against Pydantic models"""
        try:
            test_results_data = parsed_data.test_results

            if not test_results_data:
                logging.warning("No test results found in parsed data")
                return None
            
            if not len(test_results_data) == 30:
                logger.error(f"[Validation Error] Expected 30 test results got {len(test_results_data)} test results")
                return None
            
            cbc_params:List[str] = cbc_parameters.keys()
            for validated_test_name in test_results_data:
                if not validated_test_name['test_name'] in cbc_params:
                    logger.error(f"[Validation Error] Got Invalid cbc param: {validated_test_name['test_name']}")
                    return None
            
            message_header = parsed_data.message_header
            message_id:str = message_header['message_id']
            machine:str = message_header['machine']
            model:str = message_header['model']

            raw_message:List[Any] = parsed_data.raw_segments
            findings = parsed_data.findings

            if not findings:
                logger.warning("No findings results found in parsed data")

            erba_message:ErbaMessage = ErbaMessage(
                message_id=message_id,
                test_results=[ErbaTestResult(**result) for result in parsed_data.test_results],
                timestamp=time.strftime('%Y-%m-%d %H:%M:%S'),
                analyzer_id=self.config.device,
                raw_message=raw_message,
                findings=findings,
                machine=machine,
                model=model
            )
            
            logger.info("Message Validated Successfully")
            return erba_message
            
        except ValidationError as e:
            logging.error(f"[Validation Error] error: {e}")
            return None
        except Exception as e:
            logging.error(f"[Validation Error] error: {e}")
            return None