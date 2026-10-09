import React from 'react';
import { LayoutPanelLeft, Sparkles, Layers, ChevronRight } from 'lucide-react';
import { StructuredResponse } from '../../types/structured';
import { ComponentRenderer } from './ComponentRenderer';
import { SourceCard } from '../ai/SourceCard';

interface ResponseBlockProps {
  structured: StructuredResponse;
  onSelectSource?: (docId: string, chunkId?: string, page?: number) => void;
  onOpenWorkspace?: (structured: StructuredResponse) => void;
  onMutateCommand?: (command: string) => void;
}

export const ResponseBlock: React.FC<ResponseBlockProps> = ({
  structured,
  onSelectSource,
  onOpenWorkspace,
  onMutateCommand,
}) => {
  const components = Array.isArray(structured?.components) ? structured.components : [];
  const statComponents = components.filter((c) => c.type === 'stat');
  const otherComponents = components.filter((c) => c.type !== 'stat');

  const hasRichVisuals = components.some((c) =>
    ['table', 'chart', 'stat', 'timeline', 'comparison'].includes(c.type)
  );

  return (
    <div className="space-y-3">
      {/* Structured Workspace Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-1.5 border-b border-slate-200/70 dark:border-slate-800">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-semibold bg-emerald-500/15 text-emerald-600 dark:text-emerald-300">
            <Sparkles className="w-3 h-3" />
            <span className=" uppercase">{structured.response_type}</span>
          </span>
          <span className="text-xs font-semibold text-slate-700 dark:text-slate-200">
            {structured.title}
          </span>
          <span className="text-[11px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-600 dark:text-emerald-400">
            v{structured.version || 1}
          </span>
          {typeof structured.confidence === 'number' && (
            <span className="text-[11px] text-slate-400">
              Confidence: {(structured.confidence * 100).toFixed(0)}%
            </span>
          )}
        </div>

        {onOpenWorkspace && components.length > 0 && (
          <button
            type="button"
            onClick={() => onOpenWorkspace(structured)}
            className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white shadow-md shadow-emerald-600/20 transition-all transform active:scale-95"
          >
            <LayoutPanelLeft className="w-3.5 h-3.5" />
            <span>Open Artifact Canvas</span>
          </button>
        )}
      </div>

      {/* Embedded Artifact View CTA Banner */}
      {onOpenWorkspace && (hasRichVisuals || components.length >= 1) && (
        <div className="my-2.5 p-3 rounded-2xl bg-gradient-to-r from-emerald-500/10 via-teal-500/10 to-emerald-500/10 border border-emerald-500/30 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 shadow-sm">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-xl bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shrink-0">
              <LayoutPanelLeft className="w-4 h-4" />
            </div>
            <div>
              <div className="text-xs font-bold text-zinc-900 dark:text-zinc-100">
                Interactive Artifact View Ready
              </div>
              <div className="text-[11px] text-zinc-500 dark:text-zinc-400">
                View structured tables, interactive charts, and KPI stats on canvas.
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={() => onOpenWorkspace(structured)}
            className="px-3.5 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-md shadow-emerald-600/20 transition flex items-center justify-center gap-1 shrink-0 active:scale-95"
          >
            <span>Open Artifact View</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* KPI Stat Grid if multiple stats */}
      {statComponents.length > 0 && (
        <div
          className={`grid gap-3 ${
            statComponents.length >= 3
              ? 'grid-cols-1 sm:grid-cols-3'
              : statComponents.length === 2
              ? 'grid-cols-1 sm:grid-cols-2'
              : 'grid-cols-1'
          }`}
        >
          {statComponents.map((comp, idx) => (
            <ComponentRenderer
              key={comp.id || `stat_${idx}`}
              component={comp}
              onSelectSource={onSelectSource}
              onMutateCommand={onMutateCommand}
            />
          ))}
        </div>
      )}

      {/* Remaining Structured Components */}
      <div className="space-y-3">
        {otherComponents.map((comp, idx) => (
          <ComponentRenderer
            key={comp.id || `comp_${idx}`}
            component={comp}
            onSelectSource={onSelectSource}
            onMutateCommand={onMutateCommand}
          />
        ))}
      </div>

      {/* Grounded Sources Footer */}
      {structured.sources && structured.sources.length > 0 && (
        <SourceCard sources={structured.sources} onSelectSource={onSelectSource} />
      )}
    </div>
  );
};
