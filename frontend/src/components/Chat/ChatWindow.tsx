import React, { useState, useRef, useEffect } from 'react';
import { Send, User, Loader2, RefreshCw, ShieldCheck, Zap, MessageCircle, FileText } from 'lucide-react';
import { Message, Source } from '../../types';
import { apiService, ChatResponse } from '../../services/apiService';

interface ChatWindowProps { }

const STATIC_SUGGESTIONS = [
  "Plinest Eye injection protocol",
  "Newest dosing for facial rejuvenation",
  "Purasomes Skin Glow composition",
  "NewGyn vulvar treatment protocol",
  "Contraindications for polynucleotides"
];

// Confidence tier classification for better UX
const getConfidenceTier = (confidence: number): { label: string; color: string; bgColor: string } => {
  if (confidence >= 0.75) {
    return { label: 'High', color: 'text-emerald-700', bgColor: 'bg-emerald-50 border-emerald-200' };
  } else if (confidence >= 0.55) {
    return { label: 'Medium', color: 'text-amber-700', bgColor: 'bg-amber-50 border-amber-200' };
  } else {
    return { label: 'Low', color: 'text-red-600', bgColor: 'bg-red-50 border-red-200' };
  }
};

const ChatWindow: React.FC<ChatWindowProps> = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'model',
      text: "System Ready. I am the DermaFocus Clinical Reference Agent.\n\nConnected to DermaAI CKPA Backend API. Every clinical fact will be cited with document and page references for regulatory defensibility. \n\nHow can I assist your clinical practice today?",
      timestamp: new Date()
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [useStreaming, setUseStreaming] = useState(true);
  const [dynamicSuggestions, setDynamicSuggestions] = useState<string[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendStreaming = async (query: string) => {
    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      text: query,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);

    // Create placeholder for streaming message
    const botMsgId = (Date.now() + 1).toString();
    const botMsg: Message = {
      id: botMsgId,
      role: 'model',
      text: '',
      timestamp: new Date(),
      isStreaming: true,
      sources: [],
      confidence: 0
    };

    setMessages(prev => [...prev, botMsg]);

    try {
      let fullText = '';
      let sources: Source[] = [];
      let followUps: string[] = [];

      // Stream the response
      for await (const chunk of apiService.sendMessageStream(
        query,
        undefined,
        [],
        (receivedSources) => {
          sources = receivedSources;
        },
        (receivedFollowUps) => {
          followUps = receivedFollowUps;
          // Update dynamic suggestions immediately when received
          setDynamicSuggestions(receivedFollowUps);
        }
      )) {
        fullText += chunk;

        // Update message with new text
        setMessages(prev => prev.map(msg =>
          msg.id === botMsgId
            ? { ...msg, text: fullText, isStreaming: true }
            : msg
        ));
      }

      // Finalize message with sources and follow-ups
      let finalText = fullText;
      if (followUps.length > 0) {
        finalText += `\n\n<follow_ups>${JSON.stringify(followUps)}</follow_ups>`;
      }

      setMessages(prev => prev.map(msg =>
        msg.id === botMsgId
          ? {
            ...msg,
            text: finalText,
            isStreaming: false,
            sources: sources,
            confidence: sources.length > 0
              ? sources.reduce((sum, s) => sum + s.relevance_score, 0) / sources.length
              : 0
          }
          : msg
      ));

    } catch (error) {
      console.error('Streaming Error:', error);
      setMessages(prev => prev.map(msg =>
        msg.id === botMsgId
          ? {
            ...msg,
            text: error instanceof Error
              ? `System Error: ${error.message}`
              : 'Streaming error occurred',
            isStreaming: false
          }
          : msg
      ));
    } finally {
      setIsLoading(false);
    }
  };

  const handleSend = async (overrideInput?: string) => {
    const query = (overrideInput || input).trim();
    if (!query || isLoading) return;

    setInput('');

    // Use streaming or instant based on toggle
    if (useStreaming) {
      await handleSendStreaming(query);
      return;
    }

    // Original instant response handling
    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      text: query,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);

    try {
      // Call backend API
      const response: ChatResponse = await apiService.sendMessage(query);

      const botMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'model',
        text: response.answer,
        timestamp: new Date(),
        isStreaming: false,
        sources: response.sources || [],
        confidence: response.confidence
      };

      // Add follow-ups to the message text if present
      if (response.follow_ups && response.follow_ups.length > 0) {
        botMsg.text += `\n\n<follow_ups>${JSON.stringify(response.follow_ups)}</follow_ups>`;
        // Update dynamic suggestions for the suggestion bar
        setDynamicSuggestions(response.follow_ups);
      }

      setMessages(prev => [...prev, botMsg]);

    } catch (error) {
      console.error('API Error:', error);
      const errorMsg: Message = {
        id: Date.now().toString(),
        role: 'model',
        text: error instanceof Error
          ? `System Error: ${error.message}\n\nPlease ensure the backend server is running at http://localhost:8000`
          : "System fault: Unable to retrieve clinical evidence. Please check your connection and try again.",
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    // Clear messages and reset conversation
    setMessages([
      {
        id: Date.now().toString(),
        role: 'model',
        text: "Session cleared. Clinical context reset. Ready for new query.",
        timestamp: new Date()
      }
    ]);
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const cleanText = (text: string) => {
    return text.replace(/<follow_ups>[\s\S]*?<\/follow_ups>/, '').trim();
  };

  const formatMessageText = (text: string) => {
    const lines = cleanText(text).split('\n');
    return lines.map((line, i) => {
      // Step 1: Split by bold text
      let parts: (string | React.ReactNode)[] = line.split(/(\*\*.*?\*\*)/g);

      // Step 2: Handle Citations: [Document Name, p. X]
      parts = parts.flatMap((part) => {
        if (typeof part !== 'string') return part;

        const subParts = part.split(/(\[.*?, p\. \d+\])/g);
        return subParts.map((sub, k) => {
          if (sub.startsWith('[') && sub.includes(', p. ') && sub.endsWith(']')) {
            return (
              <span key={`cite-${k}`} className="inline-flex items-center gap-1 bg-teal-50 text-teal-700 px-1.5 py-0.5 rounded text-[10px] font-bold border border-teal-200 mx-1 align-middle whitespace-nowrap">
                <ShieldCheck size={10} />
                {sub.slice(1, -1)}
              </span>
            );
          }
          if (sub.startsWith('**') && sub.endsWith('**')) {
            return <strong key={`bold-${k}`} className="font-semibold text-slate-900">{sub.slice(2, -2)}</strong>;
          }
          // Bullets formatting
          if (sub.trim().startsWith('- ') || sub.trim().startsWith('* ')) {
            return (
              <span key={k} className="flex items-start gap-2 py-0.5">
                <span className="w-1.5 h-1.5 rounded-full bg-teal-400 mt-1.5 shrink-0" />
                <span>{sub.trim().slice(2)}</span>
              </span>
            );
          }
          return sub;
        });
      });

      return (
        <div key={i} className="min-h-[1.2em] mb-1">
          {parts}
        </div>
      );
    });
  };

  return (
    <div className="flex flex-col h-full bg-slate-50 relative">
      <div className="absolute top-4 right-4 z-10 flex gap-2">
        <button
          onClick={() => setUseStreaming(!useStreaming)}
          className={`px-3 py-2 rounded-full shadow-sm border transition-all flex items-center gap-2 text-xs font-bold ${useStreaming
              ? 'bg-teal-50 text-teal-600 border-teal-200 hover:bg-teal-100'
              : 'bg-white text-slate-400 border-slate-200 hover:bg-slate-50'
            }`}
          title={useStreaming ? 'Streaming Mode (word-by-word)' : 'Instant Mode (full response)'}
        >
          <Zap size={16} className={useStreaming ? 'text-teal-500' : 'text-slate-400'} />
          <span className="hidden sm:inline">{useStreaming ? 'Streaming' : 'Instant'}</span>
        </button>

        <button
          onClick={handleReset}
          className="bg-white p-2 rounded-full shadow-sm text-slate-400 hover:text-teal-600 border border-slate-200 transition-all"
          title="Reset Retrieval Cache"
        >
          <RefreshCw size={16} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6 scrollbar-hide">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col gap-2 ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
          >
            <div className={`flex gap-3 w-full ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
              <div className={`
                w-8 h-8 rounded-full flex items-center justify-center shrink-0
                ${msg.role === 'user' ? 'bg-slate-200 text-slate-600' : 'bg-slate-900 text-teal-400'}
              `}>
                {msg.role === 'user' ? <User size={16} /> : <ShieldCheck size={16} />}
              </div>

              <div className={`
                max-w-[85%] sm:max-w-[75%] rounded-2xl px-5 py-3 shadow-sm text-sm leading-relaxed
                ${msg.role === 'user'
                  ? 'bg-white text-slate-800 rounded-tr-none border border-slate-200'
                  : 'bg-white text-slate-800 rounded-tl-none border border-teal-100'}
              `}>
                {msg.role === 'model' && (
                  <div className="flex items-center gap-2 mb-2">
                    <span className="relative flex h-2 w-2">
                      {msg.isStreaming ? (
                        <>
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-teal-400 opacity-75"></span>
                          <span className="relative inline-flex rounded-full h-2 w-2 bg-teal-500 animate-pulse"></span>
                        </>
                      ) : (
                        <>
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-teal-400 opacity-75"></span>
                          <span className="relative inline-flex rounded-full h-2 w-2 bg-teal-500"></span>
                        </>
                      )}
                    </span>
                    <span className="text-[10px] font-bold text-teal-600 uppercase tracking-widest">
                      {msg.isStreaming ? 'Streaming...' : 'Verified Clinical Evidence'}
                    </span>
                  </div>
                )}
                <div className="text-slate-700 whitespace-pre-wrap">
                  {formatMessageText(msg.text)}
                  {msg.isStreaming && (
                    <span className="inline-block w-0.5 h-4 bg-teal-500 ml-1 animate-pulse"></span>
                  )}
                </div>

                {/* Display Sources */}
                {msg.role === 'model' && !msg.isStreaming && msg.sources && msg.sources.length > 0 && (
                  <div className="mt-4 pt-3 border-t border-slate-100 animate-fadeIn">
                    <div className="flex items-center gap-2 mb-2">
                      <FileText size={12} className="text-teal-600" />
                      <span className="text-[10px] font-bold text-slate-600 uppercase tracking-wider">
                        Sources ({msg.sources.length})
                      </span>
                      {msg.confidence !== undefined && msg.confidence > 0 && (
                        <span className={`text-[9px] font-semibold ml-auto px-2 py-0.5 rounded border ${getConfidenceTier(msg.confidence).bgColor} ${getConfidenceTier(msg.confidence).color}`}>
                          {getConfidenceTier(msg.confidence).label} Confidence ({(msg.confidence * 100).toFixed(0)}%)
                        </span>
                      )}
                    </div>
                    <div className="space-y-2">
                      {msg.sources.map((source, idx) => (
                        <div
                          key={idx}
                          className="bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-[11px]"
                        >
                          <div className="flex items-start justify-between gap-2 mb-1">
                            <div className="flex items-center gap-1.5 text-teal-700 font-semibold">
                              <ShieldCheck size={11} className="shrink-0" />
                              <span className="truncate">{source.document}</span>
                            </div>
                            <span className="text-teal-600 font-mono shrink-0">
                              p. {source.page}
                            </span>
                          </div>
                          {source.section && (
                            <div className="text-slate-500 text-[10px] mb-1">
                              Section: {source.section}
                            </div>
                          )}
                          {source.text_snippet && (
                            <div className="text-slate-600 text-[10px] leading-relaxed mt-1.5 pt-1.5 border-t border-slate-200">
                              "{source.text_snippet}"
                            </div>
                          )}
                          <div className="flex items-center justify-between mt-1.5 pt-1 border-t border-slate-200">
                            <span className="text-slate-400 text-[9px]">
                              Relevance: {(source.relevance_score * 100).toFixed(0)}%
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="mt-2 text-[10px] text-slate-400 text-right font-mono">
                  {formatTime(msg.timestamp)}
                </div>
              </div>
            </div>

          </div>
        ))}
        {isLoading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-slate-900 text-teal-400 flex items-center justify-center">
              <ShieldCheck size={16} className="animate-pulse" />
            </div>
            <div className="bg-white px-4 py-3 rounded-2xl rounded-tl-none border border-teal-100 flex items-center gap-2">
              <Loader2 size={16} className="animate-spin text-teal-600" />
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
                {useStreaming ? 'Retrieving Evidence...' : 'Querying Backend API...'}
              </span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Section */}
      <div className="bg-white border-t border-slate-200 p-4">
        {/* Quick Query Suggestions - Dynamic or Static */}
        <div className="max-w-4xl mx-auto mb-4 overflow-x-auto scrollbar-hide flex items-center gap-2 py-1">
          {(dynamicSuggestions.length > 0 ? dynamicSuggestions : STATIC_SUGGESTIONS).map((suggestion, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(suggestion)}
              disabled={isLoading}
              className={`shrink-0 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                dynamicSuggestions.length > 0
                  ? 'bg-teal-50 hover:bg-teal-100 text-teal-700 border border-teal-200 hover:border-teal-300'
                  : 'bg-slate-50 hover:bg-teal-50 text-slate-600 hover:text-teal-700 border border-slate-200 hover:border-teal-200'
              }`}
            >
              {dynamicSuggestions.length > 0 && <MessageCircle size={10} className="inline mr-1.5 text-teal-500" />}
              {suggestion}
            </button>
          ))}
        </div>

        <div className="max-w-4xl mx-auto relative">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Search clinical manual or protocols..."
            className="w-full bg-slate-50 border border-slate-300 text-slate-900 rounded-xl pl-4 pr-12 py-3.5 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent transition-all placeholder:text-slate-400 text-sm font-medium"
          />
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || isLoading}
            className="absolute right-2 top-2.5 p-1.5 bg-teal-600 text-white rounded-lg hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm"
          >
            <Send size={18} />
          </button>
        </div>

        <div className="flex justify-between items-center mt-3 px-1 max-w-4xl mx-auto">
          <p className="text-[9px] text-slate-400 font-bold uppercase tracking-tighter flex items-center gap-1">
            <ShieldCheck size={10} className="text-teal-500" />
            Regulatory-Gated Verification Active
          </p>
          <p className="text-[9px] text-slate-400 italic">
            DermaFocus © 2025 Clinical AI
          </p>
        </div>
      </div>
    </div>
  );
};

export default ChatWindow;