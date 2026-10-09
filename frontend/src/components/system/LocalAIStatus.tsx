import React from 'react';
import { RefreshCw, AlertCircle } from 'lucide-react';

interface LocalAIStatusProps {
  status: 'online' | 'local_fallback_ready' | 'connecting' | 'degraded' | 'unavailable';
  modelName?: string;
  onRetry?: () => void;
  isRetrying?: boolean;
}

export const LocalAIStatus: React.FC<LocalAIStatusProps> = ({
  status,
  modelName,
  onRetry,
  isRetrying = false,
}) => {
  const shortModel = modelName ? modelName.split('/').pop()?.split('\\').pop() : 'Local Llama';

  if (status === 'unavailable' || status === 'degraded') {
    return (
      <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-lg bg-amber-500/10 border border-amber-500/25 text-xs text-amber-700 dark:text-amber-300">
        <AlertCircle className="w-3.5 h-3.5 text-amber-500 shrink-0" />
        <span>
          {status === 'unavailable'
            ? 'Local AI unavailable'
            : `Local AI degraded (${shortModel})`}
        </span>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            disabled={isRetrying}
            className="inline-flex items-center gap-1 ml-1 px-1.5 py-0.5 rounded bg-amber-500/15 hover:bg-amber-500/25 text-[11px] font-medium transition-colors"
          >
            <RefreshCw className={`w-3 h-3 ${isRetrying ? 'animate-spin' : ''}`} />
            <span>Retry connection</span>
          </button>
        )}
      </div>
    );
  }

  if (status === 'connecting') {
    return (
      <div className="inline-flex items-center gap-2 text-xs text-zinc-500 dark:text-zinc-400">
        <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
        <span>Connecting to local AI...</span>
      </div>
    );
  }

  return (
    <div className="inline-flex items-center gap-2 text-xs text-zinc-600 dark:text-zinc-300">
      <span className="w-2 h-2 rounded-full bg-emerald-500" />
      <span className="font-medium">
        {status === 'local_fallback_ready' ? 'Local AI engine active' : 'Local AI connected'}
      </span>
      {shortModel && (
        <span className="font-mono text-[11px] text-zinc-400 dark:text-zinc-500">
          ({shortModel})
        </span>
      )}
    </div>
  );
};

