PAGE_ANALYSIS_PROMPT = """
Analyze this page image. 
1. Extract the full text content in Markdown format.
2. Identify all layout elements (paragraphs, headings, tables, images) and provide their bounding boxes.

Special instructions for **Devanagari Hindustani / Karnatak music notation**:

- Treat any block that mainly contains swaras (Sa Re Ga Ma Pa Dha Ni or their Devanagari forms) or their variants as `type: "music_notation"` (unless it is clearly part of a table, in which case keep `type: "table"` but still preserve notation exactly).
- Preserve indications of **komal** and **teevra** notes exactly as printed:
  - Do not replace them with “flat” or “sharp”.
  - If a swara has a small sign, dot or extra stroke associated with komal/teevra, include that character exactly in the text. Do not drop it.
- Preserve **saptak** information:
  - If a swara has dots above or below (mandra/madhya/tara saptak notation), keep the dots or any combining marks exactly as visible.
  - If dots or strokes cannot be represented perfectly, describe them textually in parentheses, e.g. `सा (dot above)` or `नि (dot below)`, rather than omitting them.
- Preserve **meend** indications:
  - If a curved line connects two or more notes, treat that as part of the same `music_notation` element.
  - In the `text` field, describe it explicitly, e.g. `"सा –(meend)→ रे"` or `"meend between ग and म"`.
- Do not convert these notations to Western staff notation or Western note names.


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
