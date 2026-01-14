import React from 'react';
import { Printer, FileText, Cpu, Database, Shield } from 'lucide-react';

const SystemDocs: React.FC = () => {
  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="h-full overflow-y-auto bg-white" id="doc-container">
      {/* Print Controls (Hidden when printing) */}
      <div className="sticky top-0 z-10 bg-white/80 backdrop-blur-md border-b border-slate-200 p-4 flex justify-between items-center print:hidden">
        <div>
          <h2 className="text-xl font-bold text-slate-900">System Documentation</h2>
          <p className="text-sm text-slate-500">Technical Specification & User Guide</p>
        </div>
        <button 
          onClick={handlePrint}
          className="bg-slate-900 text-white px-4 py-2 rounded-lg flex items-center gap-2 hover:bg-slate-800 transition-colors font-medium shadow-sm"
        >
          <Printer size={18} />
          Download / Print PDF
        </button>
      </div>

      {/* Document Content */}
      <div className="max-w-4xl mx-auto p-8 md:p-12 print:p-0 print:max-w-full">
        
        {/* Document Header */}
        <div className="border-b-2 border-slate-900 pb-8 mb-8 print:border-black">
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-3xl md:text-4xl font-bold text-slate-900 mb-2 print:text-black">DermaAI CKPA</h1>
              <h2 className="text-xl text-teal-600 font-medium print:text-slate-800">Clinical Knowledge & Protocol Agent</h2>
            </div>
            <div className="text-right">
              <p className="text-sm text-slate-500 font-mono print:text-black">VER: 2.5.0-HYBRID</p>
              <p className="text-sm text-slate-500 font-mono print:text-black">DATE: OCT 2025</p>
            </div>
          </div>
        </div>

        {/* 1. Executive Summary */}
        <section className="mb-10 break-inside-avoid">
          <h3 className="text-lg font-bold text-slate-900 uppercase tracking-wider mb-4 border-l-4 border-teal-500 pl-3 print:border-slate-800 print:text-black">
            1. Executive Summary
          </h3>
          <p className="text-slate-700 leading-relaxed mb-4 print:text-black">
            The DermaAI CKPA is a specialized <strong>Clinical Decision Support System (CDSS)</strong> designed for aesthetic clinicians utilising Dermafocus regenerative products (Newest®, Plinest®). It serves as an intelligent, real-time interface to the manufacturer's Instructions For Use (IFU) and clinical training protocols.
          </p>
          <p className="text-slate-700 leading-relaxed print:text-black">
            Unlike generic large language models (LLMs), DermaAI is engineered with a strict <strong>Hybrid RAG (Retrieval-Augmented Generation)</strong> architecture to minimize hallucination and ensure strict adherence to medical safety guardrails.
          </p>
        </section>

        {/* 2. System Architecture */}
        <section className="mb-10 break-inside-avoid">
          <h3 className="text-lg font-bold text-slate-900 uppercase tracking-wider mb-4 border-l-4 border-teal-500 pl-3 print:border-slate-800 print:text-black">
            2. Technical Architecture
          </h3>
          
          <div className="grid md:grid-cols-2 gap-6 mb-6">
            <div className="bg-slate-50 p-5 rounded-lg border border-slate-200 print:bg-white print:border-slate-300">
              <div className="flex items-center gap-2 mb-3">
                <Cpu className="text-teal-600 print:text-slate-800" size={20} />
                <h4 className="font-bold text-slate-900 print:text-black">AI Core</h4>
              </div>
              <p className="text-sm text-slate-600 print:text-black">
                Powered by <strong>Google Gemini 2.5 Flash</strong>. Selected for its multimodal capabilities and long context window (1M+ tokens), allowing the injection of full clinical protocols directly into the system prompt context while processing text, voice, and video.
              </p>
            </div>
            <div className="bg-slate-50 p-5 rounded-lg border border-slate-200 print:bg-white print:border-slate-300">
              <div className="flex items-center gap-2 mb-3">
                <Database className="text-teal-600 print:text-slate-800" size={20} />
                <h4 className="font-bold text-slate-900 print:text-black">Hybrid Knowledge Base</h4>
              </div>
              <p className="text-sm text-slate-600 print:text-black">
                Data is split into two streams:
                <br/>1. <strong>Structured DB (JSON):</strong> Rigid parameters (Dose, Depth, Tools).
                <br/>2. <strong>Narrative (Text):</strong> Context, MoA, and clinical nuance.
              </p>
            </div>
          </div>

          <div className="bg-slate-900 text-white p-6 rounded-xl overflow-hidden relative print:bg-white print:text-black print:border print:border-black">
            <div className="relative z-10">
              <h4 className="font-bold mb-2 text-teal-400 print:text-black">The "Multimodal Reasoning Pipeline"</h4>
              <p className="text-sm text-slate-300 font-mono print:text-black">
                Input (Text / Voice / <strong>Video Frames</strong>) → <br/>
                [Step 1] Multimodal Feature Extraction → <br/>
                [Step 2] Query Structured DB (Exact Match) → <br/>
                [Step 3] Retrieve Narrative Context (Enrichment) → <br/>
                [Step 4] Safety Guardrail Check → <br/>
                Response (Voice / Text)
              </p>
            </div>
          </div>
        </section>

        {/* 3. Core Modules */}
        <section className="mb-10 break-inside-avoid">
          <h3 className="text-lg font-bold text-slate-900 uppercase tracking-wider mb-4 border-l-4 border-teal-500 pl-3 print:border-slate-800 print:text-black">
            3. Functional Modules
          </h3>
          
          <div className="space-y-4">
            <div className="flex gap-4">
              <div className="w-12 h-12 bg-teal-100 rounded-lg flex items-center justify-center shrink-0 text-teal-700 print:bg-white print:border print:border-slate-300 print:text-black">
                <FileText size={24} />
              </div>
              <div>
                <h4 className="font-bold text-slate-900 print:text-black">Clinical Intelligence (Chat)</h4>
                <p className="text-sm text-slate-600 print:text-black">
                  Natural language interface for ad-hoc clinical queries. Capable of answering specific questions on dosing, contraindications, and product composition.
                </p>
              </div>
            </div>

            <div className="flex gap-4">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center shrink-0 text-blue-700 print:bg-white print:border print:border-slate-300 print:text-black">
                <Database size={24} />
              </div>
              <div>
                <h4 className="font-bold text-slate-900 print:text-black">Structured Protocols</h4>
                <p className="text-sm text-slate-600 print:text-black">
                  Static, step-by-step guides that can be toggled into "Procedure Mode" for sterile, hands-free operation during treatment sessions.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* 4. Safety Guardrails */}
        <section className="mb-10 break-inside-avoid">
          <h3 className="text-lg font-bold text-slate-900 uppercase tracking-wider mb-4 border-l-4 border-teal-500 pl-3 print:border-slate-800 print:text-black">
            4. Safety & Compliance
          </h3>
          <p className="text-slate-700 mb-4 print:text-black">
            The system operates under a specific "Negative Constraint" prompt architecture to ensure medical safety:
          </p>
          <ul className="list-disc pl-6 space-y-2 text-slate-700 print:text-black">
            <li><strong>No Diagnosis:</strong> The AI explicitly refuses to diagnose skin conditions.</li>
            <li><strong>Scope Limitation:</strong> Answers are restricted *only* to Dermafocus indexed products.</li>
            <li><strong>Uncertainty Handling:</strong> If a specific protocol parameter is missing from the Structured DB, the AI states it does not know, rather than hallucinating a plausible value.</li>
          </ul>
        </section>

        {/* Footer */}
        <div className="border-t border-slate-200 pt-8 text-center print:border-slate-400">
          <p className="text-xs text-slate-400 print:text-black">
            CONFIDENTIAL • FOR INTERNAL CLINICAL USE ONLY • DERMAFOCUS 2025
          </p>
        </div>

      </div>
    </div>
  );
};

export default SystemDocs;