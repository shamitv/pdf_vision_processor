# Bounding Box Extraction Analysis

## Comparison: Notebook vs. Project

| Feature | Notebook Approach (`document_parsing.ipynb`) | Project Approach (`app/prompts.py`) |
| :--- | :--- | :--- |
| **Model** | Qwen2.5-VL | Vision LLM (e.g., GPT-4o) |
| **Output Format** | **HTML/Markdown**: Bounding boxes are embedded directly in the content string (e.g., `<div data-bbox="...">` or `<!-- Image (...) -->`). | **Structured JSON**: Bounding boxes are returned in a separate `elements` list, distinct from the `markdown` content. |
| **Coordinate Order** | `[x1, y1, x2, y2]` (Left, Top, Right, Bottom) | `[ymin, xmin, ymax, xmax]` (Top, Left, Bottom, Right) |
| **Coordinate Scale** | Normalized 0-1000 | Normalized 0-1000 |
| **Extraction Logic** | Parses HTML attributes or Regex matches Markdown comments. | Parses a JSON object. |

## Key Takeaway

The project uses a more structured **JSON-first approach** which separates the layout data (`elements`) from the content (`markdown`), whereas the notebook uses an **integrated approach** where layout data is embedded within the content representation itself.

## Updates Implemented

The project code has been updated to align the coordinate ordering with the notebook's approach:

*   **Coordinate Order**: Changed from `[ymin, xmin, ymax, xmax]` to `[xmin, ymin, xmax, ymax]`.
*   **Files Updated**:
    *   `app/prompts.py`: Prompt instructions updated.
    *   `app/static/app.js`: Frontend visualization logic updated.
    *   `docs/pdf_processing.md`: Documentation updated.
