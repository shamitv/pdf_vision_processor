# Walkthrough - LLM Bounding Box Scale Migration (0-999)

## Request
The user requested a migration of the LLM bounding box scale from 0-1000 to 0-999 to avoid off-by-one errors and align with standard practices.

## Implementation
I updated the LLM prompt, server-side normalization logic, and client-side rendering to support the 0-999 scale.

### Changes

#### [MODIFY] [prompts.py](file:///Volumes/work_ext/work/pdf_vision_processor/app/prompts.py)
- Updated `PAGE_ANALYSIS_PROMPT` to explicitly request `box_2d` coordinates in the 0-999 range.

#### [MODIFY] [overlay.py](file:///Volumes/work_ext/work/pdf_vision_processor/app/utils/overlay.py)
- Defined `_NORM_MAX = 999`.
- Updated `_normalize_bbox` to use `_NORM_MAX` for normalization.
- **Heuristic Compatibility**: Implemented logic to treat all existing 0-1000 values as 0-999, accepting a negligible <0.1% shift to avoid database migration.
- Updated `_OVERLAY_VERSION` to `v4` to invalidate cached overlays.

#### [MODIFY] [app.js](file:///Volumes/work_ext/work/pdf_vision_processor/app/static/app.js)
- Updated `renderOverlays` and `showBboxInfo` to normalize using 999 instead of 1000.
- Updated detection logic to treat values <= 1000 as normalized 0-999 values.

#### [MODIFY] [base.html](file:///Volumes/work_ext/work/pdf_vision_processor/app/templates/base.html)
- Bumped static asset versions to `v4`.

## Verification
- **New Data**: Newly processed pages will have bounding boxes strictly within 0-999.
- **Legacy Data**: Existing pages with 0-1000 coordinates will be rendered correctly using the new logic, with a visually imperceptible shift.
- **UI**: The info panel now correctly identifies the coordinate space and shows translated pixel values.
