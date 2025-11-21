# PDF Processing Workflow

This document outlines how a PDF document is processed within the PDF Vision Processor application.

## Overview

The processing pipeline is triggered when a document is uploaded and processing is initiated. The core logic resides in `pdf_vision_processor/processor.py`.

## Workflow Steps

1.  **Initialization**:
    *   The `process_document` function is called with the `document_id`.
    *   The document status is updated to `PROCESSING` in the database.

2.  **PDF Conversion**:
    *   The PDF file is opened using `pymupdf` (fitz).
    *   Each page of the PDF is converted into a PNG image.
    *   Images are stored in a dedicated directory under the configured data root (default: `~/.pdf-vision-processor/data/images/{document_id}/`).

3.  **Page Analysis (Per Page)**:
    *   The system iterates through each generated page image.
    *   A `Page` record is created in the database.
    *   The image is encoded in Base64 format.
    *   The image and a specific prompt are sent to the Vision LLM (e.g., GPT-4o).

4.  **LLM Interaction**:
    *   **Prompt**: The system uses a predefined prompt from `pdf_vision_processor/prompts.py`.
    *   **Request**: A chat completion request is made with the `user` role containing both the text prompt and the image URL (data URI).
    *   **Response Format**: The LLM is instructed to return a valid JSON object.

5.  **Data Extraction & Storage**:
    *   The JSON response from the LLM is parsed.
    *   A `PageAnalysis` record is created for the page.
    *   **Markdown**: The extracted text content in Markdown format is stored in the `markdown_text` field.
    *   **Raw Data**: The complete JSON response (including bounding boxes and element types) is stored in the `raw_json` field.

6.  **Completion**:
    *   Once all pages are processed successfully, the document status is updated to `COMPLETED`.
    *   If an error occurs at any step, the status is set to `FAILED`, and the error message is recorded.

## LLM Prompt

The prompt sent to the LLM is defined in `pdf_vision_processor/prompts.py`:

```python
PAGE_ANALYSIS_PROMPT = """
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
            "box_2d": [xmin, ymin, xmax, ymax] 
        }
    ]
}
Note: box_2d should be normalized coordinates (0-1000).
Ensure the response is valid JSON.
"""
```

## Response Processing

The LLM response is expected to be a JSON object with two main keys:

*   `markdown`: A string containing the full text of the page formatted as Markdown.
*   `elements`: A list of objects, where each object represents a layout element (paragraph, heading, table, etc.) and includes:
    *   `type`: The type of element.
    *   `text`: The text content of the element.
    *   `box_2d`: The bounding box coordinates [xmin, ymin, xmax, ymax], normalized to a 0-1000 scale.

This structure allows the application to display both the readable text and overlay bounding boxes on the original image in the UI.
