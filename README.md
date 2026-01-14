# DermaAI Clinical Knowledge & Protocol Agent (CKPA)

A clinical intelligence platform powered by **Claude AI** and **Pinecone** vector search, designed to help clinicians quickly access dermatological protocols, product information, and treatment recommendations.

## 🎯 Project Overview

DermaAI CKPA is a **RAG (Retrieval-Augmented Generation)** application that combines:
- 🧠 **Claude AI** (Anthropic) for intelligent medical responses
- 📚 **Pinecone** vector database for semantic search
- 🔍 **FastAPI** backend with real-time streaming
- ⚛️ **React + TypeScript** modern frontend

The application helps clinicians retrieve evidence-based protocols and product information efficiently during consultations.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│         React Frontend (Port 5173)          │
│      (Chat, Protocols, Products, Docs)      │
└─────────────────┬───────────────────────────┘
                  │ HTTP/REST
┌─────────────────▼───────────────────────────┐
│      FastAPI Backend (Port 8000)            │
│  (RAG Service, Document Processing)         │
└─────────────────┬───────────────────────────┘
                  │
        ┌─────────┴──────────┐
        │                    │
   ┌────▼────┐         ┌────▼──────────┐
   │ Pinecone│         │ Anthropic API │
   │ Vector  │         │    (Claude)    │
   │   DB    │         └────────────────┘
   └─────────┘
        │
   ┌────▼──────────┐
   │  OpenAI API   │
   │  (Embeddings) │
   └───────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+** (backend)
- **Node.js 18.x or 20.x** (frontend)
- **API Keys:**
  - [Anthropic Claude](https://console.anthropic.com/)
  - [Pinecone](https://app.pinecone.io/)
  - [OpenAI](https://platform.openai.com/) (for embeddings)

### Setup & Run

#### 1. Clone & Install Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
```

#### 2. Start Backend Server

```bash
# From backend/
uvicorn app.main:app --reload --port 8000
```

**Backend is ready at:** `http://localhost:8000`  
**API Docs:** `http://localhost:8000/docs`

#### 3. Setup & Run Frontend

```bash
cd frontend
npm install
npm run dev
```

**Frontend is ready at:** `http://localhost:5173`

### Environment Configuration

Create `.env` in `backend/` directory:

```env
# Core API Keys
ANTHROPIC_API_KEY=sk-ant-...
PINECONE_API_KEY=...
OPENAI_API_KEY=sk-...

# Application
ENVIRONMENT=development
DEBUG=True
LOG_LEVEL=INFO

# Vector Search
VECTOR_SEARCH_TOP_K=10
EMBEDDING_MODEL=text-embedding-3-small

# Claude LLM
CLAUDE_MODEL=claude-3-5-sonnet-20241022
CLAUDE_TEMPERATURE=0.2

# Frontend CORS
CORS_ORIGINS=http://localhost:5173
```

See [.env.example](./backend/.env.example) for all available options.

## 📚 Project Structure

```
dermafocus-clinical-intelligence-agent/
├── backend/                          # FastAPI application
│   ├── app/
│   │   ├── main.py                  # FastAPI app, middleware setup
│   │   ├── config.py                # Configuration management
│   │   ├── api/
│   │   │   └── routes/              # API endpoints
│   │   │       ├── health.py        # Health checks
│   │   │       ├── chat.py          # Chat & RAG
│   │   │       ├── documents.py     # Document management
│   │   │       └── search.py        # Vector search
│   │   ├── services/                # Business logic
│   │   │   ├── rag_service.py       # RAG orchestration
│   │   │   ├── claude_service.py    # Claude API wrapper
│   │   │   ├── embedding_service.py # Embedding & Pinecone
│   │   │   └── pinecone_service.py  # Vector DB operations
│   │   ├── utils/
│   │   │   ├── document_processor.py # PDF/document handling
│   │   │   ├── chunking.py          # Text chunking strategies
│   │   │   └── video_processor.py   # Video transcription
│   │   └── models/
│   │       └── schemas.py           # Pydantic request/response models
│   ├── tests/                       # Unit & integration tests
│   ├── scripts/                     # Utility scripts
│   ├── requirements.txt             # Python dependencies
│   ├── .env.example                 # Configuration template
│   └── README.md                    # Backend documentation
│
├── frontend/                        # React + TypeScript application
│   ├── src/
│   │   ├── App.tsx                  # Main app component
│   │   ├── components/
│   │   │   ├── Chat/                # Chat interface
│   │   │   ├── Protocols/           # Protocol viewing
│   │   │   ├── Products/            # Product information
│   │   │   ├── Docs/                # Documentation
│   │   │   ├── Safety/              # Safety information
│   │   │   └── Layout/              # Navigation & sidebar
│   │   ├── services/
│   │   │   └── apiService.ts        # Backend API client
│   │   ├── types/                   # TypeScript types
│   │   └── constants/               # App constants
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
│
├── .github/
│   ├── workflows/                   # GitHub Actions CI/CD
│   │   ├── backend-tests.yml       # Backend testing pipeline
│   │   ├── frontend-tests.yml      # Frontend build pipeline
│   │   ├── integration-tests.yml   # Integration testing
│   │   ├── code-quality.yml        # Security & quality checks
│   │   └── release.yml             # Docker build & release
│   ├── copilot-instructions.md     # AI agent guidelines
│   └── CI_CD_PIPELINE.md           # Pipeline documentation
│
└── recommendation.md                # Future features & roadmap
```

## 🔌 API Endpoints

### Health Checks
- `GET /api/health` - Basic health check
- `GET /api/health/detailed` - Full dependency status
- `GET /api/health/ready` - Kubernetes readiness
- `GET /api/health/live` - Kubernetes liveness

### Chat & RAG
- `POST /api/chat` - Send query, get AI response with citations
- `POST /api/chat/stream` - Streaming response (SSE)
- `GET /api/chat/{conversation_id}/history` - Get conversation
- `DELETE /api/chat/{conversation_id}` - Delete conversation
- `POST /api/chat/feedback` - Submit feedback

### Documents
- `POST /api/documents/upload` - Upload PDF/document
- `GET /api/documents` - List all documents
- `GET /api/documents/{doc_id}` - Get document metadata
- `DELETE /api/documents/{doc_id}` - Delete document

### Vector Search
- `POST /api/search/semantic` - Semantic search with vectors
- `GET /api/search/similar/{doc_id}` - Find similar documents
- `GET /api/search/stats` - Index statistics

### Protocols & Products
- `GET /api/protocols/` - Get all protocols (RAG-powered)
- `GET /api/products/` - Get all products (RAG-powered)

## 🧪 Testing

### Backend Tests

```bash
cd backend

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run specific test
pytest tests/test_health.py -v
```

### Code Quality

```bash
# Linting
ruff check app/

# Format checking
black --check app/

# Type checking
mypy app/ --ignore-missing-imports
```

### Frontend Build

```bash
cd frontend
npm run build
```

## 📊 Development Status

### ✅ Completed (Phase 1-4)
- FastAPI backend foundation with middleware & error handling
- Configuration management with environment variables
- Health check system (basic, detailed, readiness, liveness)
- API route structure with request/response models
- Structured JSON logging
- RAG integration with Claude AI
- Pinecone vector database integration
- Semantic search capabilities
- Streaming chat responses
- Protocol & Product caching

### 🔄 In Progress / Planned
- **Phase 5:** Frontend UI completion & optimization
- **Phase 6:** Advanced features (conversation memory, user auth)
- **Phase 7:** Testing, performance optimization
- **Phase 8:** Deployment, Docker containerization
- **Phase 9:** Monitoring, analytics, scaling

See [recommendation.md](./recommendation.md) for future features and roadmap.

## 🔒 Security

- ✅ API key management via environment variables
- ✅ CORS configuration for frontend
- ✅ Request/response validation with Pydantic
- ✅ Error handling with sensitive data masking
- ✅ Structured logging for audit trails

**In Development:**
- Rate limiting
- API authentication (OAuth2/JWT)
- Input sanitization
- HTTPS enforcement (production)

## 🚀 Deployment

### Docker Support
Dockerfile available for production deployment. See [CI/CD Pipeline](./.github/CI_CD_PIPELINE.md) for Docker build and deployment instructions.

### GitHub Actions
Automated CI/CD pipeline with:
- Backend tests (Python 3.9-3.11)
- Frontend builds (Node 18.x, 20.x)
- Code quality & security scans
- Docker image build & push
- Integration testing

Run `git push` to trigger workflows. See [CI/CD docs](./.github/CI_CD_PIPELINE.md) for details.

## 📖 Documentation

- [Backend README](./backend/README.md) - Backend API & setup guide
- [GETTING_STARTED.md](./backend/GETTING_STARTED.md) - Step-by-step setup
- [PHASE_1_COMPLETE.md](./backend/PHASE_1_COMPLETE.md) - Phase 1 deliverables
- [CI_CD_PIPELINE.md](./.github/CI_CD_PIPELINE.md) - GitHub Actions workflows
- [Copilot Instructions](./.github/copilot-instructions.md) - AI agent guidelines
- [Recommendation.md](./recommendation.md) - Feature roadmap

## 🤝 Contributing

### Code Style
- Python: Black, Ruff, mypy
- TypeScript: ESLint, Prettier
- Commits: Conventional format (`feat:`, `fix:`, `docs:`, etc.)

### Branch Protection
Main branch requires:
- All tests passing
- Code review approval
- Branches up to date

## 📞 Support

For issues, questions, or feature requests:
1. Check existing [documentation](./backend/README.md)
2. Review [recommendation.md](./recommendation.md) for planned features
3. Check backend logs: `tail -f backend/logs/app.log`

## 📝 License

This project is proprietary and confidential.

---

**Last Updated:** January 14, 2026  
**Maintained by:** DermaAI Team
