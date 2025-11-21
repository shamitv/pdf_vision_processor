from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class PageAnalysisBase(BaseModel):
    markdown_text: Optional[str] = None
    raw_json: Optional[str] = None

class PageAnalysis(PageAnalysisBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class PageBase(BaseModel):
    page_number: int
    image_path: str
    
    # Telemetry
    llm_latency_seconds: float = 0.0
    post_process_time_seconds: float = 0.0
    token_count: int = 0

class Page(PageBase):
    id: int
    document_version_id: int
    analysis: Optional[PageAnalysis] = None

    class Config:
        from_attributes = True

class DocumentVersionBase(BaseModel):
    version_number: int
    status: ProcessingStatus

class DocumentVersion(DocumentVersionBase):
    id: int
    document_id: int
    created_at: datetime
    page_count: int
    error_message: Optional[str] = None
    
    # Telemetry
    total_processing_time_seconds: float = 0.0
    pdf_conversion_time_seconds: float = 0.0
    total_tokens: int = 0
    
    pages: List[Page] = []

    class Config:
        from_attributes = True

class DocumentBase(BaseModel):
    filename: str

class Document(DocumentBase):
    id: int
    uploaded_at: datetime
    versions: List[DocumentVersion] = []

    class Config:
        from_attributes = True
