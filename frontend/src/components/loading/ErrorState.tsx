import React, { useState } from 'react';
import { AlertCircle, RefreshCw, ChevronDown, ChevronRight } from 'lucide-react';
import { ServiceStatus, ServiceStatusItem } from './ServiceStatus';

interface ErrorStateProps {
  title?: string;
  message?: string;
  services: ServiceStatusItem[];
  technicalDetails?: string;
  onRetry: () => void;
  isRetrying?: boolean;
}

/**
 * Polished error state when the application or backend cannot finish initialization.
 * Never exposes sensitive credentials or filesystem paths.
 */
export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Something went wrong',
  message = "We couldn't finish preparing your workspace.",
  services,
  technicalDetails,
  onRetry,
  isRetrying = false,
}) => {
  const [showTech, setShowTech] = useState(false);

  return (
    <div className="w-full max-w-sm rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-6 shadow-sm animate-onyx-content">
      <div className="flex items-center gap-2.5 text-rose-600 dark:text-rose-400 mb-2">
        <AlertCircle className="w-5 h-5 shrink-0" />
        <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">{title}</h2>
      </div>

      <p className="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed mb-4">{message}</p>

      <div className="divide-y divide-zinc-100 dark:divide-zinc-800/70 border-y border-zinc-100 dark:border-zinc-800/80 mb-5">
        {services.map((srv) => (
          <ServiceStatus key={srv.id} item={srv} />
        ))}
      </div>

      <button
        type="button"
        onClick={onRetry}
        disabled={isRetrying}
        className="w-full min-h-[44px] py-2.5 px-4 rounded-xl bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-100 dark:hover:bg-zinc-200 text-white dark:text-zinc-900 text-xs font-semibold flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
      >
        <RefreshCw className={`w-3.5 h-3.5 ${isRetrying ? 'animate-spin' : ''}`} />
        <span>{isRetrying ? 'Retrying connection...' : 'Retry connection'}</span>
      </button>

      {technicalDetails && (
        <div className="mt-4 pt-3 border-t border-zinc-100 dark:border-zinc-800/70">
          <button
            type="button"
            onClick={() => setShowTech(!showTech)}
            className="flex items-center gap-1 text-[11px] font-medium text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300"
          >
            {showTech ? (
              <ChevronDown className="w-3.5 h-3.5" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5" />
            )}
            <span>Technical details</span>
          </button>
          {showTech && (
            <pre className="mt-2 p-2.5 rounded-lg bg-zinc-100 dark:bg-zinc-950 text-[11px] font-mono text-zinc-500 dark:text-zinc-400 overflow-x-auto">
              {technicalDetails}
            </pre>
          )}
        </div>
      )}
    </div>
  );
};
