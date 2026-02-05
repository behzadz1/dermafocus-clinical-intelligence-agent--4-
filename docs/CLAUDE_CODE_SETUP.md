# Claude Code Setup Strategy for DermaFocus RAG Project

## Overview

This document outlines the complete Claude Code configuration for efficient development of your RAG system focused on Derma Focus PDF documentation.

## Files Created

```
.claude/
├── settings.json           # Claude Code permissions
└── skills/
    ├── chunking-expert.md  # Advanced chunking strategies
    ├── pdf-preprocessor.md # PDF to Markdown conversion
    └── rag-validator.md    # RAG answer validation
CLAUDE.md                   # Project context for Claude
```

---

## Skills vs Agents: What We Chose and Why

### Skills (Chosen for Your Use Cases)

**Skills are better when:**
- You need specialized knowledge/instructions for a domain
- The task requires back-and-forth conversation
- You want the skill's context available throughout the session
- The work is exploratory and iterative

**Your Skills:**

| Skill | Invocation | Purpose |
|-------|------------|---------|
| Chunking Expert | `/chunking-expert` | Advanced chunking strategies |
| PDF Preprocessor | `/pdf-preprocessor` | Clean text extraction |
| RAG Validator | `/rag-validator` | Answer quality & confidence |

### Agents (Task Tool)

**Agents are better when:**
- The task is well-defined and autonomous
- You need parallel execution
- The task is research/exploration focused
- You want to minimize token usage for simple tasks

**When to use Agents in your project:**
- Use `Explore` agent for codebase research
- Use `Plan` agent for complex feature planning
- Use background agents for long-running processes

---

## How to Use Each Skill

### 1. Chunking Expert (`/chunking-expert`)

**When to invoke:**
- Improving chunk quality for specific document types
- Implementing semantic or hierarchical chunking
- Optimizing chunk size/overlap for retrieval
- Adding post-chunking enrichment

**Example usage:**
```
/chunking-expert

I need to implement semantic chunking for clinical papers.
The current sentence-aware chunking loses context between
related findings in methods and results sections.
```

**What it provides:**
- Semantic chunking with embeddings
- Hierarchical parent-child chunks
- Proposition-based chunking using LLM
- Document-type specific strategies (factsheets, clinical papers, protocols)
- Chunk quality metrics

### 2. PDF Preprocessor (`/pdf-preprocessor`)

**When to invoke:**
- Improving text extraction quality
- Converting PDFs to structured Markdown
- Handling scanned documents (OCR)
- Preserving document structure (tables, headers, sections)

**Example usage:**
```
/pdf-preprocessor

The current extraction is losing table structure from product
factsheets. I need better table detection and conversion to
Markdown format.
```

**What it provides:**
- Layout-aware extraction using PyMuPDF
- Multi-column detection
- OCR integration for scanned documents
- Table to Markdown conversion
- Medical document structure detection
- Quality validation

### 3. RAG Validator (`/rag-validator`)

**When to invoke:**
- Improving confidence scoring accuracy
- Detecting hallucinations in answers
- Verifying answers are grounded in sources
- Building quality metrics dashboard

**Example usage:**
```
/rag-validator

Users are reporting low confidence scores even when answers
seem accurate. I need to improve the confidence calculation
and add faithfulness validation.
```

**What it provides:**
- Enhanced multi-dimensional confidence scoring
- Hallucination detection for medical claims
- Faithfulness validation using LLM
- Citation verification
- Source agreement analysis
- Quality metrics reporting

---

## Development Workflow

### Recommended Approach

```
1. Start Session
   └── Claude reads CLAUDE.md automatically (project context)

2. For Chunking Work
   └── /chunking-expert → Discuss strategy → Implement changes

3. For PDF Processing Work
   └── /pdf-preprocessor → Analyze issues → Improve extraction

4. For RAG Quality Work
   └── /rag-validator → Review metrics → Enhance validation

5. For Research/Exploration
   └── Use Task tool with Explore agent
```

### Token-Saving Strategies

1. **Use Skills for Specialized Work**
   - Skills load domain expertise once
   - Claude focuses on specific files, not entire codebase

2. **Use Agents for Research**
   - Explore agent for finding code patterns
   - Plan agent for complex features

3. **CLAUDE.md Provides Context**
   - Key files, commands, and architecture
   - Avoids repeated explanations

4. **Targeted Modifications**
   - Skills reference specific files
   - Provide line numbers for edits
   - Avoid full file rewrites

---

## Improvement Priority

### Phase 1: PDF Preprocessing (Immediate)

The most reliable RAG approach is clean, structured text. Focus here first:

1. **Enhance text extraction**
   - Better layout handling
   - Preserve document structure

2. **Convert to Markdown**
   - Headers, sections, tables
   - Clean, logical text order

3. **Add structure detection**
   - Identify factsheet sections
   - Parse clinical paper IMRAD

### Phase 2: Chunking Optimization (Short-term)

With clean text, optimize how it's split:

1. **Document-type specific strategies**
   - Smaller chunks for factsheets (500-800 chars)
   - Larger chunks for clinical papers (1200-1500 chars)

2. **Semantic chunking**
   - Split by topic changes
   - Preserve complete concepts

3. **Chunk enrichment**
   - Add section headers to chunks
   - Include document context

### Phase 3: Validation & Quality (Medium-term)

Ensure answer quality:

1. **Enhanced confidence scoring**
   - Multi-factor scoring with breakdown
   - User-friendly interpretation

2. **Hallucination detection**
   - Flag unverified medical claims
   - Source verification

3. **Quality metrics**
   - Track confidence distribution
   - Identify improvement areas

---

## Quick Reference

### Invoke Skills
```
/chunking-expert    # Chunking strategies
/pdf-preprocessor   # PDF text extraction
/rag-validator      # Answer validation
```

### Key Files to Modify
```
backend/app/utils/chunking.py           # Chunking logic
backend/app/utils/document_processor.py # PDF processing
backend/app/services/rag_service.py     # RAG orchestration
backend/app/api/routes/chat.py          # Confidence scoring
```

### Run Commands
```bash
# Start backend
cd backend && uvicorn app.main:app --reload

# Process documents
cd backend && python scripts/batch_ingest_pdfs.py

# Run tests
cd backend && pytest
```

---

## Additional Recommendations

### 1. Add Evaluation Dataset

Create a test set of questions with expected answers:
```
backend/data/eval/
├── questions.json      # Test queries
├── expected_chunks.json # Which chunks should be retrieved
└── expected_answers.json # Ground truth answers
```

### 2. Implement Chunk Quality Checks

Before indexing, validate chunks:
- Minimum information density
- No truncated sentences
- Proper context preservation

### 3. Add Retrieval Debugging

Log and analyze:
- Which chunks are retrieved
- Why certain queries fail
- Score distributions

### 4. Consider Hybrid Search

Combine semantic + keyword search:
- BM25 for exact term matching
- Embeddings for semantic similarity
- Weighted combination
