import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  User,
  Loader2,
  RefreshCw,
  MessageCircle,
  Sparkles,
  Bot,
  ChevronRight,
  FileText,
  ExternalLink,
  BookOpen,
  Zap,
  Shield,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  HelpCircle
} from 'lucide-react';
import { Message, Source } from '../../types';
import { apiService, ChatResponse } from '../../services/apiService';
import { API_BASE_URL } from '../../config';

interface ChatWindowProps {}

const STATIC_SUGGESTIONS = [
  { text: "What is Newest?", icon: Sparkles },
  { text: "Plinest Eye injection protocol", icon: BookOpen },
  { text: "Purasomes mechanism of action", icon: Zap },
  { text: "Contraindications for polynucleotides", icon: Shield }
];

// Confidence configuration
const getConfidenceConfig = (confidence: number) => {
  if (confidence >= 0.75) {
    return {
      label: 'High Confidence',
      short: 'High',
      icon: CheckCircle2,
      gradient: 'from-emerald-500 to-emerald-600',
      bg: 'bg-emerald-50',
      border: 'border-emerald-200',
      text: 'text-emerald-700',
      dot: 'bg-emerald-500'
    };
  }
  if (confidence >= 0.55) {
    return {
      label: 'Medium Confidence',
      short: 'Medium',
      icon: AlertCircle,
      gradient: 'from-amber-500 to-amber-600',
      bg: 'bg-amber-50',
      border: 'border-amber-200',
      text: 'text-amber-700',
      dot: 'bg-amber-500'
    };
  }
  return {
    label: 'Low Confidence',
    short: 'Low',
    icon: HelpCircle,
    gradient: 'from-red-500 to-red-600',
    bg: 'bg-red-50',
    border: 'border-red-200',
    text: 'text-red-600',
    dot: 'bg-red-500'
  };
};

const ChatWindow: React.FC<ChatWindowProps> = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [useStreaming] = useState(true);
  const [dynamicSuggestions, setDynamicSuggestions] = useState<string[]>([]);
  const [conversationId, setConversationId] = useState<string>(`conv_${Date.now()}`);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const isWelcomeState = messages.length === 0;

  const buildConversationHistory = () => {
    return messages
      .slice(-10)
      .map(m => ({
        role: m.role === 'user' ? 'user' as const : 'assistant' as const,
        content: m.text.replace(/<follow_ups>[\s\S]*?<\/follow_ups>/, '').trim()
      }));
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSendStreaming = async (query: string) => {
    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      text: query,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);

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
      const history = buildConversationHistory();

      for await (const chunk of apiService.sendMessageStream(
        query,
        conversationId,
        history,
        (receivedSources) => {
          sources = receivedSources;
        },
        (receivedFollowUps) => {
          followUps = receivedFollowUps;
          setDynamicSuggestions(receivedFollowUps);
        },
        (receivedConversationId) => {
          if (receivedConversationId) {
            setConversationId(receivedConversationId);
          }
        }
      )) {
        fullText += chunk;
        setMessages(prev => prev.map(msg =>
          msg.id === botMsgId
            ? { ...msg, text: fullText, isStreaming: true }
            : msg
        ));
      }

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
              ? `Unable to process request: ${error.message}`
              : 'An error occurred',
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

    if (useStreaming) {
      await handleSendStreaming(query);
      return;
    }

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      text: query,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const history = buildConversationHistory();
      const response: ChatResponse = await apiService.sendMessage(query, conversationId, history);
      if (response.conversation_id) {
        setConversationId(response.conversation_id);
      }

      const botMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'model',
        text: response.answer,
        timestamp: new Date(),
        isStreaming: false,
        sources: response.sources || [],
        confidence: response.confidence
      };

      if (response.follow_ups && response.follow_ups.length > 0) {
        botMsg.text += `\n\n<follow_ups>${JSON.stringify(response.follow_ups)}</follow_ups>`;
        setDynamicSuggestions(response.follow_ups);
      }

      setMessages(prev => [...prev, botMsg]);

    } catch (error) {
      console.error('API Error:', error);
      const errorMsg: Message = {
        id: Date.now().toString(),
        role: 'model',
        text: error instanceof Error
          ? `Connection error: ${error.message}`
          : "Unable to connect to the server.",
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setConversationId(`conv_${Date.now()}`);
    setDynamicSuggestions([]);
    setMessages([]);
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const cleanText = (text: string) => {
    return text.replace(/<follow_ups>[\s\S]*?<\/follow_ups>/, '').trim();
  };

  // Render formatted message content
  const renderMessageContent = (text: string) => {
    const lines = cleanText(text).split('\n');

    return lines.map((line, i) => {
      // Headers
      if (line.startsWith('## ')) {
        return (
          <h2 key={i} className="text-base font-semibold text-slate-800 mt-4 mb-2 first:mt-0">
            {line.slice(3)}
          </h2>
        );
      }
      if (line.startsWith('### ')) {
        return (
          <h3 key={i} className="text-sm font-semibold text-slate-700 mt-3 mb-1.5">
            {line.slice(4)}
          </h3>
        );
      }

      // Bold text handling
      let content: React.ReactNode = line;
      if (line.includes('**')) {
        const parts = line.split(/(\*\*.*?\*\*)/g);
        content = parts.map((part, j) => {
          if (part.startsWith('**') && part.endsWith('**')) {
            return <strong key={j} className="font-semibold text-slate-800">{part.slice(2, -2)}</strong>;
          }
          return part;
        });
      }

      // Bullet points
      if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
        return (
          <div key={i} className="flex items-start gap-2.5 py-1 ml-1">
            <span className="w-1.5 h-1.5 rounded-full bg-gradient-to-r from-teal-400 to-teal-500 mt-2 shrink-0" />
            <span className="text-slate-600 leading-relaxed">{typeof content === 'string' ? line.trim().slice(2) : content}</span>
          </div>
        );
      }

      // Regular paragraph
      if (line.trim()) {
        return (
          <p key={i} className="text-slate-600 leading-relaxed mb-2 last:mb-0">
            {content}
          </p>
        );
      }

      return <div key={i} className="h-2" />;
    });
  };

  // Welcome Screen Component
  const WelcomeScreen = () => (
    <div className="flex-1 flex flex-col items-center justify-center px-6 py-12">
      {/* Hero Section */}
      <div className="text-center mb-10">
        <div className="inline-flex items-center justify-center w-20 h-20 rounded-3xl bg-gradient-to-br from-teal-500 via-teal-600 to-emerald-600 shadow-xl shadow-teal-500/25 mb-6">
          <Sparkles size={36} className="text-white" />
        </div>
        <h1 className="text-2xl font-bold text-slate-800 mb-3">
          Clinical Intelligence Assistant
        </h1>
        <p className="text-slate-500 max-w-md mx-auto leading-relaxed">
          Access product documentation, clinical papers, and treatment protocols.
          Every response is grounded in official materials with source citations.
        </p>
      </div>

      {/* Quick Start Cards */}
      <div className="w-full max-w-2xl">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4 text-center">
          Try asking about
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {STATIC_SUGGESTIONS.map((suggestion, idx) => {
            const Icon = suggestion.icon;
            return (
              <button
                key={idx}
                onClick={() => handleSend(suggestion.text)}
                disabled={isLoading}
                className="group flex items-center gap-4 p-4 rounded-2xl bg-white border border-slate-200 hover:border-teal-300 hover:shadow-lg hover:shadow-teal-500/10 transition-all duration-200 text-left"
              >
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-slate-100 to-slate-50 group-hover:from-teal-100 group-hover:to-teal-50 flex items-center justify-center transition-colors">
                  <Icon size={18} className="text-slate-500 group-hover:text-teal-600 transition-colors" />
                </div>
                <div className="flex-1 min-w-0">
                  <span className="text-sm font-medium text-slate-700 group-hover:text-slate-900 transition-colors">
                    {suggestion.text}
                  </span>
                </div>
                <ArrowRight size={16} className="text-slate-300 group-hover:text-teal-500 group-hover:translate-x-1 transition-all" />
              </button>
            );
          })}
        </div>
      </div>

      {/* Features */}
      <div className="flex items-center gap-6 mt-10 text-xs text-slate-400">
        <div className="flex items-center gap-1.5">
          <CheckCircle2 size={12} className="text-emerald-500" />
          <span>RAG-Powered</span>
        </div>
        <div className="flex items-center gap-1.5">
          <FileText size={12} className="text-teal-500" />
          <span>Source Citations</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Shield size={12} className="text-blue-500" />
          <span>Clinical Accuracy</span>
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex flex-col h-full bg-gradient-to-b from-slate-50 via-white to-slate-50">
      {/* Messages Area or Welcome Screen */}
      {isWelcomeState ? (
        <WelcomeScreen />
      ) : (
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
              >
                {/* Avatar */}
                <div className={`
                  w-9 h-9 rounded-2xl flex items-center justify-center shrink-0 shadow-md
                  ${msg.role === 'user'
                    ? 'bg-gradient-to-br from-slate-700 to-slate-800'
                    : 'bg-gradient-to-br from-teal-500 to-emerald-600'}
                `}>
                  {msg.role === 'user'
                    ? <User size={16} className="text-white" />
                    : <Bot size={16} className="text-white" />}
                </div>

                {/* Message Content */}
                <div className={`max-w-[80%] ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                  {/* User Message */}
                  {msg.role === 'user' && (
                    <div className="bg-gradient-to-br from-slate-800 to-slate-900 text-white px-5 py-3.5 rounded-2xl rounded-tr-md shadow-lg shadow-slate-900/10">
                      <p className="text-sm leading-relaxed">{msg.text}</p>
                    </div>
                  )}

                  {/* Bot Message */}
                  {msg.role === 'model' && (
                    <div className="bg-white border border-slate-200/80 rounded-2xl rounded-tl-md shadow-sm overflow-hidden">
                      {/* Streaming Header */}
                      {msg.isStreaming && (
                        <div className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-teal-50 to-emerald-50 border-b border-teal-100/50">
                          <div className="flex gap-1">
                            <span className="w-2 h-2 bg-teal-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                            <span className="w-2 h-2 bg-teal-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                            <span className="w-2 h-2 bg-teal-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                          </div>
                          <span className="text-xs font-semibold text-teal-700">
                            Generating response...
                          </span>
                        </div>
                      )}

                      {/* Message Text */}
                      <div className="px-5 py-4">
                        <div className="text-sm">
                          {renderMessageContent(msg.text)}
                          {msg.isStreaming && (
                            <span className="inline-block w-0.5 h-4 bg-teal-500 ml-0.5 animate-pulse" />
                          )}
                        </div>
                      </div>

                      {/* Sources Section */}
                      {!msg.isStreaming && msg.sources && msg.sources.length > 0 && (
                        <div className="px-5 pb-4">
                          <div className="pt-4 border-t border-slate-100">
                            {/* Sources Header */}
                            <div className="flex items-center justify-between mb-3">
                              <div className="flex items-center gap-2">
                                <div className="w-6 h-6 rounded-lg bg-slate-100 flex items-center justify-center">
                                  <FileText size={12} className="text-slate-500" />
                                </div>
                                <span className="text-xs font-semibold text-slate-600">
                                  Sources ({msg.sources.length})
                                </span>
                              </div>
                              {msg.confidence !== undefined && msg.confidence > 0 && (
                                <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold ${getConfidenceConfig(msg.confidence).bg} ${getConfidenceConfig(msg.confidence).border} border ${getConfidenceConfig(msg.confidence).text}`}>
                                  <div className={`w-1.5 h-1.5 rounded-full ${getConfidenceConfig(msg.confidence).dot}`} />
                                  {getConfidenceConfig(msg.confidence).short} ({Math.round(msg.confidence * 100)}%)
                                </div>
                              )}
                            </div>

                            {/* Source Cards */}
                            <div className="space-y-2">
                              {msg.sources.map((source, idx) => (
                                <a
                                  key={idx}
                                  href={source.view_url ? `${API_BASE_URL}${source.view_url}` : '#'}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="group flex items-center gap-3 p-3 rounded-xl bg-gradient-to-r from-slate-50 to-white hover:from-teal-50 hover:to-white border border-slate-100 hover:border-teal-200 transition-all duration-200"
                                >
                                  <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-teal-500 to-teal-600 flex items-center justify-center shadow-sm">
                                    <span className="text-[11px] font-bold text-white">{idx + 1}</span>
                                  </div>
                                  <div className="flex-1 min-w-0">
                                    <p className="text-sm font-medium text-slate-700 group-hover:text-teal-700 truncate transition-colors">
                                      {source.title || source.document}
                                    </p>
                                    <p className="text-[11px] text-slate-400 mt-0.5">
                                      Page {source.page} {source.section && `• ${source.section}`}
                                    </p>
                                  </div>
                                  <div className="flex items-center gap-2 shrink-0">
                                    <span className="text-[10px] font-medium text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">
                                      {Math.round(source.relevance_score * 100)}% match
                                    </span>
                                    <ExternalLink size={14} className="text-slate-300 group-hover:text-teal-500 transition-colors" />
                                  </div>
                                </a>
                              ))}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Timestamp */}
                  <p className={`text-[10px] text-slate-400 mt-1.5 ${msg.role === 'user' ? 'text-right mr-1' : 'ml-1'}`}>
                    {formatTime(msg.timestamp)}
                  </p>
                </div>
              </div>
            ))}

            {/* Loading State */}
            {isLoading && messages[messages.length - 1]?.role !== 'model' && (
              <div className="flex gap-3">
                <div className="w-9 h-9 rounded-2xl bg-gradient-to-br from-teal-500 to-emerald-600 flex items-center justify-center shadow-md">
                  <Bot size={16} className="text-white" />
                </div>
                <div className="bg-white border border-slate-200/80 rounded-2xl rounded-tl-md px-5 py-4 shadow-sm">
                  <div className="flex items-center gap-3">
                    <Loader2 size={16} className="animate-spin text-teal-500" />
                    <span className="text-sm text-slate-500">Searching documentation...</span>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>
      )}

      {/* Input Section */}
      <div className="border-t border-slate-200/60 bg-white/80 backdrop-blur-xl">
        <div className="max-w-3xl mx-auto px-4 py-4">
          {/* Dynamic Suggestions */}
          {!isWelcomeState && (
            <div className="mb-3 flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
              {(dynamicSuggestions.length > 0 ? dynamicSuggestions : STATIC_SUGGESTIONS.map(s => s.text)).slice(0, 4).map((suggestion, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSend(typeof suggestion === 'string' ? suggestion : suggestion)}
                  disabled={isLoading}
                  className={`shrink-0 flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all border ${
                    dynamicSuggestions.length > 0
                      ? 'bg-gradient-to-r from-teal-50 to-emerald-50 hover:from-teal-100 hover:to-emerald-100 text-teal-700 border-teal-200 hover:border-teal-300'
                      : 'bg-white hover:bg-slate-50 text-slate-600 border-slate-200 hover:border-slate-300'
                  } disabled:opacity-50 shadow-sm`}
                >
                  {dynamicSuggestions.length > 0 && <MessageCircle size={12} />}
                  <span className="truncate max-w-[200px]">{suggestion}</span>
                </button>
              ))}
            </div>
          )}

          {/* Input Field */}
          <div className="relative">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Ask about products, protocols, or clinical guidelines..."
              className="w-full bg-slate-50 border border-slate-200 text-slate-800 rounded-2xl pl-5 pr-14 py-4 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-400 focus:bg-white transition-all placeholder:text-slate-400 text-sm shadow-sm"
            />
            <button
              onClick={() => handleSend()}
              disabled={!input.trim() || isLoading}
              className="absolute right-2 top-1/2 -translate-y-1/2 w-10 h-10 bg-gradient-to-r from-teal-500 to-teal-600 hover:from-teal-600 hover:to-teal-700 text-white rounded-xl flex items-center justify-center disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-lg shadow-teal-500/25 disabled:shadow-none"
            >
              <Send size={16} />
            </button>
          </div>

          {/* Footer */}
          <div className="mt-3 flex items-center justify-between">
            <p className="text-[11px] text-slate-400">
              Responses sourced from official DermaFocus documentation
            </p>
            {messages.length > 0 && (
              <button
                onClick={handleReset}
                className="flex items-center gap-1.5 text-[11px] text-slate-400 hover:text-slate-600 transition-colors"
              >
                <RefreshCw size={10} />
                <span>New conversation</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatWindow;
