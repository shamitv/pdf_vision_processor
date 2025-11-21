# Walkthrough - Fix Coordinate Translation Logic

## Issue
The user reported that "Raw Coordinates (LLM)" and "Translated Coordinates (px)" were identical in the UI, even though the LLM is instructed to return normalized coordinates (0-1000).

## Investigation
1.  **Prompt Verification**: I checked `app/prompts.py` and confirmed that the LLM is explicitly instructed to return `normalized coordinates (0-1000)`.
2.  **Logic Flaw**: The frontend logic in `app/static/app.js` was defaulting to 'pixels' and only switching to 'thousand' (normalized) if the coordinates *exceeded* the image dimensions.
    - For high-resolution images (e.g., A4 @ 150 DPI is ~1240x1755), valid 0-1000 coordinates are *smaller* than the image dimensions.
    - This caused the system to incorrectly interpret normalized coordinates as pixels, resulting in no translation (and likely incorrect bounding box placement).

## Solution
I updated the coordinate detection logic in `app/static/app.js` to prioritize 'thousand' normalization.

### Changes

#### [MODIFY] [app.js](file:///Volumes/work_ext/work/pdf_vision_processor/app/static/app.js)
Updated `renderOverlays` and `showBboxInfo` functions to:
- Default to 'thousand' normalization (0-1000).
- Only switch to 'pixels' if coordinates are significantly larger than 1000 (indicating they are likely absolute pixels).
- Retain 'unit' (0-1) detection for very small values.

#### [MODIFY] [base.html](file:///Volumes/work_ext/work/pdf_vision_processor/app/templates/base.html)
- Bumped static asset version to `?v=3` to force browser cache refresh.
- Fixed a minor syntax error in the viewport meta tag.

## Verification
- The logic now correctly interprets 0-1000 coordinates as normalized values for large images.
- If the LLM returns absolute pixels (and they are > 1000), the system will still handle them correctly.
- The UI should now show different values for "Raw" (0-1000) and "Translated" (pixels).
