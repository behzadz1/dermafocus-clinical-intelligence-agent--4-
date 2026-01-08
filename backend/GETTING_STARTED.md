# Phase 1: Backend Foundation - Getting Started Guide

Welcome to Phase 1! This guide will walk you through setting up and running the DermaAI CKPA backend.

## 📋 Prerequisites

Before starting, ensure you have:

1. **Python 3.11+** installed
   ```bash
   python3 --version  # Should show 3.11 or higher
   ```

2. **API Keys** (you can start without these, but you'll need them for full functionality):
   - **Anthropic Claude API**: https://console.anthropic.com/
   - **Pinecone**: https://app.pinecone.io/
   - **OpenAI** (for embeddings): https://platform.openai.com/

3. **Git** (optional, for version control)

---

## 🚀 Step-by-Step Setup

### Step 1: Navigate to Backend Directory

```bash
cd backend
```

### Step 2: Run the Setup Script

We've created an automated setup script that handles everything:

```bash
chmod +x setup.sh
./setup.sh
```

This script will:
- ✅ Check Python version
- ✅ Create virtual environment
- ✅ Install all dependencies
- ✅ Create necessary directories
- ✅ Copy .env.example to .env

### Step 3: Configure Environment Variables

Edit the `.env` file and add your API keys:

```bash
nano .env  # or use your favorite editor
```

**Minimum required configuration:**

```bash
# API Keys (required for RAG, not needed for basic health checks)
ANTHROPIC_API_KEY="sk-ant-your-actual-key-here"
PINECONE_API_KEY="your-pinecone-key-here"
OPENAI_API_KEY="sk-your-openai-key-here"

# Generate a random secret key (for JWT tokens, sessions, etc.)
SECRET_KEY="replace-with-a-long-random-string"
```

**To generate a secure SECRET_KEY:**

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Optional configuration** (can keep defaults):

```bash
# Server settings
PORT=8000
DEBUG=True
ENVIRONMENT="development"

# CORS (add your frontend URL)
CORS_ORIGINS="http://localhost:5173,http://localhost:3000"
```

### Step 4: Start the Server

**Option A: Using Python directly**

```bash
source venv/bin/activate
python3 -m app.main
```

**Option B: Using uvicorn (recommended for development)**

```bash
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The `--reload` flag enables auto-reload when you change code.

You should see output like:

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 5: Test the API

**Test 1: Health Check (in a new terminal)**

```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-08T...",
  "version": "1.0.0",
  "environment": "development",
  "python_version": "3.11.x"
}
```

**Test 2: Detailed Health Check**

```bash
curl http://localhost:8000/api/health/detailed
```

This shows the status of all dependencies (Anthropic, Pinecone, OpenAI).

**Test 3: Run automated test suite**

```bash
chmod +x test_api.sh
./test_api.sh
```

This tests all endpoints and gives you a pass/fail report.

### Step 6: View API Documentation

Open your browser and go to:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

These interactive docs let you test all endpoints directly from your browser.

---

## 🎯 What's Working Now (Phase 1)

After completing Phase 1 setup, you have:

✅ **Working API Server**
- FastAPI application running on port 8000
- CORS configured for frontend
- Request logging
- Error handling

✅ **Health Check Endpoints**
- `/api/health` - Basic health check
- `/api/health/detailed` - Dependency status
- `/api/health/ready` - Readiness probe
- `/api/health/live` - Liveness probe

✅ **Chat Endpoints (Placeholder)**
- `POST /api/chat` - Chat endpoint (returns placeholder response)
- `POST /api/chat/stream` - Streaming endpoint (not yet implemented)
- `GET /api/chat/{id}/history` - Conversation history (not yet implemented)

✅ **Document Endpoints (Placeholder)**
- `POST /api/documents/upload` - Document upload (not yet implemented)
- `GET /api/documents` - List documents (not yet implemented)

✅ **Infrastructure**
- Structured logging
- Environment configuration
- API documentation

---

## 🔍 Verify Everything Works

Run through this checklist:

- [ ] Backend server starts without errors
- [ ] Health check endpoint returns "healthy"
- [ ] Detailed health check shows API key status
- [ ] API documentation loads at /docs
- [ ] Test script passes all tests
- [ ] Server logs show requests properly

---

## 🐛 Troubleshooting

### Issue: "ModuleNotFoundError"

**Solution:**
```bash
# Make sure you're in the virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: "Port 8000 already in use"

**Solution:**
```bash
# Find and kill the process
lsof -ti:8000 | xargs kill -9

# Or use a different port
uvicorn app.main:app --reload --port 8001
```

### Issue: "API keys not configured" errors

**Solution:**
- Check your `.env` file has actual keys (not placeholder values)
- Make sure `.env` is in the `backend/` directory
- Restart the server after editing `.env`

### Issue: Import errors

**Solution:**
```bash
# Make sure you're running from the backend/ directory
cd backend
python3 -m app.main
```

---

## 🔄 Connecting Frontend to Backend

To connect your React frontend to this backend:

1. Update frontend environment variables:

```bash
# frontend/.env
VITE_API_URL=http://localhost:8000
```

2. Replace the old Gemini service with API calls:

```typescript
// services/apiService.ts
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const sendMessage = async (message: string) => {
  const response = await fetch(`${API_URL}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question: message })
  });
  return response.json();
};
```

3. Test it:
   - Start backend: `uvicorn app.main:app --reload` (in backend/)
   - Start frontend: `npm run dev` (in frontend/)
   - Try sending a message

---

## 📊 Understanding the Current State

**What works:**
- ✅ Server infrastructure
- ✅ Health monitoring
- ✅ Request/response handling
- ✅ API documentation

**What's placeholder:**
- ⏳ RAG retrieval (returns placeholder message)
- ⏳ Document processing
- ⏳ Vector search
- ⏳ Conversation storage

**What's next (Phase 2):**
- 🔜 Document processing pipeline
- 🔜 PDF text extraction
- 🔜 Text chunking
- 🔜 Video transcription

---

## 💡 Development Tips

### 1. Use the Interactive Docs

The best way to test endpoints is through http://localhost:8000/docs
- Click on any endpoint
- Click "Try it out"
- Enter test data
- Execute and see results

### 2. Watch the Logs

The server logs show detailed information:
```bash
# Watch logs in real-time
tail -f logs/app.log
```

### 3. Hot Reload

When running with `--reload`, the server automatically restarts when you edit code.

### 4. Format Logs

Logs are in JSON format. To make them readable:
```bash
tail -f logs/app.log | jq .
```

---

## 🎓 Learning Resources

**FastAPI Documentation:**
- https://fastapi.tiangolo.com/

**Pydantic (for data validation):**
- https://docs.pydantic.dev/

**Uvicorn (ASGI server):**
- https://www.uvicorn.org/

**Project Structure Best Practices:**
- https://fastapi.tiangolo.com/tutorial/bigger-applications/

---

## ✅ Phase 1 Completion Checklist

Before moving to Phase 2, verify:

- [ ] Backend server runs without errors
- [ ] All health checks pass
- [ ] API documentation accessible
- [ ] Environment variables configured
- [ ] Test script passes
- [ ] Logs are generated correctly
- [ ] Can make requests from curl/Postman
- [ ] CORS allows frontend connections

---

## 🚀 Ready for Phase 2?

Once Phase 1 is complete and stable, you can move to Phase 2:

**Phase 2: Document Processing Pipeline**
- PDF text extraction
- Document chunking
- Metadata extraction
- Video transcription (optional)

See `../MVP_IMPLEMENTATION_PLAN.md` for Phase 2 details.

---

## 📞 Getting Help

If you encounter issues:

1. Check the troubleshooting section above
2. Review the logs in `logs/app.log`
3. Test individual endpoints in `/docs`
4. Verify your `.env` configuration

---

**🎉 Congratulations!** You've completed Phase 1 setup. The backend foundation is now ready for RAG implementation in the next phases.
