import os
import json
import fitz  # pymupdf
import base64
from openai import OpenAI
from sqlalchemy.orm import Session
from . import models, database
from datetime import datetime

# Configuration
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")

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
        pix = page.get_pixmap()
        image_filename = f"page_{page_num + 1}.png"
        image_path = os.path.join(output_dir, image_filename)
        pix.save(image_path)
        image_paths.append(image_path)
    
    return image_paths

def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def analyze_page_with_llm(image_path: str) -> dict:
    """
    Sends the image to the Vision LLM and returns the parsed JSON response.
    """
    base64_image = encode_image(image_path)
    
    prompt = """
    Analyze this page image. 
    1. Extract the full text content in Markdown format.
    2. Identify all layout elements (paragraphs, headings, tables, images) and provide their bounding boxes.
    
    Return a JSON object with the following structure:
    {
        "markdown": "The full markdown text...",
        "elements": [
            {
                "id": "unique_id",
                "type": "paragraph|heading|table|image",
                "text": "content of the element...",
                "box_2d": [ymin, xmin, ymax, xmax] 
            }
        ]
    }
    Note: box_2d should be normalized coordinates (0-1000).
    Ensure the response is valid JSON.
    """

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
        return json.loads(content)
    except Exception as e:
        print(f"Error calling LLM: {e}")
        return {"markdown": "", "elements": [], "error": str(e)}

def process_document(document_id: int, db: Session):
    """
    Main processing pipeline.
    """
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        return

    try:
        doc.status = models.ProcessingStatus.PROCESSING
        db.commit()

        # 1. Convert PDF to Images
        # Create a specific directory for this document's images
        doc_images_dir = os.path.join("data", "images", str(doc.id))
        image_paths = convert_pdf_to_images(doc.original_path, doc_images_dir)
        
        doc.page_count = len(image_paths)
        db.commit()

        # 2. Create Page records and Process each page
        for i, image_path in enumerate(image_paths):
            page_num = i + 1
            page = models.Page(
                document_id=doc.id,
                page_number=page_num,
                image_path=image_path
            )
            db.add(page)
            db.commit() # Commit to get page.id
            db.refresh(page)

            # 3. Call LLM
            analysis_result = analyze_page_with_llm(image_path)
            
            # 4. Store Analysis
            analysis = models.PageAnalysis(
                page_id=page.id,
                markdown_text=analysis_result.get("markdown", ""),
                raw_json=json.dumps(analysis_result)
            )
            db.add(analysis)
            db.commit()

        doc.status = models.ProcessingStatus.COMPLETED
        db.commit()

    except Exception as e:
        doc.status = models.ProcessingStatus.FAILED
        doc.error_message = str(e)
        db.commit()
        print(f"Processing failed for doc {document_id}: {e}")
