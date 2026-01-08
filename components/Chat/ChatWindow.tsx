import React, { useState, useRef, useEffect } from 'react';
import { Send, User, Bot, Loader2, RefreshCw, Video, ShieldCheck, Zap, MessageCircle } from 'lucide-react';
import { Message } from '../../types';
import { apiService, ChatResponse } from '../../services/apiService';

interface ChatWindowProps {
  onStartLive: () => void;
}

const STATIC_SUGGESTIONS = [
  "What is the needle size for Plinest Eye?",
  "Show the Hand Rejuvenation protocol",
  "Dosing for Newest on perioral lines",
  "Mechanism of action for PN-HPT®",
  "Contraindications for fish allergy"
];

const ChatWindow: React.FC<ChatWindowProps> = ({ onStartLive }) => {
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
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (overrideInput?: string) => {
    const query = (overrideInput || input).trim();
    if (!query || isLoading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      text: query,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      // Call backend API
      const response: ChatResponse = await apiService.sendMessage(query);
      
      const botMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'model',
        text: response.answer,
        timestamp: new Date(),
        isStreaming: false
      };

      // Add follow-ups to the message text if present
      if (response.follow_ups && response.follow_ups.length > 0) {
        botMsg.text += `\n\n<follow_ups>${JSON.stringify(response.follow_ups)}</follow_ups>`;
      }

      setMessages(prev => [...prev, botMsg]);

      // Log sources if present (for debugging)
      if (response.sources && response.sources.length > 0) {
        console.log('Sources:', response.sources);
      }

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

  const extractFollowUps = (text: string) => {
    const match = text.match(/<follow_ups>([\s\S]*?)<\/follow_ups>/);
    if (match) {
      try {
        const cleanedJson = match[1].trim();
        return JSON.parse(cleanedJson) as string[];
      } catch (e) {
        return [];
      }
    }
    return [];
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
          onClick={onStartLive}
          className="bg-white px-3 py-2 rounded-full shadow-sm text-teal-600 hover:bg-teal-50 border border-slate-200 flex items-center gap-2 text-xs font-bold transition-all"
          title="Clinical Video Triage"
        >
            <Video size={16} />
            <span className="hidden sm:inline">Visual Analysis</span>
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
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-teal-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-teal-500"></span>
                    </span>
                    <span className="text-[10px] font-bold text-teal-600 uppercase tracking-widest">Verified Clinical Evidence</span>
                  </div>
                )}
                <div className="text-slate-700 whitespace-pre-wrap">
                  {formatMessageText(msg.text)}
                </div>
                <div className="mt-2 text-[10px] text-slate-400 text-right font-mono">
                  {formatTime(msg.timestamp)}
                </div>
              </div>
            </div>

            {/* Contextual Follow-ups for this message */}
            {msg.role === 'model' && !msg.isStreaming && extractFollowUps(msg.text).length > 0 && (
              <div className="ml-11 flex flex-wrap gap-2 mt-2">
                {extractFollowUps(msg.text).map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSend(q)}
                    className="bg-white hover:bg-teal-50 text-teal-700 border border-teal-100 px-3 py-1.5 rounded-full text-[11px] font-medium transition-all shadow-sm hover:shadow-md flex items-center gap-1.5"
                  >
                    <MessageCircle size={12} className="text-teal-400" />
                    {q}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
        {isLoading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-slate-900 text-teal-400 flex items-center justify-center">
              <ShieldCheck size={16} className="animate-pulse" />
            </div>
            <div className="bg-white px-4 py-3 rounded-2xl rounded-tl-none border border-teal-100 flex items-center gap-2">
              <Loader2 size={16} className="animate-spin text-teal-600" />
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Querying Backend API...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Section */}
      <div className="bg-white border-t border-slate-200 p-4">
        {/* Suggestion Chips (Permanent) */}
        <div className="max-w-4xl mx-auto mb-4 overflow-x-auto scrollbar-hide flex items-center gap-2 py-1">
          <div className="flex items-center gap-2 shrink-0 pr-4 border-r border-slate-100 mr-2">
             <Zap size={14} className="text-teal-500" />
             <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Reference</span>
          </div>
          {STATIC_SUGGESTIONS.map((suggestion, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(suggestion)}
              disabled={isLoading}
              className="shrink-0 px-3 py-1.5 bg-slate-50 hover:bg-teal-50 text-slate-600 hover:text-teal-700 border border-slate-200 hover:border-teal-200 rounded-full text-xs font-medium transition-all"
            >
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