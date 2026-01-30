# DermaFocus Clinical Intelligence Agent - Claude Code Context

## Project Overview
RAG-based clinical knowledge retrieval system for Derma Focus PDF documentation. The system processes dermatology product information, clinical papers, treatment protocols, and injection techniques.

## Tech Stack
- **Backend**: FastAPI (Python 3.11+)
- **Vector DB**: Pinecone (cosine similarity, 1536 dimensions)
- **Embeddings**: OpenAI `text-embedding-3-small`
- **LLM**: Claude (claude-sonnet-4-20250514)
- **PDF Processing**: PyMuPDF (fitz), PyPDF2, pdfplumber
- **Frontend**: React + TypeScript + Vite

## Directory Structure
```
backend/
├── app/
│   ├── api/routes/       # FastAPI endpoints
│   ├── services/         # RAG, Claude, Embedding, Pinecone services
│   ├── utils/            # chunking.py, document_processor.py
│   ├── models/           # Pydantic schemas
│   └── config.py         # Settings
├── data/
│   ├── uploads/          # Raw PDFs by category
│   └── processed/        # JSON processed documents
└── scripts/              # Batch processing scripts
```

## Key Files for RAG Development
- `backend/app/utils/chunking.py` - Text chunking strategies
- `backend/app/utils/document_processor.py` - PDF extraction
- `backend/app/services/rag_service.py` - RAG orchestration
- `backend/app/services/embedding_service.py` - OpenAI embeddings
- `backend/app/services/pinecone_service.py` - Vector operations

## Current Chunking Configuration
- **Chunk Size**: 1000 characters
- **Overlap**: 200 characters
- **Strategy**: Sentence-aware splitting
- **Min Chunk**: 100 characters

## Document Types
- `product` - Product factsheets and brochures
- `protocol` - Treatment protocols and techniques
- `clinical_paper` - Clinical studies and research
- `brochure` - Marketing materials
- `case_study` - Case studies

## Commands
```bash
# Start backend
cd backend && uvicorn app.main:app --reload

# Start frontend
cd frontend && npm run dev

# Run tests
cd backend && pytest

# Process documents
cd backend && python scripts/batch_ingest_pdfs.py
```

## Environment Variables Required
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- `PINECONE_API_KEY`
- `PINECONE_INDEX_NAME` (default: dermaai-ckpa)

## Development Focus Areas
1. **Chunking Optimization** - Critical for RAG quality
2. **PDF Preprocessing** - Clean text extraction before chunking
3. **RAG Validation** - Confidence scoring and answer quality
4. **Hybrid Search** - Combining semantic + keyword search
