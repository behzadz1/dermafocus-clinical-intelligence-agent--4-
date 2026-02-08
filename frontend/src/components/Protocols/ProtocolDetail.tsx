import React, { useState } from 'react';
import { Protocol } from '../../types';
import { ChevronLeft, CircleAlert, CircleCheck, Syringe, Play, ChevronRight, RotateCcw, X, CheckCircle2 } from 'lucide-react';

interface ProtocolDetailProps {
  protocol: Protocol;
  onBack: () => void;
}

const ProtocolDetail: React.FC<ProtocolDetailProps> = ({ protocol, onBack }) => {
  const [isProcedureMode, setIsProcedureMode] = useState(false);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);

  const toggleProcedureMode = () => {
    setIsProcedureMode(!isProcedureMode);
    setCurrentStepIndex(0);
  };

  const nextStep = () => {
    if (currentStepIndex < protocol.steps.length - 1) {
      setCurrentStepIndex(prev => prev + 1);
    }
  };

  const prevStep = () => {
    if (currentStepIndex > 0) {
      setCurrentStepIndex(prev => prev - 1);
    }
  };

  // --- PROCEDURE MODE VIEW ---
  if (isProcedureMode) {
    const currentStep = protocol.steps[currentStepIndex];
    const progress = ((currentStepIndex + 1) / protocol.steps.length) * 100;
    const isLastStep = currentStepIndex === protocol.steps.length - 1;

    return (
      <div className="fixed inset-0 z-50 bg-slate-900 text-white flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-700">
          <div>
            <h2 className="text-sm font-bold text-teal-400 uppercase tracking-wider mb-1">Procedure Mode</h2>
            <h1 className="text-xl font-bold">{protocol.title}</h1>
          </div>
          <button
            onClick={toggleProcedureMode}
            aria-label="Exit procedure mode"
            className="p-2 bg-slate-800 hover:bg-slate-700 rounded-full transition-colors text-slate-400 hover:text-white"
          >
            <X size={24} />
          </button>
        </div>

        {/* Progress Bar */}
        <div className="w-full bg-slate-800 h-2">
          <div 
            className="bg-teal-500 h-2 transition-all duration-300" 
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col justify-center items-center p-8 text-center max-w-4xl mx-auto w-full">
          <div className="bg-slate-800/50 rounded-full px-4 py-2 mb-8 border border-slate-700 text-teal-400 font-bold">
            Step {currentStepIndex + 1} of {protocol.steps.length}
          </div>
          
          <h2 className="text-3xl md:text-5xl font-bold mb-8 leading-tight">
            {currentStep.title}
          </h2>
          
          <p className="text-xl md:text-2xl text-slate-300 mb-8 max-w-3xl leading-relaxed">
            {currentStep.description}
          </p>

          {currentStep.details && (
            <div className="bg-slate-800 rounded-xl p-6 md:p-8 w-full max-w-2xl text-left border border-slate-700">
               <ul className="space-y-4">
                 {currentStep.details.map((detail, idx) => (
                   <li key={idx} className="flex items-start gap-4 text-lg text-slate-300">
                     <CheckCircle2 size={24} className="mt-1 text-teal-500 shrink-0" />
                     {detail}
                   </li>
                 ))}
               </ul>
            </div>
          )}
        </div>

        {/* Footer Controls - Large buttons for easy clicking */}
        <div className="p-6 border-t border-slate-700 bg-slate-900">
          <div className="max-w-4xl mx-auto flex items-center justify-between gap-4">
            <button
              onClick={prevStep}
              disabled={currentStepIndex === 0}
              className={`
                flex-1 py-6 rounded-xl flex items-center justify-center gap-3 text-lg font-bold transition-all
                ${currentStepIndex === 0 
                  ? 'bg-slate-800 text-slate-600 cursor-not-allowed' 
                  : 'bg-slate-800 text-white hover:bg-slate-700 active:scale-95'}
              `}
            >
              <ChevronLeft size={24} />
              Previous
            </button>

            {isLastStep ? (
               <button
               onClick={toggleProcedureMode}
               className="flex-[2] py-6 bg-teal-600 hover:bg-teal-700 text-white rounded-xl flex items-center justify-center gap-3 text-lg font-bold transition-all active:scale-95 shadow-lg shadow-teal-900/50"
             >
               <CheckCircle2 size={24} />
               Complete Procedure
             </button>
            ) : (
              <button
                onClick={nextStep}
                className="flex-[2] py-6 bg-white text-slate-900 hover:bg-slate-200 rounded-xl flex items-center justify-center gap-3 text-lg font-bold transition-all active:scale-95"
              >
                Next Step
                <ChevronRight size={24} />
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  // --- STANDARD VIEW ---
  return (
    <div className="h-full overflow-y-auto bg-slate-50">
      <div className="max-w-4xl mx-auto p-6 md:p-8">
        <nav className="flex items-center gap-2 text-sm mb-6" aria-label="Breadcrumb">
          <button
            onClick={onBack}
            className="font-medium text-slate-500 hover:text-teal-600 transition-colors"
          >
            Protocols
          </button>
          <ChevronRight size={14} className="text-slate-300" />
          <span className="font-medium text-slate-800 truncate max-w-xs">
            {protocol.title}
          </span>
        </nav>

        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="bg-slate-900 p-6 md:p-8 text-white relative overflow-hidden">
            {/* Background decoration */}
            <div className="absolute top-0 right-0 w-64 h-64 bg-teal-900/20 rounded-full blur-3xl -mr-16 -mt-16 pointer-events-none" />
            
            <div className="relative z-10 flex flex-col md:flex-row md:items-start justify-between gap-6">
              <div className="flex-1">
                <div className="inline-block px-2 py-1 bg-teal-600 text-xs font-bold rounded mb-3 shadow-sm">
                  {protocol.product}
                </div>
                <h1 className="text-3xl md:text-4xl font-bold mb-3">{protocol.title}</h1>
                <p className="text-slate-300 text-lg max-w-2xl">{protocol.indication}</p>
                
                <button 
                  onClick={toggleProcedureMode}
                  className="mt-8 bg-white text-slate-900 hover:bg-slate-100 px-6 py-3 rounded-xl font-bold flex items-center gap-2 transition-all shadow-lg active:scale-95"
                >
                  <Play size={20} className="fill-slate-900" />
                  Start Procedure Mode
                </button>
              </div>

              <div className="bg-slate-800/80 backdrop-blur-sm p-5 rounded-xl border border-slate-700 min-w-[240px]">
                <p className="text-xs text-slate-400 uppercase tracking-wide font-bold mb-2 flex items-center gap-2">
                  <Syringe size={14} />
                  Standard Dose
                </p>
                <p className="text-xl font-semibold text-white tracking-tight">{protocol.dosing}</p>
              </div>
            </div>
          </div>

          <div className="p-6 md:p-8 space-y-10">
            {/* Contraindications Warning */}
            <div className="bg-red-50 border border-red-100 rounded-xl p-5 flex gap-4">
              <CircleAlert className="text-red-500 shrink-0 mt-0.5" size={24} />
              <div>
                <h4 className="text-base font-bold text-red-900 mb-2">Contraindications</h4>
                <div className="flex flex-wrap gap-2">
                  {protocol.contraindications.map((c, idx) => (
                    <span key={idx} className="px-2 py-1 bg-red-100 text-red-800 text-xs font-medium rounded-md border border-red-200">
                      {c}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* Vectors if available */}
            {protocol.vectors && (
              <section>
                <h3 className="text-xl font-bold text-slate-900 mb-5 flex items-center gap-2">
                  <span className="w-8 h-8 rounded-lg bg-teal-100 text-teal-700 flex items-center justify-center text-sm font-bold">V</span>
                  Injection Vectors
                </h3>
                <div className="grid sm:grid-cols-2 gap-4">
                  {protocol.vectors.map((vector, idx) => (
                    <div key={idx} className="group border border-slate-200 rounded-xl p-4 bg-slate-50 hover:border-teal-300 transition-colors">
                      <p className="font-bold text-slate-900 mb-1 group-hover:text-teal-800">{vector.name}</p>
                      <p className="text-sm text-slate-600 leading-relaxed">{vector.description}</p>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Steps Preview */}
            <section>
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-bold text-slate-900">Procedural Overview</h3>
                <button 
                  onClick={toggleProcedureMode}
                  className="text-sm font-medium text-teal-600 hover:text-teal-700 flex items-center gap-1"
                >
                  <Play size={14} />
                  Start Interactive Guide
                </button>
              </div>
              
              <div className="space-y-0 relative border-l-2 border-slate-200 ml-3.5">
                {protocol.steps.map((step, idx) => (
                  <div key={idx} className="relative pl-10 pb-10 last:pb-0">
                    <div className="absolute -left-[11px] top-0 w-6 h-6 rounded-full bg-white border-4 border-teal-500 shadow-sm z-10" />
                    <h4 className="text-lg font-bold text-slate-900 mb-2">{step.title}</h4>
                    <p className="text-slate-600 text-base leading-relaxed mb-3">{step.description}</p>
                    {step.details && (
                      <ul className="bg-slate-50 rounded-lg p-3 space-y-2 border border-slate-100">
                        {step.details.map((detail, dIdx) => (
                           <li key={dIdx} className="flex items-start gap-2 text-sm text-slate-600">
                             <CheckCircle2 size={16} className="mt-0.5 text-teal-500 shrink-0" />
                             {detail}
                           </li>
                        ))}
                      </ul>
                    )}
                  </div>
                ))}
              </div>
            </section>
            
            <div className="border-t border-slate-100 pt-8 mt-4">
                <p className="text-xs text-slate-400 italic text-center max-w-2xl mx-auto">
                    Source: Dermafocus Clinical Training Protocols (2025). Always refer to the full Instructions For Use (IFU) included with the product packaging.
                </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProtocolDetail;