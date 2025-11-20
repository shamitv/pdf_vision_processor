import os
import shutil
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from . import models, schemas, database, processor

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

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
        else:
            doc_dict["status"] = models.ProcessingStatus.PENDING
            doc_dict["page_count"] = 0
            
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
    upload_dir = os.path.join("data", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Create DB record
    db_doc = models.Document(
        filename=file.filename,
        original_path=file_path,
        status=models.ProcessingStatus.PENDING
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
    
    if doc.status == models.ProcessingStatus.PROCESSING:
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
