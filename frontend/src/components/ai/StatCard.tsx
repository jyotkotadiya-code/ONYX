import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface StatCardProps {
  id?: string;
  title?: string | null;
  data: {
    label?: string;
    value?: number | string;
    format?: 'currency' | 'percent' | 'number' | string;
    change?: number | null;
    change_label?: string | null;
    trend?: 'up' | 'down' | 'neutral' | string;
  };
}

export const StatCard: React.FC<StatCardProps> = ({ id, title, data }) => {
  const formatVal = (val: number | string | undefined, fmt?: string) => {
    if (val === undefined || val === null) return '—';
    if (typeof val === 'string') return val;
    if (fmt === 'currency') {
      return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        maximumFractionDigits: 2,
      }).format(val);
    }
    if (fmt === 'percent') {
      return `${val > 0 ? '+' : ''}${Number(val).toFixed(2)}%`;
    }
    return new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 }).format(val);
  };

  const trend = data?.trend || (typeof data?.change === 'number' && data.change > 0 ? 'up' : 'neutral');

  return (
    <div
      data-component-id={id}
      className="rounded-xl border border-indigo-500/25 dark:border-indigo-500/30 bg-gradient-to-br from-indigo-50/70 via-white to-slate-50 dark:from-indigo-950/40 dark:via-slate-900 dark:to-slate-900 p-4 shadow-sm"
    >
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
          {data?.label || title || 'Key Metric'}
        </span>
        {id && (
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-200/70 dark:bg-slate-800 text-slate-500">
            {id}
          </span>
        )}
      </div>

      <div className="flex items-baseline justify-between gap-3 mt-1">
        <div className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
          {formatVal(data?.value, data?.format)}
        </div>

        {(data?.change !== undefined && data?.change !== null) && (
          <div
            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${
              trend === 'up'
                ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
                : trend === 'down'
                ? 'bg-rose-500/15 text-rose-600 dark:text-rose-400'
                : 'bg-slate-500/15 text-slate-600 dark:text-slate-300'
            }`}
          >
            {trend === 'up' && <TrendingUp className="w-3.5 h-3.5" />}
            {trend === 'down' && <TrendingDown className="w-3.5 h-3.5" />}
            {trend === 'neutral' && <Minus className="w-3.5 h-3.5" />}
            <span>
              {typeof data.change === 'number'
                ? `${data.change > 0 ? '+' : ''}${data.change}%`
                : data.change}
            </span>
          </div>
        )}
      </div>

      {data?.change_label && (
        <div className="mt-1.5 text-xs text-slate-500 dark:text-slate-400">
          {data.change_label}
        </div>
      )}
    </div>
  );
};
