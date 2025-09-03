import json
from middleware import logger
from middleware.models import ErbaMessage
import uvicorn

from datetime import datetime
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from src.api.main import app
from src.api.main import (
    LabMessage,
    TestResult,
    get_db
)

from fastapi import Request
import time

""" Just a Mock endpoint to test overall flow from gui to the endpoint to the db"""

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.info(f"{request.method} {request.url.path}")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.4f}s")
    
    return response

@app.post("/lab-results/", response_model=dict)
async def create_lab_results(
    lab_data: ErbaMessage, 
    db: Session = Depends(get_db)
):
    """Store laboratory test results from analyzer"""
    try:
        logger.info(f"Endpoint hit: {lab_data.timestamp}")
        
        db_message:LabMessage = LabMessage(
            analyzer_id=lab_data.analyzer_id,
            timestamp=datetime.fromisoformat(lab_data.timestamp.replace('Z', '+00:00')),
            raw_segments=json.dumps(lab_data.raw_message),
            test_results_count=len(lab_data.test_results),
            machine = lab_data.machine,
            model = lab_data.model,
            findings = lab_data.findings
        )

        logger.info(f"Lab conversion data: {db_message}")

        db.add(db_message)
        db.commit()
        db.refresh(db_message)
        
        test_result_ids = []
        
        for test_result in lab_data.test_results:
            db_test_result = TestResult(
                analyzer_id=lab_data.analyzer_id,
                timestamp=datetime.fromisoformat(lab_data.timestamp.replace('z', '+00:00')), 
                test_code=test_result.test_code,
                test_name=test_result.test_name,
                result_value=test_result.result_value,
                units=test_result.units,
                reference_range=test_result.reference_range,
                flags=test_result.flags,
                lab_message_id=db_message.id
            )

            db.add(db_test_result)
            db.commit()
            db.refresh(db_test_result)
            test_result_ids.append(db_test_result.id)

        logger.info(f"Test Result conversion data: {db_test_result}")

        return {
            "message": "Lab results stored successfully",
            "id": db_message.id,
            "analyzer_id": db_message.analyzer_id,
            "timestamp": db_message.timestamp,
            "test_results_count": db_message.test_results_count
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error storing lab results: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now()}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)