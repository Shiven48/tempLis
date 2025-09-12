"""
Database models and Pydantic schemas for the Lab Results API
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy import JSON, ForeignKey, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from pydantic import BaseModel, ConfigDict

from .database import Base


# SQLAlchemy Database Models
class LabMessage(Base):
    """Database model for lab messages"""
    __tablename__ = "lab_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String, unique=True, nullable=False, index=True)
    analyzer_id = Column(String, index=True)
    timestamp = Column(DateTime)
    raw_segments = Column(Text)
    test_results_count = Column(Integer)
    machine = Column(String)
    model = Column(String)
    findings = Column(JSON)
    
    test_results = relationship("TestResult", back_populates="lab_message")


class TestResult(Base):
    """Database model for individual test results"""
    __tablename__ = "test_results"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    message_id = Column(String, nullable=False, index=True)
    analyzer_id = Column(String, index=True)
    timestamp = Column(DateTime)
    test_code = Column(String, index=True)
    test_name = Column(String)
    result_value = Column(String)
    units = Column(String)
    reference_range = Column(String)
    flags = Column(String)
    lab_message_id = Column(Integer, ForeignKey('lab_messages.id'), index=True)
    
    lab_message = relationship("LabMessage", back_populates="test_results")


# Pydantic Response Models
class TestResultResponse(BaseModel):
    """Response model for test results"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    test_code: str
    test_name: str
    result_value: str
    units: Optional[str] = None
    reference_range: Optional[str] = None
    flags: Optional[str] = None


class LabMessageResponse(BaseModel):
    """Response model for lab messages"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    message_id: str
    analyzer_id: str
    timestamp: datetime
    test_results_count: int
    machine: str
    model: str
    test_results: List[TestResultResponse] = []

class LabResultsCreateResponse(BaseModel):
    """Response model for creating lab results"""
    message: str
    id: Optional[int] = None
    analyzer_id: str
    timestamp: str
    test_results_count: int
    duplicate: bool = False


class HealthCheckResponse(BaseModel):
    """Response model for health check"""
    status: str
    timestamp: datetime