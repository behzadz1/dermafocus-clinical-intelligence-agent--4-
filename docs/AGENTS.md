# AGENTS.md - DermaFocus Clinical Intelligence Agent

> Comprehensive documentation for AI agents working on this codebase

## Project Overview

**DermaFocus Clinical Intelligence Agent** is a RAG-powered (Retrieval-Augmented Generation) clinical reference system for aesthetic medicine professionals. It provides evidence-based answers about Dermafocus products, treatment protocols, and clinical applications with full source citations.

### Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Backend** | FastAPI (Python 3.9+) | REST API, streaming SSE |
| **Frontend** | React 18 + TypeScript + Vite | SPA with real-time chat |
| **Vector DB** | Pinecone (Serverless) | Semantic search |
| **LLM** | Anthropic Claude (claude-sonnet-4-20250514) | Response generation |
| **Embeddings** | OpenAI text-embedding-3-small | 1536-dimensional vectors |
| **Styling** | Tailwind CSS | UI components |

---

## Project Structure

```
dermafocus-clinical-intelligence-agent/
├── backend/                    # FastAPI Python backend
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/         # API endpoint handlers
│   │   │       ├── chat.py     # Main chat + streaming endpoints
│   │   │       ├── products.py # Dynamic product retrieval
│   │   │       ├── protocols.py# Treatment protocol retrieval
│   │   │       ├── documents.py# Document upload/processing
│   │   │       ├── search.py   # Semantic search endpoints
│   │   │       └── health.py   # Health check endpoints
│   │   ├── services/           # Business logic layer
│   │   │   ├── claude_service.py    # Claude API integration
│   │   │   ├── rag_service.py       # RAG orchestration
│   │   │   ├── embedding_service.py # OpenAI embeddings
│   │   │   ├── pinecone_service.py  # Vector database ops
│   │   │   └── cache_service.py     # Caching layer
│   │   ├── models/
│   │   │   └── schemas.py      # Pydantic models
│   │   ├── utils/
│   │   │   ├── chunking.py     # Text chunking logic
│   │   │   ├── document_processor.py # PDF/DOCX processing
│   │   │   └── video_processor.py    # Video transcription
│   │   └── config.py           # Settings & env vars
│   ├── tests/                  # pytest test suite
│   ├── data/                   # Uploads and processed docs
│   └── requirements.txt        # Python dependencies
│
├── frontend/                   # React TypeScript frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── Chat/
│   │   │   │   └── ChatWindow.tsx  # Main chat interface
│   │   │   ├── Products/
│   │   │   │   └── ProductHub.tsx  # Product catalog
│   │   │   ├── Protocols/
│   │   │   │   ├── ProtocolList.tsx
│   │   │   │   └── ProtocolDetail.tsx
│   │   │   ├── Safety/
│   │   │   │   └── SafetyPanel.tsx
│   │   │   ├── Docs/
│   │   │   │   └── SystemDocs.tsx
│   │   │   └── Layout/
│   │   │       └── Sidebar.tsx
│   │   ├── services/
│   │   │   └── apiService.ts   # Backend API client
│   │   ├── types/
│   │   │   └── index.ts        # TypeScript interfaces
│   │   ├── App.tsx             # Root component
│   │   └── main.tsx            # Entry point
│   ├── package.json
│   └── vite.config.ts
│
├── .github/
│   └── workflows/              # CI/CD pipelines
│       ├── backend-tests.yml
│       ├── frontend-tests.yml
│       ├── code-quality.yml
│       ├── integration-tests.yml
│       └── release.yml
│
├── .env.example                # Environment template
├── README.md                   # User documentation
└── AGENTS.md                   # This file
```

---

## Architecture Deep Dive

### Data Flow

```
User Query
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  Frontend (ChatWindow.tsx)                               │
│  - Captures user input                                   │
│  - Manages streaming state                               │
│  - Displays confidence tiers                             │
└─────────────────────────────────────────────────────────┘
    │ POST /api/chat/stream (SSE)
    ▼
┌─────────────────────────────────────────────────────────┐
│  Backend (chat.py)                                       │
│  1. Classify intent                                      │
│  2. Query RAG for context                                │
│  3. Stream Claude response                               │
│  4. Send sources + follow-ups                            │
└─────────────────────────────────────────────────────────┘
    │                    │
    ▼                    ▼
┌────────────┐    ┌─────────────────┐
│ RAG Service│    │ Claude Service  │
│            │    │                 │
│ - Embed    │    │ - Generate      │
│   query    │    │   response      │
│ - Search   │    │ - Stream text   │
│   Pinecone │    │ - Follow-ups    │
│ - Format   │    │ - Intent class  │
│   context  │    │                 │
└────────────┘    └─────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  Pinecone Vector Database                                │
│  - Index: dermaai-ckpa                                   │
│  - Namespace: default                                    │
│  - Metric: cosine similarity                             │
│  - Dimensions: 1536                                      │
└─────────────────────────────────────────────────────────┘
```

### Confidence Calculation

The system uses a weighted confidence formula:

```python
confidence = (
    top_score * 0.35 +      # Best match quality
    avg_score * 0.30 +      # Overall retrieval quality
    coverage_score * 0.20 + # Multiple high-quality sources
    consistency_score * 0.15 # Agreement between sources
)
```

**Confidence Tiers:**
- **High (≥75%)**: Green badge, strong evidence
- **Medium (55-74%)**: Amber badge, moderate confidence
- **Low (<55%)**: Red badge, limited evidence

---

## Key Services

### 1. Claude Service (`backend/app/services/claude_service.py`)

Primary LLM integration for response generation.

**Key Methods:**
| Method | Purpose |
|--------|---------|
| `generate_response()` | Synchronous response generation |
| `generate_response_stream()` | SSE streaming responses |
| `classify_intent()` | Query categorization (9 intents) |
| `generate_follow_ups()` | Dynamic follow-up questions |
| `extract_sources()` | Source citation formatting |

**Intent Categories:**
- `product_info` - Product details, composition
- `protocol` - Treatment procedures
- `dosing` - Quantities, amounts
- `contraindications` - Safety warnings
- `comparison` - Product comparisons
- `safety` - Risk information
- `scheduling` - Treatment frequency
- `equipment` - Tools, needles
- `general_query` - Catch-all

### 2. RAG Service (`backend/app/services/rag_service.py`)

Orchestrates retrieval-augmented generation.

**Key Methods:**
| Method | Purpose |
|--------|---------|
| `search()` | Semantic search with min_score filtering (0.50) |
| `get_context_for_query()` | Prepare context for LLM (8 chunks max) |
| `rerank_results()` | Score-based reranking |
| `hybrid_search()` | Semantic + keyword (planned) |
| `get_related_documents()` | Find similar documents |

**Search Parameters:**
- `top_k`: 8 chunks retrieved
- `min_score`: 0.50 threshold
- `namespace`: "default"

### 3. Pinecone Service (`backend/app/services/pinecone_service.py`)

Vector database operations.

**Key Methods:**
| Method | Purpose |
|--------|---------|
| `upsert_vectors()` | Batch insert (100 per batch) |
| `query()` | Semantic search with filters |
| `delete_vectors()` | Remove by ID/filter/all |
| `get_index_stats()` | Index statistics |

### 4. Embedding Service (`backend/app/services/embedding_service.py`)

OpenAI embedding generation.

**Key Methods:**
| Method | Purpose |
|--------|---------|
| `generate_embedding()` | Single text embedding |
| `generate_embeddings_batch()` | Batch processing (100 per batch) |
| `embed_chunks()` | Embed document chunks |
| `embed_query()` | Embed search query |

---

## API Endpoints

### Chat Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat/` | POST | Synchronous chat response |
| `/api/chat/stream` | POST | SSE streaming response |
| `/api/chat/feedback` | POST | Submit user feedback |
| `/api/chat/{id}/history` | GET | Get conversation history (planned) |

### Products & Protocols

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/products/` | GET | List all products |
| `/api/products/{name}` | GET | Get single product |
| `/api/products/refresh` | POST | Force cache refresh |
| `/api/protocols/` | GET | List all protocols |
| `/api/protocols/{id}` | GET | Get single protocol |
| `/api/protocols/refresh` | POST | Force cache refresh |

### Documents

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/documents/upload` | POST | Upload document |
| `/api/documents/` | GET | List documents |
| `/api/documents/{id}` | GET | Get document details |
| `/api/documents/{id}` | DELETE | Delete document |

### Health

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health/` | GET | Basic health check |
| `/api/health/detailed` | GET | Full dependency status |

---

## Frontend Components

### ChatWindow.tsx

Main chat interface with:
- Real-time SSE streaming
- Dynamic follow-up suggestions
- Confidence tier badges
- Source citations display
- Streaming/Instant mode toggle

**Key State:**
```typescript
const [messages, setMessages] = useState<Message[]>([]);
const [dynamicSuggestions, setDynamicSuggestions] = useState<string[]>([]);
const [useStreaming, setUseStreaming] = useState(true);
const [isLoading, setIsLoading] = useState(false);
```

### apiService.ts

Backend API client with methods:
- `sendMessage()` - Sync chat
- `sendMessageStream()` - Async generator for SSE
- `getProducts()` / `getProtocols()` - Data retrieval
- `checkHealth()` - Health monitoring

---

## Environment Variables

### Required

```env
# AI Services
ANTHROPIC_API_KEY=sk-ant-...      # Claude API
OPENAI_API_KEY=sk-...             # Embeddings
PINECONE_API_KEY=...              # Vector DB

# Security
SECRET_KEY=your-secret-key-change-in-production
```

### Optional

```env
# Application
ENVIRONMENT=development           # development | production
DEBUG=true
LOG_LEVEL=INFO

# Server
HOST=0.0.0.0
PORT=8000

# Claude
CLAUDE_MODEL=claude-sonnet-4-20250514
CLAUDE_MAX_TOKENS=2000
CLAUDE_TEMPERATURE=0.2

# Pinecone
PINECONE_INDEX_NAME=dermaai-ckpa
PINECONE_ENVIRONMENT=us-east-1

# Embeddings
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536

# Frontend (Vite)
VITE_API_URL=http://localhost:8000
```

---

## Data Models

### Core Schemas (Pydantic)

```python
class DocumentType(Enum):
    PRODUCT = "product"
    PROTOCOL = "protocol"
    CLINICAL_PAPER = "clinical_paper"
    VIDEO = "video"
    CASE_STUDY = "case_study"
    OTHER = "other"

class IntentType(Enum):
    PRODUCT_INFO = "product_info"
    INJECTION_PROTOCOL = "injection_protocol"
    CLINICAL_EVIDENCE = "clinical_evidence"
    PRODUCT_COMPARISON = "product_comparison"
    COMPLICATION = "complication"
    CONTRAINDICATION = "contraindication"
    GENERAL = "general"

class Source(BaseModel):
    document: str
    page: int
    section: Optional[str]
    relevance_score: float
    text_snippet: str

class ChatResponse(BaseModel):
    answer: str
    sources: List[Source]
    intent: Optional[str]
    confidence: float
    conversation_id: str
    follow_ups: List[str]
```

### Frontend Types

```typescript
interface Message {
  id: string;
  role: 'user' | 'model';
  text: string;
  timestamp: Date;
  isStreaming?: boolean;
  sources?: Source[];
  confidence?: number;
}

interface Source {
  document: string;
  page: number;
  section?: string;
  relevance_score: number;
  text_snippet?: string;
}
```

---

## CI/CD Pipeline

### Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `backend-tests.yml` | Push/PR to main/develop | Python 3.9-3.11 testing |
| `frontend-tests.yml` | Push/PR to main/develop | Node 18-20 build verification |
| `code-quality.yml` | Push/PR | Security scanning (Trivy) |
| `integration-tests.yml` | Push/PR | Full stack testing |
| `release.yml` | Tag push | Docker build + GitHub release |

### Running Tests Locally

```bash
# Backend
cd backend
pip install -r requirements.txt
pytest tests/ -v --cov=app

# Frontend
cd frontend
npm install
npm run build
npm run lint
```

---

## Development Guidelines

### Code Style

**Python:**
- Formatter: Black
- Linter: Ruff
- Type checker: mypy
- Docstrings: Google style

**TypeScript:**
- ESLint + Prettier
- Strict mode enabled
- React functional components

### Adding New Features

1. **New API Endpoint:**
   - Add route in `backend/app/api/routes/`
   - Define Pydantic models in `schemas.py`
   - Register in `main.py` router

2. **New Service:**
   - Create in `backend/app/services/`
   - Use singleton pattern
   - Add health check method

3. **New Frontend Component:**
   - Create in `frontend/src/components/`
   - Add types in `types/index.ts`
   - Update routing if needed

### Error Handling

- Backend uses structlog for JSON logging
- All services have try/catch with logging
- API returns proper HTTP status codes
- Frontend displays user-friendly error messages

---

## Performance Considerations

### Caching

- Products/Protocols cached with TTL
- Document upload clears related caches
- In-memory caching for development

### Streaming

- SSE for real-time responses
- Chunked text streaming from Claude
- Sources/follow-ups sent after main content

### Vector Search

- Min score threshold (0.50) reduces noise
- Top-k=8 balances coverage and relevance
- Batch upserts (100 vectors) for efficiency

---

## Security Notes

### API Keys

- Never commit API keys
- Use `.env` file locally
- Use GitHub Secrets for CI/CD

### Input Validation

- Pydantic validates all requests
- Max length limits on inputs
- File type validation on uploads

### CORS

- Configured for localhost dev
- Update for production domains

---

## Common Tasks

### Refresh Product/Protocol Cache

```bash
# Via API
curl -X POST http://localhost:8000/api/products/refresh
curl -X POST http://localhost:8000/api/protocols/refresh
```

### Check System Health

```bash
curl http://localhost:8000/api/health/detailed
```

### Upload New Document

```bash
curl -X POST http://localhost:8000/api/documents/upload \
  -F "file=@document.pdf"
```

---

## Troubleshooting

### Backend won't start

1. Check `.env` file exists with all required keys
2. Verify Python 3.9+ installed
3. Install dependencies: `pip install -r requirements.txt`

### Frontend can't connect

1. Ensure backend is running on port 8000
2. Check `VITE_API_URL` in frontend `.env`
3. Verify CORS origins in backend config

### Low confidence scores

1. Check Pinecone index has vectors
2. Verify document processing completed
3. Review min_score threshold (0.50)

### Streaming not working

1. Check SSE event types in apiService.ts
2. Verify browser supports EventSource
3. Check network tab for SSE connection

---

## Contact & Support

- **Repository Issues**: Report bugs and feature requests
- **Documentation**: README.md for user guide
- **CI/CD**: Check GitHub Actions for build status

---

*Last Updated: January 2025*
*Version: 1.0.0*
