# Copilot Instructions for DermaAI CKPA

## Overview
This document provides essential guidelines for AI coding agents working with the DermaAI Clinical Knowledge & Protocol Agent codebase. Understanding the architecture, workflows, and conventions will enable efficient contributions and enhancements.

## Architecture
The project is structured around a FastAPI backend that integrates with Pinecone for vector storage and Claude for language processing. The architecture is as follows:

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

### Key Components
- **FastAPI**: Main API server handling requests.
- **Pinecone**: Vector database for storing embeddings.
- **Claude**: Language model for generating responses.

## Developer Workflows
### Setting Up the Environment
1. Clone the repository and navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment variables by copying `.env.example` to `.env` and editing it with your API keys.

### Running the Server
To start the development server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Testing
Run tests using pytest:
```bash
pytest
```

## Project-Specific Conventions
- **Logging**: Use structured logging with `structlog`.
- **API Key Management**: Store keys in environment variables; never commit `.env` files.
- **CORS Configuration**: Set allowed origins in the `.env` file.

## Integration Points
- **Frontend**: Communicates with the backend via HTTP/REST.
- **External APIs**: Integrates with Anthropic Claude and Pinecone for functionality.

## Common Commands
- **Health Check**: `curl http://localhost:8000/api/health`
- **Upload Document**: `curl -X POST http://localhost:8000/api/documents/upload -F "file=@document.pdf"`

## Conclusion
This document serves as a guide for AI agents to navigate and contribute effectively to the DermaAI CKPA codebase. For further details, refer to the project documentation and related files.