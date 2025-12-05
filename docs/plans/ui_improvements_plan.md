# UI Improvement Plan

This plan addresses UI usability improvements requested for the document details view.

## Goals
1.  **Sidebar Visibility**: Ensure all pages are accessible in the sidebar, even if not yet processed or if the list is long.
2.  **Clean Layout**: Hide the debug "Overlay Preview Image" by default to reduce clutter.
3.  **Navigation**: multiple ways to navigate (Dropdown, Next/Prev buttons).

## Proposed Changes

### 1. Show All Pages in Sidebar
**Problem**: Currently, the sidebar might be cutting off pages (e.g., stopping at page 13) or not scrolling correctly.
**Solution**:
-   **CSS (responsive)**: Give `.page-list` a max-height based on actual header/footer sizes (e.g., `calc(100vh - var(--header-height) - 40px)`) and `overflow-y: auto`; add mobile/tablet breakpoints to avoid clipping.
-   **Render Logic**: Loop over `range(1, total_pages + 1)` (or all `Page` objects) to include pending pages as placeholders; visually distinguish pending pages (e.g., muted text, disabled click if no data) and show a "Not processed yet" message in the detail pane instead of blank content.

### 2. Hide "Overlay Preview Image" by default
**Problem**: The overlay image takes up vertical space and isn't always needed.
**Solution**:
-   Wrap the "Overlay Preview Image" section in a `<details>` element with a clear summary label (e.g., "Show overlay preview") or use a JS toggle.
-   Default collapsed; lazy-load the image on expand to save vertical space and network.
-   Ensure keyboard accessibility and focus states on the toggle.

### 3. Quick Page Selection (Dropdown)
**Problem**: Scrolling a long sidebar to find "Page 88" is tedious.
**Solution**:
-   Add a `<select>` dropdown near the top of the details pane (or sticky header) with options `Page 1..N`.
-   On change, trigger the same selection function used by the sidebar and update the canonical state (hash or query param) so refresh/deeplink keeps the selection.
-   Add `<label>` and `aria-label` for accessibility; ensure focus order is sensible.

### 4. Previous / Next Navigation
**Problem**: Users want to read sequentially without clicking back to the sidebar.
**Solution**:
-   Add **Previous** (`<`) and **Next** (`>`) buttons in the sticky header or as floating controls.
-   Buttons call the same selection function as the dropdown/sidebar and update the canonical state (hash/query).
-   Disable `Prev` on Page 1 and `Next` on Page N; support keyboard activation and `aria-label`s.

### 5. Single Source of Truth for Selection
**Problem**: Sidebar, dropdown, and Prev/Next can get out of sync.
**Solution**:
-   Use one state store (JS variable) and a single selector function to drive UI updates.
-   On load: read initial selection from URL hash/query or default to page 1; push changes back to URL for refresh/deeplink support.
-   Keep sidebar highlight, dropdown value, and detail pane in sync on every change.

## Implementation Steps
1.  **`document.html`**: Responsive `.page-list` height + overflow; placeholder styling for pending pages; add labeled page dropdown; add overlay `<details>` summary; add Prev/Next controls.
2.  **`app.js`**: Central selection function that updates sidebar, dropdown, detail pane, and URL hash/query; wire dropdown change, Prev/Next clicks, and sidebar clicks to this function; on load, hydrate state from URL or default.
3.  **Accessibility**: Labels/`aria-label`s for dropdown and buttons; focus states; ensure toggle is keyboard-operable; announce pending page state.
4.  **Lazy loading**: Defer overlay image load until expanded.
5.  **Testing**: Long doc (100+ pages) scroll behavior; mobile/tablet/desktop viewports; refresh/deeplink keeps selection; pending page UX; keyboard-only navigation; overlay toggle and lazy load.
