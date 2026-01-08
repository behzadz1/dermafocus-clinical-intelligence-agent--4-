/**
 * API Service for DermaAI CKPA Backend
 * Replaces the Gemini service with calls to our FastAPI backend
 */

// Get API URL from environment variable or use localhost
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Types matching backend response models
export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
}

export interface Source {
  document: string;
  page: number;
  section?: string;
  relevance_score: number;
  text_snippet?: string;
}

export interface ChatResponse {
  answer: string;
  sources: Source[];
  intent?: string;
  confidence: number;
  conversation_id: string;
  follow_ups: string[];
}

export interface ChatRequest {
  question: string;
  conversation_id?: string;
  history?: Message[];
}

export interface HealthResponse {
  status: string;
  timestamp: string;
  version: string;
  environment: string;
  python_version: string;
}

/**
 * Main API Service
 */
export const apiService = {
  /**
   * Send a chat message and get response
   */
  async sendMessage(
    question: string,
    conversationId?: string,
    history: Message[] = []
  ): Promise<ChatResponse> {
    const request: ChatRequest = {
      question,
      conversation_id: conversationId,
      history
    };

    const response = await fetch(`${API_BASE_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request)
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `API Error: ${response.status}`);
    }

    return response.json();
  },

  /**
   * Send message with streaming response
   * Uses Server-Sent Events (SSE) for real-time word-by-word streaming
   */
  async *sendMessageStream(
    question: string,
    conversationId?: string,
    history: Message[] = [],
    onSources?: (sources: Source[]) => void
  ): AsyncGenerator<string, void, unknown> {
    const request: ChatRequest = {
      question,
      conversation_id: conversationId,
      history
    };

    const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request)
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `API Error: ${response.status}`);
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) {
      throw new Error('Response body is not readable');
    }

    try {
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
              if (data.type === 'content') {
                yield data.content;
              } else if (data.type === 'sources' && onSources) {
                onSources(data.sources);
              } else if (data.type === 'done') {
                return;
              } else if (data.type === 'error') {
                throw new Error(data.error);
              }
            } catch (e) {
              // Skip invalid JSON
              if (e instanceof SyntaxError) continue;
              throw e;
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  },

  /**
   * Check API health
   */
  async checkHealth(): Promise<HealthResponse> {
    const response = await fetch(`${API_BASE_URL}/api/health`);
    
    if (!response.ok) {
      throw new Error(`Health check failed: ${response.status}`);
    }
    
    return response.json();
  },

  /**
   * Get detailed health status including dependencies
   */
  async checkDetailedHealth(): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/api/health/detailed`);
    
    if (!response.ok) {
      throw new Error(`Detailed health check failed: ${response.status}`);
    }
    
    return response.json();
  },

  /**
   * Submit feedback for a response
   */
  async submitFeedback(
    conversationId: string,
    messageId: string,
    feedbackType: 'thumbs_up' | 'thumbs_down' | 'flag',
    comment?: string
  ): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/chat/feedback`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        conversation_id: conversationId,
        message_id: messageId,
        feedback_type: feedbackType,
        comment
      })
    });

    if (!response.ok) {
      throw new Error(`Failed to submit feedback: ${response.status}`);
    }
  },

  /**
   * Upload a document (for future use in Phase 2)
   */
  async uploadDocument(file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/api/documents/upload`, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Upload failed: ${response.status}`);
    }

    return response.json();
  }
};

/**
 * Utility to check if backend is available
 */
export async function isBackendAvailable(): Promise<boolean> {
  try {
    await apiService.checkHealth();
    return true;
  } catch (error) {
    console.error('Backend not available:', error);
    return false;
  }
}

/**
 * Initialize connection to backend
 * Call this when your app starts
 */
export async function initializeAPI(): Promise<boolean> {
  try {
    const health = await apiService.checkHealth();
    console.log('✅ Backend connected:', health);
    return true;
  } catch (error) {
    console.error('❌ Failed to connect to backend:', error);
    console.log(`Make sure backend is running at ${API_BASE_URL}`);
    return false;
  }
}

export default apiService;
