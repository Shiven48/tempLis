"""
Main FastAPI application initialization and configuration
"""
import uvicorn
from fastapi import FastAPI

from .models import LabResultsCreateResponse
from .database import create_tables
from .endpoints import create_lab_results, health_check, log_requests_middleware


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application
    
    Returns:
        FastAPI: Configured FastAPI application instance
    """
    app = FastAPI(
        title="Lab Results API",
        version="1.0.0",
        description="API for processing and storing laboratory test results from analyzers",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # middleware
    app.middleware("http")(log_requests_middleware)
    
    # routes
    app.post("/lab-results/", response_model=LabResultsCreateResponse, tags=["Lab Results"])(create_lab_results)
    app.get("/health", tags=["Health"])(health_check)
    
    create_tables()    
    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
