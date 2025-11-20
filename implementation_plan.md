# Implementation Plan - Document Versioning

## Goal Description
Add a feature to re-process a PDF, creating a new "version" of the processed document each time. This allows users to retry processing with different settings (e.g., updated prompts) or to recover from errors without losing previous history.

## Proposed Changes

### Database Schema (`app/models.py`)

1.  **New Model: `DocumentVersion`**
    *   `id` (PK)
    *   `document_id` (FK to `documents.id`)
    *   `version_number` (Integer)
    *   `created_at` (DateTime)
    *   `status` (Enum: PENDING, PROCESSING, COMPLETED, FAILED) - moved from Document
    *   `page_count` (Integer) - moved from Document
    *   `error_message` (String) - moved from Document

2.  **Update Model: `Page`**
    *   Add `document_version_id` (FK to `document_versions.id`)
    *   Make `document_id` nullable (or remove it if we reset DB). For backward compatibility/migration ease, we might keep it but rely on `document_version_id` for new logic. *Decision: We will reset the database to ensure a clean schema.*

3.  **Update Model: `Document`**
    *   Add relationship `versions` (One-to-Many with `DocumentVersion`).
    *   `status`, `page_count`, `error_message` on `Document` can remain as "latest" cache or be removed. *Decision: Remove them to avoid single source of truth issues.*

### Processing Logic (`app/processor.py`)

1.  **`process_document`**
    *   Accept `document_id`.
    *   Determine new version number: `max(version_number) + 1` or `1`.
    *   Create `DocumentVersion` record.
    *   Create directory `data/images/{doc_id}/v{version}/`.
    *   Convert PDF to images (store in new dir).
    *   Create `Page` records linked to `DocumentVersion`.
    *   Run LLM analysis.
    *   Update `DocumentVersion` status.

### API (`app/routes.py`)

1.  **`POST /process/{document_id}`**
    *   Trigger processing for a new version.
2.  **`GET /documents/{document_id}`**
    *   Return document details including a list of versions.
3.  **`GET /documents/{document_id}/versions/{version_id}`** (Optional or part of main view)
    *   We might just update the main document view to take a query param `?version=X`.

### UI (`app/templates/document.html`)

1.  Add a "Version" selector (dropdown).
2.  Add a "Re-process" button.
3.  Update view to display data for the selected version.

## Verification Plan

### Automated Tests
*   None (Manual verification as per project style).

### Manual Verification
1.  Upload a PDF.
2.  Process it (Version 1).
3.  View results.
4.  Click "Re-process".
5.  Verify Version 2 is created and processing starts.
6.  Verify images are stored in `v2` directory.
7.  Switch between Version 1 and Version 2 in UI.
