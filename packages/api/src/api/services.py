"""
Business logic and service layer for lab results processing
"""
import json
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from erba.models import ErbaMessage

from .models import LabMessage, TestResult, LabResultsCreateResponse
from .logging_setup import logger


class LabResultsService:
    """Service class for handling lab results business logic"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_lab_results(self, lab_data: ErbaMessage) -> LabResultsCreateResponse:
        """
        Process and store laboratory test results from analyzer
        
        Args:
            lab_data: ErbaMessage containing lab results data
            
        Returns:
            LabResultsCreateResponse with processing results
            
        Raises:
            Exception: If there's an error during processing
        """
        try:
            logger.info(f"Processing lab results for message_id: {lab_data.message_id}")
            
            duplicate_response = self._check_duplicate_message(lab_data)
            if duplicate_response:
                return duplicate_response
            
            db_message = self._create_lab_message(lab_data)
            self._create_test_results(lab_data, db_message.id)
            
            logger.info(f"Successfully processed lab results for message_id: {lab_data.message_id}")
            
            return LabResultsCreateResponse(
                message="Lab results stored successfully",
                id=db_message.id,
                analyzer_id=db_message.analyzer_id,
                timestamp=lab_data.timestamp,
                test_results_count=db_message.test_results_count,
                duplicate=False
            )
            
        except IntegrityError as e:
            self.db.rollback()
            logger.warning(f"Integrity constraint violation for message_id: {lab_data.message_id}")
            return self._handle_duplicate_integrity_error(lab_data)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error processing lab results for message_id {lab_data.message_id}: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            raise
    
    def _check_duplicate_message(self, lab_data: ErbaMessage) -> Optional[LabResultsCreateResponse]:
        """Check if message already exists in database"""
        existing_message = self.db.query(LabMessage).filter(
            LabMessage.message_id == lab_data.message_id
        ).first()
        
        if existing_message:
            logger.info(f"Duplicate message detected - message_id: {lab_data.message_id} already exists")
            return LabResultsCreateResponse(
                message="Duplicate message ignored - already processed",
                id=existing_message.id,
                analyzer_id=existing_message.analyzer_id,
                timestamp=existing_message.timestamp.isoformat(),
                test_results_count=existing_message.test_results_count,
                duplicate=True
            )
        return None
    
    def _create_lab_message(self, lab_data: ErbaMessage) -> LabMessage:
        """Create and save lab message record"""
        db_message = LabMessage(
            message_id=lab_data.message_id,
            analyzer_id=lab_data.analyzer_id,
            timestamp=datetime.fromisoformat(lab_data.timestamp.replace('Z', '+00:00')),
            raw_segments=json.dumps(lab_data.raw_message),
            test_results_count=len(lab_data.test_results),
            machine=lab_data.machine,
            model=lab_data.model,
            findings=lab_data.findings
        )
        
        self.db.add(db_message)
        self.db.commit()
        self.db.refresh(db_message)
        
        logger.info(f"Created lab message record: {db_message.id}")
        return db_message
    
    def _create_test_results(self, lab_data: ErbaMessage, lab_message_id: int) -> None:
        """Create and save test result records"""
        for test_result in lab_data.test_results:
            db_test_result = TestResult(
                message_id=lab_data.message_id,
                analyzer_id=lab_data.analyzer_id,
                timestamp=datetime.fromisoformat(lab_data.timestamp.replace('Z', '+00:00')),
                test_code=test_result.test_code,
                test_name=test_result.test_name,
                result_value=test_result.result_value,
                units=test_result.units,
                reference_range=test_result.reference_range,
                flags=test_result.flags,
                lab_message_id=lab_message_id
            )
            self.db.add(db_test_result)
        
        self.db.commit()
        logger.info(f"Created {len(lab_data.test_results)} test result records")
    
    def _handle_duplicate_integrity_error(self, lab_data: ErbaMessage) -> LabResultsCreateResponse:
        """Handle integrity constraint violations (duplicates)"""
        existing_message = self.db.query(LabMessage).filter(
            LabMessage.message_id == lab_data.message_id
        ).first()
        
        return LabResultsCreateResponse(
            message="Duplicate message ignored - integrity constraint violation",
            id=existing_message.id if existing_message else None,
            analyzer_id=lab_data.analyzer_id,
            timestamp=lab_data.timestamp,
            test_results_count=len(lab_data.test_results),
            duplicate=True
        )