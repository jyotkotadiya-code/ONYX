import React from 'react';
import { Lock, Globe } from 'lucide-react';

interface PrivacyIndicatorProps {
  offlineMode?: boolean;
  verifiedPrivate?: boolean;
  compact?: boolean;
}

/**
 * Displays an honest, restrained privacy indicator based on actual runtime configuration.
 * Never claims offline mode if offlineMode is false.
 */
export const PrivacyIndicator: React.FC<PrivacyIndicatorProps> = ({
  offlineMode = true,
  verifiedPrivate = true,
  compact = false,
}) => {
  const isStrictlyLocal = Boolean(offlineMode && verifiedPrivate);

  if (compact) {
    return (
      <div
        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium border border-zinc-200 dark:border-zinc-800 bg-zinc-100/80 dark:bg-zinc-900/80 text-zinc-600 dark:text-zinc-300"
        title={
          isStrictlyLocal
            ? 'All documents, embeddings, and AI inference run locally on this machine.'
            : 'Running on local workstation.'
        }
      >
        {isStrictlyLocal ? (
          <>
            <Lock className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
            <span>Local & private</span>
          </>
        ) : (
          <>
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
            <span>Local network mode</span>
          </>
        )}
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center gap-2 text-xs text-zinc-500 dark:text-zinc-400">
      {isStrictlyLocal ? (
        <>
          <Lock className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
          <span>Your data stays local</span>
        </>
      ) : (
        <>
          <Globe className="w-3.5 h-3.5 text-amber-500 shrink-0" />
          <span>Connected workspace</span>
        </>
      )}
    </div>
  );
};
