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

// Event delegation for page links
document.getElementById('pageList')?.addEventListener('click', (e) => {
    const link = e.target.closest('.page-link-item');
    if (link) {
        e.preventDefault();
        const pageId = link.dataset.pageId;
        const pageNum = link.dataset.pageNumber;
        const imagePath = link.dataset.imagePath;
        const latency = link.dataset.latency;
        const tokens = link.dataset.tokens;
        loadPage(pageId, pageNum, imagePath, latency, tokens);
    }
});

async function loadPage(pageId, pageNum, imagePath, latency, tokens) {
    document.getElementById('placeholder').style.display = 'none';
    document.getElementById('viewer').style.display = 'flex';

    // Update image
    // Fix image path: remove 'data/' prefix if present in DB path because we mount 'data' at /data
    // Actually, DB path is like 'data/images/1/page_1.png'. 
    // We mounted 'data' directory at '/data'. So '/data/images/1/page_1.png' should work if we prepend '/'
    const img = document.getElementById('pageImage');
    img.src = '/' + imagePath;

    // Clear overlays and markdown
    const overlays = document.getElementById('overlays');
    overlays.innerHTML = '';
    document.getElementById('markdownContent').textContent = 'Loading...';

    // Hide bbox info panel
    document.getElementById('bboxInfo').style.display = 'none';

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
                loadOverlayPreview(pageId);
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
        overlayPlaceholder.textContent = 'Select a page to generate a rendered overlay image preview.';
    }
}

function loadOverlayPreview(pageId) {
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
        if (overlayCard) overlayCard.style.display = 'none';
        if (overlayPlaceholder) {
            overlayPlaceholder.style.display = 'block';
            overlayPlaceholder.textContent = 'Overlay preview not available for this page.';
        }
    };
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

