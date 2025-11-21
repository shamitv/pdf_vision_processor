# Environment Configuration

This document lists the environment variables used by the application and recommended defaults.

## Required
- `LLM_API_KEY`: API key for the LLM provider (OpenAI, Azure, etc.). Example: `sk-...`.

## Optional / Recommended
- `LLM_BASE_URL` (default: `https://api.openai.com/v1`): Base URL for the LLM HTTP API.
- `LLM_MODEL` (default: `gpt-4o`): Model identifier to use for LLM calls.
- `LLM_MAX_TOKENS` (default: `4096`): Maximum number of tokens to allow for model completions. Set this to an integer appropriate for your model. If you use models with smaller output limits, reduce this (e.g., `1024`).
- `DPI` (default: `150`): DPI used when rasterizing PDF pages to images.
- `PDF_VISION_PROCESSOR_HOST`: Override the HTTP host binding (mirrors `--host`).
- `PDF_VISION_PROCESSOR_PORT`: Override the server port (mirrors `--port`).
- `PDF_VISION_PROCESSOR_RELOAD`: `true/false` toggle for auto-reload.
- `PDF_VISION_PROCESSOR_LOG_LEVEL`: Logging verbosity passed to Uvicorn.
- `PDF_VISION_PROCESSOR_HOME`: Root directory for derived data/logs (defaults to `~/.pdf-vision-processor`).
- `PDF_VISION_PROCESSOR_DATA_DIR`: Custom data directory (uploads, generated images).
- `PDF_VISION_PROCESSOR_LOG_DIR`: Directory for runtime + LLM logs.
- `PDF_VISION_PROCESSOR_DATABASE_URL`: SQLAlchemy connection string (defaults to SQLite under the home dir).

## Example `.env`
```
LLM_API_KEY="your-api-key-here"
LLM_BASE_URL="https://api.openai.com/v1"
LLM_MODEL="gpt-4o"
LLM_MAX_TOKENS=4096
DPI=150
PDF_VISION_PROCESSOR_PORT=8080
PDF_VISION_PROCESSOR_DATA_DIR="/var/lib/pdf-vision-processor/data"
```

## Notes & Recommendations
- Verify your chosen `LLM_MODEL` supports the `LLM_MAX_TOKENS` output; otherwise the request may be truncated or fail.
- Prefer setting conservative `LLM_MAX_TOKENS` (e.g., `1024`) in production to reduce cost and memory usage unless you specifically require very large outputs.
- If you run into truncated responses, inspect the LLM SDK response `usage` or completion status for a `finish_reason` indicating token truncation.

Place the `.env` file in the project root or export the variables in your shell before running the app.
