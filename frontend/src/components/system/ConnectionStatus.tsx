import React from 'react';
import { WifiOff, RefreshCw, AlertTriangle } from 'lucide-react';

interface ConnectionStatusProps {
  apiAvailable: boolean;
  degradedServices?: string[];
  onRetry: () => void;
  isRetrying?: boolean;
}

export const ConnectionStatus: React.FC<ConnectionStatusProps> = ({
  apiAvailable,
  degradedServices = [],
  onRetry,
  isRetrying = false,
}) => {
  if (!apiAvailable) {
    return (
      <div
        role="alert"
        className="px-4 py-2.5 bg-rose-500/10 border-b border-rose-500/25 flex flex-wrap items-center justify-between gap-3 text-xs text-rose-700 dark:text-rose-200"
      >
        <div className="flex items-center gap-2">
          <WifiOff className="w-4 h-4 text-rose-500 shrink-0" />
          <div>
            <span className="font-semibold">Backend unavailable</span>
            <span className="mx-1.5 text-rose-400">•</span>
            <span>Make sure the local RAG server is running.</span>
          </div>
        </div>
        <button
          type="button"
          onClick={onRetry}
          disabled={isRetrying}
          className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white font-medium transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRetrying ? 'animate-spin' : ''}`} />
          <span>Retry connection</span>
        </button>
      </div>
    );
  }

  if (degradedServices.length > 0) {
    return (
      <div
        role="status"
        className="px-4 py-2 bg-amber-500/10 border-b border-amber-500/20 flex flex-wrap items-center justify-between gap-2 text-xs text-amber-800 dark:text-amber-200"
      >
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0" />
          <span>
            Some services are unavailable ({degradedServices.join(', ')}). Core workspace remains active.
          </span>
        </div>
        <button
          type="button"
          onClick={onRetry}
          disabled={isRetrying}
          className="inline-flex items-center gap-1 text-[11px] font-medium underline hover:no-underline"
        >
          <RefreshCw className={`w-3 h-3 ${isRetrying ? 'animate-spin' : ''}`} />
          <span>Retry</span>
        </button>
      </div>
    );
  }

  return null;
};
