import json
import os
import shutil
from importlib import resources
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from . import models, schemas, database, processor
from .settings import get_settings
from .utils.overlay import generate_overlay_image

router = APIRouter()
templates = Jinja2Templates(directory=str(resources.files("pdf_vision_processor").joinpath("templates")))

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=List[schemas.Document])
def list_documents_ui(request: Request, db: Session = Depends(get_db)):
    documents = db.query(models.Document).order_by(models.Document.uploaded_at.desc()).all()
    
    # Add latest version info for each document to make it easier for the template
    docs_with_status = []
    for doc in documents:
        doc_dict = {
            "id": doc.id,
            "filename": doc.filename,
            "uploaded_at": doc.uploaded_at,
            "versions": doc.versions
        }
        
        # Get latest version for display
        if doc.versions:
            latest_version = max(doc.versions, key=lambda v: v.version_number)
            doc_dict["status"] = latest_version.status
            doc_dict["page_count"] = latest_version.page_count
            doc_dict["pdf_conversion_time_seconds"] = latest_version.pdf_conversion_time_seconds
            doc_dict["total_processing_time_seconds"] = latest_version.total_processing_time_seconds
            doc_dict["total_tokens"] = latest_version.total_tokens
        else:
            doc_dict["status"] = models.ProcessingStatus.PENDING
            doc_dict["page_count"] = 0
            doc_dict["pdf_conversion_time_seconds"] = 0.0
            doc_dict["total_processing_time_seconds"] = 0.0
            doc_dict["total_tokens"] = 0
            
        docs_with_status.append(doc_dict)
    
    return templates.TemplateResponse("index.html", {"request": request, "documents": docs_with_status})

@router.get("/documents", response_model=List[schemas.Document])
def list_documents(db: Session = Depends(get_db)):
    return db.query(models.Document).order_by(models.Document.uploaded_at.desc()).all()

@router.post("/upload", response_model=schemas.Document)
def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Save file
    upload_dir = get_settings().uploads_dir
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Create DB record (status is now on DocumentVersion, not Document)
    db_doc = models.Document(
        filename=file.filename,
        original_path=file_path
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    return db_doc

@router.post("/process/{document_id}")
def process_document(document_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check if any version is currently processing
    processing_version = db.query(models.DocumentVersion).filter(
        models.DocumentVersion.document_id == document_id,
        models.DocumentVersion.status == models.ProcessingStatus.PROCESSING
    ).first()
    
    if processing_version:
        raise HTTPException(status_code=400, detail="Document is already processing")

    background_tasks.add_task(processor.process_document, document_id, database.SessionLocal())
    return {"message": "Processing started"}

@router.get("/documents/{document_id}", response_model=schemas.Document)
def get_document(document_id: int, request: Request, version_id: int = None, db: Session = Depends(get_db)):
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Determine which version to display
    if version_id:
        selected_version = db.query(models.DocumentVersion).filter(
            models.DocumentVersion.id == version_id,
            models.DocumentVersion.document_id == document_id
        ).first()
        if not selected_version:
            raise HTTPException(status_code=404, detail="Version not found")
    else:
        # Get latest version by default
        if doc.versions:
            selected_version = max(doc.versions, key=lambda v: v.version_number)
        else:
            selected_version = None
    
    # For UI, we might want to return a template
    if "text/html" in request.headers.get("accept", ""):
        return templates.TemplateResponse("document.html", {
            "request": request, 
            "document": doc,
            "selected_version": selected_version
        })
    
    return doc

@router.get("/pages/{page_id}/analysis", response_model=schemas.PageAnalysis)
def get_page_analysis(page_id: int, db: Session = Depends(get_db)):
    analysis = db.query(models.PageAnalysis).filter(models.PageAnalysis.page_id == page_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis

@router.get("/pages/{page_id}/overlay-image")
def get_page_overlay_image(page_id: int, db: Session = Depends(get_db)):
    page = db.query(models.Page).filter(models.Page.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    if not page.analysis or not page.analysis.raw_json:
        raise HTTPException(status_code=404, detail="Analysis not available")

    if not os.path.exists(page.image_path):
        raise HTTPException(status_code=404, detail="Source image not found")

    try:
        analysis_payload = json.loads(page.analysis.raw_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"Invalid analysis payload: {exc}")

    elements = analysis_payload.get("elements") or []
    overlay_path = generate_overlay_image(page.image_path, elements)
    return FileResponse(overlay_path)

@router.get("/documents/{document_id}/versions/{version_id}/failures")
def get_failed_pages(document_id: int, version_id: int, db: Session = Depends(get_db)):
    pages = db.query(models.Page).filter(
        models.Page.document_version_id == version_id,
        models.Page.status == models.ProcessingStatus.FAILED
    ).all()
    
    return [
        {
            "id": p.id,
            "page_number": p.page_number,
            "error_message": p.error_message
        }
        for p in pages
    ]

@router.post("/documents/{document_id}/versions/{version_id}/reprocess")
def reprocess_pages_endpoint(
    document_id: int, 
    version_id: int, 
    payload: dict, # Expect {"page_ids": [...]}
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    page_ids = payload.get("page_ids", [])
    
    background_tasks.add_task(
        processor.reprocess_pages, 
        document_id, 
        version_id, 
        page_ids, 
        database.SessionLocal()
    )
    return {"message": "Reprocessing started"}


@router.get("/documents/{document_id}/versions/{version_id}/pages/status")
def get_page_statuses(document_id: int, version_id: int, db: Session = Depends(get_db)):
    version = db.query(models.DocumentVersion).filter(
        models.DocumentVersion.id == version_id,
        models.DocumentVersion.document_id == document_id
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    pages = db.query(models.Page).filter(models.Page.document_version_id == version_id).all()
    payload = {
        "document_id": document_id,
        "version_id": version_id,
        "version_status": version.status,
        "page_count": version.page_count,
        "pages": []
    }

    for p in pages:
        payload["pages"].append(
            {
                "id": p.id,
                "page_number": p.page_number,
                "status": p.status,
                "image_path": p.image_path,
                "token_count": p.token_count,
                "llm_latency_seconds": p.llm_latency_seconds,
                "error_message": p.error_message,
            }
        )

    return payload
