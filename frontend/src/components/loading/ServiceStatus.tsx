import React from 'react';
import { Check, AlertTriangle, X } from 'lucide-react';

export type ServiceState = 'pending' | 'loading' | 'success' | 'warning' | 'error';

export interface ServiceStatusItem {
  id: string;
  label: string;
  detail?: string;
  state: ServiceState;
  optional?: boolean;
}

export const ServiceStatus: React.FC<{ item: ServiceStatusItem }> = ({ item }) => {
  return (
    <div className="flex items-center justify-between py-2 text-xs">
      <div className="flex items-center gap-3">
        {/* Status Indicator Icon */}
        <span className="w-4 h-4 flex items-center justify-center shrink-0">
          {item.state === 'success' && (
            <Check className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 stroke-[2.5]" />
          )}
          {item.state === 'loading' && (
            <span className="w-2 h-2 rounded-full bg-zinc-900 dark:bg-zinc-100 animate-pulse" />
          )}
          {item.state === 'pending' && (
            <span className="w-2 h-2 rounded-full border border-zinc-400 dark:border-zinc-600" />
          )}
          {item.state === 'warning' && (
            <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
          )}
          {item.state === 'error' && (
            <X className="w-3.5 h-3.5 text-rose-500 stroke-[2.5]" />
          )}
        </span>

        <span
          className={`${
            item.state === 'pending'
              ? 'text-zinc-400 dark:text-zinc-500'
              : item.state === 'loading'
              ? 'text-zinc-900 dark:text-zinc-100 font-medium'
              : 'text-zinc-700 dark:text-zinc-300'
          }`}
        >
          {item.label}
        </span>
      </div>

      {item.detail && (
        <span className="font-mono text-[11px] text-zinc-400 dark:text-zinc-500 truncate max-w-[160px]">
          {item.detail}
        </span>
      )}
    </div>
  );
};
