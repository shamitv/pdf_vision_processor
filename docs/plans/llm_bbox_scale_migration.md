# Plan: Transition LLM Bounding Boxes to 0–999 Scale

## Goal
Adopt a 0–999 normalized coordinate scale for all LLM-generated bounding boxes to remove ambiguity at the upper bound (currently 0–1000) and align UI, overlay rendering, and downstream calculations with the new convention.

## Drivers
- Avoid off-by-one ambiguity at the 1000 bound when converting to pixel space.
- Keep scaling math consistent across client, server, and stored artifacts.
- Ensure previously processed data is either migrated or safely interpreted.

## Proposed Phases

### 1. Specification & Prompt Updates
- [ ] Define and document the 0–999 contract (inclusive) for `box_2d` values.
- [ ] Update `PAGE_ANALYSIS_PROMPT` to instruct the LLM to emit `box_2d` coordinates between 0 and 999.
- [ ] Add prompt acceptance criteria (examples) to avoid regression back to 0–1000.

### 2. Processing Pipeline Changes
- [ ] Adjust normalization helpers (`app/utils/overlay.py`, any other scaling helpers) to treat values `<= 999` as normalized inputs.
- [ ] Introduce constants for upper bounds (e.g., `NORM_MAX = 999`) to keep logic centralized.
- [ ] Update overlay caching key (suffix) to invalidate previously generated PNGs.
- [ ] Ensure `convert_pdf_to_images` and analysis storage remain unaffected.

### 3. Front-End Rendering
- [ ] Update `app/static/app.js` normalization logic (`renderOverlays`, `showBboxInfo`) to use the new `NORM_MAX` constant.
- [ ] Surface the scale ("0–999") in the info panel to help debugging.
- [ ] Bump static asset version in `app/templates/base.html` after changes.

### 4. Backfill / Compatibility Handling
- [ ] **Strategy: Heuristic Compatibility**. Treat all existing `box_2d` values as if they were already 0–999.
  - The difference between `x/1000` and `x/999` is < 0.1%, which is visually negligible (less than 1px on most screens).
  - No database migration or versioning column is required.
  - Legacy data will simply be rendered with the new normalization logic.
- [ ] Document this decision in the codebase (e.g., in `overlay.py` comments).

### 5. Validation & QA
- [ ] Add unit tests for `_normalize_bbox` (server) and a small Jest-style test for the client normalization helper (optional, via tooling).
- [ ] Create regression fixtures (sample LLM responses) for 0–999 and legacy 0–1000 inputs.
- [ ] Manually verify bounding boxes on a representative PDF (tables, headings, images) before rollout.

### 6. Deployment & Communication
- [ ] Update `walkthrough.md` and project README with the new scale convention.
- [ ] Note the change in release notes / changelog.
- [ ] Monitor first processed documents post-deployment for alignment issues.



## Definition of Done
- All code paths expect and correctly handle 0–999 bounding boxes.
- UI and overlay imagery reflect the new scale with no visual misalignment.
- Documentation updated and stakeholders aware of the change.
