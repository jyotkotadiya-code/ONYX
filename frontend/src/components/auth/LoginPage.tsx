import React, { useState } from 'react';
import { Sun, Moon, KeyRound, ArrowLeft } from 'lucide-react';
import { OnyxLogo } from '../system/OnyxLogo';
import { PrivacyIndicator } from '../system/PrivacyIndicator';
import { LocalAIStatus } from '../system/LocalAIStatus';
import { LoginForm } from './LoginForm';
import { AuthTransitionState } from './AuthStatus';

interface LoginPageProps {
  darkMode: boolean;
  onToggleDarkMode: () => void;
  onLogin: (username: string, password: string, rememberMe: boolean) => Promise<void>;
  onActivateInvite?: (inviteToken: string, password: string) => Promise<void>;
  transitionState: AuthTransitionState;
  errorTitle?: string;
  errorMessage: string;
  sessionExpired?: boolean;
  sysStatus?: any;
  apiAvailable: boolean;
  onRetryConnection: () => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({
  darkMode,
  onToggleDarkMode,
  onLogin,
  onActivateInvite,
  transitionState,
  errorTitle,
  errorMessage,
  sessionExpired = false,
  sysStatus,
  apiAvailable,
  onRetryConnection,
}) => {
  const [inviteMode, setInviteMode] = useState(false);
  const [inviteToken, setInviteToken] = useState('');
  const [invitePassword, setInvitePassword] = useState('');
  const [activating, setActivating] = useState(false);

  const llmState = !apiAvailable
    ? 'unavailable'
    : sysStatus?.llm === 'online'
    ? 'online'
    : sysStatus?.llm === 'local_fallback_ready'
    ? 'local_fallback_ready'
    : sysStatus
    ? 'degraded'
    : 'connecting';

  const handleActivateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteToken.trim() || !invitePassword || !onActivateInvite) return;
    setActivating(true);
    try {
      await onActivateInvite(inviteToken.trim(), invitePassword);
    } finally {
      setActivating(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col justify-between bg-[#f8f9fa] dark:bg-[#0b0c0e] text-zinc-900 dark:text-zinc-100 px-6 py-6 transition-colors">
      {/* Top Bar */}
      <header className="w-full max-w-5xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <OnyxLogo size="sm" />
          <span className="text-xs font-semibold tracking-tight text-zinc-800 dark:text-zinc-200">
            ONYX
          </span>
        </div>

        <div className="flex items-center gap-3">
          <LocalAIStatus
            status={llmState}
            modelName={sysStatus?.llm_details?.selected_model}
            onRetry={!apiAvailable ? onRetryConnection : undefined}
          />
          <button
            type="button"
            onClick={onToggleDarkMode}
            aria-label="Toggle color theme"
            className="min-w-[38px] min-h-[38px] p-2 rounded-xl border border-zinc-200/80 dark:border-zinc-800/80 bg-white dark:bg-zinc-900 text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 transition-colors flex items-center justify-center"
          >
            {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
        </div>
      </header>

      {/* Main Content: Centered / Responsive Two-Column on Large Screens */}
      <main className="w-full max-w-5xl mx-auto my-auto py-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-12 items-center">
          {/* Left Brand / Product Column */}
          <div className="lg:col-span-6 space-y-5 text-center lg:text-left animate-onyx-content">
            <div className="inline-flex lg:flex items-center justify-center lg:justify-start gap-3">
              <OnyxLogo size="lg" animated />
              <div className="text-left">
                <div className="text-xs font-mono uppercase tracking-widest text-zinc-400 dark:text-zinc-500">
                  ONYX WORKSPACE
                </div>
                <div className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">
                  Private Workplace AI Platform
                </div>
              </div>
            </div>

            <div className="space-y-2.5">
              <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
                Your private AI workspace.
              </h1>
              <p className="text-sm text-zinc-500 dark:text-zinc-400 max-w-md mx-auto lg:mx-0 leading-relaxed">
                Search, understand and work with your organization’s knowledge — locally.
              </p>
            </div>

            <div className="hidden lg:grid grid-cols-2 gap-3 pt-2 max-w-md">
              {[
                { label: 'Workplace Isolation', desc: 'Role & department-scoped knowledge' },
                { label: 'Multimodal Knowledge', desc: 'PDF, OCR, DOCX, XML, SQLite' },
                { label: 'Structured Canvas', desc: 'Grounded tables, charts & KPIs' },
                { label: '100% Local & Private', desc: 'Zero external cloud calls' },
              ].map((item) => (
                <div
                  key={item.label}
                  className="p-3 rounded-xl border border-zinc-200/70 dark:border-zinc-800/70 bg-white/60 dark:bg-zinc-900/40"
                >
                  <div className="text-xs font-medium text-zinc-800 dark:text-zinc-200">
                    {item.label}
                  </div>
                  <div className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-0.5">
                    {item.desc}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Right Login / Invite Activation Card Column */}
          <div className="lg:col-span-6 flex justify-center lg:justify-end">
            <div className="w-full max-w-[400px] rounded-2xl border border-zinc-200/90 dark:border-zinc-800/90 bg-white dark:bg-[#14161b] p-6 sm:p-8 shadow-sm animate-onyx-content">
              {!inviteMode ? (
                <>
                  <div className="mb-6">
                    <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
                      Sign in
                    </h2>
                    <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
                      Enter your workplace credentials to continue.
                    </p>
                  </div>

                  <LoginForm
                    onSubmit={onLogin}
                    transitionState={transitionState}
                    errorTitle={errorTitle}
                    errorMessage={errorMessage}
                    sessionExpired={sessionExpired}
                  />

                  {onActivateInvite && (
                    <div className="mt-4 text-center">
                      <button
                        type="button"
                        onClick={() => setInviteMode(true)}
                        className="inline-flex items-center gap-1.5 text-xs text-zinc-500 hover:text-emerald-500 transition"
                      >
                        <KeyRound className="w-3.5 h-3.5" />
                        <span>Have a workplace invite code? Activate account</span>
                      </button>
                    </div>
                  )}
                </>
              ) : (
                <>
                  <div className="mb-5">
                    <button
                      type="button"
                      onClick={() => setInviteMode(false)}
                      className="inline-flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-200 mb-3"
                    >
                      <ArrowLeft className="w-3.5 h-3.5" />
                      <span>Back to Sign in</span>
                    </button>
                    <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
                      Activate Workplace Invite
                    </h2>
                    <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
                      Enter the invite token from your workplace administrator and set your password.
                    </p>
                  </div>

                  {errorMessage && (
                    <div className="mb-4 p-3 rounded-xl border border-rose-500/30 bg-rose-500/10 text-xs text-rose-500">
                      {errorMessage}
                    </div>
                  )}

                  <form onSubmit={handleActivateSubmit} className="space-y-4">
                    <div>
                      <label className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1.5">
                        Workplace Invite Token
                      </label>
                      <input
                        type="text"
                        value={inviteToken}
                        onChange={(e) => setInviteToken(e.target.value)}
                        placeholder="Paste invite token..."
                        required
                        className="w-full px-3.5 py-2.5 rounded-xl bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-xs font-mono"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1.5">
                        Create Password (min 6 characters)
                      </label>
                      <input
                        type="password"
                        value={invitePassword}
                        onChange={(e) => setInvitePassword(e.target.value)}
                        placeholder="••••••••"
                        minLength={6}
                        required
                        className="w-full px-3.5 py-2.5 rounded-xl bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-xs"
                      />
                    </div>
                    <button
                      type="submit"
                      disabled={activating || !inviteToken.trim() || invitePassword.length < 6}
                      className="w-full py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-zinc-950 font-semibold text-xs transition"
                    >
                      {activating ? 'Activating account...' : 'Activate & Enter Workplace'}
                    </button>
                  </form>
                </>
              )}

              <div className="mt-6 pt-5 border-t border-zinc-100 dark:border-zinc-800/80">
                <PrivacyIndicator
                  offlineMode={sysStatus?.offline_mode ?? true}
                  verifiedPrivate={sysStatus?.verified_private ?? true}
                />
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="w-full max-w-5xl mx-auto text-center text-[11px] font-mono text-zinc-400 dark:text-zinc-500">
        v1.0.0 • Local AI
      </footer>
    </div>
  );
};
