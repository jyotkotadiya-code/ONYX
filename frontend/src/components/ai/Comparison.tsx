import React from 'react';
import { Scale, Trophy } from 'lucide-react';

interface ComparisonMetric {
  label: string;
  values: Array<string | number>;
  winner?: string;
}

interface ComparisonProps {
  id?: string;
  title?: string | null;
  data: {
    title?: string;
    entities?: string[];
    metrics?: ComparisonMetric[];
  };
}

export const Comparison: React.FC<ComparisonProps> = ({ id, title, data }) => {
  const entities = Array.isArray(data?.entities) ? data.entities : [];
  const metrics = Array.isArray(data?.metrics) ? data.metrics : [];
  const heading = data?.title || title || 'Entity Comparison';

  return (
    <div
      data-component-id={id}
      className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/80 p-4 shadow-sm overflow-x-auto"
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Scale className="w-4 h-4 text-indigo-500" />
          <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-100">{heading}</h4>
        </div>
        {id && (
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500">
            {id}
          </span>
        )}
      </div>

      <table className="w-full text-left border-collapse text-xs">
        <thead>
          <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400">
            <th className="py-2 px-3 font-semibold">Metric</th>
            {entities.map((ent, idx) => (
              <th key={idx} className="py-2 px-3 font-semibold text-slate-800 dark:text-slate-100">
                {ent}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 dark:divide-slate-800/70">
          {metrics.map((m, rIdx) => (
            <tr key={rIdx} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40">
              <td className="py-2.5 px-3 font-medium text-slate-700 dark:text-slate-300">
                {m.label}
              </td>
              {entities.map((ent, cIdx) => {
                const val = m.values?.[cIdx] ?? '—';
                const isWinner = m.winner && m.winner.toLowerCase() === ent.toLowerCase();
                return (
                  <td
                    key={cIdx}
                    className={`py-2.5 px-3 font-mono ${
                      isWinner
                        ? 'font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-500/5'
                        : 'text-slate-800 dark:text-slate-200'
                    }`}
                  >
                    <div className="inline-flex items-center gap-1.5">
                      <span>{typeof val === 'number' ? val.toLocaleString('en-IN') : val}</span>
                      {isWinner && <Trophy className="w-3.5 h-3.5 text-amber-500" />}
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
