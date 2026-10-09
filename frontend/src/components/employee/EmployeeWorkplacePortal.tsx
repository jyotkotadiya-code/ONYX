import React, { useEffect, useState } from 'react';
import {
  Users,
  MessageSquare,
  Bot,
  Building2,
  Sparkles,
  ShieldCheck,
  Sun,
  Moon,
  LogOut,
  ArrowRight,
  RefreshCw,
  Clock,
  CheckCircle2,
  FolderKanban,
  Zap,
} from 'lucide-react';
import { OnyxLogo } from '../system/OnyxLogo';

interface ApprovedWorkplace {
  id: string;
  name: string;
  slug?: string;
  logo?: string;
  description?: string;
  assistant_name?: string;
  welcome_message?: string;
  department_name?: string;
  job_title?: string;
  allowed_collections?: string[];
  is_current?: boolean;
  is_approved?: boolean;
  can_upload?: boolean;
}

interface EmployeeWorkplacePortalProps {
  user: any;
  currentWorkplace: any;
  darkMode: boolean;
  onToggleDarkMode: () => void;
  onLogout: () => void;
  onJoinWorkplace: (workplaceId: string) => Promise<void>;
  onEnterActiveChat: () => void;
}

export const EmployeeWorkplacePortal: React.FC<EmployeeWorkplacePortalProps> = ({
  user,
  currentWorkplace,
  darkMode,
  onToggleDarkMode,
  onLogout,
  onJoinWorkplace,
  onEnterActiveChat,
}) => {
  const [approvedList, setApprovedList] = useState<ApprovedWorkplace[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [joiningId, setJoiningId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState('');

  const fetchApprovedWorkplaces = async () => {
    setIsLoading(true);
    setErrorMessage('');
    try {
      const token = localStorage.getItem('rag_token') || sessionStorage.getItem('rag_token');
      const resp = await fetch('/api/workplaces/my-approved', {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (resp.ok) {
        const data = await resp.json();
        setApprovedList(data || []);
      } else {
        setErrorMessage('Failed loading your approved workplace teams.');
      }
    } catch (e: any) {
      setErrorMessage('Could not connect to server.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchApprovedWorkplaces();
  }, []);

  const handleJoinClick = async (wpId: string) => {
    setJoiningId(wpId);
    setErrorMessage('');
    try {
      await onJoinWorkplace(wpId);
    } catch (e: any) {
      setErrorMessage(e.message || 'Could not join team workspace.');
      setJoiningId(null);
    }
  };

  return (
    <div className="min-h-screen bg-[#f8f9fa] dark:bg-[#0b0c0e] text-zinc-900 dark:text-zinc-100 flex flex-col font-sans transition-colors duration-300">
      {/* ─── Top Navigation Header ─── */}
      <header className="sticky top-0 z-30 border-b border-zinc-200/80 dark:border-zinc-800/80 bg-white/80 dark:bg-[#111317]/80 backdrop-blur-md px-6 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <OnyxLogo size="sm" />
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold tracking-tight text-sm">ONYX Workplace Portal</span>
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-md bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 font-semibold border border-emerald-500/30">
                Employee Hub
              </span>
            </div>
            <p className="text-[11px] text-zinc-500 dark:text-zinc-400">
              Join your admin-approved teams and workspaces
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {currentWorkplace && (
            <button
              onClick={onEnterActiveChat}
              className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium shadow-md shadow-emerald-600/20 transition transform active:scale-95"
            >
              <MessageSquare className="w-3.5 h-3.5" />
              <span>Launch {currentWorkplace.name} Chat</span>
            </button>
          )}

          <button
            onClick={fetchApprovedWorkplaces}
            disabled={isLoading}
            className="p-2 rounded-xl bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300 hover:bg-zinc-200 dark:hover:bg-zinc-700 transition"
            title="Refresh Teams"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>

          <button
            onClick={onToggleDarkMode}
            className="p-2 rounded-xl bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300 hover:bg-zinc-200 dark:hover:bg-zinc-700 transition"
            title="Toggle Theme"
          >
            {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>

          <div className="h-4 w-[1px] bg-zinc-300 dark:bg-zinc-700" />

          <div className="flex items-center gap-2.5 pl-1">
            <div className="w-8 h-8 rounded-full bg-emerald-500/20 border border-emerald-500/40 text-emerald-600 dark:text-emerald-400 flex items-center justify-center font-bold text-xs uppercase">
              {(user?.name || user?.username || 'E')[0]}
            </div>
            <div className="hidden sm:block text-left">
              <div className="text-xs font-semibold">{user?.name || user?.username}</div>
              <div className="text-[10px] text-zinc-500 dark:text-zinc-400">
                {user?.job_title || 'Employee'}
              </div>
            </div>
            <button
              onClick={onLogout}
              className="p-2 rounded-xl hover:bg-red-500/10 text-zinc-400 hover:text-red-500 transition"
              title="Sign Out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* ─── Main Portal Container ─── */}
      <main className="flex-1 max-w-5xl w-full mx-auto px-6 py-10 flex flex-col gap-8">
        {/* Welcome Banner */}
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-emerald-950 via-zinc-900 to-zinc-900 text-white p-8 border border-emerald-900/50 shadow-2xl">
          <div className="absolute top-0 right-0 -mt-12 -mr-12 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
          <div className="relative z-10 max-w-2xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-300 text-xs font-medium mb-3 border border-emerald-500/30">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Admin Approved Employee Access</span>
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl text-white">
              Welcome, {user?.name || user?.username}!
            </h1>
            <p className="mt-2 text-sm text-zinc-300 leading-relaxed">
              Select an approved team workspace to enter your AI assistant, access team knowledge collections, and ask questions across company documents.
            </p>

            {currentWorkplace && (
              <div className="mt-6">
                <button
                  onClick={onEnterActiveChat}
                  className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-zinc-950 text-xs font-bold shadow-lg shadow-emerald-500/25 transition transform active:scale-95"
                >
                  <Zap className="w-4 h-4" />
                  <span>Continue Active Chat ({currentWorkplace.name})</span>
                </button>
              </div>
            )}
          </div>
        </div>

        {errorMessage && (
          <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/30 text-red-500 text-xs font-medium flex items-center justify-between">
            <span>{errorMessage}</span>
            <button onClick={() => setErrorMessage('')} className="text-xs font-bold">✕</button>
          </div>
        )}

        {/* Section Heading */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold tracking-tight">Your Approved Workplaces & Teams</h2>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Workplaces and departments assigned to your employee account by your administrator.
            </p>
          </div>

          <button
            onClick={fetchApprovedWorkplaces}
            className="text-xs text-emerald-600 dark:text-emerald-400 hover:underline flex items-center gap-1 font-medium"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Check Updates</span>
          </button>
        </div>

        {/* Loading State */}
        {isLoading ? (
          <div className="py-16 text-center flex flex-col items-center">
            <RefreshCw className="w-8 h-8 text-emerald-500 animate-spin mb-3" />
            <p className="text-sm font-medium text-zinc-500 dark:text-zinc-400">
              Loading your approved workplace teams...
            </p>
          </div>
        ) : approvedList.length === 0 ? (
          /* ─── Blank / Awaiting Admin Approval Screen ─── */
          <div className="p-12 rounded-3xl border border-dashed border-zinc-300 dark:border-zinc-800 bg-white/60 dark:bg-zinc-900/40 text-center flex flex-col items-center shadow-sm">
            <div className="w-16 h-16 rounded-3xl bg-amber-500/10 border border-amber-500/30 text-amber-500 flex items-center justify-center mb-4">
              <Clock className="w-8 h-8" />
            </div>
            <h3 className="font-bold text-lg text-zinc-900 dark:text-zinc-100">
              Awaiting Admin Team Assignment
            </h3>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 max-w-md mt-2 leading-relaxed">
              Your employee account has been created, but your administrator hasn't assigned you to an active team or workplace yet.
              <br />
              Once an admin enters your team details in the app, your approved workspace will appear here automatically.
            </p>

            <div className="mt-6 flex items-center gap-3">
              <button
                onClick={fetchApprovedWorkplaces}
                className="px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-md shadow-emerald-600/20 transition flex items-center gap-2"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Refresh Assignment Status</span>
              </button>
            </div>
          </div>
        ) : (
          /* ─── Approved Workplaces & Teams Grid ─── */
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {approvedList.map((wp) => {
              const isCurrent = wp.id === currentWorkplace?.id;
              const isJoining = joiningId === wp.id;

              return (
                <div
                  key={wp.id}
                  className={`group relative rounded-3xl p-6 border transition-all duration-300 flex flex-col justify-between ${
                    isCurrent
                      ? 'bg-white dark:bg-[#14171c] border-emerald-500/60 shadow-xl shadow-emerald-500/5 ring-1 ring-emerald-500/30'
                      : 'bg-white dark:bg-[#111317] border-zinc-200 dark:border-zinc-800/80 hover:border-zinc-300 dark:hover:border-zinc-700 hover:shadow-lg'
                  }`}
                >
                  <div>
                    {/* Top Row */}
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <div className="w-11 h-11 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-500 flex items-center justify-center font-bold text-lg">
                          {wp.logo ? (
                            <img src={wp.logo} alt={wp.name} className="w-7 h-7 object-contain" />
                          ) : (
                            wp.name[0]?.toUpperCase()
                          )}
                        </div>
                        <div>
                          <h3 className="font-bold text-lg tracking-tight group-hover:text-emerald-500 transition-colors">
                            {wp.name}
                          </h3>
                          <span className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">
                            {wp.department_name || 'General Team'}
                          </span>
                        </div>
                      </div>

                      {isCurrent ? (
                        <span className="inline-flex items-center gap-1 text-[11px] px-2.5 py-1 rounded-full font-medium bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30">
                          <CheckCircle2 className="w-3 h-3" />
                          Current Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] px-2.5 py-1 rounded-full font-medium bg-emerald-500/10 text-emerald-500">
                          <ShieldCheck className="w-3 h-3" />
                          Approved
                        </span>
                      )}
                    </div>

                    <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-2 line-clamp-2 leading-relaxed">
                      {wp.description || wp.welcome_message || 'Access team knowledge, ask AI questions, and collaborate with your department.'}
                    </p>

                    {/* AI Assistant & Role info */}
                    <div className="mt-4 pt-3 border-t border-zinc-100 dark:border-zinc-800/60 flex flex-wrap items-center justify-between gap-2 text-xs text-zinc-500 dark:text-zinc-400">
                      <div className="flex items-center gap-1.5">
                        <Bot className="w-4 h-4 text-emerald-500" />
                        <span>AI: <strong className="text-zinc-700 dark:text-zinc-200">{wp.assistant_name || `${wp.name} AI`}</strong></span>
                      </div>
                      <div>
                        Role: <strong className="text-zinc-700 dark:text-zinc-200">{wp.job_title || 'Employee'}</strong>
                      </div>
                    </div>

                    {/* Knowledge Collections */}
                    {wp.allowed_collections && wp.allowed_collections.length > 0 && (
                      <div className="mt-3 flex items-center gap-1.5 flex-wrap">
                        <span className="text-[10px] text-zinc-400 uppercase font-semibold">Scope:</span>
                        {wp.allowed_collections.map((col) => (
                          <span
                            key={col}
                            className="text-[10px] px-2 py-0.5 rounded-md bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300 font-mono"
                          >
                            📁 {col}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Primary Action Button */}
                  <div className="mt-6 pt-4 border-t border-zinc-100 dark:border-zinc-800/60 flex items-center justify-end">
                    <button
                      onClick={() => handleJoinClick(wp.id)}
                      disabled={isJoining}
                      className={`w-full py-2.5 px-4 rounded-xl text-xs font-bold flex items-center justify-center gap-2 transition shadow-md ${
                        isCurrent
                          ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-600/20'
                          : 'bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-100 dark:hover:bg-white text-white dark:text-zinc-950'
                      }`}
                    >
                      {isJoining ? (
                        <span>Joining Team Workspace...</span>
                      ) : isCurrent ? (
                        <>
                          <Zap className="w-4 h-4" />
                          <span>Enter Team Chat UI</span>
                        </>
                      ) : (
                        <>
                          <span>Join & Launch Team Workspace</span>
                          <ArrowRight className="w-4 h-4" />
                        </>
                      )}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
};
