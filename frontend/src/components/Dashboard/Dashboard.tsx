import React from 'react';
import { ViewState } from '../../types';
import {
  Sparkles,
  ChevronRight,
  BookOpen,
  Zap,
  CheckCircle2,
  Clock,
  Package,
  Shield
} from 'lucide-react';

const RECOMMENDED_PROTOCOLS = [
  { title: 'Perioral Rejuvenation', area: 'PERIORAL', product: 'NEWEST®' },
  { title: 'Periorbital Biostimulation', area: 'PERIOCULAR', product: 'PLINEST® EYE' },
  { title: 'Hand Bio-revitalization', area: 'HANDS', product: 'PLINEST®' },
];

interface DashboardProps {
  onLaunchChat: () => void;
  onNavigate: (view: string) => void;
}

const Dashboard: React.FC<DashboardProps> = ({ onLaunchChat, onNavigate }) => {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 animate-fade-in">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Stats & Protocols */}
        <div className="lg:col-span-2 space-y-6">
          {/* Stats Cards */}
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5 hover:shadow-md transition-shadow">
              <BookOpen size={24} className="text-teal-500 mb-3" />
              <div className="text-3xl font-bold text-slate-800 dark:text-slate-100">3</div>
              <div className="text-xs font-semibold text-teal-600 dark:text-teal-400 tracking-wider mt-1">PROTOCOLS</div>
            </div>
            <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5 hover:shadow-md transition-shadow">
              <Zap size={24} className="text-amber-500 mb-3" />
              <div className="text-3xl font-bold text-slate-800 dark:text-slate-100">3</div>
              <div className="text-xs font-semibold text-slate-500 dark:text-slate-400 tracking-wider mt-1">ACTIVE AGENTS</div>
            </div>
            <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5 hover:shadow-md transition-shadow">
              <CheckCircle2 size={24} className="text-emerald-500 mb-3" />
              <div className="text-3xl font-bold text-slate-800 dark:text-slate-100">100%</div>
              <div className="text-xs font-semibold text-slate-500 dark:text-slate-400 tracking-wider mt-1">INTEGRITY</div>
            </div>
          </div>

          {/* Recommended Protocols */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-6">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">Recommended Protocols</h2>
              <button
                onClick={() => onNavigate(ViewState.PROTOCOLS)}
                className="flex items-center gap-1 text-sm font-medium text-teal-600 dark:text-teal-400 hover:text-teal-700 dark:hover:text-teal-300 transition-colors"
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
                  className="w-full flex items-center gap-4 p-4 rounded-xl bg-slate-50 dark:bg-slate-800/50 hover:bg-teal-50 dark:hover:bg-teal-900/20 border border-slate-100 dark:border-slate-700 hover:border-teal-200 dark:hover:border-teal-700 transition-all group"
                >
                  <div className="w-12 h-12 rounded-xl bg-teal-100 dark:bg-teal-900/50 flex items-center justify-center shrink-0">
                    <BookOpen size={20} className="text-teal-600 dark:text-teal-400" />
                  </div>
                  <div className="flex-1 text-left">
                    <h3 className="font-semibold text-slate-800 dark:text-slate-100 group-hover:text-teal-700 dark:group-hover:text-teal-400 transition-colors">
                      {protocol.title}
                    </h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                      {protocol.area} <span className="text-slate-300 dark:text-slate-600 mx-1">•</span> {protocol.product}
                    </p>
                  </div>
                  <ChevronRight size={18} className="text-slate-300 dark:text-slate-600 group-hover:text-teal-500 dark:group-hover:text-teal-400 transition-colors" />
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
            className="w-full flex items-center justify-center gap-3 bg-gradient-to-r from-slate-800 to-slate-900 dark:from-teal-600 dark:to-teal-700 hover:from-slate-700 hover:to-slate-800 dark:hover:from-teal-500 dark:hover:to-teal-600 text-white py-4 px-6 rounded-2xl font-semibold shadow-lg shadow-slate-900/20 dark:shadow-teal-900/30 hover:shadow-xl transition-all"
          >
            LAUNCH CHAT
            <Sparkles size={18} className="text-teal-400 dark:text-white" />
          </button>

          {/* Grounding Score */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-slate-500 dark:text-slate-400 tracking-wide">GROUNDING SCORE</span>
              <span className="text-sm font-bold text-emerald-600 dark:text-emerald-400 tracking-wide">OPTIMAL</span>
            </div>
            <div className="mt-3 h-1.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
              <div className="h-full w-full bg-gradient-to-r from-teal-400 to-teal-500 rounded-full"></div>
            </div>
          </div>

          {/* Session Status */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5">
            <div className="flex items-center gap-2 mb-4">
              <Clock size={18} className="text-slate-400" />
              <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 tracking-wide">SESSION STATUS</h3>
            </div>
            <div className="flex items-center gap-2 mb-3">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Practitioner Auth Verified</span>
            </div>
            <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed">
              "Clinical intelligence session active. All data served is sourced from DermaFocus Clinical Dossier 2026."
            </p>
          </div>

          {/* Quick Actions */}
          <div className="bg-gradient-to-br from-teal-50 to-white dark:from-teal-900/20 dark:to-slate-900 rounded-2xl border border-teal-100 dark:border-teal-800/50 p-5">
            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">Quick Actions</h3>
            <div className="space-y-2">
              <button
                onClick={() => onNavigate(ViewState.PRODUCTS)}
                className="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl bg-white dark:bg-slate-800 hover:bg-teal-50 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-700 hover:border-teal-200 dark:hover:border-teal-700 text-sm font-medium text-slate-700 dark:text-slate-300 transition-all"
              >
                <Package size={16} className="text-teal-600 dark:text-teal-400" />
                View Products
              </button>
              <button
                onClick={() => onNavigate(ViewState.SAFETY)}
                className="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl bg-white dark:bg-slate-800 hover:bg-teal-50 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-700 hover:border-teal-200 dark:hover:border-teal-700 text-sm font-medium text-slate-700 dark:text-slate-300 transition-all"
              >
                <Shield size={16} className="text-teal-600 dark:text-teal-400" />
                Safety Guidelines
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
