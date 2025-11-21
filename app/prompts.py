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
Note: box_2d should be normalized coordinates (0-999).
Ensure the response is valid JSON.
"""
