import React, { useState } from 'react';
import ChatWindow from './components/Chat/ChatWindow';
import ProtocolList from './components/Protocols/ProtocolList';
import ProtocolDetail from './components/Protocols/ProtocolDetail';
import ProductHub from './components/Products/ProductHub';
import SafetyPanel from './components/Safety/SafetyPanel';
import SystemDocs from './components/Docs/SystemDocs';
import { ViewState, Protocol } from './types';
import {
  Activity,
  LayoutGrid,
  MessageSquare,
  Calendar,
  FileText,
  Package,
  Shield,
  Sparkles,
  ChevronRight,
  BookOpen,
  Zap,
  CheckCircle2,
  Clock,
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

// Recommended protocols for dashboard
const RECOMMENDED_PROTOCOLS = [
  { title: 'Perioral Rejuvenation', area: 'PERIORAL', product: 'NEWEST®' },
  { title: 'Periorbital Biostimulation', area: 'PERIOCULAR', product: 'PLINEST® EYE' },
  { title: 'Hand Bio-revitalization', area: 'HANDS', product: 'PLINEST®' },
];

const App: React.FC = () => {
  const [currentView, setCurrentView] = useState<string>('HOME');
  const [selectedProtocol, setSelectedProtocol] = useState<Protocol | null>(null);
  const [isChatOpen, setIsChatOpen] = useState(false);

  const renderContent = () => {
    // Chat modal/overlay
    if (isChatOpen) {
      return (
        <div className="fixed inset-0 z-50 bg-white">
          <div className="h-full flex flex-col">
            {/* Chat Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-slate-800 to-slate-900 flex items-center justify-center">
                  <Sparkles size={20} className="text-teal-400" />
                </div>
                <div>
                  <h1 className="text-lg font-semibold text-slate-800">Clinical Assistant</h1>
                  <p className="text-xs text-slate-500">Powered by RAG Intelligence</p>
                </div>
              </div>
              <button
                onClick={() => setIsChatOpen(false)}
                className="p-2 rounded-lg hover:bg-slate-100 text-slate-500 hover:text-slate-700 transition-colors"
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
    <div className="min-h-screen bg-slate-50/50">
      {/* Top Navigation */}
      <nav className="bg-white border-b border-slate-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-slate-100 to-slate-200 flex items-center justify-center border border-slate-200">
                <Activity size={22} className="text-teal-600" />
              </div>
              <div>
                <span className="text-lg font-bold text-slate-800">DermaAI</span>
                <span className="hidden sm:block text-[10px] text-teal-600 font-semibold tracking-[0.2em] uppercase -mt-0.5">
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
                        ? 'bg-slate-100 text-slate-900'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                    }`}
                  >
                    <Icon size={16} className={isActive ? 'text-teal-600' : ''} />
                    <span className="tracking-wide">{item.label}</span>
                  </button>
                );
              })}
            </div>

            {/* Status Indicator */}
            <div className="flex items-center gap-3">
              <div className="hidden sm:flex items-center gap-2 px-4 py-2 rounded-lg border border-emerald-200 bg-emerald-50">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                <span className="text-xs font-semibold text-emerald-700 tracking-wide">SYNC ACTIVE</span>
              </div>
            </div>
          </div>
        </div>

        {/* Mobile Navigation */}
        <div className="md:hidden border-t border-slate-100 overflow-x-auto">
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
                      ? 'bg-slate-100 text-slate-900'
                      : 'text-slate-500 hover:text-slate-700'
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
        {renderContent()}
      </main>

      {/* Footer */}
      {currentView === 'HOME' && (
        <footer className="bg-white border-t border-slate-200 py-4">
          <div className="max-w-7xl mx-auto px-4 sm:px-6">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-2 text-slate-400">
                <Shield size={14} />
                <span className="text-xs font-medium tracking-wide">
                  DERMAAI INTELLIGENCE FRAMEWORK 2026
                </span>
              </div>
              <div className="flex items-center gap-6">
                <button className="text-xs font-medium text-slate-500 hover:text-teal-600 transition-colors tracking-wide">
                  DOSSIER ACCESS
                </button>
                <button className="text-xs font-medium text-slate-500 hover:text-teal-600 transition-colors tracking-wide">
                  GOVERNANCE
                </button>
                <button className="text-xs font-medium text-slate-500 hover:text-teal-600 transition-colors tracking-wide">
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

// Dashboard Component
interface DashboardProps {
  onLaunchChat: () => void;
  onNavigate: (view: string) => void;
}

const Dashboard: React.FC<DashboardProps> = ({ onLaunchChat, onNavigate }) => {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Stats & Protocols */}
        <div className="lg:col-span-2 space-y-6">
          {/* Stats Cards */}
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-white rounded-2xl border border-slate-200 p-5 hover:shadow-md transition-shadow">
              <BookOpen size={24} className="text-teal-500 mb-3" />
              <div className="text-3xl font-bold text-slate-800">3</div>
              <div className="text-xs font-semibold text-teal-600 tracking-wider mt-1">PROTOCOLS</div>
            </div>
            <div className="bg-white rounded-2xl border border-slate-200 p-5 hover:shadow-md transition-shadow">
              <Zap size={24} className="text-amber-500 mb-3" />
              <div className="text-3xl font-bold text-slate-800">3</div>
              <div className="text-xs font-semibold text-slate-500 tracking-wider mt-1">ACTIVE AGENTS</div>
            </div>
            <div className="bg-white rounded-2xl border border-slate-200 p-5 hover:shadow-md transition-shadow">
              <CheckCircle2 size={24} className="text-emerald-500 mb-3" />
              <div className="text-3xl font-bold text-slate-800">100%</div>
              <div className="text-xs font-semibold text-slate-500 tracking-wider mt-1">INTEGRITY</div>
            </div>
          </div>

          {/* Recommended Protocols */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-semibold text-slate-800">Recommended Protocols</h2>
              <button
                onClick={() => onNavigate(ViewState.PROTOCOLS)}
                className="flex items-center gap-1 text-sm font-medium text-teal-600 hover:text-teal-700 transition-colors"
              >
                VIEW ALL
                <ChevronRight size={16} />
              </button>
            </div>
            <div className="space-y-3">
              {RECOMMENDED_PROTOCOLS.map((protocol, idx) => (
                <button
                  key={idx}
                  onClick={() => onNavigate(ViewState.PROTOCOLS)}
                  className="w-full flex items-center gap-4 p-4 rounded-xl bg-slate-50 hover:bg-teal-50 border border-slate-100 hover:border-teal-200 transition-all group"
                >
                  <div className="w-12 h-12 rounded-xl bg-teal-100 flex items-center justify-center shrink-0">
                    <BookOpen size={20} className="text-teal-600" />
                  </div>
                  <div className="flex-1 text-left">
                    <h3 className="font-semibold text-slate-800 group-hover:text-teal-700 transition-colors">
                      {protocol.title}
                    </h3>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {protocol.area} <span className="text-slate-300 mx-1">•</span> {protocol.product}
                    </p>
                  </div>
                  <ChevronRight size={18} className="text-slate-300 group-hover:text-teal-500 transition-colors" />
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column - Chat & Status */}
        <div className="space-y-6">
          {/* Launch Chat Button */}
          <button
            onClick={onLaunchChat}
            className="w-full flex items-center justify-center gap-3 bg-gradient-to-r from-slate-800 to-slate-900 hover:from-slate-700 hover:to-slate-800 text-white py-4 px-6 rounded-2xl font-semibold shadow-lg shadow-slate-900/20 hover:shadow-xl hover:shadow-slate-900/30 transition-all"
          >
            LAUNCH CHAT
            <Sparkles size={18} className="text-teal-400" />
          </button>

          {/* Grounding Score */}
          <div className="bg-white rounded-2xl border border-slate-200 p-5">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-slate-500 tracking-wide">GROUNDING SCORE</span>
              <span className="text-sm font-bold text-emerald-600 tracking-wide">OPTIMAL</span>
            </div>
            <div className="mt-3 h-1.5 bg-slate-100 rounded-full overflow-hidden">
              <div className="h-full w-full bg-gradient-to-r from-teal-400 to-teal-500 rounded-full"></div>
            </div>
          </div>

          {/* Session Status */}
          <div className="bg-white rounded-2xl border border-slate-200 p-5">
            <div className="flex items-center gap-2 mb-4">
              <Clock size={18} className="text-slate-400" />
              <h3 className="text-sm font-semibold text-slate-700 tracking-wide">SESSION STATUS</h3>
            </div>
            <div className="flex items-center gap-2 mb-3">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              <span className="text-sm font-medium text-slate-700">Practitioner Auth Verified</span>
            </div>
            <p className="text-sm text-slate-500 leading-relaxed">
              "Clinical intelligence session active. All data served is sourced from DermaFocus Clinical Dossier 2026."
            </p>
          </div>

          {/* Quick Actions */}
          <div className="bg-gradient-to-br from-teal-50 to-white rounded-2xl border border-teal-100 p-5">
            <h3 className="text-sm font-semibold text-slate-700 mb-3">Quick Actions</h3>
            <div className="space-y-2">
              <button
                onClick={() => onNavigate(ViewState.PRODUCTS)}
                className="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl bg-white hover:bg-teal-50 border border-slate-200 hover:border-teal-200 text-sm font-medium text-slate-700 transition-all"
              >
                <Package size={16} className="text-teal-600" />
                View Products
              </button>
              <button
                onClick={() => onNavigate(ViewState.SAFETY)}
                className="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl bg-white hover:bg-teal-50 border border-slate-200 hover:border-teal-200 text-sm font-medium text-slate-700 transition-all"
              >
                <Shield size={16} className="text-teal-600" />
                Safety Guidelines
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;
