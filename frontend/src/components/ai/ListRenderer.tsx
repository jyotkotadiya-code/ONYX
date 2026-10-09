import React from 'react';
import { CheckCircle2, ListOrdered, List } from 'lucide-react';

interface ListRendererProps {
  id?: string;
  title?: string | null;
  data: {
    title?: string;
    ordered?: boolean;
    items?: Array<string | { title?: string; label?: string; description?: string; checked?: boolean }>;
  };
}

export const ListRenderer: React.FC<ListRendererProps> = ({ id, title, data }) => {
  const items = Array.isArray(data?.items) ? data.items : [];
  const ordered = Boolean(data?.ordered);
  const heading = data?.title || title;

  return (
    <div
      data-component-id={id}
      className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/80 p-4 shadow-sm"
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {ordered ? (
            <ListOrdered className="w-4 h-4 text-indigo-500" />
          ) : (
            <List className="w-4 h-4 text-indigo-500" />
          )}
          <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-100">
            {heading || 'Key Items'}
          </h4>
        </div>
        {id && (
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500">
            {id}
          </span>
        )}
      </div>

      <div className="space-y-2">
        {items.map((item, idx) => {
          if (typeof item === 'string') {
            return (
              <div
                key={idx}
                className="flex items-start gap-2.5 text-sm text-slate-700 dark:text-slate-200"
              >
                <span className="text-xs font-semibold text-indigo-500 mt-0.5 min-w-[1.25rem]">
                  {ordered ? `${idx + 1}.` : '•'}
                </span>
                <span>{item}</span>
              </div>
            );
          }
          return (
            <div
              key={idx}
              className="flex items-start gap-2.5 p-2 rounded-lg bg-slate-50 dark:bg-slate-800/50 text-sm"
            >
              <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
              <div>
                <div className="font-medium text-slate-800 dark:text-slate-100">
                  {item.title || item.label || `Item ${idx + 1}`}
                </div>
                {item.description && (
                  <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    {item.description}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
