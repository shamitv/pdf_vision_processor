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
import time
import logging

from .settings import get_settings

# Configuration
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")

# Make the max tokens configurable via environment variable.
logger = logging.getLogger(__name__)
default_max_tokens = 16384  # Example default for GPT-4o
try:
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", default_max_tokens))
    if LLM_MAX_TOKENS <= 0:
        raise ValueError("LLM_MAX_TOKENS must be > 0")
except Exception as _e:
    logger.warning("Invalid LLM_MAX_TOKENS value, falling back to %d: %s", default_max_tokens, _e)
    LLM_MAX_TOKENS = default_max_tokens

DPI = 150

client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)

SETTINGS = get_settings()
PROCESSING_LOG_DIR = str(SETTINGS.processing_log_dir)
LLM_DEBUG_DIR = str(SETTINGS.llm_log_dir)
DATA_IMAGES_DIR = str(SETTINGS.images_dir)
PROCESSING_LOG_FORMAT = "%(asctime)s %(message)s"


class ProcessingRunLogger:
    """Lightweight helper to emit structured processing logs."""

    def __init__(self, document_id: int, version_number: int):
        self.document_id = document_id
        self.version_number = version_number
        logger_name = f"{__name__}.processing.doc{document_id}.v{version_number}"
        self._logger = logging.getLogger(logger_name)
        self._logger.setLevel(logging.INFO)
        if not self._logger.handlers:
            os.makedirs(PROCESSING_LOG_DIR, exist_ok=True)
            log_path = os.path.join(
                PROCESSING_LOG_DIR, f"doc_{document_id}_v{version_number}.log"
            )
            handler = logging.FileHandler(log_path)
            handler.setFormatter(logging.Formatter(PROCESSING_LOG_FORMAT))
            self._logger.addHandler(handler)
        self._logger.propagate = False

    def log(self, **fields):
        payload = {"doc": self.document_id, "version": f"v{self.version_number}"}
        payload.update(fields)
        message = " ".join(
            f"{key}={self._stringify(value)}" for key, value in payload.items() if value is not None
        )
        self._logger.info(message)

    @staticmethod
    def _stringify(value):
        text = str(value)
        if any(ch.isspace() for ch in text):
            return f'"{text}"'
        return text

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

def analyze_page_with_llm(
    image_path: str,
    document_id: int,
    page_num: int,
    version_number: int,
    processing_log: "ProcessingRunLogger | None" = None,
) -> dict:
    """
    Sends the image to the Vision LLM and returns the parsed JSON response.
    """
    base64_image = encode_image(image_path)
    
    prompt = PAGE_ANALYSIS_PROMPT

    # Ensure logs directory exists and is versioned per processing run
    logs_dir = os.path.join(LLM_DEBUG_DIR, f"doc_{document_id}", f"v{version_number}")
    os.makedirs(logs_dir, exist_ok=True)

    page_prefix = os.path.join(logs_dir, f"page_{page_num:03d}")

    # Log Request
    request_log_path = f"{page_prefix}_request.json"
    request_data = {
        "prompt": prompt,
        "image_path": image_path,
        "version_number": version_number,
        "timestamp": datetime.now().isoformat()
    }
    with open(request_log_path, "w") as f:
        json.dump(request_data, f, indent=2)

    if processing_log:
        processing_log.log(page=page_num, step="llm_request", status="sent", model=LLM_MODEL)

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
            max_tokens=LLM_MAX_TOKENS,
            #max_completion_tokens=LLM_MAX_TOKENS,
        )
        
        content = response.choices[0].message.content

        # Log raw LLM response payload for debugging
        raw_response_path = f"{page_prefix}_response_raw.json"
        raw_payload = None
        if hasattr(response, "model_dump"):
            try:
                raw_payload = response.model_dump()
            except Exception as dump_err:  # pragma: no cover - defensive
                logger.warning("Failed to serialize LLM response via model_dump: %s", dump_err)
        if raw_payload is None:
            # Fallback to string representation if serialization fails
            raw_payload = {"raw": str(response)}
        with open(raw_response_path, "w") as f:
            json.dump(raw_payload, f, indent=2)

        # Log Response
        response_log_path = f"{page_prefix}_response.json"
        with open(response_log_path, "w") as f:
            f.write(content)

        result = json.loads(content)
        
        # Add usage metadata if available
        if hasattr(response, 'usage') and response.usage:
            result['_usage'] = {
                'total_tokens': response.usage.total_tokens,
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens
            }
            
        return result
    except Exception as e:
        if processing_log:
            processing_log.log(page=page_num, step="llm_request", status="error", error=str(e))
        print(f"Error calling LLM: {e}")
        return {"markdown": "", "elements": [], "error": str(e)}

def process_document(document_id: int, db: Session):
    """
    Main processing pipeline with versioning support.
    """
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        return

    processing_log: ProcessingRunLogger | None = None
    try:
        # Determine new version number
        existing_versions = db.query(models.DocumentVersion).filter(
            models.DocumentVersion.document_id == doc.id
        ).all()
        
        if existing_versions:
            version_number = max(v.version_number for v in existing_versions) + 1
        else:
            version_number = 1

        processing_log = ProcessingRunLogger(doc.id, version_number)
        pdf_name = doc.filename or (os.path.basename(doc.original_path) if doc.original_path else "")
        processing_log.log(event="run_start", pdf_name=pdf_name, pdf_path=doc.original_path, status="starting")

        # Create DocumentVersion record
        doc_version = models.DocumentVersion(
            document_id=doc.id,
            version_number=version_number,
            status=models.ProcessingStatus.PROCESSING
        )
        db.add(doc_version)
        db.commit()
        db.refresh(doc_version)
        processing_log.log(event="version_record", status="created", document_version_id=doc_version.id)

        # 1. Convert PDF to Images
        t0_conversion = time.perf_counter()
        # Create a version-specific directory for this document's images
        doc_images_dir = os.path.join(str(DATA_IMAGES_DIR), str(doc.id), f"v{version_number}")
        if processing_log:
            processing_log.log(step="pdf_to_images", status="begin", output_dir=doc_images_dir)
        image_paths = convert_pdf_to_images(doc.original_path, doc_images_dir)
        t1_conversion = time.perf_counter()
        
        doc_version.page_count = len(image_paths)
        doc_version.pdf_conversion_time_seconds = t1_conversion - t0_conversion
        db.commit()
        if processing_log:
            processing_log.log(
                step="pdf_to_images",
                status="complete",
                pages=len(image_paths),
                elapsed_seconds=round(doc_version.pdf_conversion_time_seconds, 4),
            )

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
            if processing_log:
                processing_log.log(page=page_num, step="page_record", status="created", page_id=page.id)

            # 3. Call LLM
            t0_llm = time.perf_counter()
            analysis_result = analyze_page_with_llm(
                image_path=image_path,
                document_id=doc.id,
                page_num=page_num,
                version_number=doc_version.version_number,
                processing_log=processing_log,
            )
            t1_llm = time.perf_counter()
            usage = analysis_result.get('_usage', {})
            if processing_log:
                processing_log.log(
                    page=page_num,
                    step="llm_request",
                    status="complete",
                    latency_seconds=round(t1_llm - t0_llm, 4),
                    tokens_total=usage.get('total_tokens', 0),
                    tokens_prompt=usage.get('prompt_tokens', 0),
                    tokens_completion=usage.get('completion_tokens', 0),
                )

            # Generate overlay image as part of processing pipeline
            t0_post = time.perf_counter()
            try:
                generate_overlay_image(image_path, analysis_result.get("elements") or [])
                if processing_log:
                    processing_log.log(page=page_num, step="overlay", status="complete")
            except Exception as overlay_error:
                if processing_log:
                    processing_log.log(page=page_num, step="overlay", status="error", error=str(overlay_error))
                print(f"Overlay generation failed for doc {document_id} page {page_num}: {overlay_error}")
            
            # 4. Store Analysis
            analysis = models.PageAnalysis(
                page_id=page.id,
                markdown_text=analysis_result.get("markdown", ""),
                raw_json=json.dumps(analysis_result)
            )
            db.add(analysis)
            
            # Update Page Telemetry
            page.llm_latency_seconds = t1_llm - t0_llm
            
            page.token_count = usage.get('total_tokens', 0)
            
            # Accumulate version totals
            doc_version.total_tokens += page.token_count
            
            t1_post = time.perf_counter()
            page.post_process_time_seconds = t1_post - t0_post
            
            db.commit()
            if processing_log:
                processing_log.log(
                    page=page_num,
                    step="analysis_persist",
                    status="complete",
                    page_id=page.id,
                    token_count=page.token_count,
                    post_process_seconds=round(page.post_process_time_seconds, 4),
                )

        doc_version.status = models.ProcessingStatus.COMPLETED
        doc_version.total_processing_time_seconds = time.perf_counter() - t0_conversion # approx total time since start
        db.commit()
        if processing_log:
            processing_log.log(
                event="run_complete",
                status="completed",
                total_tokens=doc_version.total_tokens,
                total_pages=doc_version.page_count,
                total_elapsed_seconds=round(doc_version.total_processing_time_seconds, 4),
            )

    except Exception as e:
        if 'doc_version' in locals():
            doc_version.status = models.ProcessingStatus.FAILED
            doc_version.error_message = str(e)
            db.commit()
        if processing_log:
            processing_log.log(event="run_complete", status="failed", error=str(e))
        print(f"Processing failed for doc {document_id}: {e}")

