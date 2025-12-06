async function processDocument(id) {
    try {
        const response = await fetch(`/process/${id}`, { method: 'POST' });
        if (response.ok) {
            location.reload();
        } else {
            alert('Failed to start processing');
        }
    } catch (e) {
        console.error(e);
        alert('Error starting processing');
    }
}

document.getElementById('uploadForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const fileInput = document.getElementById('pdfFile');
    const file = fileInput.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        if (response.ok) {
            location.reload();
        } else {
            alert('Upload failed');
        }
    } catch (e) {
        console.error(e);
        alert('Error uploading file');
    }
});

// Shared state for page selection and overlay context
const selectionState = {
    currentPageNumber: null,
    currentPageId: null,
    maxPage: 0 // Will be hydrated on DOMContentLoaded
};

const overlayContext = {
    pageId: null,
    baseImageSrc: null
};

let pageStatusPoller = null;

function updateUrlWithPage(pageNumber) {
    const url = new URL(window.location.href);
    url.searchParams.set('page', pageNumber);
    window.history.replaceState({}, '', url);
}

function setActivePageLink(pageNumber) {
    document.querySelectorAll('.page-link-item').forEach(link => {
        const isActive = parseInt(link.dataset.pageNumber, 10) === pageNumber;
        link.classList.toggle('active', isActive);
    });
}

function syncControls(pageNumber) {
    const dropdown = document.getElementById('pageSelect');
    if (dropdown) {
        dropdown.value = String(pageNumber);
        // Fallback: if value didn't stick (e.g. type mismatch), try forcing it
        if (dropdown.value !== String(pageNumber)) {
            console.warn(`Failed to set dropdown value to ${pageNumber}`);
        }
    }

    const countLabel = document.getElementById('pageCountLabel');
    if (countLabel && selectionState.maxPage) {
        countLabel.textContent = `of ${selectionState.maxPage}`;
    }

    const prevBtn = document.getElementById('prevPageBtn');
    const nextBtn = document.getElementById('nextPageBtn');
    if (prevBtn) prevBtn.disabled = pageNumber <= 1;
    if (nextBtn) nextBtn.disabled = selectionState.maxPage ? pageNumber >= selectionState.maxPage : false;

    setActivePageLink(pageNumber);

    const controls = document.getElementById('pageControls');
    if (controls) controls.style.display = selectionState.maxPage > 0 ? 'flex' : 'none';
}

function updatePageMeta(link, pageData) {
    let metaEl = link.querySelector('.page-meta');
    if (!metaEl) {
        metaEl = document.createElement('small');
        metaEl.className = 'text-muted page-meta';
        metaEl.style.fontSize = '0.75em';
        link.querySelector('.d-flex')?.appendChild(metaEl);
    }

    const status = pageData.status || 'pending';
    const tokens = Number(pageData.token_count || 0);
    const latency = Number(pageData.llm_latency_seconds || 0);

    let text = status;
    if (status === 'completed' && tokens > 0) {
        text = `${latency.toFixed(1)}s | ${tokens}t`;
    } else if (status === 'failed') {
        text = 'failed';
    } else if (status === 'processing') {
        text = 'processing';
    } else if (status === 'pending') {
        text = 'pending';
    }

    metaEl.textContent = text;
}

function updatePageLinkFromStatus(pageData) {
    const link = document.querySelector(`.page-link-item[data-page-number="${pageData.page_number}"]`);
    if (!link) return;

    const isReady = pageData.status === 'completed';

    link.dataset.pageId = pageData.id || '';
    link.dataset.imagePath = pageData.image_path || '';
    link.dataset.latency = pageData.llm_latency_seconds ?? '';
    link.dataset.tokens = pageData.token_count ?? '';
    link.dataset.status = pageData.status || '';
    link.dataset.pending = isReady ? 'false' : 'true';

    link.classList.toggle('disabled', !isReady);
    link.classList.toggle('pending-page', !isReady);

    updatePageMeta(link, pageData);

    if (selectionState.currentPageNumber === pageData.page_number && selectionState.currentPageId === null && isReady) {
        handlePageSelection(pageData.page_number, { updateUrl: false });
    }
}

function updatePageListFromStatus(payload) {
    if (!payload) return;
    if (payload.page_count) {
        selectionState.maxPage = payload.page_count;
        if (selectionState.currentPageNumber) syncControls(selectionState.currentPageNumber);
    }

    const pages = payload.pages || [];
    pages.forEach(updatePageLinkFromStatus);
}

async function pollPageStatuses() {
    const meta = document.getElementById('pageData');
    if (!meta) return;
    const docId = meta.dataset.documentId;
    const versionId = meta.dataset.versionId;
    if (!docId || !versionId) return;

    try {
        const resp = await fetch(`/documents/${docId}/versions/${versionId}/pages/status`);
        if (!resp.ok) return;
        const data = await resp.json();
        updatePageListFromStatus(data);

        const versionDone = data.version_status && data.version_status !== 'processing';
        const pendingLeft = document.querySelector('.page-link-item[data-pending="true"]');
        if (versionDone && !pendingLeft && pageStatusPoller) {
            clearInterval(pageStatusPoller);
            pageStatusPoller = null;
        }
    } catch (err) {
        console.error('Failed polling page status', err);
    }
}

function startPageStatusPolling() {
    const meta = document.getElementById('pageData');
    if (!meta) return;
    const versionStatus = meta.dataset.versionStatus;
    const hasPending = !!document.querySelector('.page-link-item[data-pending="true"]');

    if (versionStatus !== 'processing' && !hasPending) return;

    if (pageStatusPoller) return;

    // kick off immediately then on interval
    pollPageStatuses();
    pageStatusPoller = setInterval(pollPageStatuses, 5000);
}

function showPendingPage(pageNumber) {
    const placeholder = document.getElementById('placeholder');
    const viewer = document.getElementById('viewer');
    if (viewer) viewer.style.display = 'none';
    if (placeholder) {
        placeholder.style.display = 'block';
        placeholder.textContent = `Page ${pageNumber} has not been processed yet.`;
    }
    resetOverlayPreview();
}

function handlePageSelection(pageNumber, { updateUrl = true } = {}) {
    const link = document.querySelector(`.page-link-item[data-page-number="${pageNumber}"]`);
    if (!link) return;

    const isPending = link.dataset.pending === 'true' || !link.dataset.pageId;
    const pageId = link.dataset.pageId;
    const imagePath = link.dataset.imagePath;
    const latency = link.dataset.latency;
    const tokens = link.dataset.tokens;

    selectionState.currentPageNumber = pageNumber;
    selectionState.currentPageId = isPending ? null : pageId;

    syncControls(pageNumber);
    if (updateUrl) updateUrlWithPage(pageNumber);

    if (isPending) {
        showPendingPage(pageNumber);
        return;
    }

    loadPage(pageId, pageNumber, imagePath, latency, tokens);
}

function hydrateInitialPageSelection() {
    const url = new URL(window.location.href);
    const requestedPage = parseInt(url.searchParams.get('page') || '0', 10);
    const firstLink = document.querySelector('.page-link-item');
    const fallbackPage = firstLink ? parseInt(firstLink.dataset.pageNumber, 10) : null;
    const initialPage = !isNaN(requestedPage) && requestedPage > 0 ? requestedPage : fallbackPage;
    if (initialPage) handlePageSelection(initialPage, { updateUrl: !!requestedPage });
}

// Event delegation for page links
document.getElementById('pageList')?.addEventListener('click', (e) => {
    const link = e.target.closest('.page-link-item');
    if (link) {
        e.preventDefault();
        const pageNum = parseInt(link.dataset.pageNumber, 10);
        handlePageSelection(pageNum);
    }
});

async function loadPage(pageId, pageNum, imagePath, latency, tokens) {
    const placeholder = document.getElementById('placeholder');
    const viewer = document.getElementById('viewer');
    if (placeholder) placeholder.style.display = 'none';
    if (viewer) viewer.style.display = 'flex';

    // Update image
    // Resolve filesystem or DB image paths into the mounted '/data' URL.
    // Common stored formats:
    // - Absolute filesystem: '/Users/.../data/images/...'
    // - Relative DB path: 'data/images/...'
    // We mount the app's data directory at '/data', so prefer the '/data/...' URL.
    const img = document.getElementById('pageImage');
    let resolvedSrc = imagePath || '';
    // If the stored path contains '/data/', use that suffix as the URL root
    const dataIdx = resolvedSrc.indexOf('/data/');
    if (dataIdx !== -1) {
        resolvedSrc = resolvedSrc.substring(dataIdx);
    } else if (resolvedSrc.startsWith('data/')) {
        // relative path stored as 'data/...' -> prepend '/'
        resolvedSrc = '/' + resolvedSrc;
    } else if (!resolvedSrc.startsWith('/')) {
        // fallback: make it an absolute URL path
        resolvedSrc = '/' + resolvedSrc;
    }
    img.src = resolvedSrc;

    // Clear overlays and markdown
    const overlays = document.getElementById('overlays');
    overlays.innerHTML = '';
    document.getElementById('markdownContent').textContent = 'Loading...';

    // Hide bbox info panel
    document.getElementById('bboxInfo').style.display = 'none';

    overlayContext.pageId = pageId;
    overlayContext.baseImageSrc = resolvedSrc;
    resetOverlayPreview();

    // Fetch analysis
    try {
        const response = await fetch(`/pages/${pageId}/analysis`);
        if (response.ok) {
            const data = await response.json();
            document.getElementById('markdownContent').textContent = data.markdown_text || 'No markdown text found.';

            if (data.raw_json) {
                const analysis = JSON.parse(data.raw_json);
                renderOverlays(analysis.elements);
                const overlayToggle = document.getElementById('overlayToggle');
                if (overlayToggle?.open) {
                    loadOverlayPreview(pageId, resolvedSrc);
                }
            }
        } else {
            document.getElementById('markdownContent').textContent = 'Analysis not available yet.';
        }
    } catch (e) {
        console.error(e);
        document.getElementById('markdownContent').textContent = 'Error loading analysis.';
    }
}

function renderOverlays(elements) {
    const container = document.getElementById('imageContainer');
    const overlays = document.getElementById('overlays');
    const img = document.getElementById('pageImage');

    if (!elements) return;

    const clampPercent = (value) => Math.min(100, Math.max(0, value));

    // Function to render boxes once we have image dimensions
    const renderBoxes = () => {
        // Clear any existing overlays
        overlays.innerHTML = '';

        // Get the natural (original) dimensions of the image
        const imageWidth = img.naturalWidth;
        const imageHeight = img.naturalHeight;

        if (!imageWidth || !imageHeight) {
            console.warn('Image dimensions not available yet');
            return;
        }

        elements.forEach((el, index) => {
            if (!el.box_2d) return;

            const [xmin, ymin, xmax, ymax] = el.box_2d;

            const div = document.createElement('div');
            div.className = 'bbox';
            div.dataset.elementIndex = index;

            // Decide which scale to use for the coordinates.
            // Many LLM responses normalise to a 0-999 grid (previously 0-1000).
            // HEURISTIC COMPATIBILITY: Treat 0-1000 as 0-999.
            let normalizer = 'thousand';
            if (xmax <= 1 && ymax <= 1) {
                normalizer = 'unit';
            } else if (xmax > 1000 || ymax > 1000) {
                normalizer = 'pixels';
            }

            const toRelativeX = (value) => {
                if (normalizer === 'unit') return value;
                if (normalizer === 'thousand') return value / 999;
                return value / imageWidth;
            };

            const toRelativeY = (value) => {
                if (normalizer === 'unit') return value;
                if (normalizer === 'thousand') return value / 999;
                return value / imageHeight;
            };

            const topPctRaw = toRelativeY(ymin) * 100;
            const bottomPctRaw = toRelativeY(ymax) * 100;
            const leftPctRaw = toRelativeX(xmin) * 100;
            const rightPctRaw = toRelativeX(xmax) * 100;

            const topPct = clampPercent(Math.min(topPctRaw, bottomPctRaw));
            const bottomPct = clampPercent(Math.max(topPctRaw, bottomPctRaw));
            const leftPct = clampPercent(Math.min(leftPctRaw, rightPctRaw));
            const rightPct = clampPercent(Math.max(leftPctRaw, rightPctRaw));

            const widthPct = Math.max(0, rightPct - leftPct);
            const heightPct = Math.max(0, bottomPct - topPct);

            div.style.top = `${topPct}%`;
            div.style.left = `${leftPct}%`;
            div.style.height = `${heightPct}%`;
            div.style.width = `${widthPct}%`;

            const convertToPixels = (value, axisLength) => {
                if (normalizer === 'unit') return value * axisLength;
                if (normalizer === 'thousand') return (value / 999) * axisLength;
                return value;
            };

            let translatedXmin = convertToPixels(xmin, imageWidth);
            let translatedXmax = convertToPixels(xmax, imageWidth);
            let translatedYmin = convertToPixels(ymin, imageHeight);
            let translatedYmax = convertToPixels(ymax, imageHeight);

            translatedXmin = Math.max(0, Math.min(imageWidth, translatedXmin));
            translatedXmax = Math.max(0, Math.min(imageWidth, translatedXmax));
            translatedYmin = Math.max(0, Math.min(imageHeight, translatedYmin));
            translatedYmax = Math.max(0, Math.min(imageHeight, translatedYmax));

            if (translatedXmin > translatedXmax) {
                [translatedXmin, translatedXmax] = [translatedXmax, translatedXmin];
            }
            if (translatedYmin > translatedYmax) {
                [translatedYmin, translatedYmax] = [translatedYmax, translatedYmin];
            }

            const translatedWidth = Math.max(0, Math.round(translatedXmax - translatedXmin));
            const translatedHeight = Math.max(0, Math.round(translatedYmax - translatedYmin));

            el._bboxMeta = {
                normalizer,
                rawBox: { xmin, ymin, xmax, ymax },
                rawDimensions: {
                    width: xmax - xmin,
                    height: ymax - ymin
                },
                translatedBox: {
                    xmin: Math.round(translatedXmin),
                    ymin: Math.round(translatedYmin),
                    xmax: Math.round(translatedXmax),
                    ymax: Math.round(translatedYmax)
                },
                translatedDimensions: {
                    width: translatedWidth,
                    height: translatedHeight
                }
            };

            // Color coding
            if (el.type === 'heading') div.style.borderColor = 'blue';
            if (el.type === 'table') div.style.borderColor = 'green';
            if (el.type === 'image') div.style.borderColor = 'orange';

            div.title = `${el.type}: ${el.text ? el.text.substring(0, 50) + '...' : ''}`;

            // Add click handler
            div.addEventListener('click', (e) => {
                e.stopPropagation();
                showBboxInfo(el, index);

                // Visual feedback - highlight selected bbox
                document.querySelectorAll('.bbox').forEach(b => b.classList.remove('bbox-selected'));
                div.classList.add('bbox-selected');
            });

            overlays.appendChild(div);
        });
    };

    // If image is already loaded, render immediately
    if (img.complete && img.naturalWidth) {
        renderBoxes();
    } else {
        // Wait for image to load
        img.onload = renderBoxes;
    }
}

function resetOverlayPreview() {
    const overlayCard = document.getElementById('overlayPreviewCard');
    const overlayImage = document.getElementById('overlayPreviewImage');
    const overlayPlaceholder = document.getElementById('overlayPreviewPlaceholder');

    if (overlayCard) overlayCard.style.display = 'none';
    if (overlayImage) {
        overlayImage.src = '';
        overlayImage.onload = null;
        overlayImage.onerror = null;
    }
    if (overlayPlaceholder) {
        overlayPlaceholder.style.display = 'block';
        overlayPlaceholder.textContent = 'Select a page and open the overlay preview to generate the rendered image.';
    }
}

function loadOverlayPreview(pageId, baseImageSrc) {
    const overlayCard = document.getElementById('overlayPreviewCard');
    const overlayImage = document.getElementById('overlayPreviewImage');
    const overlayPlaceholder = document.getElementById('overlayPreviewPlaceholder');

    if (!overlayImage) return;

    if (overlayPlaceholder) {
        overlayPlaceholder.style.display = 'block';
        overlayPlaceholder.textContent = 'Generating overlay preview image...';
    }

    const timestamp = Date.now();

    overlayImage.onload = () => {
        if (overlayCard) overlayCard.style.display = 'block';
        if (overlayPlaceholder) overlayPlaceholder.style.display = 'none';
    };

    overlayImage.onerror = () => {
        // If the direct overlay file isn't available, fall back to the overlay-generation route
        if (!overlayImage.dataset.fallback) {
            overlayImage.dataset.fallback = '1';
            overlayImage.src = `/pages/${pageId}/overlay-image?t=${timestamp}`;
            return;
        }
        if (overlayCard) overlayCard.style.display = 'none';
        if (overlayPlaceholder) {
            overlayPlaceholder.style.display = 'block';
            overlayPlaceholder.textContent = 'Overlay preview not available for this page.';
        }
    };

    // Prefer the cached overlay image next to the base image (e.g. '/data/.../page_001_overlay_v4.png')
    if (baseImageSrc) {
        // Try to append the overlay suffix before the extension
        const m = baseImageSrc.match(/(.*)\.(png|jpg|jpeg)$/i);
        if (m) {
            const overlayCandidate = `${m[1]}_overlay_v4.${m[2]}?t=${timestamp}`;
            overlayImage.src = overlayCandidate;
            return;
        }
    }

    // Fallback to the server route which will generate/return the overlay
    overlayImage.src = `/pages/${pageId}/overlay-image?t=${timestamp}`;
}

function showBboxInfo(element, index) {
    const infoPanel = document.getElementById('bboxInfo');

    // Populate the info panel
    document.getElementById('bboxType').textContent = element.type || 'unknown';
    document.getElementById('bboxId').textContent = element.id || `element-${index}`;
    document.getElementById('bboxRawValues').textContent = '';
    document.getElementById('bboxTranslatedValues').textContent = '';
    document.getElementById('bboxCoordinateSpace').textContent = '';
    document.getElementById('bboxDimensions').textContent = '';

    if (element.box_2d) {
        const [xmin, ymin, xmax, ymax] = element.box_2d;
        const previewImg = document.getElementById('pageImage');
        const imageWidth = previewImg?.naturalWidth || 0;
        const imageHeight = previewImg?.naturalHeight || 0;

        let normalizer = 'pixels';
        let translatedXmin = xmin;
        let translatedYmin = ymin;
        let translatedXmax = xmax;
        let translatedYmax = ymax;

        if (imageWidth && imageHeight) {
            if (xmax <= 1 && ymax <= 1) {
                normalizer = 'unit (0-1)';
                translatedXmin = xmin * imageWidth;
                translatedXmax = xmax * imageWidth;
                translatedYmin = ymin * imageHeight;
                translatedYmax = ymax * imageHeight;
            } else if (xmax > 1000 || ymax > 1000) {
                normalizer = 'pixels';
                // Already in pixels, but we might want to clamp
                translatedXmin = xmin;
                translatedXmax = xmax;
                translatedYmin = ymin;
                translatedYmax = ymax;
            } else {
                normalizer = 'thousand (0-999)';
                translatedXmin = (xmin / 999) * imageWidth;
                translatedXmax = (xmax / 999) * imageWidth;
                translatedYmin = (ymin / 999) * imageHeight;
                translatedYmax = (ymax / 999) * imageHeight;
            }
        }

        translatedXmin = Math.round(Math.max(0, Math.min(imageWidth || translatedXmin, translatedXmin)));
        translatedXmax = Math.round(Math.max(0, Math.min(imageWidth || translatedXmax, translatedXmax)));
        translatedYmin = Math.round(Math.max(0, Math.min(imageHeight || translatedYmin, translatedYmin)));
        translatedYmax = Math.round(Math.max(0, Math.min(imageHeight || translatedYmax, translatedYmax)));

        if (translatedXmin > translatedXmax) {
            [translatedXmin, translatedXmax] = [translatedXmax, translatedXmin];
        }
        if (translatedYmin > translatedYmax) {
            [translatedYmin, translatedYmax] = [translatedYmax, translatedYmin];
        }

        document.getElementById('bboxXmin').textContent = translatedXmin;
        document.getElementById('bboxYmin').textContent = translatedYmin;
        document.getElementById('bboxXmax').textContent = translatedXmax;
        document.getElementById('bboxYmax').textContent = translatedYmax;

        const rawValues = `[${xmin}, ${ymin}, ${xmax}, ${ymax}]`;
        const translatedValues = imageWidth && imageHeight
            ? `[${translatedXmin}, ${translatedYmin}, ${translatedXmax}, ${translatedYmax}]`
            : 'N/A';

        const rawWidth = xmax - xmin;
        const rawHeight = ymax - ymin;
        const translatedWidth = imageWidth && imageHeight ? translatedXmax - translatedXmin : 'N/A';
        const translatedHeight = imageWidth && imageHeight ? translatedYmax - translatedYmin : 'N/A';

        document.getElementById('bboxRawValues').textContent = rawValues;
        document.getElementById('bboxTranslatedValues').textContent = translatedValues;
        document.getElementById('bboxCoordinateSpace').textContent = imageWidth && imageHeight ? normalizer : 'pixels (assumed)';
        document.getElementById('bboxDimensions').textContent = imageWidth && imageHeight
            ? `Raw: ${rawWidth} × ${rawHeight} (${normalizer}) | Translated: ${translatedWidth} × ${translatedHeight} px`
            : `Raw: ${rawWidth} × ${rawHeight}`;
    }

    document.getElementById('bboxText').textContent = element.text || 'No text content';

    // Show the panel with animation
    infoPanel.style.display = 'block';

    // Smooth scroll to the info panel
    setTimeout(() => {
        infoPanel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 100);
}

function closeBboxInfo() {
    document.getElementById('bboxInfo').style.display = 'none';
    // Remove selection highlight
    document.querySelectorAll('.bbox').forEach(b => b.classList.remove('bbox-selected'));
}



// Check for failures and populate list
async function checkFailures() {
    const versionSelect = document.getElementById('versionSelect');
    if (!versionSelect) return;

    // Parse version ID from URL or select
    const urlParams = new URLSearchParams(window.location.search);
    const versionId = urlParams.get('version_id') || versionSelect.value;

    // Need document ID too... assume embedded in template or parse from URL
    // URL pattern: /documents/{id}
    const pathParts = window.location.pathname.split('/');
    const docId = pathParts[2]; // /documents/5 -> 5

    if (!docId || !versionId) return;

    try {
        const response = await fetch(`/documents/${docId}/versions/${versionId}/failures`);
        if (response.ok) {
            const failures = await response.json();
            const section = document.getElementById('failedPagesSection');
            const list = document.getElementById('failedPagesList');

            if (failures.length > 0) {
                section.style.display = 'block';
                list.innerHTML = failures.map(f => `
                    <div class="col-md-3 mb-2">
                        <div class="form-check">
                            <input class="form-check-input failed-page-checkbox" type="checkbox" value="${f.id}" id="fail-${f.id}" checked>
                            <label class="form-check-label" for="fail-${f.id}">
                                Page ${f.page_number}
                                <i class="bi bi-info-circle text-danger" title="${f.error_message}"></i>
                            </label>
                        </div>
                    </div>
                `).join('');
            } else {
                section.style.display = 'none';
            }
        }
    } catch (e) {
        console.error("Error checking failures:", e);
    }
}

async function reprocessSelectedPages() {
    const checkboxes = document.querySelectorAll('.failed-page-checkbox:checked');
    if (checkboxes.length === 0) {
        alert('Please select at least one page to re-process.');
        return;
    }

    const pageIds = Array.from(checkboxes).map(cb => parseInt(cb.value));

    const versionSelect = document.getElementById('versionSelect');
    const urlParams = new URLSearchParams(window.location.search);
    const versionId = urlParams.get('version_id') || versionSelect.value;
    const pathParts = window.location.pathname.split('/');
    const docId = pathParts[2];

    if (!confirm(`Re-process ${pageIds.length} pages?`)) return;

    try {
        const response = await fetch(`/documents/${docId}/versions/${versionId}/reprocess`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ page_ids: pageIds })
        });

        if (response.ok) {
            alert('Reprocessing started. Logs will update in the background. Refresh shortly to see results.');
            // Ideally reload or poll
            setTimeout(() => location.reload(), 2000);
        } else {
            alert('Failed to trigger reprocessing');
        }
    } catch (e) {
        console.error(e);
        alert('Error triggering reprocessing');
    }
}

function initNavigationControls() {
    const dropdown = document.getElementById('pageSelect');
    const prevBtn = document.getElementById('prevPageBtn');
    const nextBtn = document.getElementById('nextPageBtn');
    const overlayToggle = document.getElementById('overlayToggle');

    selectionState.maxPage = parseInt(dropdown?.dataset.maxPage || selectionState.maxPage || '0', 10) || selectionState.maxPage;

    dropdown?.addEventListener('change', (e) => {
        const value = parseInt(e.target.value, 10);
        if (!isNaN(value)) handlePageSelection(value);
    });

    prevBtn?.addEventListener('click', (e) => {
        e.preventDefault();
        if (selectionState.currentPageNumber > 1) {
            handlePageSelection(selectionState.currentPageNumber - 1);
        }
    });

    nextBtn?.addEventListener('click', (e) => {
        e.preventDefault();
        if (selectionState.maxPage && selectionState.currentPageNumber < selectionState.maxPage) {
            handlePageSelection(selectionState.currentPageNumber + 1);
        }
    });

    overlayToggle?.addEventListener('toggle', () => {
        if (overlayToggle.open && overlayContext.pageId) {
            loadOverlayPreview(overlayContext.pageId, overlayContext.baseImageSrc);
        }
    });
}

// Init
document.addEventListener('DOMContentLoaded', () => {
    initNavigationControls();
    hydrateInitialPageSelection();
    checkFailures();
    startPageStatusPolling();
});
