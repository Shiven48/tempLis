"""
Lab Results API Package

This package provides a FastAPI-based REST API for processing and storing
laboratory test results from medical analyzers.

Package Structure:
- main.py: FastAPI application initialization and configuration
- models.py: Database models and Pydantic schemas
- database.py: Database configuration and session management
- endpoints.py: API route handlers
- services.py: Business logic and service layer
- dependencies.py: Dependency injection functions

Usage:
    from src.api import app
    # or
    from src.api.main import app
"""

from .models import LabMessage, TestResult, LabResultsCreateResponse, HealthCheckResponse
from .database import get_db, create_tables, drop_tables
from .services import LabResultsService

__version__ = "1.0.0"
__all__ = [
    "app",
    "create_app", 
    "LabMessage",
    "TestResult",
    "LabResultsCreateResponse",
    "HealthCheckResponse",
    "get_db",
    "create_tables",
    "drop_tables",
    "LabResultsService"
]