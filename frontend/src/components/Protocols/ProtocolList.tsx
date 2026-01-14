import React, { useState, useEffect } from 'react';
import { Protocol } from '../../types';
import { apiService, ProtocolInfo } from '../../services/apiService';
import { ArrowRight, Syringe, Search, X, ImageOff, Clock, Layers, RefreshCw, AlertCircle, Loader2 } from 'lucide-react';

interface ProtocolListProps {
  onSelect: (protocol: Protocol) => void;
}

const ProtocolList: React.FC<ProtocolListProps> = ({ onSelect }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [imgErrors, setImgErrors] = useState<Record<string, boolean>>({});
  const [protocols, setProtocols] = useState<ProtocolInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [dataSource, setDataSource] = useState<string>('');

  const handleImgError = (id: string) => {
    setImgErrors(prev => ({ ...prev, [id]: true }));
  };

  const fetchProtocols = async (refresh: boolean = false) => {
    try {
      if (refresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);

      const response = await apiService.getProtocols(refresh);
      setProtocols(response.protocols);
      setLastUpdated(response.last_updated);
      setDataSource(response.source);
    } catch (err) {
      console.error('Failed to fetch protocols:', err);
      setError(err instanceof Error ? err.message : 'Failed to load protocols');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchProtocols();
  }, []);

  const handleRefresh = () => {
    fetchProtocols(true);
  };

  // Convert ProtocolInfo to Protocol type for compatibility with ProtocolDetail
  const convertToProtocol = (info: ProtocolInfo): Protocol => ({
    id: info.id,
    title: info.title,
    product: info.product,
    indication: info.indication,
    dosing: info.dosing,
    steps: info.steps.map(s => ({
      title: s.title,
      description: s.description,
      details: s.details
    })),
    contraindications: info.contraindications,
    vectors: info.vectors,
    imagePlaceholder: info.imagePlaceholder
  });

  const filteredProtocols = protocols.filter(protocol => {
    const query = searchQuery.toLowerCase();
    return (
      protocol.title.toLowerCase().includes(query) ||
      protocol.product.toLowerCase().includes(query) ||
      protocol.indication.toLowerCase().includes(query)
    );
  });

  const renderLoadingState = () => (
    <div className="flex flex-col items-center justify-center py-20">
      <Loader2 className="w-12 h-12 text-teal-600 animate-spin mb-4" />
      <p className="text-slate-600 text-lg font-medium">Loading protocols from knowledge base...</p>
      <p className="text-slate-400 text-sm mt-2">Extracting treatment protocol information</p>
    </div>
  );

  const renderErrorState = () => (
    <div className="flex flex-col items-center justify-center py-20">
      <AlertCircle className="w-12 h-12 text-red-500 mb-4" />
      <p className="text-slate-800 text-lg font-medium mb-2">Failed to load protocols</p>
      <p className="text-slate-500 text-sm mb-6">{error}</p>
      <button
        onClick={() => fetchProtocols()}
        className="px-6 py-3 bg-teal-600 text-white rounded-xl font-bold hover:bg-teal-700 transition-colors flex items-center gap-2"
      >
        <RefreshCw size={18} />
        Try Again
      </button>
    </div>
  );

  const renderEmptyState = () => (
    <div className="text-center py-20 bg-white rounded-3xl border border-slate-200 border-dashed">
      <div className="mx-auto h-20 w-20 text-slate-200 mb-6">
        <Search size={80} />
      </div>
      <h3 className="text-2xl font-bold text-slate-900">No protocols found</h3>
      <p className="mt-2 text-slate-500">Add protocol PDFs to the RAG knowledge base to see them here.</p>
      <button
        onClick={handleRefresh}
        className="mt-6 px-6 py-2.5 bg-teal-600 text-white font-bold rounded-xl hover:bg-teal-700 transition-colors"
      >
        Refresh from RAG
      </button>
    </div>
  );

  return (
    <div className="p-6 md:p-8 max-w-6xl mx-auto h-full overflow-y-auto">
      <div className="mb-10 flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <h2 className="text-3xl font-bold text-slate-900 tracking-tight">Clinical Protocols</h2>
          <p className="text-slate-500 mt-2 text-lg">Dynamic protocol information extracted from clinical documentation.</p>
          {lastUpdated && (
            <p className="text-slate-400 text-sm mt-1">
              Last updated: {new Date(lastUpdated).toLocaleString()}
              {dataSource === 'cache' && <span className="ml-2 text-amber-500">(cached)</span>}
            </p>
          )}
        </div>

        <div className="flex items-center gap-4">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className={`
              flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold transition-all border
              ${refreshing
                ? 'bg-slate-100 text-slate-400 border-slate-200 cursor-not-allowed'
                : 'bg-white text-teal-700 border-teal-200 hover:bg-teal-50 hover:border-teal-300'}
            `}
            title="Refresh protocols from RAG"
          >
            <RefreshCw size={16} className={refreshing ? 'animate-spin' : ''} />
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </button>

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
      </div>

      {loading && renderLoadingState()}
      {!loading && error && renderErrorState()}
      {!loading && !error && protocols.length === 0 && renderEmptyState()}

      {!loading && !error && protocols.length > 0 && (
        filteredProtocols.length > 0 ? (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {filteredProtocols.map((protocol) => (
              <div
                key={protocol.id}
                onClick={() => onSelect(convertToProtocol(protocol))}
                className="group bg-white rounded-2xl shadow-sm border border-slate-200 hover:border-teal-500 hover:shadow-xl transition-all duration-300 cursor-pointer overflow-hidden flex flex-col"
              >
                <div className="h-44 bg-slate-100 relative overflow-hidden">
                   {protocol.imagePlaceholder && !imgErrors[protocol.id] ? (
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
                       <span className="text-[10px] font-black uppercase tracking-widest opacity-50">Protocol Guide</span>
                     </div>
                   )}
                   <div className="absolute top-4 left-4 flex gap-2">
                      <div className="bg-teal-600 text-white text-[10px] font-black px-2.5 py-1.5 rounded-lg shadow-lg backdrop-blur-md uppercase tracking-widest z-10">
                        RAG Extracted
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
                        <span className="text-sm text-slate-600 line-clamp-2 leading-relaxed">{protocol.indication || 'Clinical protocol'}</span>
                    </div>
                    <div className="flex items-center gap-2.5">
                        <Clock size={16} className="text-slate-400 shrink-0" />
                        <span className="text-xs font-bold text-slate-500 bg-slate-100 px-2 py-1 rounded">{protocol.dosing || 'See protocol details'}</span>
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
        )
      )}
    </div>
  );
};

export default ProtocolList;
