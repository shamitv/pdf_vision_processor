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

class Page(PageBase):
    id: int
    document_id: int
    analysis: Optional[PageAnalysis] = None

    class Config:
        from_attributes = True

class DocumentBase(BaseModel):
    filename: str

class Document(DocumentBase):
    id: int
    uploaded_at: datetime
    status: ProcessingStatus
    page_count: int
    error_message: Optional[str] = None
    pages: List[Page] = []

    class Config:
        from_attributes = True
