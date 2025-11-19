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

    // Wait for image to load to get natural dimensions? 
    // Actually, if we use percentage based positioning, we don't need natural dimensions if the box_2d is normalized.
    // The prompt asked for normalized 0-1000 coordinates.
    
    elements.forEach(el => {
        if (!el.box_2d) return;
        
        const [ymin, xmin, ymax, xmax] = el.box_2d;
        
        const div = document.createElement('div');
        div.className = 'bbox';
        
        // Convert 0-1000 to percentage
        div.style.top = (ymin / 10) + '%';
        div.style.left = (xmin / 10) + '%';
        div.style.height = ((ymax - ymin) / 10) + '%';
        div.style.width = ((xmax - xmin) / 10) + '%';
        
        // Color coding
        if (el.type === 'heading') div.style.borderColor = 'blue';
        if (el.type === 'table') div.style.borderColor = 'green';
        if (el.type === 'image') div.style.borderColor = 'orange';
        
        div.title = `${el.type}: ${el.text ? el.text.substring(0, 50) + '...' : ''}`;
        
        overlays.appendChild(div);
    });
}
