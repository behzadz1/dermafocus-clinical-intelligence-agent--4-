import React from 'react';
import { ViewState } from '../../types';
import { MessageSquare, FileText, Package, ShieldCheck, Menu, X, Video, BookOpen } from 'lucide-react';

interface SidebarProps {
  currentView: ViewState;
  setView: (view: ViewState) => void;
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ currentView, setView, isOpen, setIsOpen }) => {
  const navItems = [
    { id: ViewState.CHAT, label: 'Clinical Intelligence', icon: MessageSquare },
    { id: ViewState.LIVE_CONSULT, label: 'Live Consult', icon: Video },
    { id: ViewState.PROTOCOLS, label: 'Treatment Protocols', icon: FileText },
    { id: ViewState.PRODUCTS, label: 'Product Portfolio', icon: Package },
    { id: ViewState.SAFETY, label: 'Medical Guardrails', icon: ShieldCheck },
    { id: ViewState.DOCS, label: 'System Documentation', icon: BookOpen },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-20 md:hidden"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Sidebar Container */}
      <div className={`
        fixed md:relative z-30 flex flex-col h-full bg-slate-900 text-white w-64 transition-transform duration-300 ease-in-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
        print:hidden
      `}>
        <div className="p-6 border-b border-slate-700 flex justify-between items-center">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-teal-400">DermaFocus</h1>
            <p className="text-xs text-slate-400">Clinical Intelligence Agent</p>
          </div>
          <button className="md:hidden" onClick={() => setIsOpen(false)}>
            <X size={20} />
          </button>
        </div>

        <nav className="flex-1 p-4 space-y-2">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => {
                setView(item.id);
                setIsOpen(false);
              }}
              className={`
                w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors
                ${currentView === item.id
                  ? 'bg-teal-600 text-white shadow-lg'
                  : 'text-slate-300 hover:bg-slate-800 hover:text-white'}
              `}
            >
              <item.icon size={18} />
              {item.label}
            </button>
          ))}
        </nav>

        <div className="p-4 border-t border-slate-700">
          <div className="bg-slate-800 rounded-lg p-3">
            <p className="text-xs text-slate-400 font-semibold mb-1">CLINICIAN MODE</p>
            <p className="text-xs text-slate-500">
              Dermafocus © 2026<br />
              Confidential MVP
            </p>
          </div>
        </div>
      </div>
    </>
  );
};

export default Sidebar;