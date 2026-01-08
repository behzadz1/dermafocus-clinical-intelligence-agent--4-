import React, { useState } from 'react';
import { Protocol } from '../../types';
import { PROTOCOLS } from '../../constants';
import { ArrowRight, Activity, Syringe, Search, X, ImageOff, Clock, Layers } from 'lucide-react';

interface ProtocolListProps {
  onSelect: (protocol: Protocol) => void;
}

const ProtocolList: React.FC<ProtocolListProps> = ({ onSelect }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [imgErrors, setImgErrors] = useState<Record<string, boolean>>({});

  const handleImgError = (id: string) => {
    setImgErrors(prev => ({ ...prev, [id]: true }));
  };

  const filteredProtocols = PROTOCOLS.filter(protocol => {
    const query = searchQuery.toLowerCase();
    return (
      protocol.title.toLowerCase().includes(query) ||
      protocol.product.toLowerCase().includes(query) ||
      protocol.indication.toLowerCase().includes(query)
    );
  });

  return (
    <div className="p-6 md:p-8 max-w-6xl mx-auto h-full overflow-y-auto">
      <div className="mb-10 flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <h2 className="text-3xl font-bold text-slate-900 tracking-tight">Clinical Protocols</h2>
          <p className="text-slate-500 mt-2 text-lg">Validated injection guidelines from the Mastelli Portfolio (2025).</p>
        </div>
        
        <div className="relative max-w-md w-full">
          <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
            <Search className="h-5 w-5 text-slate-400" />
          </div>
          <input
            type="text"
            className="block w-full pl-11 pr-10 py-3.5 border border-slate-200 rounded-2xl leading-5 bg-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent transition-all shadow-sm font-medium"
            placeholder="Search by product or area..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      {filteredProtocols.length > 0 ? (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          {filteredProtocols.map((protocol) => (
            <div 
              key={protocol.id} 
              onClick={() => onSelect(protocol)}
              className="group bg-white rounded-2xl shadow-sm border border-slate-200 hover:border-teal-500 hover:shadow-xl transition-all duration-300 cursor-pointer overflow-hidden flex flex-col"
            >
              <div className="h-44 bg-slate-100 relative overflow-hidden">
                 {!imgErrors[protocol.id] ? (
                   <>
                    <img 
                      src={protocol.imagePlaceholder} 
                      alt={protocol.title} 
                      onError={() => handleImgError(protocol.id)}
                      className="w-full h-full object-cover opacity-85 group-hover:opacity-100 transition-all duration-700 transform group-hover:scale-110" 
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-slate-900/60 via-slate-900/20 to-transparent pointer-events-none" />
                   </>
                 ) : (
                   <div className="w-full h-full flex flex-col items-center justify-center text-slate-300">
                     <ImageOff size={40} className="mb-2 opacity-50" />
                     <span className="text-[10px] font-black uppercase tracking-widest opacity-50">Visual Unavailable</span>
                   </div>
                 )}
                 <div className="absolute top-4 left-4 flex gap-2">
                    <div className="bg-teal-600 text-white text-[10px] font-black px-2.5 py-1.5 rounded-lg shadow-lg backdrop-blur-md uppercase tracking-widest z-10">
                      Mastelli 2025
                    </div>
                 </div>
              </div>
              
              <div className="p-6 flex flex-col flex-1">
                <div className="flex items-center gap-2 mb-2">
                   <Syringe size={14} className="text-teal-600" />
                   <span className="text-[11px] font-bold text-teal-600 uppercase tracking-wider">{protocol.product}</span>
                </div>
                
                <h3 className="text-xl font-bold text-slate-900 mb-3 group-hover:text-teal-700 transition-colors">
                  {protocol.title}
                </h3>
                
                <div className="space-y-3 mb-8">
                  <div className="flex items-start gap-2.5">
                      <Layers size={16} className="text-slate-400 mt-0.5 shrink-0" />
                      <span className="text-sm text-slate-600 line-clamp-2 leading-relaxed">{protocol.indication}</span>
                  </div>
                  <div className="flex items-center gap-2.5">
                      <Clock size={16} className="text-slate-400 shrink-0" />
                      <span className="text-xs font-bold text-slate-500 bg-slate-100 px-2 py-1 rounded">14-21 Day Cycle</span>
                  </div>
                </div>
                
                <div className="mt-auto pt-4 border-t border-slate-50 flex items-center justify-between">
                  <span className="text-teal-600 font-bold text-sm">View Protocol</span>
                  <div className="w-8 h-8 rounded-full bg-slate-50 flex items-center justify-center group-hover:bg-teal-600 group-hover:text-white transition-all">
                    <ArrowRight size={18} className="transform group-hover:translate-x-0.5 transition-transform" />
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-20 bg-white rounded-3xl border border-slate-200 border-dashed">
            <div className="mx-auto h-20 w-20 text-slate-200 mb-6">
                <Search size={80} />
            </div>
            <h3 className="text-2xl font-bold text-slate-900">Protocol not indexed</h3>
            <p className="mt-2 text-slate-500">Try searching by anatomical area or product name.</p>
            <button 
                onClick={() => setSearchQuery('')}
                className="mt-6 px-6 py-2.5 bg-teal-600 text-white font-bold rounded-xl hover:bg-teal-700 transition-colors"
            >
                Clear Filters
            </button>
        </div>
      )}
    </div>
  );
};

export default ProtocolList;