# Raga Information Extraction Plan

## Objective
Extract structured information about Indian Classical Ragas from Document ID 4 ("Raga Nidhi"). The current generic markdown extraction is insufficient for capturing specific musical notation (Aroha/Avroha) and structured attributes. We will re-process the document images with a specialized Vision LLM prompt to populate a structured database.

## Current State
- **Document ID**: 4
- **Title**: Raga Nidhi A Comparative Study of Hindustani & Karnatik Ragas Subba Rao B. Vol 1_text.pdf
- **Status**: Processed (Version 1), but `markdown_text` lacks detailed musical notation (Swaras) for Aroha/Avroha.
- **Assets**: Page images are available in `~/.pdf-vision-processor/data/images/4/v1/`.

## Target Data Schema
We will extract the following fields for each Raga:

| Field | Type | Description |
|-------|------|-------------|
| `name` | String | Name of the Raga (e.g., "Bageshree") |
| `thaat` | String | Parent scale/Thaat (e.g., "Kafi") |
| `type_hindustani` | Boolean | True if Hindustani, False if Karnatik (or specify type) |
| `aroha` | String | Ascending scale notes (e.g., "S R g m P D n S'") |
| `avroha` | String | Descending scale notes |
| `vadi` | String | Vadi swara (King note) |
| `samvadi` | String | Samvadi swara (Queen note) |
| `time` | String | Time of performance (e.g., "Midnight") |
| `jati` | String | Classification (e.g., "Audav-Sampurna") |
| `related_ragas` | List[String] | Names of similar/allied ragas |
| `compositions` | List[String] | Listed compositions/songs |
| `description` | Text | General description and characteristics |

## Implementation Plan

### 1. Database Schema Update
Create a new table `extracted_ragas` to store the structured data.

```python
class ExtractedRaga(Base):
    __tablename__ = "extracted_ragas"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    page_number = Column(Integer)  # Page where the Raga description starts or is found
    
    name = Column(String, index=True)
    thaat = Column(String)
    aroha = Column(String)
    avroha = Column(String)
    vadi = Column(String)
    samvadi = Column(String)
    time = Column(String)
    jati = Column(String)
    
    # Store complex lists/text as JSON or Text
    related_ragas = Column(Text) # JSON list
    compositions = Column(Text)  # JSON list
    description = Column(Text)
    
    raw_extraction = Column(Text) # Full JSON from LLM
    created_at = Column(DateTime, default=datetime.utcnow)
```

### 2. Specialized LLM Prompt
We need a prompt specifically designed for the Vision LLM to look for musical notation and structured headers.

**Draft Prompt:**
```text
You are an expert in Indian Classical Music. Analyze this page image from the book "Raga Nidhi".
Identify if one or more Ragas are described on this page.
For each Raga, extract the following details into a JSON object:
- Name: The name of the Raga (usually a header).
- Thaat: The parent scale.
- Aroha: The ascending notes. Look carefully for notation like 'S R G M P D N', 'Sa Re Ga', or specific symbols. If missing, state "Not found".
- Avroha: The descending notes.
- Vadi: The primary note.
- Samvadi: The secondary note.
- Jati: The classification (e.g., Audava-Shadhava).
- Time: The time of day/season for performance.
- Related Ragas: Any other ragas mentioned as similar or allied.
- Compositions: List of songs or compositions mentioned.
- Description: A brief summary of the raga's characteristics, including vakra (crooked) movements if described.

Output a JSON object with a key "ragas" containing a list of these objects.
```

### 3. Extraction Script (`scripts/extract_ragas.py`)
A standalone script to:
1.  Connect to the database.
2.  Fetch all `Pages` for Document ID 4.
3.  Iterate through pages:
    - Load the image from `image_path`.
    - Send to LLM with the specialized prompt.
    - Parse JSON response.
    - Validate data.
    - Insert into `extracted_ragas` table.
4.  Handle Rate Limiting and Errors.

### 4. TO-DO List

- [ ] **Step 1: Setup**
    - [ ] Create `docs/plans/raga_extraction.md` (This file).
    - [ ] Create a new branch `feat/raga-extraction`.

- [ ] **Step 2: Database**
    - [ ] Add `ExtractedRaga` model to `models.py`.
    - [ ] Create a migration script or manually update DB (for now, `Base.metadata.create_all` in a script).

- [ ] **Step 3: Development**
    - [ ] Create `scripts/extract_ragas.py`.
    - [ ] Implement image loading and LLM call logic (reuse `processor.py` logic where possible, or instantiate `PDFProcessor` components).
    - [ ] Implement JSON parsing and DB insertion.

- [ ] **Step 4: Execution**
    - [ ] Run extraction on a sample range (e.g., pages 50-55) to verify prompt effectiveness.
    - [ ] Refine prompt if Aroha/Avroha are still missed.
    - [ ] Run full extraction for Document 4.

- [ ] **Step 5: Review**
    - [ ] Inspect `extracted_ragas` table.
    - [ ] Generate a report or simple UI view to browse extracted Ragas.

## Risks & Mitigations
- **Risk**: LLM fails to read musical notation (e.g., if it's in a non-standard font or handwritten style).
    - **Mitigation**: Experiment with different Vision LLMs (e.g., GPT-4o vs Claude 3.5 Sonnet) or adjust image contrast/preprocessing.
- **Risk**: Raga description spans multiple pages.
    - **Mitigation**: The script will store per-page extractions. A post-processing step can merge entries with the same Raga name if they appear on consecutive pages.
