import React from 'react';
import { Check, Clock } from 'lucide-react';

export type AuthTransitionState =
  | 'idle'
  | 'signing_in'
  | 'authenticated'
  | 'preparing_workspace';

interface AuthStatusProps {
  transitionState: AuthTransitionState;
  sessionExpired?: boolean;
}

export const AuthStatus: React.FC<AuthStatusProps> = ({
  transitionState,
  sessionExpired = false,
}) => {
  if (sessionExpired && transitionState === 'idle') {
    return (
      <div
        role="status"
        className="mb-4 p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/25 text-xs text-amber-800 dark:text-amber-200 flex items-start gap-2.5 animate-onyx-content"
      >
        <Clock className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
        <div>
          <div className="font-semibold">Your session has expired.</div>
          <div className="text-amber-700/90 dark:text-amber-300/90 mt-0.5">
            Please sign in again to continue working in your workspace.
          </div>
        </div>
      </div>
    );
  }

  if (transitionState === 'authenticated' || transitionState === 'preparing_workspace') {
    return (
      <div
        role="status"
        aria-live="polite"
        className="py-6 flex flex-col items-center justify-center text-center space-y-3 animate-onyx-content"
      >
        <div className="w-8 h-8 rounded-full bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
          <Check className="w-4 h-4 stroke-[2.5]" />
        </div>
        <div className="space-y-1">
          <div className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            {transitionState === 'authenticated'
              ? 'Authentication successful'
              : 'Preparing workspace'}
          </div>
          <div className="text-xs text-zinc-500 dark:text-zinc-400">
            Loading your local knowledge environment...
          </div>
        </div>
      </div>
    );
  }

  return null;
};
