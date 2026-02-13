# Document Ingestion Guide for RAG System

## Overview

This guide explains how to add missing critical documents to the DermaFocus RAG system to improve response accuracy and consistency.

---

## Current Status

**Database Contents (as of analysis):**
- ~59 vectors indexed in Pinecone
- Only 3 main documents:
  - "Advancing Hand Rejuvenation With Newest®.pdf"
  - "Injection Technique and Protocols for the Perioral area with Newest®.pdf"
  - "Polynucleotides Versus Platelet-Rich Plasma for Androgenetic Alopecia: A Case Series.pdf"

**Result:** Insufficient coverage for comprehensive product queries, causing inconsistent responses.

---

## Missing Critical Documents

### High Priority (CRITICAL)

1. **Mastelli_Aesthetic_Medicine_Portfolio.pdf**
   - Authoritative product catalog
   - Contains definitive product indications and contraindications
   - Distinguishes between Newest, Plinest Eye, Plinest, etc.

2. **Product Factsheets:**
   - `Newest_Factsheet.pdf` - Complete Newest product information
   - `Plinest_Eye_Factsheet.pdf` - Periorbital/periocular treatment product
   - `Plinest_Factsheet.pdf` - Base Plinest product information
   - `NewGyn_Factsheet.pdf` - Gynecological product information
   - `Plinest_Hair_Factsheet.pdf` - Hair restoration product

### Medium Priority

3. **Product Comparison Documents:**
   - Documents that explicitly compare products (e.g., Newest vs Plinest Eye for different treatment areas)
   - Treatment area matrices showing which product for which indication

4. **Comprehensive Protocol Guidelines:**
   - Detailed injection techniques by product
   - Treatment protocols with expected outcomes
   - Aftercare instructions per product

---

## Document Ingestion Steps

### Step 1: Organize Documents

Place PDFs in the appropriate category folder:

```bash
backend/data/uploads/product/
├── Newest_Factsheet.pdf
├── Plinest_Eye_Factsheet.pdf
├── Plinest_Factsheet.pdf
├── NewGyn_Factsheet.pdf
├── Plinest_Hair_Factsheet.pdf
└── Mastelli_Aesthetic_Medicine_Portfolio.pdf
```

**Category folders:**
- `product/` - Product factsheets and brochures
- `protocol/` - Treatment protocols and injection techniques
- `clinical_paper/` - Clinical studies and research papers
- `brochure/` - Patient-facing marketing materials
- `case_study/` - Clinical case studies

### Step 2: Run Batch Ingestion

```bash
cd backend

# Option 1: Ingest specific category
python scripts/batch_ingest_pdfs.py --category product

# Option 2: Force reprocess existing documents (if you updated chunking settings)
python scripts/batch_ingest_pdfs.py --category product --force-reprocess

# Option 3: Ingest all categories
python scripts/batch_ingest_pdfs.py --all
```

### Step 3: Verify Indexing

**Check Pinecone vector count:**

```bash
python -c "
from app.services.pinecone_service import PineconeService
svc = PineconeService()
stats = svc.index.describe_index_stats()
print(f'Total vectors: {stats.total_vector_count}')
"
```

**Expected Results:**
- Vector count should increase from ~59 to ~150+
- Each document typically generates 10-30 vectors depending on length

**Test specific query:**

```bash
python debug_rag_search.py --query "What is Newest?" --show-sources --top-k 5
```

**Expected output:**
- Top result should be `Newest_Factsheet.pdf` with score ≥ 0.7
- Sources should include factsheet page numbers

---

## Validation Tests

### Test 1: Product Information Query

```bash
# Query
"What is Newest?"

# Expected Response Should Include:
- Product name: Newest
- Composition: Polynucleotides + Hyaluronic Acid
- Indications: Face, neck, décolleté, hands, PERIORAL area
- Concentration: 20mg/2ml
- Mechanism: Bio-remodeling

# Expected Sources:
- Newest_Factsheet.pdf (score ≥ 0.7)
```

### Test 2: Product Comparison Query

```bash
# Query
"Can Newest be used for periorbital area?"

# Expected Response:
- NO - Newest is for face/neck/décolleté/hands/perioral
- Plinest Eye is the dedicated periorbital product
- Plinest Eye has 15mg/2ml (lower concentration for delicate eye area)
- Newest has 20mg/2ml (higher concentration, not suitable for periorbital)

# Expected Sources:
- Mastelli_Aesthetic_Medicine_Portfolio.pdf
- Plinest_Eye_Factsheet.pdf
- Newest_Factsheet.pdf
```

### Test 3: Indication Coverage

```bash
# Query
"What are the indications for Newest?"

# Expected Response Should Include ALL:
- Facial rejuvenation
- Neck rejuvenation
- Décolleté treatment
- Hand rejuvenation
- Perioral rejuvenation (lips and perioral area)
- Fine lines and wrinkles
- Skin quality improvement

# Missing ANY of these = FAILED TEST
```

### Test 4: Metadata Filtering

```bash
# Test perioral anatomy filter
python -c "
from app.services.rag_service import RAGService
rag = RAGService()

# Search for perioral documents
results = rag.search('perioral treatment', namespace='default')

# Check metadata
for result in results:
    print(f\"Doc: {result['metadata']['doc_id']}\")
    print(f\"Anatomy: {result['metadata'].get('anatomy', 'MISSING')}\")
    print(f\"Score: {result['score']}\")
"

# Expected: Documents with perioral should have anatomy='perioral'
```

---

## Re-processing Existing Documents

If you made changes to chunking settings or metadata enrichment (which we did), you need to reprocess existing documents:

### Option 1: Delete and Re-ingest

```bash
# Delete existing vectors
python -c "
from app.services.pinecone_service import PineconeService
svc = PineconeService()
svc.index.delete(delete_all=True, namespace='default')
print('All vectors deleted')
"

# Re-ingest all documents
cd backend
python scripts/batch_ingest_pdfs.py --all
```

### Option 2: Selective Re-processing

```bash
# Only reprocess product category documents
python scripts/batch_ingest_pdfs.py --category product --force-reprocess
```

**Note:** Force reprocessing will:
1. Delete existing vectors for those documents
2. Re-extract text from PDFs
3. Re-chunk with new settings (600 char chunks for factsheets)
4. Re-enrich metadata with new anatomy terms (perioral, hand)
5. Re-embed and re-index

---

## Expected Impact After Ingestion

### Before:
- Document Coverage: 3 documents
- Perioral Query Success: 50% (only if specific protocol doc retrieved)
- Confidence Scores: 0.42-0.50 (low)
- Indication Coverage: 60-70% (missing key areas)

### After:
- Document Coverage: 15+ authoritative factsheets and protocols
- Perioral Query Success: 95%+ (comprehensive metadata + factsheets)
- Confidence Scores: 0.7-0.85 (high)
- Indication Coverage: 95-100% (complete product information)

---

## Troubleshooting

### Problem: Vector count didn't increase

**Possible causes:**
- PDFs not in correct folder
- File permissions issue
- PDF extraction failed

**Solution:**
```bash
# Check if PDFs are readable
ls -lah backend/data/uploads/product/

# Check processing logs
tail -f backend/logs/ingestion.log

# Try manual processing
python scripts/process_single_pdf.py --file backend/data/uploads/product/Newest_Factsheet.pdf
```

### Problem: Query still returns wrong documents

**Possible causes:**
- Old vectors still in database
- Metadata not updated
- Chunking changes not applied

**Solution:**
```bash
# Delete all vectors and start fresh
python -c "from app.services.pinecone_service import PineconeService; svc = PineconeService(); svc.index.delete(delete_all=True, namespace='default')"

# Re-ingest with force flag
python scripts/batch_ingest_pdfs.py --all --force-reprocess
```

### Problem: Confidence scores still low (<0.5)

**Possible causes:**
- Documents missing key information
- Query doesn't match document content well
- Need query expansion

**Solution:**
- Verify factsheets contain complete information (check PDF manually)
- Test with more specific queries
- Check if query expansion is enabled in settings

---

## Monitoring & Maintenance

### Regular Checks

1. **Weekly vector count check:**
   ```bash
   python -c "from app.services.pinecone_service import PineconeService; svc = PineconeService(); print(svc.index.describe_index_stats())"
   ```

2. **Monthly RAG evaluation:**
   ```bash
   python scripts/validate_rag_quality.py --dataset tests/fixtures/rag_eval_dataset.json
   ```

3. **Confidence score monitoring:**
   - Track average confidence in logs
   - Alert if average drops below 0.6

### When to Re-ingest

- New product documents added
- Factsheets updated with new information
- Chunking strategy changed
- Metadata enrichment rules updated
- Confidence scores decline

---

## Contact

For issues with document ingestion or RAG performance:
1. Check logs: `backend/logs/ingestion.log`
2. Review debug output: `python debug_rag_search.py --query "your query" --debug`
3. Validate chunks: `python scripts/inspect_chunks.py --doc-id "document_name"`

---

## Summary Checklist

- [ ] Obtain missing factsheets (Newest, Plinest Eye, Plinest, NewGyn, Plinest Hair)
- [ ] Obtain Mastelli_Aesthetic_Medicine_Portfolio.pdf
- [ ] Place PDFs in `backend/data/uploads/product/`
- [ ] Run batch ingestion: `python scripts/batch_ingest_pdfs.py --category product`
- [ ] Verify vector count increased to ~150+
- [ ] Test query "What is Newest?" - expect factsheet as top result (score ≥ 0.7)
- [ ] Test query "Can Newest be used for periorbital?" - expect correct refusal
- [ ] Validate indication coverage - expect 100% coverage for known indications
- [ ] Check metadata - documents with "perioral" should have `anatomy='perioral'`
- [ ] Run comprehensive evaluation: `python scripts/validate_rag_quality.py`
- [ ] Monitor confidence scores - expect ≥ 0.7 for factsheet queries

**Success Criteria:**
- ✅ All critical documents indexed
- ✅ Vector count ≥ 150
- ✅ Confidence scores ≥ 0.7 for factsheet queries
- ✅ 100% indication coverage
- ✅ Correct product differentiation (Newest ≠ Plinest Eye for periorbital)
