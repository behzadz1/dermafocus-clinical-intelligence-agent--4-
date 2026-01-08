import React, { useState } from 'react';
import { PRODUCTS } from '../../constants';
import { Package, Sparkles, Microscope, CircleCheck, ShieldAlert, LayoutList, Columns2, ImageOff, Droplets, Zap } from 'lucide-react';

const ProductHub: React.FC = () => {
  const [viewMode, setViewMode] = useState<'list' | 'compare'>('list');
  const [imgErrors, setImgErrors] = useState<Record<string, boolean>>({});

  const handleImgError = (name: string) => {
    setImgErrors(prev => ({ ...prev, [name]: true }));
  };

  const renderListView = () => (
    <div className="grid gap-8 max-w-5xl mx-auto">
      {PRODUCTS.map((product, idx) => (
        <div key={idx} className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden hover:shadow-lg transition-shadow">
          <div className="p-8 flex flex-col md:flex-row gap-8 border-b border-slate-100">
            <div className="bg-slate-50 rounded-2xl w-full md:w-56 h-56 flex items-center justify-center shrink-0 overflow-hidden border border-slate-100 group relative">
              {product.imageUrl && !imgErrors[product.name] ? (
                <img 
                  src={product.imageUrl} 
                  alt={product.name} 
                  onError={() => handleImgError(product.name)}
                  className="w-full h-full object-cover transition-transform group-hover:scale-105"
                />
              ) : (
                <div className="flex flex-col items-center gap-3 text-slate-300">
                  <Package size={48} className="opacity-20" />
                  <span className="text-[10px] font-black uppercase tracking-widest opacity-50">Clinical Asset</span>
                </div>
              )}
              <div className="absolute bottom-3 left-3 flex gap-1.5">
                 {product.composition.includes('HA') && (
                   <span className="p-1.5 bg-blue-500 text-white rounded-lg shadow-sm" title="Contains Hyaluronic Acid">
                     <Droplets size={14} />
                   </span>
                 )}
                 <span className="p-1.5 bg-teal-600 text-white rounded-lg shadow-sm" title="PN-HPT Technology">
                    <Zap size={14} />
                 </span>
              </div>
            </div>
            
            <div className="flex-1">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-2xl font-bold text-slate-900">{product.name}</h3>
                <span className="px-3 py-1.5 bg-teal-50 text-teal-700 text-[10px] font-black rounded-lg border border-teal-100 uppercase tracking-tighter">
                  Mastelli Portfolio
                </span>
              </div>

              <div className="flex items-center gap-2 text-sm text-teal-600 font-bold mb-5 bg-teal-50/50 w-fit px-3 py-1 rounded-full">
                <Sparkles size={16} />
                {product.technology}
              </div>

              <div className="bg-slate-50 p-4 rounded-xl mb-6 border border-slate-100">
                <p className="text-slate-700 text-sm leading-relaxed font-bold">
                  {product.composition}
                </p>
              </div>

              <div>
                <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] mb-3">Key Indications</h4>
                <div className="flex flex-wrap gap-2.5">
                  {product.indications.map((ind, i) => (
                    <span key={i} className="px-3 py-1.5 bg-white border border-slate-200 text-slate-600 text-xs font-bold rounded-lg shadow-sm">
                      {ind}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="bg-slate-50/50 p-8 grid md:grid-cols-2 gap-10">
            <div>
              <h4 className="flex items-center gap-2.5 text-sm font-black text-slate-900 mb-4 uppercase tracking-wider">
                <Microscope size={18} className="text-teal-600" />
                Mechanism of Action
              </h4>
              <p className="text-sm text-slate-600 leading-relaxed font-medium">
                {product.mechanism}
              </p>
            </div>
            <div>
              <h4 className="flex items-center gap-2.5 text-sm font-black text-slate-900 mb-4 uppercase tracking-wider">
                <CircleCheck size={18} className="text-teal-600" />
                Clinical Benefits
              </h4>
              <ul className="grid grid-cols-1 gap-3 mb-6">
                {product.benefits.map((benefit, i) => (
                  <li key={i} className="flex items-start gap-3 text-sm text-slate-700 font-medium">
                    <div className="w-5 h-5 rounded-full bg-teal-100 flex items-center justify-center shrink-0">
                       <CircleCheck size={12} className="text-teal-600" />
                    </div>
                    {benefit}
                  </li>
                ))}
              </ul>

              <div className="bg-red-50/50 border border-red-100 rounded-xl p-5">
                <h4 className="flex items-center gap-2.5 text-xs font-black text-red-800 mb-3 uppercase tracking-wider">
                  <ShieldAlert size={16} />
                  Contraindications
                </h4>
                <div className="flex flex-wrap gap-2">
                  {product.contraindications.map((c, i) => (
                    <span key={i} className="px-2.5 py-1 bg-white text-red-700 text-[10px] font-bold rounded-lg border border-red-100 uppercase tracking-tighter shadow-sm">
                      {c}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );

  const renderCompareView = () => (
    <div className="overflow-x-auto pb-10">
      <div className="min-w-[1100px] px-2">
        <table className="w-full border-separate border-spacing-0 rounded-3xl border border-slate-200 bg-white shadow-xl overflow-hidden">
          <thead>
            <tr className="bg-slate-900 text-white">
              <th className="p-6 text-left font-black text-xs uppercase tracking-[0.2em] w-56 sticky left-0 z-10 bg-slate-900 border-b border-slate-700">Clinical Spec</th>
              {PRODUCTS.map((p, idx) => (
                <th key={p.name} className={`p-6 text-left font-bold w-1/5 border-b border-slate-700 ${idx > 0 ? 'border-l border-slate-700' : ''}`}>
                  <div className="text-xl text-teal-400">{p.name}</div>
                  <div className="text-[10px] font-black text-slate-400 mt-2 uppercase tracking-widest">{p.technology}</div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
             <tr className="hover:bg-slate-50 transition-colors">
              <td className="p-5 font-black text-[10px] uppercase tracking-wider text-slate-500 bg-slate-50/50 sticky left-0 z-10 border-r border-slate-200">Composition</td>
              {PRODUCTS.map((p, i) => (
                <td key={i} className={`p-5 text-sm text-slate-900 font-bold align-top ${i > 0 ? 'border-l border-slate-100' : ''}`}>
                  {p.composition}
                </td>
              ))}
            </tr>
            <tr className="hover:bg-slate-50 transition-colors">
              <td className="p-5 font-black text-[10px] uppercase tracking-wider text-slate-500 bg-slate-50/50 sticky left-0 z-10 border-r border-slate-200">Indications</td>
              {PRODUCTS.map((p, i) => (
                <td key={i} className={`p-5 text-sm text-slate-600 align-top ${i > 0 ? 'border-l border-slate-100' : ''}`}>
                  <div className="flex flex-wrap gap-2">
                    {p.indications.map((ind, j) => (
                      <span key={j} className="inline-block px-2 py-1 bg-slate-100 text-slate-700 text-[10px] font-bold rounded uppercase tracking-tighter">
                        {ind}
                      </span>
                    ))}
                  </div>
                </td>
              ))}
            </tr>
            <tr className="hover:bg-slate-50 transition-colors">
              <td className="p-5 font-black text-[10px] uppercase tracking-wider text-slate-500 bg-slate-50/50 sticky left-0 z-10 border-r border-slate-200">Primary Goal</td>
              {PRODUCTS.map((p, i) => (
                <td key={i} className={`p-5 text-sm text-slate-600 align-top leading-relaxed font-medium italic ${i > 0 ? 'border-l border-slate-100' : ''}`}>
                  {p.benefits[0]}
                </td>
              ))}
            </tr>
            <tr className="hover:bg-slate-50 transition-colors">
              <td className="p-5 font-black text-[10px] uppercase tracking-wider text-slate-500 bg-slate-50/50 sticky left-0 z-10 border-r border-slate-200">Mechanism</td>
              {PRODUCTS.map((p, i) => (
                <td key={i} className={`p-5 text-xs text-slate-600 align-top leading-relaxed ${i > 0 ? 'border-l border-slate-100' : ''}`}>
                  {p.mechanism}
                </td>
              ))}
            </tr>
            <tr className="hover:bg-slate-50 transition-colors">
              <td className="p-5 font-black text-[10px] uppercase tracking-wider text-slate-500 bg-slate-50/50 sticky left-0 z-10 border-r border-slate-200 rounded-bl-3xl">Precautions</td>
              {PRODUCTS.map((p, i) => (
                <td key={i} className={`p-5 text-sm text-slate-600 align-top ${i > 0 ? 'border-l border-slate-100' : ''}`}>
                   <ul className="space-y-1.5">
                    {p.contraindications.slice(0, 3).map((c, j) => (
                      <li key={j} className="flex items-center gap-2 text-red-600 text-[10px] font-black uppercase tracking-tighter">
                         <div className="w-1.5 h-1.5 rounded-full bg-red-400 shrink-0" />
                        <span>{c}</span>
                      </li>
                    ))}
                  </ul>
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );

  return (
    <div className={`p-6 md:p-8 mx-auto h-full overflow-y-auto bg-slate-50/30 ${viewMode === 'compare' ? 'max-w-full' : 'max-w-6xl'}`}>
      <div className="mb-12 border-b border-slate-200 pb-8 flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <h2 className="text-3xl font-bold text-slate-900 tracking-tight">Product Portfolio</h2>
          <p className="text-slate-500 mt-2 text-lg">Official PN-HPT® Technology solutions for Regenerative Aesthetics.</p>
        </div>
        
        <div className="bg-slate-200/50 p-1.5 rounded-2xl flex shrink-0 self-start md:self-auto shadow-inner">
          <button
            onClick={() => setViewMode('list')}
            className={`
              flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-black uppercase tracking-widest transition-all
              ${viewMode === 'list' 
                ? 'bg-white text-teal-700 shadow-md scale-100' 
                : 'text-slate-500 hover:text-slate-700 hover:bg-slate-200/30'}
            `}
          >
            <LayoutList size={16} />
            List
          </button>
          <button
            onClick={() => setViewMode('compare')}
            className={`
              flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-black uppercase tracking-widest transition-all
              ${viewMode === 'compare' 
                ? 'bg-white text-teal-700 shadow-md scale-100' 
                : 'text-slate-500 hover:text-slate-700 hover:bg-slate-200/30'}
            `}
          >
            <Columns2 size={16} />
            Compare
          </button>
        </div>
      </div>

      {viewMode === 'list' ? renderListView() : renderCompareView()}
    </div>
  );
};

export default ProductHub;