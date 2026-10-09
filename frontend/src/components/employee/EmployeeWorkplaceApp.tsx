import React, { useState, useEffect } from 'react';
import {
  MessageSquare,
  Plus,
  Send,
  Sun,
  Moon,
  LogOut,
  User as UserIcon,
  Sparkles,
  Trash2,
  Building2,
  Briefcase,
  Mail,
  ShieldCheck,
  FileText,
  X,
  ChevronRight,
  Clock,
} from 'lucide-react';
import { StructuredResponse } from '../../types/structured';
import { ResponseBlock } from '../workspace/ResponseBlock';
import { Workspace } from '../workspace/Workspace';
import { OnyxLogo } from '../system/OnyxLogo';

interface EmployeeWorkplaceAppProps {
  user: any;
  workplace: any;
  darkMode: boolean;
  onToggleDarkMode: () => void;
  onLogout: () => void;
  messages: any[];
  activeSessionId: string | null;
  activeWorkspace: StructuredResponse | null;
  onSelectWorkspace: (ws: StructuredResponse | null) => void;
  onMutateWorkspace: (command: string, baseWs?: StructuredResponse) => Promise<void>;
  questionInput: string;
  onQuestionChange: (val: string) => void;
  onSendChat: (e?: React.FormEvent, overrideQuestion?: string) => Promise<void>;
  isStreaming: boolean;
  onNewChat: () => void;
  chatSessions: any[];
  onSelectSession: (sessionId: string) => Promise<void>;
  onDeleteSession: (sessionId: string) => Promise<void>;
  onOpenCitationPreview: (docId: string, chunkId?: string, page?: number) => void;
  previewDoc: any | null;
  onClosePreview: () => void;
  chatEndRef: React.RefObject<HTMLDivElement>;
  onOpenPortal?: () => void;
}

const SUGGESTED_WORKPLACE_PROMPTS = [
  'What is our company leave and time-off policy?',
  'Summarize recent project updates and milestones',
  'What are our core onboarding and security guidelines?',
  'Show key metrics or tables from shared reports',
];

export const EmployeeWorkplaceApp: React.FC<EmployeeWorkplaceAppProps> = ({
  user,
  workplace,
  darkMode,
  onToggleDarkMode,
  onLogout,
  messages,
  activeSessionId,
  activeWorkspace,
  onSelectWorkspace,
  onMutateWorkspace,
  questionInput,
  onQuestionChange,
  onSendChat,
  isStreaming,
  onNewChat,
  chatSessions,
  onSelectSession,
  onDeleteSession,
  onOpenCitationPreview,
  previewDoc,
  onClosePreview,
  chatEndRef,
  onOpenPortal,
}) => {
  const [view, setView] = useState<'chat' | 'profile'>(() =>
    window.location.pathname === '/profile' ? 'profile' : 'chat'
  );

  useEffect(() => {
    const targetPath = view === 'profile' ? '/profile' : '/chat';
    if (window.location.pathname !== targetPath) {
      window.history.replaceState(null, '', targetPath);
    }
  }, [view]);

  const firstName = (user?.name || user?.username || 'there').split(' ')[0];
  const hour = new Date().getHours();
  const greetingPrefix =
    hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';

  const workplaceName = workplace?.name || user?.workplace?.name || user?.workspace || 'ONYX Workplace';
  const assistantName = workplace?.assistant_name || 'ONYX AI';
  const welcomeMessage =
    workplace?.welcome_message ||
    'Ask anything about your workplace policies, projects, and shared team knowledge.';

  return (
    <div className="min-h-screen flex bg-[#f8f9fa] dark:bg-[#090a0f] text-zinc-900 dark:text-zinc-100">
      {/* Minimal Employee Left Sidebar */}
      <aside className="w-64 shrink-0 border-r border-zinc-200/80 dark:border-zinc-800/80 bg-white dark:bg-[#0d0f17] flex flex-col justify-between">
        <div className="p-4 space-y-4 flex-1 flex flex-col min-h-0">
          {/* Workplace & Assistant Brand */}
          <div className="flex items-center justify-between px-1">
            <div className="flex items-center gap-2.5 min-w-0">
              <OnyxLogo size="sm" />
              <div className="truncate">
                <div className="text-xs font-bold tracking-tight text-zinc-900 dark:text-zinc-100 truncate">
                  {assistantName}
                </div>
                <div className="text-[11px] text-zinc-500 dark:text-zinc-400 truncate">
                  {workplaceName}
                </div>
              </div>
            </div>
            <button
              onClick={onToggleDarkMode}
              aria-label="Toggle color theme"
              className="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800/70 transition"
            >
              {darkMode ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
            </button>
          </div>

          {/* New Chat Button */}
          <button
            onClick={() => {
              setView('chat');
              onNewChat();
            }}
            className="w-full flex items-center justify-center gap-2 px-3.5 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-semibold text-xs shadow-sm transition"
          >
            <Plus className="w-4 h-4" />
            <span>New Chat</span>
          </button>

          {/* Recent Chats List */}
          <div className="flex-1 flex flex-col min-h-0">
            <div className="px-2 pb-1.5 text-[10px] font-mono uppercase tracking-wider text-zinc-400 dark:text-zinc-500">
              Recent Chats
            </div>
            <div className="flex-1 overflow-y-auto space-y-1 pr-1">
              {chatSessions.length === 0 ? (
                <div className="px-2.5 py-4 text-xs text-zinc-400 dark:text-zinc-500">
                  Your recent conversations will appear here.
                </div>
              ) : (
                chatSessions.map((sess) => {
                  const active = view === 'chat' && activeSessionId === sess.id;
                  return (
                    <div
                      key={sess.id}
                      className={`group flex items-center justify-between rounded-xl px-2.5 py-2 text-xs transition cursor-pointer ${
                        active
                          ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-300 font-medium'
                          : 'text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800/60'
                      }`}
                      onClick={() => {
                        setView('chat');
                        onSelectSession(sess.id);
                      }}
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <MessageSquare className="w-3.5 h-3.5 shrink-0 opacity-70" />
                        <span className="truncate">{sess.title || 'Conversation'}</span>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteSession(sess.id);
                        }}
                        title="Delete conversation"
                        className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-rose-500/15 hover:text-rose-400 transition"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {/* Bottom Employee Profile & Sign Out */}
        <div className="p-3 border-t border-zinc-200/80 dark:border-zinc-800/80 space-y-1">
          <button
            onClick={() => setView(view === 'profile' ? 'chat' : 'profile')}
            className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs transition ${
              view === 'profile'
                ? 'bg-zinc-200/80 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 font-medium'
                : 'text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800/60'
            }`}
          >
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-7 h-7 rounded-full bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-500 font-semibold text-xs shrink-0">
                {(user?.name || user?.username || 'U')[0].toUpperCase()}
              </div>
              <div className="text-left truncate">
                <div className="font-medium truncate">{user?.name || user?.username}</div>
                <div className="text-[10px] text-zinc-400 truncate">
                  {user?.job_title || 'Team Member'}
                </div>
              </div>
            </div>
            <UserIcon className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
          </button>

          <button
            onClick={onLogout}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-xs text-zinc-500 hover:text-rose-500 hover:bg-rose-500/10 transition"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Sign out</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-hidden">
        {/* Minimal Employee Header */}
        <header className="h-14 shrink-0 px-6 border-b border-zinc-200/80 dark:border-zinc-800/80 bg-white/80 dark:bg-[#0d0f17]/80 backdrop-blur flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className="text-sm font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">
              {assistantName}
            </span>
            <span className="text-xs text-zinc-400">•</span>
            <span className="text-xs text-zinc-500 dark:text-zinc-400">
              Private workplace assistant
            </span>
          </div>

          <div className="flex items-center gap-3">
            {onOpenPortal && (
              <button
                onClick={onOpenPortal}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-800 dark:hover:bg-zinc-700 text-xs font-semibold text-zinc-700 dark:text-zinc-200 transition"
                title="View all approved team workplaces"
              >
                <Building2 className="w-3.5 h-3.5 text-emerald-500" />
                <span>My Teams</span>
              </button>
            )}
            {view === 'profile' && (
              <button
                onClick={() => setView('chat')}
                className="px-3 py-1.5 rounded-xl bg-emerald-500 text-zinc-950 font-semibold text-xs hover:bg-emerald-400 transition"
              >
                Back to AI Chat
              </button>
            )}
            <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-[11px] text-emerald-600 dark:text-emerald-300">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>{workplaceName}</span>
            </div>
          </div>
        </header>

        {/* View 1: Employee Profile (/profile) */}
        {view === 'profile' ? (
          <div className="flex-1 overflow-y-auto p-6 sm:p-10">
            <div className="max-w-xl mx-auto space-y-6">
              <div>
                <h1 className="text-xl font-semibold tracking-tight">Your Workplace Profile</h1>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
                  Account details and workplace assignment managed by your organization administrator.
                </p>
              </div>

              <div className="p-6 rounded-2xl bg-white dark:bg-[#12151f] border border-zinc-200/80 dark:border-zinc-800/80 space-y-5 shadow-sm">
                <div className="flex items-center gap-4">
                  <div className="w-14 h-14 rounded-2xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-500 text-xl font-bold">
                    {(user?.name || user?.username || 'U')[0].toUpperCase()}
                  </div>
                  <div>
                    <div className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
                      {user?.name || user?.username}
                    </div>
                    <div className="text-xs text-zinc-500 dark:text-zinc-400">
                      {user?.job_title || 'Employee'} • @{user?.username}
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-3 border-t border-zinc-100 dark:border-zinc-800/80 text-xs">
                  <div className="p-3.5 rounded-xl bg-zinc-50 dark:bg-zinc-900/60 border border-zinc-200/60 dark:border-zinc-800/60">
                    <div className="flex items-center gap-1.5 text-zinc-400 mb-1">
                      <Building2 className="w-3.5 h-3.5" />
                      <span>Workplace</span>
                    </div>
                    <div className="font-semibold text-zinc-900 dark:text-zinc-100">
                      {workplaceName}
                    </div>
                  </div>

                  <div className="p-3.5 rounded-xl bg-zinc-50 dark:bg-zinc-900/60 border border-zinc-200/60 dark:border-zinc-800/60">
                    <div className="flex items-center gap-1.5 text-zinc-400 mb-1">
                      <Briefcase className="w-3.5 h-3.5" />
                      <span>Department</span>
                    </div>
                    <div className="font-semibold text-zinc-900 dark:text-zinc-100">
                      {user?.department || 'General'}
                    </div>
                  </div>

                  {user?.email && (
                    <div className="p-3.5 rounded-xl bg-zinc-50 dark:bg-zinc-900/60 border border-zinc-200/60 dark:border-zinc-800/60 sm:col-span-2">
                      <div className="flex items-center gap-1.5 text-zinc-400 mb-1">
                        <Mail className="w-3.5 h-3.5" />
                        <span>Email</span>
                      </div>
                      <div className="font-semibold text-zinc-900 dark:text-zinc-100">
                        {user.email}
                      </div>
                    </div>
                  )}
                </div>

                <div className="pt-2 flex items-center justify-between">
                  <span className="text-[11px] text-zinc-400">
                    Responses in chat are tailored to the workplace knowledge shared with your role.
                  </span>
                  <button
                    onClick={onLogout}
                    className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl border border-rose-500/30 text-rose-500 hover:bg-rose-500/10 text-xs font-medium transition"
                  >
                    <LogOut className="w-3.5 h-3.5" />
                    <span>Sign out</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        ) : (
          /* View 2: Clean Employee AI Chat (/chat) */
          <div className="flex-1 flex min-h-0 overflow-hidden">
            <div className="flex-1 flex flex-col min-w-0 h-full">
              <div className="flex-1 overflow-y-auto px-4 sm:px-8 py-6">
                {messages.length === 0 ? (
                  <div className="max-w-2xl mx-auto my-12 text-center space-y-6">
                    <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto text-emerald-500">
                      <Sparkles className="w-6 h-6" />
                    </div>
                    <div className="space-y-2">
                      <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">
                        {greetingPrefix}, {firstName}.
                      </h1>
                      <p className="text-base text-zinc-600 dark:text-zinc-300">
                        How can I help you today?
                      </p>
                      <p className="text-xs text-zinc-400 max-w-md mx-auto">
                        {welcomeMessage}
                      </p>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-left pt-2">
                      {SUGGESTED_WORKPLACE_PROMPTS.map((prompt) => (
                        <button
                          key={prompt}
                          onClick={() => onSendChat(undefined, prompt)}
                          className="p-3.5 rounded-2xl border border-zinc-200/80 dark:border-zinc-800/80 bg-white dark:bg-[#12151f] hover:border-emerald-500/40 text-xs text-zinc-700 dark:text-zinc-300 flex items-center justify-between gap-2 transition shadow-sm"
                        >
                          <span>{prompt}</span>
                          <ChevronRight className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
                        </button>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="max-w-3xl mx-auto space-y-6">
                    {messages.map((m) => (
                      <div
                        key={m.id}
                        className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
                      >
                        {m.role === 'user' ? (
                          <div className="max-w-xl rounded-2xl px-4 py-3 bg-emerald-500 text-zinc-950 font-medium text-sm shadow-sm">
                            {m.content}
                          </div>
                        ) : (
                          <div className="w-full rounded-2xl p-5 bg-white dark:bg-[#12151f] border border-zinc-200/80 dark:border-zinc-800/80 shadow-sm space-y-4">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                                <Sparkles className="w-3.5 h-3.5" />
                                <span>{assistantName}</span>
                              </div>
                              {m.structured_response &&
                                m.structured_response.components?.some((c: any) =>
                                  ['table', 'chart', 'stat', 'timeline', 'comparison'].includes(
                                    c.type
                                  )
                                ) && (
                                  <button
                                    onClick={() => onSelectWorkspace(m.structured_response)}
                                    className="text-[11px] font-medium text-emerald-500 hover:underline"
                                  >
                                    Open visual view
                                  </button>
                                )}
                            </div>

                            {m.structured_response ? (
                              <ResponseBlock
                                structured={m.structured_response}
                                onSelectSource={(docId, chunkId, page) =>
                                  onOpenCitationPreview(docId, chunkId, page)
                                }
                                onOpenWorkspace={(sr) => onSelectWorkspace(sr)}
                                onMutateCommand={(cmd) =>
                                  onMutateWorkspace(cmd, m.structured_response)
                                }
                              />
                            ) : (
                              <div className="text-sm leading-relaxed whitespace-pre-wrap text-zinc-800 dark:text-zinc-200">
                                {m.content || (isStreaming ? 'Thinking...' : '')}
                              </div>
                            )}

                            {/* Clean Workplace Citations (Only Authorized Sources) */}
                            {m.citations && m.citations.length > 0 && (
                              <div className="pt-3 border-t border-zinc-100 dark:border-zinc-800/80">
                                <div className="text-[11px] text-zinc-400 mb-2">Sources</div>
                                <div className="flex flex-wrap gap-1.5">
                                  {m.citations.map((c: any, idx: number) => (
                                    <button
                                      key={idx}
                                      onClick={() =>
                                        onOpenCitationPreview(
                                          c.document_id,
                                          c.chunk_id,
                                          c.page_number
                                        )
                                      }
                                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-zinc-100 dark:bg-zinc-800/80 hover:bg-emerald-500/15 text-[11px] text-zinc-700 dark:text-zinc-300 transition"
                                    >
                                      <FileText className="w-3 h-3 text-emerald-500" />
                                      <span>{c.filename}</span>
                                      {c.page_number ? (
                                        <span className="text-zinc-400">p.{c.page_number}</span>
                                      ) : null}
                                    </button>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                    <div ref={chatEndRef} />
                  </div>
                )}
              </div>

              {/* Clean Employee Chat Input Bar */}
              <div className="p-4 border-t border-zinc-200/80 dark:border-zinc-800/80 bg-white/90 dark:bg-[#0d0f17]/90">
                <form
                  onSubmit={(e) => onSendChat(e)}
                  className="max-w-3xl mx-auto flex items-center gap-2"
                >
                  <input
                    type="text"
                    value={questionInput}
                    onChange={(e) => onQuestionChange(e.target.value)}
                    placeholder={`Ask ${assistantName} anything...`}
                    disabled={isStreaming}
                    className="flex-1 px-4 py-3 rounded-2xl bg-zinc-100 dark:bg-[#141824] border border-zinc-200 dark:border-zinc-800 text-sm focus:outline-none focus:border-emerald-500"
                  />
                  <button
                    type="submit"
                    disabled={isStreaming || !questionInput.trim()}
                    className="px-5 py-3 rounded-2xl bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-zinc-950 font-semibold text-sm flex items-center gap-1.5 transition"
                  >
                    <Send className="w-4 h-4" />
                    <span>Ask</span>
                  </button>
                </form>
              </div>
            </div>

            {/* Interactive Structured Response Canvas (when active) */}
            {activeWorkspace && (
              <div className="w-full lg:w-[46%] border-l border-zinc-200 dark:border-zinc-800 bg-white dark:bg-[#0d0f17] h-full overflow-hidden flex flex-col">
                <Workspace
                  workspace={activeWorkspace}
                  onClose={() => onSelectWorkspace(null)}
                  onMutate={(cmd) => onMutateWorkspace(cmd, activeWorkspace)}
                  onRestoreVersion={(snap) => onSelectWorkspace(snap)}
                  onSelectSource={(docId, chunkId, page) =>
                    onOpenCitationPreview(docId, chunkId, page)
                  }
                />
              </div>
            )}
          </div>
        )}
      </div>

      {/* Authorized Source Excerpt Preview Modal */}
      {previewDoc && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl max-w-2xl w-full max-h-[80vh] flex flex-col overflow-hidden shadow-2xl">
            <div className="p-4 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-emerald-500" />
                <span className="text-sm font-semibold">
                  {previewDoc.document?.filename || 'Source Preview'}
                </span>
              </div>
              <button
                onClick={onClosePreview}
                className="p-1.5 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="p-5 overflow-y-auto space-y-3 text-xs leading-relaxed">
              {(previewDoc.chunks || []).map((ch: any) => (
                <div
                  key={ch.id}
                  className="p-3.5 rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-200/70 dark:border-zinc-800/70"
                >
                  {ch.section_title && (
                    <div className="font-semibold text-emerald-600 dark:text-emerald-400 mb-1">
                      {ch.section_title} {ch.page_number ? `• Page ${ch.page_number}` : ''}
                    </div>
                  )}
                  <div className="whitespace-pre-wrap text-zinc-700 dark:text-zinc-300">
                    {ch.content}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
