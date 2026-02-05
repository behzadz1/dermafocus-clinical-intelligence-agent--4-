import React from 'react';
import { FileText, ExternalLink, ChevronRight } from 'lucide-react';
import { API_BASE_URL } from '../../config';

interface Source {
  document: string;
  title: string;
  page: number;
  section?: string;
  relevance_score: number;
  text_snippet?: string;
  view_url: string;
  download_url: string;
}

interface SourceCardProps {
  source: Source;
  index: number;
  compact?: boolean;
}

export const SourceCard: React.FC<SourceCardProps> = ({ source, index, compact = false }) => {
  const url = source.view_url ? `${API_BASE_URL}${source.view_url}` : '#';
  const relevancePercent = Math.round(source.relevance_score * 100);

  // Relevance color based on score
  const getRelevanceColor = (score: number) => {
    if (score >= 0.6) return 'text-emerald-600 bg-emerald-50';
    if (score >= 0.4) return 'text-teal-600 bg-teal-50';
    return 'text-slate-500 bg-slate-50';
  };

  if (compact) {
    return (
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className="group flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-50/80 hover:bg-teal-50 border border-slate-200/60 hover:border-teal-200 transition-all duration-200"
      >
        <div className="flex items-center justify-center w-5 h-5 rounded bg-teal-100 text-teal-600 text-[10px] font-bold shrink-0">
          {index + 1}
        </div>
        <span className="text-xs text-slate-700 font-medium truncate flex-1">
          {source.title || source.document}
        </span>
        <span className="text-[10px] text-slate-400 font-mono">
          p.{source.page}
        </span>
        <ChevronRight size={12} className="text-slate-300 group-hover:text-teal-500 transition-colors" />
      </a>
    );
  }

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="group block rounded-xl overflow-hidden bg-white border border-slate-200/80 hover:border-teal-300 shadow-sm hover:shadow-md transition-all duration-200"
    >
      {/* Header */}
      <div className="flex items-start gap-3 p-3 bg-gradient-to-r from-slate-50 to-white">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-gradient-to-br from-teal-500 to-teal-600 text-white text-sm font-bold shadow-sm shrink-0">
          {index + 1}
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold text-slate-800 truncate group-hover:text-teal-700 transition-colors">
            {source.title || source.document}
          </h4>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-[11px] text-slate-500">
              Page {source.page}
            </span>
            {source.section && (
              <>
                <span className="text-slate-300">•</span>
                <span className="text-[11px] text-slate-400 truncate">
                  {source.section}
                </span>
              </>
            )}
          </div>
        </div>
        <div className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${getRelevanceColor(source.relevance_score)}`}>
          {relevancePercent}%
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between px-3 py-2 bg-slate-50/50 border-t border-slate-100">
        <div className="flex items-center gap-1.5 text-slate-400">
          <FileText size={12} />
          <span className="text-[10px]">PDF Document</span>
        </div>
        <div className="flex items-center gap-1 text-teal-600 opacity-0 group-hover:opacity-100 transition-opacity">
          <span className="text-[10px] font-medium">View</span>
          <ExternalLink size={10} />
        </div>
      </div>
    </a>
  );
};

// Sources list component for clean rendering
interface SourcesListProps {
  sources: Source[];
  variant?: 'default' | 'compact';
  maxVisible?: number;
}

export const SourcesList: React.FC<SourcesListProps> = ({
  sources,
  variant = 'default',
  maxVisible = 3
}) => {
  const visibleSources = sources.slice(0, maxVisible);
  const isCompact = variant === 'compact';

  return (
    <div className={isCompact ? 'space-y-1.5' : 'space-y-2'}>
      {visibleSources.map((source, idx) => (
        <SourceCard
          key={idx}
          source={source}
          index={idx}
          compact={isCompact}
        />
      ))}
    </div>
  );
};

export default SourceCard;
