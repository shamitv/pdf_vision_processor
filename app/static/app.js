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

    // Fetch analysis
    try {
        const response = await fetch(`/pages/${pageId}/analysis`);
        if (response.ok) {
            const data = await response.json();
            document.getElementById('markdownContent').textContent = data.markdown_text || 'No markdown text found.';

            if (data.raw_json) {
                const analysis = JSON.parse(data.raw_json);
                renderOverlays(analysis.elements);
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

            // Convert absolute pixel coordinates to percentage
            // box_2d contains absolute pixel coordinates from the original image
            div.style.top = ((ymin / imageHeight) * 100) + '%';
            div.style.left = ((xmin / imageWidth) * 100) + '%';
            div.style.height = (((ymax - ymin) / imageHeight) * 100) + '%';
            div.style.width = (((xmax - xmin) / imageWidth) * 100) + '%';

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

        const width = xmax - xmin;
        const height = ymax - ymin;
        document.getElementById('bboxDimensions').textContent = `${width} × ${height} px`;
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

