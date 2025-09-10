from fastapi import FastAPI
from sqlalchemy import JSON, ForeignKey, create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, relationship

DATABASE_URL = "sqlite:///./lab_results.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class TestResult(Base):
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

class LabMessage(Base):
    __tablename__ = "lab_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String, unique=True, nullable=False, index=True)  # Add this line
    analyzer_id = Column(String, index=True)
    timestamp = Column(DateTime)
    raw_segments = Column(Text)
    test_results_count = Column(Integer)
    machine = Column(String)
    model = Column(String)
    findings = Column(JSON)
    test_results = relationship("TestResult", back_populates="lab_message")

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI(title="Lab Results API", version="1.0.0")
