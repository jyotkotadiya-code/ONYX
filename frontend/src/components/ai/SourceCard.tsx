import React from 'react';
import { FileText, Database, ExternalLink } from 'lucide-react';
import { SourceItem } from '../../types/structured';

interface SourceCardProps {
  sources: SourceItem[];
  onSelectSource?: (docId: string, chunkId?: string, page?: number) => void;
}

export const SourceCard: React.FC<SourceCardProps> = ({ sources, onSelectSource }) => {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="pt-2 border-t border-slate-200/70 dark:border-slate-800/80">
      <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-2">
        Verified Grounding Sources ({sources.length})
      </div>
      <div className="flex flex-wrap gap-2">
        {sources.map((src, idx) => {
          const isDb = Boolean(src.table);
          const loc =
            src.locator ||
            (src.table
              ? `table=${src.table}${src.row_id ? ` row=${src.row_id}` : ''}`
              : src.page
              ? `p.${src.page}`
              : 'verified');
          return (
            <button
              key={idx}
              type="button"
              onClick={() =>
                src.document_id &&
                onSelectSource &&
                onSelectSource(src.document_id, src.chunk_id || undefined, src.page || undefined)
              }
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-600 dark:text-indigo-300 border border-indigo-500/20 transition-colors"
            >
              {isDb ? <Database className="w-3.5 h-3.5" /> : <FileText className="w-3.5 h-3.5" />}
              <span>{src.filename}</span>
              <span className="text-[10px] opacity-75 font-mono">({loc})</span>
              {src.document_id && <ExternalLink className="w-3 h-3 opacity-60" />}
            </button>
          );
        })}
      </div>
    </div>
  );
};
