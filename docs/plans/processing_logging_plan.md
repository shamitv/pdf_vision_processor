# Processing Logging Plan

## Goals
- Persist step-by-step processing telemetry under `logs/processing` so investigations have a single timeline per document/version.
- Capture human-readable entries with the format `TIMESTAMP message`, where message uses key=value pairs for easy parsing.
- Surface major lifecycle events (start/finish, PDF conversion, LLM calls, overlays, persistence, failures).

## Implementation Steps
1. **Logger Configuration**
   - Create/get a module-level logger in `app/processor.py` (or shared logging helper).
   - Ensure the `logs` directory exists prior to configuring handlers.
   - Attach a `logging.FileHandler` (or `RotatingFileHandler` if size is a concern) targeting `logs/processing/doc_{document_id}_v{version}.log`.
   - Use `logging.Formatter("%(asctime)s %(message)s")` to satisfy the `Timestamp + message` requirement.

2. **Run Kickoff Entry**
   - Immediately after loading the `Document` from the DB, log: `doc=<id> pdf_name="<original_filename>" status=starting`.
   - Include the resolved version number once computed: `version=v{version_number}`.

3. **PDF Conversion Logging**
   - Before invoking `convert_pdf_to_images`, log: `doc=<id> version=v{version} step=pdf_to_images status=begin`.
   - After conversion, log pages produced and elapsed time: `... status=complete pages=<count> elapsed_seconds=<value>`.
   - On exceptions, log `status=error error="<message>"` before raising/handling.

4. **Per-Page Processing Logging**
   - When creating each `Page`, log: `doc=<id> version=v{version} page=<n> step=page_record status=created page_id=<id>`.
   - Prior to LLM invocation log: `... step=llm_request status=sent model=<LLM_MODEL>`.
   - After LLM response log success with latency and token metadata: `... step=llm_request status=complete latency_seconds=<value> tokens_total=<value>`.
   - If the LLM call fails, log `status=error` with the exception, then proceed with existing error handling.

5. **Overlay + Analysis Logging**
   - After overlay generation log either `status=complete` or `status=error` with details.
   - Once `PageAnalysis` is persisted, log: `step=analysis_persist status=complete analysis_id=<id> token_count=<value>`.

6. **Run Completion Logging**
   - At the end of `process_document`, log: `doc=<id> version=v{version} status=completed total_tokens=<value> total_elapsed_seconds=<value>`.
   - In the exception path, log `status=failed error="<message>"` before updating DB state.

7. **Helper Utility (Optional)**
   - Implement a small helper `log_step(doc_id, version, **fields)` to centralize string formatting so every message automatically starts with the timestamp from the handler.

8. **Documentation Update**
   - Add a short note to `README.md` or `docs/architecture.md` describing the existence and location of the new processing logs so operators know where to inspect run timelines.
