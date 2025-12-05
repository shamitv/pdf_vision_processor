# Plan: Page Re-processing for Partial Runs

## Problem Statement
- Full-document runs can finish with partial success (e.g., 70/100 pages processed). Missing/failed pages lack analysis and overlays, degrading UX and downstream exports.
- We need a targeted re-processing path to retry only the failed/missing pages without rerunning the entire document.

## Goals
- Detect and surface incomplete processing for any document version.
- Allow operators to select and re-process only the failed/missing pages.
- Keep successful pages untouched, avoid duplicate records, and make the flow idempotent.
- Preserve auditability: log attempts, outcomes, and timestamps for each re-processed page.

## Functional Requirements
1. **Detection & Surfacing**
   - Maintain per-page processing status (e.g., `pending`, `processing`, `succeeded`, `failed`).
   - Compute per-version rollups (e.g., `pages_total=100`, `pages_succeeded=70`, `pages_failed=30`).
   - Expose the rollup and the list of failed page numbers/ids via API and UI.
2. **Re-process Trigger**
   - Operator can re-process all failed pages or a selected subset.
   - Avoid re-processing pages already in `succeeded` state unless explicitly forced.
   - Support retry limits/backoff to prevent hot-looping on persistent failures.
   - **Page Processing Retry Logic**: Implement a `max-retry` mechanism (default 3) for the LLM analysis step to handle transient failures during both initial processing and re-processing.
   - **Coverage for Untried Pages**: The re-processing logic generally targets "failed" pages, but must also pick up "pending" or "untried" pages (e.g., if a previous run crashed midway).
3. **Idempotency & Consistency**
   - Re-processing a page replaces or supersedes its prior failed analysis/overlay records without duplication.
   - Concurrency-safe: two overlapping reprocess requests should not double-run the same page.
4. **Audit & Observability**
   - Log reprocess requests and outcomes per page (success/failure, error messages, durations).
   - Optional metrics: count of retries, last retry timestamp, last error cause.

## Proposed Flow
1. **Post-run Evaluation**
   - After a document version run, mark each page with its final status and record errors for failures.
   - Summarize counts in `DocumentVersion` (or equivalent) for quick UI display.
2. **UI Surfacing**
   - On the document detail page, show a banner/card when `pages_failed > 0`, e.g., "70/100 processed; 30 failed." with a CTA "Re-process failed pages".
   - Provide a table/list of failed pages with checkboxes and a bulk-select option.
3. **Trigger**
   - User selects pages → clicks "Re-process" → frontend calls a new API endpoint with the selected page IDs/numbers.
   - Backend enqueues these pages for processing (same pipeline used in initial run) and immediately returns an acknowledgement.
4. **Execution**
   - Processing worker picks up pages, runs the normal per-page pipeline (LLM call, overlay, persistence) but skips document-wide steps (e.g., PDF-to-images) if assets already exist.
   - On success: update page status to `succeeded`, replace analysis/overlay artifacts, clear last error.
   - On failure: increment retry count, capture error, keep status `failed`.
5. **Progress & Completion**
   - UI periodically polls (or uses websocket/SSE if available) for updated statuses until all targeted pages reach a terminal state.
   - When all pages are `succeeded`, clear the failure banner; otherwise show remaining failed pages.

## Backend Changes
- **Data Model**
  - Ensure `Page` has a `processing_status` enum + `last_error`, `retry_count`, `last_attempt_at`.
  - `DocumentVersion` rollups: `pages_total`, `pages_succeeded`, `pages_failed`, `pages_pending`.
- **API**
  - `GET /documents/{doc_id}/versions/{version}/pages?status=failed` to list failed pages.
  - `POST /documents/{doc_id}/versions/{version}/reprocess` with body `{ page_numbers: [..] }` (or page IDs) to enqueue retries.
  - Responses include counts so the UI can display "70/100" and the failed page list.
- **Processor**
  - Add a "retry mode" path that:
    - Skips PDF→image conversion when assets exist.
    - Reuses the existing per-page pipeline; ensures idempotent writes (update existing analysis/overlay rows/files).
    - **Retry Wrapper**: In `analyze_page_with_llm`, wrap the API call in a loop with `max_retries` (default 3). 
    - **Handling Partial Runs**: Ensure the "reprocess" identifier can select pages that are effectively "missing" (no analysis record) in addition to those marked "failed".
    - Guards against concurrent reprocessing of the same page (e.g., DB row-level lock or in-flight flag).
  - Respect retry policies (max attempts/backoff). Persist attempt metadata.
- **Tasking/Queueing** (if applicable)
  - If a queue exists, enqueue one job per page with doc/version/page identifiers.
  - If synchronous, process pages sequentially but still update statuses incrementally for UI visibility.

## Frontend Updates
- **Document Detail Page (`document.html` + `app.js`)**
  - Display processing summary counts for the active version.
  - Show failed pages with checkboxes and a "Re-process selected" button; include a "Select all failed" option.
  - Show per-page status badges and last error snippet/tooltips for failed pages.
  - Poll the API after triggering retries to update progress in place.
- **Styling (`static/style.css`)**
  - Add styles for status badges (succeeded/failed/pending/processing) and the reprocess banner/CTA.

## Observability & Logging
- Log reprocess requests (who triggered, when, pages targeted, counts).
- Log per-page retry attempts with status, latency, and error message for failures.
- Add metrics if available: `reprocess_attempts`, `reprocess_success`, `reprocess_failure` per page/version.

## Testing
- Unit: processor retry path updates statuses correctly; idempotent write behavior; retry limit enforcement.
- API: endpoints return correct counts and respect filtering; reprocess request enqueues only failed pages.
- UI: selecting failed pages triggers API call; statuses refresh and reflect completion/failure; banner hides when all pages succeed.
- Integration/manual: simulate a run with deliberate failures (e.g., 30/100) and verify only those 30 get retried and resolved.
- **Specific Test Case**:
  - Test with **Document ID 5, Version ID 9** via the UI.
  - specifically verify pages **58, 62, 64, 76** which previously failed.
  - Verify that pages after 76 (which were likely not tried) are also picked up and processed correctly.

## Rollout Notes
- Backfill not required, but consider initializing legacy pages with `processing_status` = `succeeded` where analysis exists, else `failed`.
- Communicate new operator flow: how to trigger reprocess and where to monitor progress.
- Guardrails: cap retries per page to avoid runaway costs; surface clear errors for persistent failures.
