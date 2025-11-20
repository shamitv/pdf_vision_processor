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
        loadPage(pageId, pageNum, imagePath);
    }
});

async function loadPage(pageId, pageNum, imagePath) {
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
            // Many LLM responses normalise to a 0-1000 grid rather than returning
            // absolute pixels, so detect that pattern and adjust on the fly.
            let normalizer = 'pixels';
            if (xmax <= 1 && ymax <= 1) {
                normalizer = 'unit';
            } else if (xmax > imageWidth || ymax > imageHeight) {
                normalizer = 'thousand';
            }

            const toRelativeX = (value) => {
                if (normalizer === 'unit') return value;
                if (normalizer === 'thousand') return value / 1000;
                return value / imageWidth;
            };

            const toRelativeY = (value) => {
                if (normalizer === 'unit') return value;
                if (normalizer === 'thousand') return value / 1000;
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

    if (element.box_2d) {
        const [xmin, ymin, xmax, ymax] = element.box_2d;
        document.getElementById('bboxXmin').textContent = xmin;
        document.getElementById('bboxYmin').textContent = ymin;
        document.getElementById('bboxXmax').textContent = xmax;
        document.getElementById('bboxYmax').textContent = ymax;

        const previewImg = document.getElementById('pageImage');
        const imageWidth = previewImg?.naturalWidth || 0;
        const imageHeight = previewImg?.naturalHeight || 0;

        let widthPx = xmax - xmin;
        let heightPx = ymax - ymin;

        if (imageWidth && imageHeight) {
            let normalizer = 'pixels';
            if (xmax <= 1 && ymax <= 1) {
                normalizer = 'unit';
            } else if (xmax > imageWidth || ymax > imageHeight) {
                normalizer = 'thousand';
            }

            if (normalizer === 'unit') {
                widthPx = Math.round((xmax - xmin) * imageWidth);
                heightPx = Math.round((ymax - ymin) * imageHeight);
            } else if (normalizer === 'thousand') {
                widthPx = Math.round(((xmax - xmin) / 1000) * imageWidth);
                heightPx = Math.round(((ymax - ymin) / 1000) * imageHeight);
            }
        }

        document.getElementById('bboxDimensions').textContent = `${widthPx} × ${heightPx} px`;
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

