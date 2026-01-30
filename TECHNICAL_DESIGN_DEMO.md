# DermaFocus Clinical Intelligence Agent - Technical Design & RAG Pipeline

**Date:** January 2026  
**Version:** 1.0.0  
**Purpose:** Complete technical documentation for demo presentation

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [RAG Pipeline Flow](#rag-pipeline-flow)
4. [Technical Stack](#technical-stack)
5. [Data Flow Diagrams](#data-flow-diagrams)
6. [Service Layer Architecture](#service-layer-architecture)
7. [API Design](#api-design)
8. [Database Schema](#database-schema)
9. [Performance & Optimization](#performance--optimization)
10. [Security & Compliance](#security--compliance)

---

## Executive Summary

DermaFocus Clinical Intelligence Agent is a production-grade RAG (Retrieval-Augmented Generation) system designed for aesthetic medicine professionals. It provides evidence-based clinical answers with full source citations, leveraging state-of-the-art AI technologies.

### Key Features
- **Real-time Streaming Responses**: Server-Sent Events (SSE) for live answer generation
- **Semantic Search**: Vector-based retrieval with 1536-dimensional embeddings
- **Multi-format Support**: PDF, DOCX, video transcripts processing
- **Confidence Scoring**: Weighted algorithm for answer reliability
- **Intent Classification**: 9 distinct query categories
- **Source Citations**: Full provenance tracking with page numbers

---

## System Architecture

### High-Level Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                  │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │  React 18 + TypeScript Frontend (Vite)                     │     │
│  │  - ChatWindow Component (SSE Streaming)                    │     │
│  │  - Product & Protocol Hubs                                 │     │
│  │  - Real-time confidence badges                             │     │
│  │  - Source citation display                                 │     │
│  └─────────────────────┬──────────────────────────────────────┘     │
└────────────────────────┼──────────────────────────────────────────────┘
                         │
                         │ HTTP/REST + SSE
                         │
┌────────────────────────▼──────────────────────────────────────────────┐
│                      API GATEWAY LAYER                                 │
│  ┌────────────────────────────────────────────────────────────┐      │
│  │  FastAPI (Python 3.9+)                                      │      │
│  │  - CORS Middleware                                          │      │
│  │  - Request Validation (Pydantic)                            │      │
│  │  - Error Handling & Logging (structlog)                     │      │
│  │  - Rate Limiting (future)                                   │      │
│  └─────────────────────┬──────────────────────────────────────┘      │
└────────────────────────┼──────────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
┌────────────────┐ ┌────────────┐ ┌──────────────┐
│ Chat Routes    │ │ Document   │ │ Product/     │
│ /api/chat      │ │ Routes     │ │ Protocol     │
│                │ │ /api/docs  │ │ Routes       │
└────────┬───────┘ └─────┬──────┘ └──────┬───────┘
         │               │               │
┌────────▼───────────────▼───────────────▼──────────────────────────────┐
│                      SERVICE LAYER                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │ RAG Service  │  │ Claude       │  │ Embedding    │               │
│  │              │  │ Service      │  │ Service      │               │
│  │ - Search     │  │ - Generate   │  │ - OpenAI     │               │
│  │ - Rerank     │  │ - Stream     │  │ - Batch      │               │
│  │ - Context    │  │ - Intent     │  │ - Cache      │               │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘               │
│         │                  │                  │                       │
│  ┌──────▼───────┐  ┌──────▼───────┐  ┌──────▼───────┐               │
│  │ Pinecone     │  │ Cache        │  │ Document     │               │
│  │ Service      │  │ Service      │  │ Processor    │               │
│  │              │  │              │  │              │               │
│  │ - Upsert     │  │ - TTL Cache  │  │ - PDF/DOCX   │               │
│  │ - Query      │  │ - Invalidate │  │ - Chunking   │               │
│  │ - Delete     │  │              │  │ - Metadata   │               │
│  └──────┬───────┘  └──────────────┘  └──────┬───────┘               │
└─────────┼──────────────────────────────────┼─────────────────────────┘
          │                                  │
          ▼                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      DATA & AI LAYER                                  │
│  ┌──────────────────┐  ┌─────────────────┐  ┌──────────────────┐   │
│  │ Pinecone         │  │ Anthropic       │  │ OpenAI           │   │
│  │ Vector DB        │  │ Claude API      │  │ Embeddings API   │   │
│  │                  │  │                 │  │                  │   │
│  │ - Serverless     │  │ - Sonnet 4      │  │ - text-embed-3   │   │
│  │ - Cosine         │  │ - 2000 tokens   │  │ - 1536 dims      │   │
│  │ - us-east-1      │  │ - Temp: 0.2     │  │                  │   │
│  └──────────────────┘  └─────────────────┘  └──────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## RAG Pipeline Flow

### Complete Request-Response Cycle

```
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 1: USER INPUT & INTENT CLASSIFICATION                         │
└─────────────────────────────────────────────────────────────────────┘

User Query: "What is the recommended dosage of Newest for hand rejuvenation?"
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ ChatWindow.tsx                                                   │
│ - Capture input                                                  │
│ - Set isLoading = true                                          │
│ - Call apiService.sendMessageStream()                           │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        │ POST /api/chat/stream
                        │ Content-Type: text/event-stream
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ chat.py: stream_chat_response()                                 │
│ Step 1: Intent Classification                                   │
│   - Call claude_service.classify_intent(query)                  │
│   - Result: "dosing"                                            │
│ Step 2: Initialize streaming                                    │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼

┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 2: SEMANTIC SEARCH & RETRIEVAL                                │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ rag_service.get_context_for_query()                             │
│ Step 1: Generate Query Embedding                                │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ embedding_service.embed_query()                                  │
│ - Call OpenAI API: text-embedding-3-small                       │
│ - Input: "What is the recommended dosage..."                    │
│ - Output: [0.023, -0.041, 0.018, ...] (1536 dims)              │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ rag_service.search()                                             │
│ Step 2: Vector Search in Pinecone                               │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ pinecone_service.query()                                         │
│ Parameters:                                                      │
│   - vector: [0.023, -0.041, ...]                               │
│   - top_k: 8                                                    │
│   - namespace: "default"                                        │
│   - include_metadata: true                                      │
│                                                                  │
│ Results (Top 3 shown):                                          │
│   1. Score: 0.87 | Doc: "Newest_Hand_Rejuvenation.pdf"         │
│      Page: 4 | Chunk: "Recommended dosage for hands..."        │
│   2. Score: 0.82 | Doc: "Newest_Dosing_Guidelines.pdf"         │
│      Page: 2 | Chunk: "Clinical protocols suggest..."          │
│   3. Score: 0.76 | Doc: "Injection_Techniques.pdf"             │
│      Page: 7 | Chunk: "For volumizing hands..."                │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ rag_service.rerank_results()                                     │
│ Step 3: Filter & Score                                          │
│ - Filter: min_score >= 0.50                                     │
│ - Sort by relevance_score descending                            │
│ - Take top 8 chunks                                             │
│                                                                  │
│ Confidence Calculation:                                         │
│   top_score = 0.87                                              │
│   avg_score = 0.82                                              │
│   coverage_score = 0.88 (multiple high-quality sources)        │
│   consistency_score = 0.85 (agreement between sources)         │
│                                                                  │
│   confidence = (0.87 * 0.35) + (0.82 * 0.30) +                │
│                (0.88 * 0.20) + (0.85 * 0.15)                  │
│              = 0.304 + 0.246 + 0.176 + 0.128                  │
│              = 0.854 (85.4%)                                   │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ rag_service.format_context()                                    │
│ Step 4: Prepare Context for LLM                                 │
│                                                                  │
│ Context String:                                                 │
│ """                                                             │
│ Document: Newest_Hand_Rejuvenation.pdf (Page 4)                │
│ Relevance: 87%                                                  │
│ Recommended dosage for hands: 2-4ml per hand depending on...   │
│                                                                  │
│ Document: Newest_Dosing_Guidelines.pdf (Page 2)                │
│ Relevance: 82%                                                  │
│ Clinical protocols suggest starting with 2ml per hand...       │
│ """                                                             │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼

┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 3: LLM GENERATION & STREAMING                                 │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ claude_service.generate_response_stream()                        │
│ Step 1: Build Prompt                                            │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ Prompt Construction:                                             │
│                                                                  │
│ System:                                                         │
│ You are DermaAI, a clinical reference assistant for aesthetic  │
│ medicine professionals. Provide evidence-based answers using    │
│ the following context...                                        │
│                                                                  │
│ Context: [Formatted context from Phase 2]                       │
│                                                                  │
│ User: What is the recommended dosage of Newest for hand        │
│       rejuvenation?                                             │
│                                                                  │
│ Parameters:                                                     │
│ - model: claude-sonnet-4-20250514                              │
│ - max_tokens: 2000                                             │
│ - temperature: 0.2                                             │
│ - stream: true                                                 │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ Anthropic API Streaming Response                                │
│                                                                  │
│ Stream Chunk 1: "The"                                           │
│ Stream Chunk 2: " recommended"                                  │
│ Stream Chunk 3: " dosage"                                       │
│ Stream Chunk 4: " for"                                          │
│ Stream Chunk 5: " Newest"                                       │
│ ...                                                             │
│ Stream Chunk N: " based on clinical literature."               │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼

┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 4: RESPONSE STREAMING TO CLIENT                               │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ chat.py: Stream Events via SSE                                  │
│                                                                  │
│ Event 1: type=start                                            │
│   data: {"conversation_id": "abc123"}                          │
│                                                                  │
│ Event 2: type=content                                          │
│   data: {"text": "The"}                                        │
│                                                                  │
│ Event 3: type=content                                          │
│   data: {"text": " recommended"}                               │
│ ...                                                             │
│                                                                  │
│ Event N: type=sources                                          │
│   data: {                                                       │
│     "sources": [                                               │
│       {                                                        │
│         "document": "Newest_Hand_Rejuvenation.pdf",           │
│         "page": 4,                                            │
│         "relevance_score": 0.87,                              │
│         "text_snippet": "Recommended dosage..."               │
│       }                                                        │
│     ],                                                         │
│     "confidence": 0.854                                       │
│   }                                                            │
│                                                                  │
│ Event N+1: type=follow_ups                                     │
│   data: {                                                       │
│     "questions": [                                             │
│       "What are the injection techniques for hands?",         │
│       "Are there any contraindications for hand treatment?",  │
│       "How does Newest compare to other hand fillers?"        │
│     ]                                                          │
│   }                                                            │
│                                                                  │
│ Event N+2: type=end                                            │
│   data: {}                                                      │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ ChatWindow.tsx: Handle SSE Events                               │
│                                                                  │
│ eventSource.onmessage = (event) => {                           │
│   const data = JSON.parse(event.data);                         │
│   switch(data.type) {                                          │
│     case 'content':                                            │
│       appendToCurrentMessage(data.text);                       │
│       break;                                                   │
│     case 'sources':                                            │
│       setMessageSources(data.sources);                         │
│       setConfidence(data.confidence);                          │
│       break;                                                   │
│     case 'follow_ups':                                         │
│       setDynamicSuggestions(data.questions);                   │
│       break;                                                   │
│   }                                                            │
│ }                                                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Technical Stack

### Backend Technologies

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Web Framework** | FastAPI | 0.104+ | High-performance async API |
| **Language** | Python | 3.9+ | Primary backend language |
| **ASGI Server** | Uvicorn | Latest | Production ASGI server |
| **Validation** | Pydantic | 2.0+ | Request/response validation |
| **Logging** | structlog | Latest | Structured JSON logging |
| **HTTP Client** | httpx | Latest | Async HTTP requests |
| **PDF Processing** | PyPDF2 | Latest | PDF text extraction |
| **DOCX Processing** | python-docx | Latest | Word document processing |

### Frontend Technologies

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Framework** | React | 18.2+ | UI component library |
| **Language** | TypeScript | 5.0+ | Type-safe JavaScript |
| **Build Tool** | Vite | 5.0+ | Fast dev server & bundler |
| **Styling** | Tailwind CSS | 3.4+ | Utility-first CSS |
| **HTTP Client** | Fetch API | Native | API communication |
| **SSE** | EventSource | Native | Server-sent events |

### AI & Data Services

| Service | Provider | Model/Config | Purpose |
|---------|----------|--------------|---------|
| **LLM** | Anthropic | claude-sonnet-4-20250514 | Response generation |
| **Embeddings** | OpenAI | text-embedding-3-small | Vector embeddings (1536d) |
| **Vector DB** | Pinecone | Serverless (us-east-1) | Semantic search |

---

## Data Flow Diagrams

### Document Ingestion Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│ DOCUMENT UPLOAD & PROCESSING FLOW                                   │
└─────────────────────────────────────────────────────────────────────┘

User Upload (PDF/DOCX)
    │
    ▼
┌───────────────────────────────┐
│ POST /api/documents/upload    │
│ - Validate file type          │
│ - Check file size (< 50MB)    │
│ - Generate unique ID          │
└───────────┬───────────────────┘
            │
            ▼
┌───────────────────────────────┐
│ document_processor.py         │
│ Step 1: Extract Text          │
│ - PDF: PyPDF2                 │
│ - DOCX: python-docx           │
│ - Extract metadata            │
└───────────┬───────────────────┘
            │
            ▼
┌───────────────────────────────────────────────────────────────┐
│ chunking.py                                                    │
│ Step 2: Smart Chunking                                        │
│                                                                │
│ Parameters:                                                   │
│ - chunk_size: 800 characters                                 │
│ - chunk_overlap: 200 characters                              │
│ - respect_boundaries: true (sentences, paragraphs)           │
│                                                                │
│ Example:                                                      │
│ Input Text (2400 chars):                                     │
│ "Newest is a polynucleotide-based dermal filler..."         │
│                                                                │
│ Output Chunks:                                               │
│ Chunk 1 (800 chars): "Newest is a polynucleotide..."        │
│ Chunk 2 (800 chars): "...based dermal filler that..."       │
│   (includes 200 char overlap from Chunk 1)                  │
│ Chunk 3 (800 chars): "...provides long-lasting..."          │
│   (includes 200 char overlap from Chunk 2)                  │
└───────────┬───────────────────────────────────────────────────┘
            │
            ▼
┌───────────────────────────────────────────────────────────────┐
│ embedding_service.embed_chunks()                              │
│ Step 3: Generate Embeddings                                   │
│                                                                │
│ Process:                                                      │
│ 1. Batch chunks (100 per batch)                              │
│ 2. Call OpenAI API for each batch                           │
│ 3. Get 1536-dimensional vectors                              │
│                                                                │
│ Example:                                                      │
│ Chunk 1 text → [0.023, -0.041, 0.018, ...] (1536 floats)   │
│ Chunk 2 text → [-0.012, 0.034, -0.021, ...] (1536 floats)  │
│ Chunk 3 text → [0.045, -0.019, 0.037, ...] (1536 floats)   │
└───────────┬───────────────────────────────────────────────────┘
            │
            ▼
┌───────────────────────────────────────────────────────────────┐
│ pinecone_service.upsert_vectors()                             │
│ Step 4: Store in Vector Database                             │
│                                                                │
│ Vector Structure:                                            │
│ {                                                             │
│   "id": "doc_abc123_chunk_0",                               │
│   "values": [0.023, -0.041, ...],  // 1536 dims            │
│   "metadata": {                                              │
│     "document_id": "abc123",                                │
│     "document_name": "Newest_Hand_Rejuvenation.pdf",        │
│     "document_type": "injection_technique",                 │
│     "page_number": 4,                                       │
│     "section": "Dosing Guidelines",                         │
│     "chunk_index": 0,                                       │
│     "chunk_text": "Newest is a polynucleotide...",         │
│     "timestamp": "2026-01-21T10:30:00Z"                    │
│   }                                                          │
│ }                                                             │
│                                                                │
│ Batch upsert: 100 vectors per API call                      │
└───────────┬───────────────────────────────────────────────────┘
            │
            ▼
┌───────────────────────────────┐
│ Save metadata to:             │
│ data/uploads/                 │
│ processed_documents.json      │
│                               │
│ Cache invalidation:           │
│ - Clear product cache         │
│ - Clear protocol cache        │
└───────────────────────────────┘
```

### Query Processing Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│ SEMANTIC SEARCH OPTIMIZATION                                         │
└─────────────────────────────────────────────────────────────────────┘

Query: "What are contraindications for Newest?"
    │
    ▼
┌───────────────────────────────────────────────────────────────┐
│ Pre-processing                                                 │
│ - Trim whitespace                                             │
│ - Normalize text                                              │
│ - Extract key terms: ["contraindications", "Newest"]         │
└───────────┬───────────────────────────────────────────────────┘
            │
            ▼
┌───────────────────────────────────────────────────────────────┐
│ Embedding Generation                                           │
│ OpenAI API Call:                                              │
│   Input: "What are contraindications for Newest?"            │
│   Output: [0.034, -0.021, 0.056, ...] (1536 dims)          │
│   Time: ~200ms                                                │
└───────────┬───────────────────────────────────────────────────┘
            │
            ▼
┌───────────────────────────────────────────────────────────────┐
│ Pinecone Vector Search                                         │
│                                                                │
│ Query Parameters:                                             │
│ - vector: [0.034, -0.021, ...]                              │
│ - top_k: 8                                                   │
│ - namespace: "default"                                       │
│ - metric: "cosine"                                           │
│ - include_metadata: true                                     │
│                                                                │
│ Cosine Similarity Calculation:                               │
│ For each stored vector V:                                    │
│   similarity = cos(θ) = (Q · V) / (||Q|| × ||V||)          │
│                                                                │
│ Results (sorted by similarity):                              │
│ 1. Score: 0.92 | "Newest_Safety_Info.pdf" p.3              │
│ 2. Score: 0.88 | "Newest_Product_Guide.pdf" p.12           │
│ 3. Score: 0.84 | "Contraindications_Summary.pdf" p.2       │
│ 4. Score: 0.79 | "Clinical_Protocols.pdf" p.8              │
│ 5. Score: 0.72 | "Newest_FAQ.pdf" p.5                      │
│ 6. Score: 0.68 | "Treatment_Guidelines.pdf" p.15           │
│ 7. Score: 0.61 | "Product_Comparison.pdf" p.7              │
│ 8. Score: 0.55 | "Injection_Techniques.pdf" p.4            │
│                                                                │
│ Time: ~300ms                                                  │
└───────────┬───────────────────────────────────────────────────┘
            │
            ▼
┌───────────────────────────────────────────────────────────────┐
│ Reranking & Filtering                                          │
│                                                                │
│ Step 1: Apply min_score threshold (0.50)                     │
│   ✓ Keep: scores 0.92, 0.88, 0.84, 0.79, 0.72, 0.68, 0.61   │
│   ✗ Drop: score 0.55                                         │
│                                                                │
│ Step 2: Diversity filtering (prevent duplicates)             │
│   - Check for same document + page                           │
│   - Keep only highest-scoring chunk per page                 │
│                                                                │
│ Step 3: Calculate confidence                                  │
│   top_score = 0.92                                           │
│   avg_score = 0.78                                           │
│   coverage = 0.85 (5+ sources)                               │
│   consistency = 0.88 (similar content)                       │
│                                                                │
│   confidence = (0.92×0.35)+(0.78×0.30)+(0.85×0.20)+(0.88×0.15) │
│              = 0.322 + 0.234 + 0.170 + 0.132                │
│              = 0.858 (85.8% - HIGH)                          │
└───────────┬───────────────────────────────────────────────────┘
            │
            ▼
┌───────────────────────────────────────────────────────────────┐
│ Context Formatting for LLM                                     │
│                                                                │
│ Formatted Context:                                            │
│ ---                                                           │
│ Document: Newest_Safety_Info.pdf (Page 3)                    │
│ Relevance: 92%                                                │
│ Content: Contraindications include: pregnancy, breastfeeding, │
│ active skin infections, autoimmune disorders affecting...     │
│                                                                │
│ Document: Newest_Product_Guide.pdf (Page 12)                 │
│ Relevance: 88%                                                │
│ Content: Do not use in patients with known hypersensitivity   │
│ to polynucleotides or any component of the product...        │
│ ---                                                           │
└───────────────────────────────────────────────────────────────┘
```

---

## Service Layer Architecture

### Service Dependencies

```
┌────────────────────────────────────────────────────────────────┐
│                     SERVICE DEPENDENCY GRAPH                    │
└────────────────────────────────────────────────────────────────┘

                    ┌──────────────────┐
                    │   FastAPI App    │
                    │   (main.py)      │
                    └────────┬─────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────┐  ┌──────────────────┐
│  Chat Routes    │  │  Document   │  │  Product Routes  │
│  (chat.py)      │  │  Routes     │  │  (products.py)   │
└────────┬────────┘  └──────┬──────┘  └────────┬─────────┘
         │                  │                   │
         │                  │                   │
         ▼                  ▼                   ▼
┌──────────────────────────────────────────────────────────┐
│                    RAG Service                            │
│                 (rag_service.py)                         │
│  - search()                                              │
│  - get_context_for_query()                              │
│  - rerank_results()                                      │
│  - calculate_confidence()                               │
└────┬──────────┬──────────┬──────────┬──────────┬────────┘
     │          │          │          │          │
     │          │          │          │          │
     ▼          ▼          ▼          ▼          ▼
┌─────────┐ ┌──────────┐ ┌─────────┐ ┌────────┐ ┌──────────┐
│ Claude  │ │Embedding │ │Pinecone │ │ Cache  │ │Document  │
│ Service │ │ Service  │ │ Service │ │Service │ │Processor │
└─────────┘ └──────────┘ └─────────┘ └────────┘ └──────────┘
     │          │          │          │          │
     ▼          ▼          ▼          ▼          ▼
┌─────────┐ ┌──────────┐ ┌─────────┐ ┌────────┐ ┌──────────┐
│Anthropic│ │  OpenAI  │ │Pinecone │ │In-Mem  │ │PyPDF2/   │
│   API   │ │   API    │ │   API   │ │ Dict   │ │python-   │
│         │ │          │ │         │ │        │ │docx      │
└─────────┘ └──────────┘ └─────────┘ └────────┘ └──────────┘
```

### Service Methods & Responsibilities

#### RAG Service (`rag_service.py`)

```python
class RAGService:
    """Orchestrates retrieval-augmented generation"""
    
    def __init__(self):
        self.pinecone_service = PineconeService()
        self.embedding_service = EmbeddingService()
        self.cache_service = CacheService()
    
    async def search(
        self, 
        query: str, 
        top_k: int = 8,
        min_score: float = 0.50,
        filters: Optional[Dict] = None
    ) -> List[SearchResult]:
        """
        Semantic search with filtering
        
        Flow:
        1. Generate query embedding
        2. Search Pinecone
        3. Filter by min_score
        4. Return formatted results
        """
        pass
    
    async def get_context_for_query(
        self,
        query: str,
        intent: Optional[str] = None
    ) -> ContextResult:
        """
        Retrieve and format context for LLM
        
        Flow:
        1. Search for relevant chunks
        2. Rerank results
        3. Calculate confidence
        4. Format context string
        5. Extract sources
        """
        pass
    
    def calculate_confidence(
        self,
        results: List[SearchResult]
    ) -> float:
        """
        Weighted confidence formula:
        - 35% top score
        - 30% average score
        - 20% coverage (# of sources)
        - 15% consistency (agreement)
        """
        pass
```

#### Claude Service (`claude_service.py`)

```python
class ClaudeService:
    """Anthropic Claude API integration"""
    
    MODEL = "claude-sonnet-4-20250514"
    MAX_TOKENS = 2000
    TEMPERATURE = 0.2
    
    async def generate_response_stream(
        self,
        query: str,
        context: str,
        conversation_history: List[Message] = []
    ) -> AsyncGenerator[str, None]:
        """
        Stream response from Claude
        
        Yields:
        - Text chunks as they arrive
        - Handles backpressure
        - Supports cancellation
        """
        pass
    
    async def classify_intent(
        self,
        query: str
    ) -> IntentType:
        """
        Classify query into 9 categories:
        - product_info
        - protocol
        - dosing
        - contraindications
        - comparison
        - safety
        - scheduling
        - equipment
        - general_query
        
        Uses Claude with structured output
        """
        pass
    
    async def generate_follow_ups(
        self,
        query: str,
        answer: str,
        sources: List[Source]
    ) -> List[str]:
        """
        Generate 3 contextual follow-up questions
        Based on query, answer, and available sources
        """
        pass
```

#### Embedding Service (`embedding_service.py`)

```python
class EmbeddingService:
    """OpenAI embeddings generation"""
    
    MODEL = "text-embedding-3-small"
    DIMENSIONS = 1536
    BATCH_SIZE = 100
    
    async def generate_embedding(
        self,
        text: str
    ) -> List[float]:
        """
        Generate single embedding
        Returns 1536-dimensional vector
        """
        pass
    
    async def generate_embeddings_batch(
        self,
        texts: List[str]
    ) -> List[List[float]]:
        """
        Batch embedding generation
        Processes 100 texts per API call
        Includes retry logic with exponential backoff
        """
        pass
    
    async def embed_query(
        self,
        query: str
    ) -> List[float]:
        """
        Embed search query
        Includes caching for repeated queries
        """
        pass
```

#### Pinecone Service (`pinecone_service.py`)

```python
class PineconeService:
    """Pinecone vector database operations"""
    
    INDEX_NAME = "dermaai-ckpa"
    NAMESPACE = "default"
    METRIC = "cosine"
    
    async def upsert_vectors(
        self,
        vectors: List[Vector]
    ) -> Dict:
        """
        Batch upsert vectors
        Processes 100 vectors per batch
        Returns upserted count
        """
        pass
    
    async def query(
        self,
        vector: List[float],
        top_k: int = 8,
        filter: Optional[Dict] = None,
        namespace: str = "default"
    ) -> QueryResponse:
        """
        Semantic search query
        Returns matches with scores and metadata
        """
        pass
    
    async def delete_vectors(
        self,
        ids: Optional[List[str]] = None,
        filter: Optional[Dict] = None,
        delete_all: bool = False
    ) -> Dict:
        """
        Delete vectors by ID, filter, or all
        Includes safety confirmation for delete_all
        """
        pass
    
    async def get_index_stats(self) -> Dict:
        """
        Get index statistics:
        - Total vector count
        - Dimension
        - Index fullness
        - Namespace stats
        """
        pass
```

---

## API Design

### REST Endpoints

#### Chat Endpoints

```
POST /api/chat/
├── Request Body:
│   {
│     "message": "string",
│     "conversation_id": "string (optional)",
│     "use_streaming": false
│   }
├── Response (200):
│   {
│     "answer": "string",
│     "sources": [
│       {
│         "document": "string",
│         "page": "number",
│         "section": "string (optional)",
│         "relevance_score": "float",
│         "text_snippet": "string"
│       }
│     ],
│     "intent": "string",
│     "confidence": "float",
│     "conversation_id": "string",
│     "follow_ups": ["string"]
│   }
└── Errors:
    - 400: Invalid request body
    - 500: Internal server error

POST /api/chat/stream
├── Request Body:
│   {
│     "message": "string",
│     "conversation_id": "string (optional)"
│   }
├── Response (200): Server-Sent Events
│   event: start
│   data: {"conversation_id": "string"}
│
│   event: content
│   data: {"text": "string"}
│
│   event: sources
│   data: {"sources": [...], "confidence": 0.85}
│
│   event: follow_ups
│   data: {"questions": [...]}
│
│   event: end
│   data: {}
└── Headers:
    Content-Type: text/event-stream
    Cache-Control: no-cache
    Connection: keep-alive
```

#### Document Endpoints

```
POST /api/documents/upload
├── Request: multipart/form-data
│   file: File (PDF/DOCX, max 50MB)
│   metadata: {
│     "document_type": "product|protocol|clinical_paper|video|case_study",
│     "tags": ["string"]
│   }
├── Response (201):
│   {
│     "document_id": "string",
│     "filename": "string",
│     "status": "processing",
│     "chunks_created": "number",
│     "vectors_upserted": "number"
│   }
└── Errors:
    - 400: Invalid file type or size
    - 500: Processing error

GET /api/documents/
├── Query Parameters:
│   - type: document_type filter
│   - limit: number (default: 50)
│   - offset: number (default: 0)
├── Response (200):
│   {
│     "documents": [
│       {
│         "id": "string",
│         "filename": "string",
│         "type": "string",
│         "upload_date": "ISO8601",
│         "chunk_count": "number",
│         "status": "processed|processing|error"
│       }
│     ],
│     "total": "number"
│   }
└── Errors:
    - 500: Database error

DELETE /api/documents/{document_id}
├── Response (200):
│   {
│     "message": "Document deleted",
│     "vectors_deleted": "number"
│   }
└── Errors:
    - 404: Document not found
    - 500: Deletion error
```

#### Product & Protocol Endpoints

```
GET /api/products/
├── Response (200):
│   {
│     "products": [
│       {
│         "name": "string",
│         "type": "string",
│         "description": "string",
│         "indications": ["string"],
│         "composition": "string",
│         "document_count": "number"
│       }
│     ]
│   }
└── Cache: 1 hour TTL

POST /api/products/refresh
├── Response (200):
│   {
│     "message": "Cache cleared",
│     "products_refreshed": "number"
│   }
└── Purpose: Force cache invalidation

GET /api/protocols/
├── Query Parameters:
│   - area: treatment area filter
│   - product: product name filter
├── Response (200):
│   {
│     "protocols": [
│       {
│         "id": "string",
│         "title": "string",
│         "treatment_area": "string",
│         "product": "string",
│         "steps": ["string"],
│         "duration": "string",
│         "source_document": "string"
│       }
│     ]
│   }
└── Cache: 1 hour TTL
```

#### Health Endpoints

```
GET /api/health/
├── Response (200):
│   {
│     "status": "healthy",
│     "timestamp": "ISO8601",
│     "version": "1.0.0"
│   }
└── Purpose: Basic health check

GET /api/health/detailed
├── Response (200):
│   {
│     "status": "healthy",
│     "services": {
│       "pinecone": {
│         "status": "connected",
│         "vector_count": "number",
│         "latency_ms": "number"
│       },
│       "claude": {
│         "status": "available",
│         "latency_ms": "number"
│       },
│       "openai": {
│         "status": "available",
│         "latency_ms": "number"
│       }
│     },
│     "timestamp": "ISO8601"
│   }
└── Purpose: Dependency health monitoring
```

---

## Database Schema

### Pinecone Vector Structure

```json
{
  "id": "doc_{document_id}_chunk_{chunk_index}",
  "values": [0.023, -0.041, 0.018, ...],  // 1536 dimensions
  "metadata": {
    "document_id": "abc123",
    "document_name": "Newest_Hand_Rejuvenation.pdf",
    "document_type": "injection_technique",
    "page_number": 4,
    "section": "Dosing Guidelines",
    "chunk_index": 0,
    "chunk_text": "Full text of the chunk...",
    "timestamp": "2026-01-21T10:30:00Z",
    "tags": ["newest", "hands", "dosing"],
    "language": "en"
  }
}
```

### Local Metadata Storage

**File:** `backend/data/uploads/processed_documents.json`

```json
{
  "documents": [
    {
      "id": "abc123",
      "filename": "Newest_Hand_Rejuvenation.pdf",
      "original_filename": "Advancing Hand Rejuvenation With Newest®.pdf",
      "document_type": "injection_technique",
      "upload_date": "2026-01-21T10:30:00Z",
      "file_size_bytes": 1048576,
      "page_count": 12,
      "chunk_count": 24,
      "processing_status": "completed",
      "vector_ids": [
        "doc_abc123_chunk_0",
        "doc_abc123_chunk_1",
        "..."
      ],
      "tags": ["newest", "hands", "rejuvenation"],
      "metadata": {
        "author": "Dr. Smith",
        "publication_date": "2025-12-01",
        "version": "1.0"
      }
    }
  ],
  "last_updated": "2026-01-21T10:30:00Z",
  "total_documents": 1,
  "total_vectors": 24
}
```

---

## Performance & Optimization

### Response Time Breakdown

```
┌─────────────────────────────────────────────────────────────────┐
│ TYPICAL QUERY PERFORMANCE (85th percentile)                     │
└─────────────────────────────────────────────────────────────────┘

Total Response Time: ~2500ms

┌────────────────────────┬──────────┬──────────────────────────┐
│ Component              │ Time (ms)│ Optimization Strategy    │
├────────────────────────┼──────────┼──────────────────────────┤
│ Intent Classification  │   400    │ • Cache common queries   │
│                        │          │ • Use faster model       │
├────────────────────────┼──────────┼──────────────────────────┤
│ Query Embedding        │   200    │ • Cache embeddings       │
│ (OpenAI API)           │          │ • Use smaller model      │
├────────────────────────┼──────────┼──────────────────────────┤
│ Pinecone Search        │   300    │ • Optimize index         │
│                        │          │ • Use filters            │
├────────────────────────┼──────────┼──────────────────────────┤
│ Context Formatting     │   100    │ • Parallel processing    │
│                        │          │ • Lazy evaluation        │
├────────────────────────┼──────────┼──────────────────────────┤
│ LLM Generation         │  1200    │ • Streaming enabled      │
│ (Claude Streaming)     │          │ • Lower temperature      │
├────────────────────────┼──────────┼──────────────────────────┤
│ Follow-up Generation   │   300    │ • Async execution        │
│                        │          │ • Template-based         │
└────────────────────────┴──────────┴──────────────────────────┘

Time to First Token (TTFT): ~1000ms
Tokens per Second: ~15-20
```

### Caching Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│ MULTI-LEVEL CACHING ARCHITECTURE                                │
└─────────────────────────────────────────────────────────────────┘

Level 1: In-Memory Cache (Application)
├── Products: TTL 1 hour
├── Protocols: TTL 1 hour
├── Common Embeddings: TTL 24 hours
└── Intent Classifications: TTL 6 hours

Level 2: API Response Cache (Future)
├── Full responses: TTL 15 minutes
├── Partial matches: Similarity threshold 0.95
└── Invalidation: On document upload

Level 3: Vector Database (Pinecone)
├── Automatic caching by Pinecone
└── Edge caching in nearest region
```

### Batch Processing

```python
# Document Upload Batch Processing
BATCH_SIZES = {
    "embedding_generation": 100,    # OpenAI limit
    "vector_upsert": 100,           # Pinecone limit
    "chunk_processing": 50          # Memory optimization
}

# Parallel Processing
MAX_WORKERS = {
    "document_processing": 4,
    "embedding_generation": 8,
    "vector_operations": 4
}
```

---

## Security & Compliance

### API Security

```
┌─────────────────────────────────────────────────────────────────┐
│ SECURITY LAYERS                                                  │
└─────────────────────────────────────────────────────────────────┘

1. API Key Management
   ├── Environment variables only
   ├── Rotation policy: 90 days
   ├── Separate keys for dev/prod
   └── Never logged or exposed

2. CORS Configuration
   ├── Allowed origins: Whitelist only
   ├── Methods: GET, POST, DELETE
   ├── Headers: Content-Type, Authorization
   └── Credentials: true (for future auth)

3. Input Validation
   ├── Pydantic models for all endpoints
   ├── Max message length: 2000 chars
   ├── File size limit: 50MB
   ├── File type whitelist: PDF, DOCX
   └── SQL injection prevention: N/A (no SQL)

4. Rate Limiting (Planned)
   ├── Per IP: 100 requests/minute
   ├── Per user: 1000 requests/hour
   └── Burst allowance: 10 requests/second

5. Data Privacy
   ├── No PII collection
   ├── Anonymous conversation IDs
   ├── No query logging (optional)
   └── GDPR compliant architecture
```

### Error Handling

```python
# Structured Error Response
{
  "error": {
    "code": "SEARCH_FAILED",
    "message": "Unable to retrieve relevant documents",
    "details": "Pinecone index unavailable",
    "timestamp": "2026-01-21T10:30:00Z",
    "request_id": "req_abc123"
  }
}

# Error Codes
ERROR_CODES = {
    "VALIDATION_ERROR": 400,
    "DOCUMENT_NOT_FOUND": 404,
    "SEARCH_FAILED": 500,
    "LLM_ERROR": 500,
    "EMBEDDING_ERROR": 500,
    "RATE_LIMIT_EXCEEDED": 429
}
```

---

## Deployment Architecture

### Production Setup (Recommended)

```
┌─────────────────────────────────────────────────────────────────┐
│ CLOUD DEPLOYMENT ARCHITECTURE                                    │
└─────────────────────────────────────────────────────────────────┘

                        Internet
                           │
                           ▼
                   ┌───────────────┐
                   │ Load Balancer │
                   │  (AWS ALB)    │
                   └───────┬───────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
┌─────────────────┐ ┌─────────────┐ ┌─────────────────┐
│ Frontend        │ │ Frontend    │ │ Frontend        │
│ (S3 + CloudFront│ │ (Replica)   │ │ (Replica)       │
│  or Vercel)     │ │             │ │                 │
└─────────────────┘ └─────────────┘ └─────────────────┘
                           │
                           ▼
                   ┌───────────────┐
                   │ API Gateway   │
                   │ (AWS API GW)  │
                   └───────┬───────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
┌─────────────────┐ ┌─────────────┐ ┌─────────────────┐
│ Backend         │ │ Backend     │ │ Backend         │
│ (ECS/Fargate)   │ │ (Instance 2)│ │ (Instance 3)    │
│ FastAPI         │ │ FastAPI     │ │ FastAPI         │
└────────┬────────┘ └──────┬──────┘ └────────┬────────┘
         │                 │                 │
         └─────────────────┼─────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
┌─────────────────┐ ┌─────────────┐ ┌─────────────────┐
│ Pinecone        │ │ Anthropic   │ │ OpenAI          │
│ (External SaaS) │ │ (External)  │ │ (External SaaS) │
└─────────────────┘ └─────────────┘ └─────────────────┘
```

### Environment Configuration

```bash
# Production Environment Variables
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Security
SECRET_KEY=<generated-secret>
ALLOWED_ORIGINS=https://dermaai.example.com

# AI Services
ANTHROPIC_API_KEY=<production-key>
OPENAI_API_KEY=<production-key>
PINECONE_API_KEY=<production-key>

# Performance
WORKERS=4
MAX_CONNECTIONS=100
KEEPALIVE_TIMEOUT=65

# Monitoring
SENTRY_DSN=<sentry-url>
DATADOG_API_KEY=<datadog-key>
```

---

## Monitoring & Observability

### Key Metrics

```
┌─────────────────────────────────────────────────────────────────┐
│ PERFORMANCE METRICS                                              │
└─────────────────────────────────────────────────────────────────┘

Application Metrics:
├── Request latency (p50, p95, p99)
├── Throughput (requests/second)
├── Error rate (%)
├── Cache hit rate (%)
└── Active connections

AI Service Metrics:
├── Embedding generation time
├── Vector search latency
├── LLM response time (TTFT, total)
├── Token usage (input/output)
└── API error rates

Business Metrics:
├── Queries per day
├── Average confidence score
├── Most common intents
├── Popular products/protocols
└── User satisfaction (from feedback)
```

### Logging Structure

```json
{
  "timestamp": "2026-01-21T10:30:00.123Z",
  "level": "info",
  "event": "query_processed",
  "conversation_id": "abc123",
  "query": "What is Newest?",
  "intent": "product_info",
  "confidence": 0.85,
  "sources_count": 5,
  "response_time_ms": 2340,
  "tokens_used": {
    "input": 450,
    "output": 230
  },
  "metadata": {
    "user_agent": "Mozilla/5.0...",
    "ip_address": "192.168.1.1"
  }
}
```

---

## Future Enhancements

### Roadmap

```
┌─────────────────────────────────────────────────────────────────┐
│ PLANNED FEATURES                                                 │
└─────────────────────────────────────────────────────────────────┘

Phase 1 (Q1 2026):
├── ✓ Core RAG pipeline
├── ✓ Streaming responses
├── ✓ Confidence scoring
├── ✓ Source citations
└── ✓ Multi-format document support

Phase 2 (Q2 2026):
├── [ ] User authentication & profiles
├── [ ] Conversation history
├── [ ] Bookmark favorite responses
├── [ ] Export chat to PDF
└── [ ] Advanced search filters

Phase 3 (Q3 2026):
├── [ ] Hybrid search (semantic + keyword)
├── [ ] Multi-modal support (images)
├── [ ] Voice input/output
├── [ ] Mobile app (React Native)
└── [ ] Offline mode

Phase 4 (Q4 2026):
├── [ ] Personalized recommendations
├── [ ] Clinical decision support
├── [ ] Integration with EMR systems
├── [ ] Multi-language support
└── [ ] Advanced analytics dashboard
```

---

## Appendix

### Confidence Tier System

```
┌─────────────────────────────────────────────────────────────────┐
│ CONFIDENCE INTERPRETATION GUIDE                                  │
└─────────────────────────────────────────────────────────────────┘

HIGH Confidence (≥75%)
├── Badge: Green
├── Interpretation: Strong evidence from multiple sources
├── Recommendation: Trust the answer
└── Example: Direct product information from official docs

MEDIUM Confidence (55-74%)
├── Badge: Amber
├── Interpretation: Moderate evidence, some uncertainty
├── Recommendation: Review sources, verify if critical
└── Example: Inferential answers from related documents

LOW Confidence (<55%)
├── Badge: Red
├── Interpretation: Limited or weak evidence
├── Recommendation: Seek additional verification
└── Example: Tangentially related information only
```

### Document Type Categories

```
┌─────────────────────────────────────────────────────────────────┐
│ DOCUMENT TAXONOMY                                                │
└─────────────────────────────────────────────────────────────────┘

Product Documents:
├── Product guides
├── Fact sheets
├── Brochures
└── Package inserts

Clinical Documents:
├── Clinical papers
├── Case studies
├── Clinical trials
└── Research reports

Protocol Documents:
├── Injection techniques
├── Treatment protocols
├── Step-by-step guides
└── Best practices

Educational Materials:
├── Training videos
├── Webinar transcripts
├── FAQs
└── Educational articles
```

---

**End of Technical Design Documentation**

*For questions or clarification, refer to:*
- `README.md` - User guide
- `AGENTS.md` - Developer documentation
- `backend/app/` - Source code
- `frontend/src/` - Frontend code

