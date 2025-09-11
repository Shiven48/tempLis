"""
API endpoint handlers for the Lab Results API
"""
import time
from datetime import datetime
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from erba.models import ErbaMessage

from .database import get_db
from .models import LabResultsCreateResponse, HealthCheckResponse
from .services import LabResultsService
from .logging_setup import logger

async def log_requests_middleware(request: Request, call_next):
    """
    Middleware to log all incoming requests and their processing time
    """
    start_time = time.time()
    logger.info(f"{request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.4f}s")
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"{request.method} {request.url.path} - ERROR - {process_time:.4f}s - {str(e)}")
        
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(e),
                "path": request.url.path,
                "method": request.method
            }
        )


async def create_lab_results(
    lab_data: ErbaMessage, 
    db: Session = Depends(get_db)
) -> LabResultsCreateResponse:
    """
    Store laboratory test results from analyzer
    
    Args:
        lab_data: ErbaMessage containing the lab results data
        db: Database session dependency
        
    Returns:
        LabResultsCreateResponse with processing results
        
    Raises:
        HTTPException: If there's an error processing the lab results
    """
    try:
        logger.info(f"Lab results endpoint hit: {lab_data.timestamp}")
        
        service = LabResultsService(db)
        result:LabResultsCreateResponse = service.create_lab_results(lab_data)
        
        return result
        
    except Exception as e:
        logger.error(f"Endpoint error for message_id {lab_data.message_id}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error storing lab results: {str(e)}"
        )


async def health_check() -> HealthCheckResponse:
    """
    Health check endpoint to verify API is running
    
    Returns:
        HealthCheckResponse with current status and timestamp
    """
    return HealthCheckResponse(
        status="healthy", 
        timestamp=datetime.now()
    )