# PDF Vision Processor

A Python application that processes PDFs using a Vision LLM (OpenAI-compatible). It converts PDF pages to images, extracts text and layout elements (with bounding boxes), and provides a web UI to view the results.

## Prerequisites

- Python 3.12
- OpenAI-compatible API key (e.g., OpenAI, Azure OpenAI, or local LLM with vision support)

## Setup

1.  **Create Virtual Environment**:
    ```bash
    /Users/shamit/homebrew/bin/python3.12 -m venv .venv
    source .venv/bin/activate
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Environment Configuration**:
    Create a `.env` file in the root directory or export variables:
    ```bash
    export LLM_API_KEY="your-api-key"
    export LLM_BASE_URL="https://api.openai.com/v1" # Optional, defaults to OpenAI
    export LLM_MODEL="gpt-4o" # Optional, defaults to gpt-4o
    ```

See `docs/env_config.md` for a full list of environment variables and recommended defaults.

## Running the Application

Start the FastAPI server:
```bash
./.venv/bin/uvicorn app.main:app --reload --port 8000
```

The application will be available at `http://localhost:8000`.

## Usage

1.  **Upload**: Go to the home page and upload a PDF file.
2.  **Process**: Click the "Process" button next to the uploaded document. This runs in the background.
3.  **View**: Click "View" to see the document details. Select a page from the sidebar to view the image, bounding box overlays, and extracted Markdown.

## API Usage Example

```bash
# Upload a PDF
curl -X POST -F "file=@/path/to/document.pdf" http://localhost:8000/upload

# Start Processing (replace {id} with the ID returned from upload)
curl -X POST http://localhost:8000/process/{id}

# Get Analysis
curl http://localhost:8000/pages/{page_id}/analysis
```
