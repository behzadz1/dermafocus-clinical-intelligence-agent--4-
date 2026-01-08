import React, { useState } from 'react';
import Sidebar from './components/Layout/Sidebar';
import ChatWindow from './components/Chat/ChatWindow';
import ProtocolList from './components/Protocols/ProtocolList';
import ProtocolDetail from './components/Protocols/ProtocolDetail';
import ProductHub from './components/Products/ProductHub';
import SafetyPanel from './components/Safety/SafetyPanel';
import SystemDocs from './components/Docs/SystemDocs';
import { ViewState, Protocol } from './types';
import { Menu } from 'lucide-react';

const App: React.FC = () => {
  const [currentView, setCurrentView] = useState<ViewState>(ViewState.CHAT);
  const [selectedProtocol, setSelectedProtocol] = useState<Protocol | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const renderContent = () => {
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
      default:
        return <ChatWindow />;
    }
  };

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      <Sidebar
        currentView={currentView}
        setView={(view) => {
          setCurrentView(view);
          setSelectedProtocol(null); // Reset protocol selection on view change
        }}
        isOpen={isSidebarOpen}
        setIsOpen={setIsSidebarOpen}
      />

      <main className="flex-1 flex flex-col relative w-full h-full">
        {/* Mobile Header */}
        <div className="md:hidden h-14 bg-white border-b border-slate-200 flex items-center px-4 shrink-0 justify-between print:hidden">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsSidebarOpen(true)}
              className="text-slate-600 hover:text-slate-900"
            >
              <Menu size={24} />
            </button>
            <span className="font-bold text-teal-600">DermaAI</span>
          </div>
        </div>

        <div className="flex-1 overflow-hidden relative">
          {renderContent()}
        </div>
      </main>
    </div>
  );
};

export default App;