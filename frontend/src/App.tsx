import React, { useState } from 'react';
import ChatWindow from './components/Chat/ChatWindow';
import ProtocolList from './components/Protocols/ProtocolList';
import ProtocolDetail from './components/Protocols/ProtocolDetail';
import ProductHub from './components/Products/ProductHub';
import SafetyPanel from './components/Safety/SafetyPanel';
import SystemDocs from './components/Docs/SystemDocs';
import Dashboard from './components/Dashboard/Dashboard';
import { ViewState, Protocol } from './types';
import { useTheme } from './hooks/useTheme';
import {
  Activity,
  LayoutGrid,
  MessageSquare,
  FileText,
  Package,
  Shield,
  Sparkles,
  Moon,
  Sun,
  X
} from 'lucide-react';

// Navigation items
const NAV_ITEMS = [
  { id: 'HOME', label: 'HOME', icon: LayoutGrid },
  { id: ViewState.CHAT, label: 'ASSISTANT', icon: MessageSquare },
  { id: ViewState.PROTOCOLS, label: 'PROTOCOLS', icon: FileText },
  { id: ViewState.PRODUCTS, label: 'PRODUCTS', icon: Package },
  { id: ViewState.SAFETY, label: 'SAFETY', icon: Shield },
];

const App: React.FC = () => {
  const { theme, toggleTheme } = useTheme();
  const [currentView, setCurrentView] = useState<string>('HOME');
  const [selectedProtocol, setSelectedProtocol] = useState<Protocol | null>(null);
  const [isChatOpen, setIsChatOpen] = useState(false);

  const renderContent = () => {
    // Chat modal/overlay
    if (isChatOpen) {
      return (
        <div className="fixed inset-0 z-50 bg-white dark:bg-slate-900">
          <div className="h-full flex flex-col">
            {/* Chat Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-slate-800 to-slate-900 flex items-center justify-center">
                  <Sparkles size={20} className="text-teal-400" />
                </div>
                <div>
                  <h1 className="text-lg font-semibold text-slate-800 dark:text-slate-100">Clinical Assistant</h1>
                  <p className="text-xs text-slate-500 dark:text-slate-400">Powered by RAG Intelligence</p>
                </div>
              </div>
              <button
                onClick={() => setIsChatOpen(false)}
                aria-label="Close chat"
                className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 transition-colors"
              >
                <X size={20} />
              </button>
            </div>
            {/* Chat Content */}
            <div className="flex-1 overflow-hidden">
              <ChatWindow />
            </div>
          </div>
        </div>
      );
    }

    switch (currentView) {
      case ViewState.CHAT:
        return <ChatWindow />;
      case ViewState.PROTOCOLS:
        if (selectedProtocol) {
          return (
            <ProtocolDetail
              protocol={selectedProtocol}
              onBack={() => setSelectedProtocol(null)}
            />
          );
        }
        return <ProtocolList onSelect={setSelectedProtocol} />;
      case ViewState.PRODUCTS:
        return <ProductHub />;
      case ViewState.SAFETY:
        return <SafetyPanel />;
      case ViewState.DOCS:
        return <SystemDocs />;
      case 'HOME':
      default:
        return <Dashboard onLaunchChat={() => setIsChatOpen(true)} onNavigate={setCurrentView} />;
    }
  };

  return (
    <div className="min-h-screen bg-slate-50/50 dark:bg-slate-950 transition-colors">
      {/* Top Navigation */}
      <nav className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 sticky top-0 z-40 transition-colors">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-slate-100 to-slate-200 dark:from-slate-800 dark:to-slate-700 flex items-center justify-center border border-slate-200 dark:border-slate-700">
                <Activity size={22} className="text-teal-600 dark:text-teal-400" />
              </div>
              <div>
                <span className="text-lg font-bold text-slate-800 dark:text-slate-100">DermaAI</span>
                <span className="hidden sm:block text-[10px] text-teal-600 dark:text-teal-400 font-semibold tracking-[0.2em] uppercase -mt-0.5">
                  Precision Intelligence
                </span>
              </div>
            </div>

            {/* Navigation Items */}
            <div className="hidden md:flex items-center gap-1">
              {NAV_ITEMS.map((item) => {
                const Icon = item.icon;
                const isActive = currentView === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => {
                      setCurrentView(item.id);
                      setSelectedProtocol(null);
                    }}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                      isActive
                        ? 'bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100'
                        : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-50 dark:hover:bg-slate-800/50'
                    }`}
                  >
                    <Icon size={16} className={isActive ? 'text-teal-600 dark:text-teal-400' : ''} />
                    <span className="tracking-wide">{item.label}</span>
                  </button>
                );
              })}
            </div>

            {/* Status & Theme Toggle */}
            <div className="flex items-center gap-3">
              <button
                onClick={toggleTheme}
                aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
                className="p-2 rounded-lg text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-700 dark:hover:text-slate-200 transition-colors"
              >
                {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
              </button>
              <div className="hidden sm:flex items-center gap-2 px-4 py-2 rounded-lg border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                <span className="text-xs font-semibold text-emerald-700 dark:text-emerald-400 tracking-wide">SYNC ACTIVE</span>
              </div>
            </div>
          </div>
        </div>

        {/* Mobile Navigation */}
        <div className="md:hidden border-t border-slate-100 dark:border-slate-800 overflow-x-auto">
          <div className="flex px-2 py-2 gap-1">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const isActive = currentView === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => {
                    setCurrentView(item.id);
                    setSelectedProtocol(null);
                  }}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${
                    isActive
                      ? 'bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100'
                      : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'
                  }`}
                >
                  <Icon size={14} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="min-h-[calc(100vh-4rem)]">
        <div key={currentView} className="animate-fade-in">
          {renderContent()}
        </div>
      </main>

      {/* Footer */}
      {currentView === 'HOME' && (
        <footer className="bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 py-4 transition-colors">
          <div className="max-w-7xl mx-auto px-4 sm:px-6">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-2 text-slate-400 dark:text-slate-500">
                <Shield size={14} />
                <span className="text-xs font-medium tracking-wide">
                  DERMAAI INTELLIGENCE FRAMEWORK 2026
                </span>
              </div>
              <div className="flex items-center gap-6">
                <button className="text-xs font-medium text-slate-500 dark:text-slate-400 hover:text-teal-600 dark:hover:text-teal-400 transition-colors tracking-wide">
                  DOSSIER ACCESS
                </button>
                <button className="text-xs font-medium text-slate-500 dark:text-slate-400 hover:text-teal-600 dark:hover:text-teal-400 transition-colors tracking-wide">
                  GOVERNANCE
                </button>
                <button className="text-xs font-medium text-slate-500 dark:text-slate-400 hover:text-teal-600 dark:hover:text-teal-400 transition-colors tracking-wide">
                  CLINICAL SUPPORT
                </button>
              </div>
            </div>
          </div>
        </footer>
      )}
    </div>
  );
};

export default App;
