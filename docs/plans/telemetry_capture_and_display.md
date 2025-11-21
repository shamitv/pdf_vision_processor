# Plan: Capture Telemetry During Processing and Surface in UI

## Objective
Collect detailed processing telemetry (timings and token usage) for each document version and expose these metrics in both per-page views and the documents landing page. No backfill is required for existing data; the telemetry system should activate for new processing runs only.

## Telemetry Requirements

1. **Timing Metrics**
   - PDF-to-image conversion duration (per document version).
   - Per-page LLM response time (request → response).
   - Post-processing time for each page (JSON parsing, overlay generation, DB persistence).

2. **Token Usage**
   - Record total tokens consumed per page (prompt + completion if available from the LLM response metadata).

## Database & Models

### Changes
- Extend `DocumentVersion`:
  - Fields to store aggregate timings (e.g., total PDF conversion time, total processing time).
  - Optional JSON/structured column to summarise telemetry per page.
- Extend `Page` or create new table `PageTelemetry` to capture per-page metrics:
  - `page_id` (FK).
  - `llm_latency_ms`, `post_process_ms`, `token_count`, `created_at`.
- Ensure schema migrations (Alembic or manual migrations) include defaults so existing rows remain valid.

### Storage Strategy
- Capture metrics within `process_document` pipeline:
  - Timestamp start/end of each step.
  - Access token usage from the LLM API response (may require enabling verbose response format).
  - Persist telemetry records immediately after each page is processed.

## Backend API

1. **Capture**
   - Update `processor.py` to gather timings using `time.perf_counter()` or `datetime.now()` deltas.
   - Modify `analyze_page_with_llm` to return latency and tokens.

2. **Serve**
   - Extend `/pages/{page_id}/analysis` endpoint to include telemetry payload (either nested or separate call).
   - Create a new endpoint `/documents/{document_id}/telemetry` if needed for aggregate data (optional if included in existing responses).

## Front-End Updates

1. **Document Landing Page** (`index.html` template)
   - Add a telemetry summary section with one row per document version:
     - Conversion time.
     - Average page processing time.
     - Total tokens consumed.
   - Provide status badges for missing telemetry (e.g., "telemetry unavailable" for old versions).

2. **Document Detail Page** (`document.html` + `app.js`)
   - Extend page list panel or info card to show per-page stats:
     - LLM response time.
     - Post-processing time.
     - Token count.
   - Consider a collapsible or tooltip to avoid clutter.

3. **Styling**
   - Update `style.css` to format telemetry tables/cards.
   - Use consistent color coding for timing vs token metrics.

## Testing & Validation

- Unit tests (where feasible) to ensure telemetry fields populate correctly when mocked LLM responses are used.
- Manual QA: Process a sample PDF and verify timings increase monotonically with expected ranges.
- Check UI displays graceful fallbacks when telemetry is missing (existing documents).

## Deployment Notes

- No backfill required; telemetry applies to new processing runs only.
- Ensure migrations run before deploying updated processing pipeline.
- Update documentation (README, walkthrough) to describe telemetry availability and how to interpret metrics.

## Open Questions / Follow-Up

- Do we need to expose cumulative token usage per document version vs per page only?
- Should telemetry be exportable (CSV/JSON) from the UI?
- Consider log-level telemetry for deeper diagnostics (log files vs DB storage) if needed later.
