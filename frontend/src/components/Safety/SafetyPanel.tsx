import React from 'react';
import { ShieldAlert, Info, TriangleAlert, FileWarning, CircleHelp } from 'lucide-react';

const SafetyPanel: React.FC = () => {
  return (
    <div className="p-6 md:p-8 max-w-4xl mx-auto h-full overflow-y-auto">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-slate-900 flex items-center gap-3">
            <ShieldAlert className="text-teal-600" />
            Safety & Clinical Guardrails
        </h2>
        <p className="text-slate-500 mt-2">
            The DermaAI CKPA operates within strict medical guardrails to ensure patient safety and regulatory compliance.
        </p>
      </div>

      <div className="grid gap-6">
        {/* FAQ Section - Moved to top for visibility */}
        <div className="bg-teal-50 border border-teal-100 rounded-xl p-6">
            <h3 className="text-lg font-bold text-teal-900 mb-4 flex items-center gap-2">
                <CircleHelp size={20} />
                Agent Capabilities FAQ
            </h3>
            <div className="space-y-4">
                <div className="border-b border-teal-200/50 pb-3 last:border-0 last:pb-0">
                    <h4 className="text-sm font-bold text-teal-800 mb-1">Who is this tool for?</h4>
                    <p className="text-sm text-slate-700">
                        Designed exclusively for Aesthetic Clinicians (Doctors, Nurses, Dentists) using Dermafocus products. It is not for patient use.
                    </p>
                </div>
                <div className="border-b border-teal-200/50 pb-3 last:border-0 last:pb-0">
                    <h4 className="text-sm font-bold text-teal-800 mb-1">Does it provide medical advice?</h4>
                    <p className="text-sm text-slate-700">
                        No. It provides information based on indexed clinical protocols. It does not offer personalized medical diagnosis or treatment plans for specific patients.
                    </p>
                </div>
                <div className="border-b border-teal-200/50 pb-3 last:border-0 last:pb-0">
                    <h4 className="text-sm font-bold text-teal-800 mb-1">What sources does it use?</h4>
                    <p className="text-sm text-slate-700">
                        It references a closed knowledge base of official Dermafocus clinical literature, Instructions for Use (IFU), and training protocols.
                    </p>
                </div>
            </div>
        </div>

        <div className="bg-orange-50 border border-orange-100 rounded-xl p-6">
            <h3 className="text-lg font-bold text-orange-800 mb-4 flex items-center gap-2">
                <TriangleAlert size={20} />
                Prohibited Agent Behaviors
            </h3>
            <ul className="space-y-3">
                {[
                    "Providing diagnostic suggestions for specific patients",
                    "Recommending off-label treatments outside indexed protocols",
                    "Comparing Dermafocus products with competitor brands (e.g., toxins, other fillers)",
                    "Suggesting dosing modifications beyond manufacturer guidelines"
                ].map((item, i) => (
                    <li key={i} className="flex items-start gap-3 text-orange-900/80 text-sm">
                        <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-orange-400 shrink-0" />
                        {item}
                    </li>
                ))}
            </ul>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
             <h3 className="text-lg font-bold text-slate-900 mb-4 flex items-center gap-2">
                <Info size={20} className="text-teal-600" />
                Uncertainty Protocol
            </h3>
            <p className="text-slate-600 text-sm leading-relaxed mb-4">
                If the AI lacks specific information in its indexed knowledge base, it is programmed to state:
            </p>
            <div className="bg-slate-100 p-4 rounded-lg border-l-4 border-slate-400 italic text-slate-700 text-sm">
                "I don't have specific guidance on this topic in my current knowledge base. For this question, I recommend contacting Dermafocus clinical support directly or reviewing the full HCP brochure."
            </div>
        </div>

        <div className="bg-red-50 border border-red-100 rounded-xl p-6">
             <h3 className="text-lg font-bold text-red-900 mb-4 flex items-center gap-2">
                <FileWarning size={20} />
                Complication Escalation
            </h3>
            <p className="text-sm text-red-800 mb-3">
                Queries classified as potential adverse events trigger specific handling:
            </p>
            <ol className="list-decimal list-inside space-y-2 text-sm text-red-800/80 font-medium">
                <li>Immediate retrieval of safety protocols</li>
                <li>Explicit disclaimer that AI does not replace clinical judgment</li>
                <li>Suggestion to contact Medical Director for severe events</li>
            </ol>
        </div>
      </div>
    </div>
  );
};

export default SafetyPanel;