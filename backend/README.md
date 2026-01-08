# DermaAI CKPA Backend

Backend API for the DermaAI Clinical Knowledge & Protocol Agent.

Built with **FastAPI** + **Pinecone** + **Claude (Anthropic)** for RAG-powered clinical knowledge retrieval.

---

## 🏗️ Architecture

```
┌─────────────────┐
│   Frontend      │
│   (React)       │
└────────┬────────┘
         │
         │ HTTP/REST
         │
┌────────▼────────┐
│   FastAPI       │
│   API Server    │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼──┐  ┌──▼───────┐
│ RAG  │  │ Document │
│Service│  │Processor │
└───┬──┘  └──┬───────┘
    │        │
┌───▼────────▼───┐
│   Pinecone     │
│  Vector DB     │
└────────────────┘
    │
┌───▼────────┐
│  Claude    │
│  (LLM)     │
└────────────┘
```

---

## 📁 Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Configuration management
│   ├── api/
│   │   └── routes/
│   │       ├── health.py       # Health check endpoints
│   │       ├── chat.py         # Chat & RAG endpoints
│   │       ├── documents.py    # Document management
│   │       └── search.py       # Vector search
│   ├── services/
│   │   ├── rag_service.py      # RAG orchestration (Phase 4)
│   │   ├── llm_service.py      # Claude integration (Phase 4)
│   │   ├── embedding_service.py # Pinecone & embeddings (Phase 3)
│   │   └── conversation_service.py # Chat history (Phase 7)
│   ├── utils/
│   │   ├── document_processor.py # PDF processing (Phase 2)
│   │   ├── video_processor.py    # Video transcription (Phase 2)
│   │   └── chunking.py          # Text chunking (Phase 2)
│   └── models/
│       └── schemas.py          # Pydantic models
├── scripts/
│   ├── batch_upload.py         # Batch document upload
│   └── setup_pinecone.py       # Pinecone index setup
├── tests/
│   ├── test_health.py
│   ├── test_chat.py
│   └── test_documents.py
├── data/
│   ├── uploads/                # Uploaded documents
│   └── processed/              # Processed documents
├── logs/
│   └── app.log                # Application logs
├── requirements.txt            # Python dependencies
├── .env.example               # Environment variables template
├── .env                       # Your environment variables (git-ignored)
├── Dockerfile                 # Docker configuration (Phase 9)
└── README.md                  # This file
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- pip or uv
- API Keys:
  - [Anthropic Claude](https://console.anthropic.com/)
  - [Pinecone](https://app.pinecone.io/)
  - [OpenAI](https://platform.openai.com/) (for embeddings)

### 1. Clone & Navigate

```bash
cd backend
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

Required environment variables:
```env
ANTHROPIC_API_KEY=sk-ant-your-key-here
PINECONE_API_KEY=your-pinecone-key-here
OPENAI_API_KEY=sk-your-openai-key-here
SECRET_KEY=your-secret-key-here
```

### 5. Run Development Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or using the main file:
```bash
python -m app.main
```

### 6. Test API

Open browser: `http://localhost:8000`

API Documentation: `http://localhost:8000/docs`

Test health endpoint:
```bash
curl http://localhost:8000/api/health
```

---

## 📡 API Endpoints

### Health Check
- `GET /api/health` - Basic health check
- `GET /api/health/detailed` - Detailed health with dependency status
- `GET /api/health/ready` - Readiness probe
- `GET /api/health/live` - Liveness probe

### Chat (RAG)
- `POST /api/chat` - Send message and get AI response with citations
- `POST /api/chat/stream` - Streaming response (SSE)
- `GET /api/chat/{conversation_id}/history` - Get conversation history
- `DELETE /api/chat/{conversation_id}` - Delete conversation
- `POST /api/chat/feedback` - Submit feedback

### Documents
- `POST /api/documents/upload` - Upload document
- `GET /api/documents` - List all documents
- `GET /api/documents/{doc_id}` - Get document metadata
- `GET /api/documents/{doc_id}/status` - Get processing status
- `DELETE /api/documents/{doc_id}` - Delete document
- `POST /api/documents/{doc_id}/reprocess` - Reprocess document

### Search
- `POST /api/search/semantic` - Semantic vector search
- `GET /api/search/similar/{doc_id}` - Find similar documents
- `GET /api/search/stats` - Get index statistics
- `POST /api/search/reindex` - Reindex all documents
- `DELETE /api/search/clear` - Clear index (destructive!)

---

## 🧪 Testing

### Run Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_health.py
```

### Manual Testing

```bash
# Health check
curl http://localhost:8000/api/health

# Chat (placeholder)
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the needle size for Plinest Eye?"}'

# Upload document (placeholder)
curl -X POST http://localhost:8000/api/documents/upload \
  -F "file=@document.pdf" \
  -F "doc_type=product"
```

---

## 🔧 Development Phases

### ✅ Phase 1: Backend Foundation (CURRENT)
- [x] FastAPI setup
- [x] Configuration management
- [x] Health check endpoints
- [x] API route structure
- [x] Request/response models
- [x] Logging infrastructure

### ⏳ Phase 2: Document Processing (Week 1-2)
- [ ] PDF processing
- [ ] Text extraction
- [ ] Chunking strategy
- [ ] Video transcription
- [ ] Batch upload script

### ⏳ Phase 3: Vector Database (Week 2)
- [ ] Pinecone setup
- [ ] Embedding service
- [ ] Vector upload
- [ ] Semantic search

### ⏳ Phase 4: RAG Implementation (Week 2-3)
- [ ] Intent classification
- [ ] RAG orchestration
- [ ] Claude integration
- [ ] Citation extraction

### ⏳ Phase 5: Frontend Integration (Week 3-4)
- [ ] Update API endpoints
- [ ] Streaming support
- [ ] Error handling

### ⏳ Phase 6: Advanced Features (Week 4-5)
- [ ] Conversation memory
- [ ] Safety monitoring
- [ ] Analytics

### ⏳ Phase 7: Testing & QA (Week 5-6)
- [ ] Unit tests
- [ ] Integration tests
- [ ] RAG evaluation

### ⏳ Phase 8: Deployment (Week 6-7)
- [ ] Docker setup
- [ ] CI/CD pipeline
- [ ] Production config

---

## 🛠️ Configuration

### Environment Variables

See `.env.example` for all available configuration options.

Key settings:

```env
# Application
APP_NAME="DermaAI CKPA API"
ENVIRONMENT="development"  # development, staging, production
DEBUG=True

# API Keys
ANTHROPIC_API_KEY=sk-ant-...
PINECONE_API_KEY=...
OPENAI_API_KEY=sk-...

# Vector Search
EMBEDDING_MODEL="text-embedding-3-small"
VECTOR_SEARCH_TOP_K=10

# Claude
CLAUDE_MODEL="claude-3-5-sonnet-20241022"
CLAUDE_TEMPERATURE=0.2
```

### Logging

Structured JSON logging with `structlog`:

```python
import structlog
logger = structlog.get_logger()

logger.info("event_name", key1=value1, key2=value2)
```

Logs are written to:
- Console (development)
- `./logs/app.log` (all environments)

---

## 🔐 Security

### API Key Management
- Never commit `.env` file
- Use environment variables
- Rotate keys regularly

### CORS
Configure allowed origins in `.env`:
```env
CORS_ORIGINS="http://localhost:5173,http://localhost:3000"
```

### Rate Limiting
```env
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000
```

---

## 📊 Monitoring

### Health Checks

```bash
# Basic health
curl http://localhost:8000/api/health

# Detailed health with dependencies
curl http://localhost:8000/api/health/detailed
```

### Logs

```bash
# Follow logs
tail -f logs/app.log

# Search logs
cat logs/app.log | grep "error"
```

### Metrics (Phase 9)

- Prometheus endpoint: `:9090/metrics`
- Grafana dashboards
- Sentry error tracking

---

## 🐛 Troubleshooting

### Common Issues

**1. Import errors**
```bash
# Make sure you're in the virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

**2. API key errors**
```bash
# Check .env file exists and has correct keys
cat .env | grep API_KEY
```

**3. Port already in use**
```bash
# Use different port
uvicorn app.main:app --reload --port 8001
```

**4. Module not found errors**
```bash
# Run from backend directory
cd backend
python -m app.main
```

### Debug Mode

Enable debug logging:
```env
DEBUG=True
LOG_LEVEL="DEBUG"
```

---

## 📚 Resources

### Documentation
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Anthropic Claude API](https://docs.anthropic.com/)
- [Pinecone Docs](https://docs.pinecone.io/)
- [Pydantic](https://docs.pydantic.dev/)

### Related Files
- [MVP Implementation Plan](../MVP_IMPLEMENTATION_PLAN.md)
- [Code Review](../CODE_REVIEW.md)
- [Frontend README](../README.md)

---

## 🤝 Contributing

### Code Style
- Use Black for formatting: `black app/`
- Use Ruff for linting: `ruff check app/`
- Type hints required
- Docstrings for all functions

### Commit Messages
```
feat: Add document processing endpoint
fix: Resolve embedding dimension mismatch
docs: Update API documentation
test: Add RAG service tests
```

---

## 📝 License

Copyright © 2025 Dermafocus. All rights reserved.

---

## 🆘 Support

For questions or issues:
1. Check the [troubleshooting section](#-troubleshooting)
2. Review the [MVP Plan](../MVP_IMPLEMENTATION_PLAN.md)
3. Check API documentation at `/docs`
4. Contact the development team

---

**Current Status:** Phase 1 Complete ✅

**Next Steps:** 
1. Get API keys (Anthropic, Pinecone, OpenAI)
2. Gather 30+ Dermafocus documents
3. Begin Phase 2: Document Processing

Ready to build the RAG system! 🚀
