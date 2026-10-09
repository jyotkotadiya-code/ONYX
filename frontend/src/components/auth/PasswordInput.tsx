import React, { useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';

interface PasswordInputProps {
  id: string;
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  error?: string;
  autoComplete?: string;
}

/**
 * Accessible password input with Show/Hide toggle and >=44px interactive touch targets.
 */
export const PasswordInput: React.FC<PasswordInputProps> = ({
  id,
  value,
  onChange,
  disabled = false,
  error,
  autoComplete = 'current-password',
}) => {
  const [visible, setVisible] = useState(false);

  return (
    <div>
      <div className="relative">
        <input
          id={id}
          name="password"
          type={visible ? 'text' : 'password'}
          value={value}
          disabled={disabled}
          autoComplete={autoComplete}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? `${id}-error` : undefined}
          onChange={(e) => onChange(e.target.value)}
          className={`w-full min-h-[44px] pl-3.5 pr-12 py-2.5 rounded-xl bg-zinc-50 dark:bg-[#111317] border text-sm text-zinc-900 dark:text-zinc-100 transition-colors focus:outline-none focus:ring-2 focus:ring-zinc-900/15 dark:focus:ring-zinc-100/20 ${
            error
              ? 'border-rose-500/70 focus:border-rose-500'
              : 'border-zinc-200 dark:border-zinc-800 focus:border-zinc-900 dark:focus:border-zinc-300'
          }`}
        />
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          disabled={disabled}
          aria-label={visible ? 'Hide password' : 'Show password'}
          className="absolute right-1.5 top-1/2 -translate-y-1/2 min-w-[40px] min-h-[38px] px-2 rounded-lg flex items-center justify-center text-xs font-medium text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 focus:outline-none focus:ring-2 focus:ring-zinc-500/30 transition-colors"
        >
          {visible ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
        </button>
      </div>
      {error && (
        <p id={`${id}-error`} role="alert" className="mt-1.5 text-xs text-rose-600 dark:text-rose-400">
          {error}
        </p>
      )}
    </div>
  );
};
