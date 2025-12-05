import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from .database import Base

class ProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    original_path = Column(String)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    versions = relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan")

class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    version_number = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(Enum(ProcessingStatus), default=ProcessingStatus.PENDING)
    page_count = Column(Integer, default=0)
    error_message = Column(String, nullable=True)
    
    # Telemetry
    total_processing_time_seconds = Column(Float, default=0.0)
    pdf_conversion_time_seconds = Column(Float, default=0.0)
    total_tokens = Column(Integer, default=0)

    # Relationships
    document = relationship("Document", back_populates="versions")
    pages = relationship("Page", back_populates="document_version", cascade="all, delete-orphan")

class Page(Base):
    __tablename__ = "pages"

    id = Column(Integer, primary_key=True, index=True)
    document_version_id = Column(Integer, ForeignKey("document_versions.id"))
    page_number = Column(Integer)
    image_path = Column(String)
    status = Column(Enum(ProcessingStatus), default=ProcessingStatus.PENDING)
    error_message = Column(Text, nullable=True)
    
    # Telemetry
    llm_latency_seconds = Column(Float, default=0.0)
    post_process_time_seconds = Column(Float, default=0.0)
    token_count = Column(Integer, default=0)

    # Relationships
    document_version = relationship("DocumentVersion", back_populates="pages")
    analysis = relationship("PageAnalysis", back_populates="page", uselist=False, cascade="all, delete-orphan")

class PageAnalysis(Base):
    __tablename__ = "page_analysis"

    id = Column(Integer, primary_key=True, index=True)
    page_id = Column(Integer, ForeignKey("pages.id"))
    markdown_text = Column(Text)
    raw_json = Column(Text) # Storing JSON as string
    created_at = Column(DateTime, default=datetime.utcnow)

    page = relationship("Page", back_populates="analysis")
