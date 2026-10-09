import React from 'react';
import { LayoutPanelLeft, Sparkles, Layers } from 'lucide-react';
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
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-semibold bg-indigo-500/15 text-indigo-600 dark:text-indigo-300">
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

        {onOpenWorkspace && (hasRichVisuals || components.length > 1) && (
          <button
            type="button"
            onClick={() => onOpenWorkspace(structured)}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-sm transition-colors"
          >
            <LayoutPanelLeft className="w-3.5 h-3.5" />
            <span>Open in Workspace Canvas</span>
          </button>
        )}
      </div>

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
