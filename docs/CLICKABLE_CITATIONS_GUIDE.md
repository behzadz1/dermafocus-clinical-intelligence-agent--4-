# Clickable Citations Implementation Guide

## Overview

This guide explains how to implement clickable citations that link directly to source PDF documents with page-specific navigation.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      CLICKABLE CITATIONS FLOW                            │
└─────────────────────────────────────────────────────────────────────────┘

User asks question
        │
        ▼
┌─────────────────┐
│ Chat Endpoint   │  Returns answer + sources with URLs
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Response includes:                                                      │
│  {                                                                       │
│    "answer": "Plinest Eye uses a 30G needle...",                        │
│    "sources": [                                                         │
│      {                                                                  │
│        "document": "Plinest_Eye_Factsheet",                            │
│        "title": "Plinest® Eye Factsheet",                              │
│        "page": 3,                                                       │
│        "view_url": "/api/documents/view?doc_id=...&page=3",            │
│        "download_url": "/api/documents/download/..."                    │
│      }                                                                  │
│    ]                                                                    │
│  }                                                                      │
└─────────────────────────────────────────────────────────────────────────┘
         │
         │  User clicks citation
         ▼
┌─────────────────┐
│ Document Viewer │  Opens PDF at specific page
└─────────────────┘
```

---

## API Endpoints

### 1. Chat Endpoint (Updated)

**POST** `/api/chat`

Now returns sources with clickable URLs:

```json
{
  "answer": "For periorbital rejuvenation, Plinest® Eye is recommended...",
  "sources": [
    {
      "document": "Plinest_Eye_Protocol",
      "title": "Plinest® Eye Protocol",
      "page": 5,
      "section": "Treatment Protocol",
      "relevance_score": 0.87,
      "text_snippet": "The periorbital area requires careful...",
      "view_url": "/api/documents/view?doc_id=Plinest_Eye_Protocol&page=5",
      "download_url": "/api/documents/download/Plinest_Eye_Protocol"
    }
  ],
  "confidence": 0.85
}
```

### 2. Document View Endpoint

**GET** `/api/documents/view?doc_id={id}&page={page}`

Returns HTML page with embedded PDF viewer that:
- Opens the PDF file
- Automatically navigates to the specified page
- Includes download button
- Has back navigation

### 3. Document File Endpoint

**GET** `/api/documents/file/{doc_id}`

Returns raw PDF file for embedding in viewers.

### 4. Document Download Endpoint

**GET** `/api/documents/download/{doc_id}`

Returns PDF as downloadable file.

### 5. Document Info Endpoint

**GET** `/api/documents/info/{doc_id}`

Returns document metadata:

```json
{
  "doc_id": "Plinest_Eye_Factsheet",
  "title": "Plinest® Eye Factsheet",
  "file_path": "/data/uploads/Fact Sheets/Plinest_Eye_Factsheet.pdf",
  "file_exists": true,
  "total_pages": 12,
  "file_size": 524288,
  "view_url": "/api/documents/view?doc_id=Plinest_Eye_Factsheet",
  "download_url": "/api/documents/download/Plinest_Eye_Factsheet"
}
```

---

## Frontend Implementation

### React Component Example

```tsx
// components/ChatResponse.tsx
import React from 'react';

interface Source {
  document: string;
  title: string;
  page: number;
  section?: string;
  relevance_score: number;
  text_snippet: string;
  view_url: string;
  download_url: string;
}

interface ChatResponseProps {
  answer: string;
  sources: Source[];
  confidence: number;
}

export const ChatResponse: React.FC<ChatResponseProps> = ({
  answer,
  sources,
  confidence
}) => {
  const openSource = (source: Source) => {
    // Option 1: Open in new tab
    window.open(source.view_url, '_blank');

    // Option 2: Open in modal (see SourceModal component below)
    // setSelectedSource(source);
    // setModalOpen(true);
  };

  return (
    <div className="chat-response">
      {/* Answer Section */}
      <div className="answer-content">
        <ReactMarkdown>{answer}</ReactMarkdown>
      </div>

      {/* Confidence Indicator */}
      <div className="confidence-bar">
        <div
          className="confidence-fill"
          style={{ width: `${confidence * 100}%` }}
        />
        <span>{Math.round(confidence * 100)}% confident</span>
      </div>

      {/* Sources Section */}
      {sources.length > 0 && (
        <div className="sources-section">
          <h4>Sources</h4>
          <div className="sources-list">
            {sources.map((source, index) => (
              <div
                key={index}
                className="source-card"
                onClick={() => openSource(source)}
              >
                <div className="source-icon">📄</div>
                <div className="source-info">
                  <span className="source-title">{source.title}</span>
                  <span className="source-details">
                    {source.section && `${source.section} • `}
                    Page {source.page}
                  </span>
                  <span className="source-relevance">
                    {Math.round(source.relevance_score * 100)}% relevant
                  </span>
                </div>
                <div className="source-actions">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      window.open(source.view_url, '_blank');
                    }}
                    title="View document"
                  >
                    👁️
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      window.location.href = source.download_url;
                    }}
                    title="Download PDF"
                  >
                    ⬇️
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
```

### CSS Styles

```css
/* styles/chat-response.css */

.chat-response {
  max-width: 800px;
  margin: 0 auto;
}

.answer-content {
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
  margin-bottom: 16px;
}

.confidence-bar {
  height: 24px;
  background: #e9ecef;
  border-radius: 12px;
  position: relative;
  margin-bottom: 16px;
  overflow: hidden;
}

.confidence-fill {
  height: 100%;
  background: linear-gradient(90deg, #28a745, #20c997);
  transition: width 0.3s ease;
}

.confidence-bar span {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 12px;
  color: #495057;
}

.sources-section h4 {
  margin-bottom: 12px;
  color: #495057;
}

.sources-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.source-card {
  display: flex;
  align-items: center;
  padding: 12px;
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.source-card:hover {
  border-color: #0d6efd;
  box-shadow: 0 2px 8px rgba(13, 110, 253, 0.15);
}

.source-icon {
  font-size: 24px;
  margin-right: 12px;
}

.source-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.source-title {
  font-weight: 500;
  color: #0d6efd;
}

.source-details {
  font-size: 13px;
  color: #6c757d;
}

.source-relevance {
  font-size: 12px;
  color: #28a745;
}

.source-actions {
  display: flex;
  gap: 8px;
}

.source-actions button {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
}

.source-actions button:hover {
  background: #e9ecef;
}
```

### Modal PDF Viewer Component

```tsx
// components/SourceModal.tsx
import React, { useState } from 'react';

interface SourceModalProps {
  isOpen: boolean;
  source: Source | null;
  onClose: () => void;
}

export const SourceModal: React.FC<SourceModalProps> = ({
  isOpen,
  source,
  onClose
}) => {
  if (!isOpen || !source) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{source.title}</h3>
          <div className="modal-actions">
            <button onClick={() => window.open(source.view_url, '_blank')}>
              Open in New Tab
            </button>
            <button onClick={() => window.location.href = source.download_url}>
              Download
            </button>
            <button onClick={onClose}>✕</button>
          </div>
        </div>
        <div className="modal-body">
          <iframe
            src={`/api/documents/file/${source.document}#page=${source.page}`}
            title={source.title}
            width="100%"
            height="100%"
          />
        </div>
        <div className="modal-footer">
          <p className="source-snippet">
            <strong>Relevant excerpt:</strong> {source.text_snippet}
          </p>
        </div>
      </div>
    </div>
  );
};
```

---

## Inline Citation Rendering

To render citations inline within the answer text:

### Backend: Add Citation Markers

The backend can format the answer with citation markers:

```python
# In claude_service.py - add to response formatting

def format_answer_with_citations(answer: str, sources: List[dict]) -> str:
    """Add inline citation markers to answer"""

    # Add sources section at end
    if sources:
        answer += "\n\n---\n\n**Sources:**\n"
        for i, source in enumerate(sources, 1):
            answer += f"- [{i}] [{source['title']}]({source['view_url']}) (p.{source['page']})\n"

    return answer
```

### Frontend: Render Markdown Links

```tsx
import ReactMarkdown from 'react-markdown';

const ChatAnswer: React.FC<{ answer: string }> = ({ answer }) => {
  return (
    <ReactMarkdown
      components={{
        a: ({ href, children }) => (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="citation-link"
          >
            {children}
          </a>
        )
      }}
    >
      {answer}
    </ReactMarkdown>
  );
};
```

---

## Response Format Examples

### Example 1: Product Question

**Request:**
```json
{
  "question": "What is Newest?"
}
```

**Response:**
```json
{
  "answer": "Newest® is a next-generation bio-remodeling treatment combining Polynucleotides HPT® with Hyaluronic Acid...\n\n---\n\n**Sources:**\n- [1] [Newest® Factsheet](/api/documents/view?doc_id=Newest_Factsheet&page=1) (p.1)",
  "sources": [
    {
      "document": "Newest_Factsheet",
      "title": "Newest® Factsheet",
      "page": 1,
      "section": "Product Overview",
      "relevance_score": 0.92,
      "text_snippet": "Newest® is a regenerative bio-remodeling treatment...",
      "view_url": "/api/documents/view?doc_id=Newest_Factsheet&page=1",
      "download_url": "/api/documents/download/Newest_Factsheet"
    }
  ],
  "confidence": 0.89
}
```

### Example 2: Multi-Source Answer

**Request:**
```json
{
  "question": "What's the difference between Newest and Plinest?"
}
```

**Response:**
```json
{
  "answer": "The key differences between Newest® and Plinest® are:\n\n| Feature | Newest® | Plinest® |\n|---------|---------|----------|\n| Composition | PN-HPT + HA | PN-HPT only |\n| Primary Use | Hydration + Regeneration | Pure regeneration |\n\n---\n\n**Sources:**\n- [1] [Newest® Factsheet](/api/documents/view?doc_id=Newest_Factsheet&page=2)\n- [2] [Plinest® Product Guide](/api/documents/view?doc_id=Plinest_Guide&page=4)",
  "sources": [
    {
      "document": "Newest_Factsheet",
      "title": "Newest® Factsheet",
      "page": 2,
      "relevance_score": 0.88,
      "view_url": "/api/documents/view?doc_id=Newest_Factsheet&page=2",
      "download_url": "/api/documents/download/Newest_Factsheet"
    },
    {
      "document": "Plinest_Guide",
      "title": "Plinest® Product Guide",
      "page": 4,
      "relevance_score": 0.85,
      "view_url": "/api/documents/view?doc_id=Plinest_Guide&page=4",
      "download_url": "/api/documents/download/Plinest_Guide"
    }
  ],
  "confidence": 0.82
}
```

---

## Testing the Implementation

### 1. Test Document View Endpoint

```bash
# View a document at page 3
curl "http://localhost:8000/api/documents/view?doc_id=Newest_Factsheet&page=3"
```

### 2. Test Document Info

```bash
curl "http://localhost:8000/api/documents/info/Newest_Factsheet"
```

### 3. Test Chat with Citations

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"question": "What is the needle size for Plinest Eye?"}'
```

---

## Security Considerations

1. **Path Traversal Prevention**: Document IDs are sanitized before file access
2. **Access Control**: Add authentication to document endpoints if needed
3. **CORS**: Configure CORS for your frontend domain
4. **Rate Limiting**: Consider rate limiting document downloads

---

## Future Enhancements

1. **Text Highlighting**: Highlight the specific text that was retrieved
2. **Thumbnail Preview**: Show PDF page thumbnails in source cards
3. **Search Within Document**: Allow searching within opened documents
4. **Annotation Support**: Let users annotate and bookmark sources
5. **Citation Export**: Export citations in various formats (BibTeX, etc.)
