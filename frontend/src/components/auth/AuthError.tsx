import React from 'react';
import { AlertCircle } from 'lucide-react';

interface AuthErrorProps {
  title?: string;
  message: string;
}

/**
 * Calm, non-technical authentication error alert.
 * Never exposes SQL errors, stack traces, or internal backend details.
 */
export const AuthError: React.FC<AuthErrorProps> = ({
  title = 'Unable to sign in',
  message,
}) => {
  if (!message) return null;

  return (
    <div
      role="alert"
      aria-live="polite"
      className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/25 text-xs text-rose-700 dark:text-rose-300 flex items-start gap-2.5 animate-onyx-content"
    >
      <AlertCircle className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
      <div className="space-y-0.5">
        <div className="font-semibold text-rose-800 dark:text-rose-200">{title}</div>
        <div className="text-rose-600/90 dark:text-rose-300/90 leading-relaxed">{message}</div>
      </div>
    </div>
  );
};
