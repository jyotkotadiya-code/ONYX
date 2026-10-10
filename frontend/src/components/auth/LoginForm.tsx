import React, { useState, useEffect } from 'react';
import { PasswordInput } from './PasswordInput';
import { AuthError } from './AuthError';
import { AuthStatus, AuthTransitionState } from './AuthStatus';

interface LoginFormProps {
  onSubmit: (username: string, password: string, rememberMe: boolean) => Promise<void>;
  transitionState: AuthTransitionState;
  errorTitle?: string;
  errorMessage: string;
  sessionExpired?: boolean;
}

export const LoginForm: React.FC<LoginFormProps> = ({
  onSubmit,
  transitionState,
  errorTitle,
  errorMessage,
  sessionExpired = false,
}) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<{ username?: string; password?: string }>({});
  const [isFocused, setIsFocused] = useState(false);

  // Clear any browser-forced autofill on mount
  useEffect(() => {
    setUsername('');
    setPassword('');
    const t = setTimeout(() => {
      setUsername('');
      setPassword('');
    }, 100);
    return () => clearTimeout(t);
  }, []);

  const isProcessing = transitionState !== 'idle';

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isProcessing) return;

    const nextErrors: { username?: string; password?: string } = {};
    if (!username.trim()) {
      nextErrors.username = 'Username required';
    }
    if (!password) {
      nextErrors.password = 'Password required';
    }

    if (Object.keys(nextErrors).length > 0) {
      setFieldErrors(nextErrors);
      return;
    }

    setFieldErrors({});
    await onSubmit(username.trim(), password, rememberMe);
  };

  if (transitionState === 'authenticated' || transitionState === 'preparing_workspace') {
    return <AuthStatus transitionState={transitionState} />;
  }

  return (
    <form onSubmit={handleFormSubmit} noValidate autoComplete="off" className="space-y-4">
      {/* Hidden dummy inputs to consume browser password-manager autofill */}
      <input type="text" name="fake_user_autofill_sink" style={{ display: 'none' }} tabIndex={-1} autoComplete="off" />
      <input type="password" name="fake_pass_autofill_sink" style={{ display: 'none' }} tabIndex={-1} autoComplete="off" />

      <AuthStatus transitionState={transitionState} sessionExpired={sessionExpired} />

      <div>
        <label
          htmlFor="onyx-login-username"
          className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1.5"
        >
          Email / Username
        </label>
        <input
          id="onyx-login-username"
          name="onyx_account_user"
          type="text"
          value={username}
          placeholder="Enter username or email..."
          disabled={isProcessing}
          readOnly={!isFocused}
          onFocus={() => setIsFocused(true)}
          autoComplete="new-password"
          aria-invalid={Boolean(fieldErrors.username)}
          aria-describedby={fieldErrors.username ? 'onyx-login-username-error' : undefined}
          onChange={(e) => {
            setUsername(e.target.value);
            if (fieldErrors.username) setFieldErrors((prev) => ({ ...prev, username: undefined }));
          }}
          className={`w-full min-h-[44px] px-3.5 py-2.5 rounded-xl bg-zinc-50 dark:bg-[#111317] border text-sm text-zinc-900 dark:text-zinc-100 transition-colors focus:outline-none focus:ring-2 focus:ring-zinc-900/15 dark:focus:ring-zinc-100/20 ${
            fieldErrors.username
              ? 'border-rose-500/70 focus:border-rose-500'
              : 'border-zinc-200 dark:border-zinc-800 focus:border-zinc-900 dark:focus:border-zinc-300'
          }`}
        />
        {fieldErrors.username && (
          <p
            id="onyx-login-username-error"
            role="alert"
            className="mt-1.5 text-xs text-rose-600 dark:text-rose-400"
          >
            {fieldErrors.username}
          </p>
        )}
      </div>

      <div>
        <label
          htmlFor="onyx-login-password"
          className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1.5"
        >
          Password
        </label>
        <PasswordInput
          id="onyx-login-password"
          name="onyx_account_secret"
          value={password}
          placeholder="Enter password..."
          disabled={isProcessing}
          readOnly={!isFocused}
          onFocus={() => setIsFocused(true)}
          autoComplete="new-password"
          error={fieldErrors.password}
          onChange={(val) => {
            setPassword(val);
            if (fieldErrors.password) setFieldErrors((prev) => ({ ...prev, password: undefined }));
          }}
        />
      </div>

      <div className="flex items-center justify-between pt-0.5">
        <label className="inline-flex items-center gap-2 cursor-pointer select-none text-xs text-zinc-600 dark:text-zinc-400">
          <input
            type="checkbox"
            checked={rememberMe}
            disabled={isProcessing}
            onChange={(e) => setRememberMe(e.target.checked)}
            className="w-4 h-4 rounded border-zinc-300 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100 focus:ring-zinc-500"
          />
          <span>Remember me</span>
        </label>
      </div>

      {errorMessage && <AuthError title={errorTitle} message={errorMessage} />}

      <button
        type="submit"
        disabled={isProcessing}
        className="w-full min-h-[44px] py-2.5 px-4 rounded-xl bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-100 dark:hover:bg-zinc-200 disabled:opacity-60 text-white dark:text-zinc-950 font-medium text-sm transition-colors flex items-center justify-center gap-2.5"
      >
        {isProcessing ? (
          <>
            <span
              className="w-3.5 h-3.5 rounded-full border-2 border-current border-t-transparent animate-spin"
              aria-hidden="true"
            />
            <span>Signing in...</span>
          </>
        ) : (
          <span>Sign in</span>
        )}
      </button>
    </form>
  );
};
