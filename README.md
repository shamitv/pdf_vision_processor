# PDF Vision Processor

A FastAPI service that converts PDFs into page images, sends them to an OpenAI-compatible Vision LLM, and exposes the parsed layout/markdown through both REST APIs and a built-in UI. The project now ships as an installable package named `pdf-vision-processor` so it can be deployed with a single CLI command.

## Installation (PyPI)

```bash
python -m venv venv && source venv/bin/activate
pip install pdf-vision-processor
pdf-vision-processor --host 0.0.0.0 --port 8080
```

The CLI loads a `.env` file from your current working directory (if present), applies overrides from environment variables prefixed with `PDF_VISION_PROCESSOR_`, and falls back to sensible defaults. Static assets and Jinja templates are bundled inside the wheel.

> **Note:** ``PyMuPDF`` (``fitz``) is expected to be available in the runtime environment (e.g., preinstalled in the platform image). The PyPI package does **not** vendor it; install `pymupdf` manually if your deployment does not already include it.

## Configuration

| Setting | CLI Flag | Environment Variable | Default |
| --- | --- | --- | --- |
| Host interface | `--host` | `PDF_VISION_PROCESSOR_HOST` | `127.0.0.1` |
| Port | `--port` | `PDF_VISION_PROCESSOR_PORT` | `8000` |
| Reload | `--reload/--no-reload` | `PDF_VISION_PROCESSOR_RELOAD` | `False` |
| Log level | `--log-level` | `PDF_VISION_PROCESSOR_LOG_LEVEL` | `info` |
| Data directory | `--data-dir` | `PDF_VISION_PROCESSOR_DATA_DIR` | `~/.pdf-vision-processor/data` |
| Logs directory | `--logs-dir` | `PDF_VISION_PROCESSOR_LOG_DIR` | `~/.pdf-vision-processor/logs` |
| Database URL | `--database-url` | `PDF_VISION_PROCESSOR_DATABASE_URL` | `sqlite:///<home>/db.sqlite3` |

Additional LLM specific variables (e.g., `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, `LLM_MAX_TOKENS`) continue to be read from the environment; see `docs/env_config.md` for the full catalog. When no overrides are provided, uploads, derived images, and logs are stored under `~/.pdf-vision-processor/` so the package works even when installed system-wide.

Optional project-level configuration can also be provided through a `config.toml` file with sections named `[server]`, `[paths]`, and `[database]`. The CLI resolves settings in the following order: CLI flags → environment variables → `config.toml` → defaults.

## Running from Source

Developers contributing to the repository can still use `run.py`, which now delegates directly to the packaged CLI to ensure consistent behavior:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run.py --host 127.0.0.1 --port 8000 --reload
```

Ensure your virtual environment already has ``pymupdf`` installed (or install it manually) before running the processor locally.

Assets, templates, and compatibility shims remain under the legacy `app/` namespace for existing imports, but all active code now lives inside the `pdf_vision_processor/` package (matching what ships to PyPI).

## Usage

1. **Upload** – Visit `/` and upload a PDF.
2. **Process** – Click **Process** next to the document to kick off background ingestion.
3. **Inspect** – Open the document view to see rendered pages, bounding box overlays, and extracted Markdown side-by-side.

### API Examples

```bash
# Upload a PDF
curl -X POST -F "file=@/path/to/document.pdf" http://localhost:8000/upload

# Start processing (replace {id} with the returned document id)
curl -X POST http://localhost:8000/process/{id}

# Retrieve page analysis
curl http://localhost:8000/pages/{page_id}/analysis
```

## Packaging & Release Workflow

Use the helper script to build and validate distribution artifacts:

```bash
python scripts/build_dist.py --bump patch
# optional: publish to TestPyPI / PyPI with twine upload dist/*
```

The script bumps the version (optional), cleans previous artifacts, runs `setup.py sdist bdist_wheel`, and executes `twine check` so we catch metadata issues before publication. See `docs/plans/publishing_checklist.md` for the full release checklist.
