import os
import json
import fitz  # pymupdf
import base64
from openai import OpenAI
from sqlalchemy.orm import Session
from . import models, database
from datetime import datetime
from .prompts import PAGE_ANALYSIS_PROMPT
from .utils.overlay import generate_overlay_image

# Configuration
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")

DPI=150

client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)

def convert_pdf_to_images(pdf_path: str, output_dir: str) -> list[str]:
    """
    Converts a PDF to a list of image paths (one per page).
    """
    doc = fitz.open(pdf_path)
    image_paths = []
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap(dpi=DPI)
        image_filename = f"page_{page_num + 1}.png"
        image_path = os.path.join(output_dir, image_filename)
        pix.save(image_path)
        image_paths.append(image_path)
    
    return image_paths

def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def analyze_page_with_llm(image_path: str, document_id: int, page_num: int) -> dict:
    """
    Sends the image to the Vision LLM and returns the parsed JSON response.
    """
    base64_image = encode_image(image_path)
    
    prompt = PAGE_ANALYSIS_PROMPT

    # Ensure logs directory exists
    logs_dir = os.path.join("logs", "llm_debug")
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    # Log Request
    request_log_path = os.path.join(logs_dir, f"doc_{document_id}_page_{page_num}_request.json")
    request_data = {
        "prompt": prompt,
        "image_path": image_path,
        "timestamp": datetime.now().isoformat()
    }
    with open(request_log_path, "w") as f:
        json.dump(request_data, f, indent=2)

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
            response_format={"type": "json_object"},
            max_tokens=4096,
        )
        
        content = response.choices[0].message.content

        # Log Response
        response_log_path = os.path.join(logs_dir, f"doc_{document_id}_page_{page_num}_response.json")
        with open(response_log_path, "w") as f:
            f.write(content)

        return json.loads(content)
    except Exception as e:
        print(f"Error calling LLM: {e}")
        return {"markdown": "", "elements": [], "error": str(e)}

def process_document(document_id: int, db: Session):
    """
    Main processing pipeline with versioning support.
    """
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        return

    try:
        # Determine new version number
        existing_versions = db.query(models.DocumentVersion).filter(
            models.DocumentVersion.document_id == doc.id
        ).all()
        
        if existing_versions:
            version_number = max(v.version_number for v in existing_versions) + 1
        else:
            version_number = 1

        # Create DocumentVersion record
        doc_version = models.DocumentVersion(
            document_id=doc.id,
            version_number=version_number,
            status=models.ProcessingStatus.PROCESSING
        )
        db.add(doc_version)
        db.commit()
        db.refresh(doc_version)

        # 1. Convert PDF to Images
        # Create a version-specific directory for this document's images
        doc_images_dir = os.path.join("data", "images", str(doc.id), f"v{version_number}")
        image_paths = convert_pdf_to_images(doc.original_path, doc_images_dir)
        
        doc_version.page_count = len(image_paths)
        db.commit()

        # 2. Create Page records and Process each page
        for i, image_path in enumerate(image_paths):
            page_num = i + 1
            page = models.Page(
                document_version_id=doc_version.id,
                page_number=page_num,
                image_path=image_path
            )
            db.add(page)
            db.commit() # Commit to get page.id
            db.refresh(page)

            # 3. Call LLM
            analysis_result = analyze_page_with_llm(image_path, doc.id, page_num)

            # Generate overlay image as part of processing pipeline
            try:
                generate_overlay_image(image_path, analysis_result.get("elements") or [])
            except Exception as overlay_error:
                print(f"Overlay generation failed for doc {document_id} page {page_num}: {overlay_error}")
            
            # 4. Store Analysis
            analysis = models.PageAnalysis(
                page_id=page.id,
                markdown_text=analysis_result.get("markdown", ""),
                raw_json=json.dumps(analysis_result)
            )
            db.add(analysis)
            db.commit()

        doc_version.status = models.ProcessingStatus.COMPLETED
        db.commit()

    except Exception as e:
        if 'doc_version' in locals():
            doc_version.status = models.ProcessingStatus.FAILED
            doc_version.error_message = str(e)
            db.commit()
        print(f"Processing failed for doc {document_id}: {e}")

