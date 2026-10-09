import React, { useState } from 'react';
import {
  Building2,
  Plus,
  ArrowRight,
  Users,
  FileText,
  Sparkles,
  ShieldCheck,
  Sun,
  Moon,
  LogOut,
  Search,
  CheckCircle2,
  Layers,
  Bot,
  Zap,
} from 'lucide-react';
import { OnyxLogo } from '../system/OnyxLogo';

interface WorkplaceItem {
  id: string;
  name: string;
  slug: string;
  logo?: string;
  description?: string;
  industry?: string;
  assistant_name?: string;
  welcome_message?: string;
  status: string;
  employee_count?: number;
  document_count?: number;
  is_current?: boolean;
}

interface AdminWorkplacePortalProps {
  user: any;
  workplaces: WorkplaceItem[];
  currentWorkplace: any;
  darkMode: boolean;
  onToggleDarkMode: () => void;
  onLogout: () => void;
  onSelectWorkplace: (workplaceId: string) => void;
  onCreateWorkplace: (payload: any) => Promise<void>;
  onEnterDashboard: () => void;
}

export const AdminWorkplacePortal: React.FC<AdminWorkplacePortalProps> = ({
  user,
  workplaces,
  currentWorkplace,
  darkMode,
  onToggleDarkMode,
  onLogout,
  onSelectWorkplace,
  onCreateWorkplace,
  onEnterDashboard,
}) => {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState('');

  // Form State for Create Workplace
  const [name, setName] = useState('');
  const [industry, setIndustry] = useState('');
  const [description, setDescription] = useState('');
  const [assistantName, setAssistantName] = useState('');
  const [welcomeMessage, setWelcomeMessage] = useState('Ask anything about your workplace knowledge.');

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setFormError('Workplace name is required.');
      return;
    }
    setFormError('');
    setIsSubmitting(true);
    try {
      await onCreateWorkplace({
        name: name.trim(),
        industry: industry.trim(),
        description: description.trim(),
        assistant_name: assistantName.trim() || `${name.trim()} AI`,
        welcome_message: welcomeMessage.trim(),
        switch_to_new: true,
      });
      setShowCreateModal(false);
      setName('');
      setIndustry('');
      setDescription('');
      setAssistantName('');
    } catch (err: any) {
      setFormError(err.message || 'Failed to create workplace.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const filteredWorkplaces = workplaces.filter(
    (w) =>
      w.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (w.industry && w.industry.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (w.description && w.description.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div className="min-h-screen bg-[#f8f9fa] dark:bg-[#0b0c0e] text-zinc-900 dark:text-zinc-100 flex flex-col font-sans transition-colors duration-300">
      {/* ─── Top Header ─── */}
      <header className="sticky top-0 z-30 border-b border-zinc-200/80 dark:border-zinc-800/80 bg-white/80 dark:bg-[#111317]/80 backdrop-blur-md px-6 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <OnyxLogo size="sm" />
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold tracking-tight text-sm">ONYX Workplace Control</span>
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-md bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 font-semibold border border-emerald-500/30">
                Admin Hub
              </span>
            </div>
            <p className="text-[11px] text-zinc-500 dark:text-zinc-400">
              Select or create an organization workspace
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {currentWorkplace && (
            <button
              onClick={onEnterDashboard}
              className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium shadow-md shadow-emerald-600/20 transition-all transform active:scale-95"
            >
              <Zap className="w-3.5 h-3.5" />
              <span>Launch {currentWorkplace.name} Dashboard</span>
            </button>
          )}

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
              {(user?.name || user?.username || 'A')[0]}
            </div>
            <div className="hidden sm:block text-left">
              <div className="text-xs font-semibold">{user?.name || user?.username}</div>
              <div className="text-[10px] text-zinc-500 dark:text-zinc-400">Administrator</div>
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

      {/* ─── Main Content ─── */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-10 flex flex-col gap-8">
        {/* Hero Banner */}
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-zinc-900 via-zinc-800 to-zinc-900 text-white p-8 border border-zinc-800 shadow-2xl">
          <div className="absolute top-0 right-0 -mt-10 -mr-10 w-80 h-80 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
          <div className="relative z-10 max-w-2xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-300 text-xs font-medium mb-3 border border-emerald-500/30">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Multi-Tenant Enterprise Knowledge Engine</span>
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl text-white">
              Workplaces & Organization Teams
            </h1>
            <p className="mt-2 text-sm text-zinc-300 leading-relaxed">
              Create and manage isolated company workspaces. Administer employee access, team departments, knowledge bases, and custom AI assistants from a centralized control plane.
            </p>

            <div className="mt-6 flex flex-wrap items-center gap-3">
              <button
                onClick={() => setShowCreateModal(true)}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-zinc-950 text-xs font-bold shadow-lg shadow-emerald-500/25 transition transform active:scale-95"
              >
                <Plus className="w-4 h-4" />
                <span>Create New Workspace</span>
              </button>
              {currentWorkplace && (
                <button
                  onClick={onEnterDashboard}
                  className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white/10 hover:bg-white/20 text-white text-xs font-semibold border border-white/10 backdrop-blur transition"
                >
                  <Layers className="w-4 h-4 text-emerald-400" />
                  <span>Go to Active Dashboard ({currentWorkplace.name})</span>
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Section Title & Search */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold tracking-tight">Existing Workplaces</h2>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Select a workplace to manage users, teams, documents, and settings.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="relative w-full sm:w-64">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search workplaces..."
                className="w-full pl-9 pr-4 py-2 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-xs font-medium focus:outline-none focus:ring-2 focus:ring-emerald-500/40"
              />
            </div>
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-3.5 py-2 rounded-xl bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-950 text-xs font-semibold hover:opacity-95 transition flex items-center gap-1.5 shrink-0"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>New Workspace</span>
            </button>
          </div>
        </div>

        {/* Workplaces Grid */}
        {filteredWorkplaces.length === 0 ? (
          <div className="p-12 rounded-3xl border border-dashed border-zinc-300 dark:border-zinc-800 bg-white/50 dark:bg-zinc-900/40 text-center flex flex-col items-center">
            <div className="w-12 h-12 rounded-2xl bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center text-zinc-400 mb-3">
              <Building2 className="w-6 h-6" />
            </div>
            <h3 className="font-semibold text-base">No Workplaces Found</h3>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 max-w-sm mt-1">
              {searchQuery
                ? `No workplace matching "${searchQuery}".`
                : 'No existing workspaces found. Click "Create New Workspace" to set up your first organization workplace.'}
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="mt-4 px-4 py-2 rounded-xl bg-emerald-600 text-white text-xs font-medium hover:bg-emerald-500 transition"
            >
              Create First Workspace
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {filteredWorkplaces.map((wp) => {
              const isSelected = wp.id === currentWorkplace?.id;
              return (
                <div
                  key={wp.id}
                  className={`group relative rounded-2xl p-6 border transition-all duration-200 flex flex-col justify-between ${
                    isSelected
                      ? 'bg-white dark:bg-[#15181e] border-emerald-500/60 shadow-xl shadow-emerald-500/5 ring-1 ring-emerald-500/30'
                      : 'bg-white dark:bg-[#111317] border-zinc-200 dark:border-zinc-800/80 hover:border-zinc-300 dark:hover:border-zinc-700 hover:shadow-md'
                  }`}
                >
                  <div>
                    {/* Badge & Header */}
                    <div className="flex items-center justify-between mb-4">
                      <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-500 flex items-center justify-center font-bold text-base">
                        {wp.logo ? (
                          <img src={wp.logo} alt={wp.name} className="w-6 h-6 object-contain" />
                        ) : (
                          wp.name[0]?.toUpperCase()
                        )}
                      </div>

                      {isSelected ? (
                        <span className="inline-flex items-center gap-1 text-[11px] px-2.5 py-1 rounded-full font-medium bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30">
                          <CheckCircle2 className="w-3 h-3" />
                          Active Workspace
                        </span>
                      ) : (
                        <span className="text-[11px] px-2 py-0.5 rounded font-mono uppercase bg-zinc-100 dark:bg-zinc-800 text-zinc-500">
                          {wp.status}
                        </span>
                      )}
                    </div>

                    {/* Workplace Title & Info */}
                    <h3 className="font-bold text-base tracking-tight group-hover:text-emerald-500 transition-colors">
                      {wp.name}
                    </h3>
                    {wp.industry && (
                      <span className="inline-block text-[11px] text-zinc-500 dark:text-zinc-400 font-medium mt-0.5">
                        {wp.industry}
                      </span>
                    )}

                    <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-2 line-clamp-2 leading-relaxed">
                      {wp.description || wp.welcome_message || 'Enterprise workplace for team collaboration and knowledge AI.'}
                    </p>

                    {/* AI Assistant Badge */}
                    <div className="mt-4 pt-3 border-t border-zinc-100 dark:border-zinc-800/60 flex items-center gap-2 text-xs text-zinc-500 dark:text-zinc-400">
                      <Bot className="w-3.5 h-3.5 text-emerald-500" />
                      <span>Assistant: <strong className="text-zinc-700 dark:text-zinc-200">{wp.assistant_name || `${wp.name} AI`}</strong></span>
                    </div>
                  </div>

                  {/* Metrics & Action Button */}
                  <div className="mt-6 pt-4 border-t border-zinc-100 dark:border-zinc-800/60 flex items-center justify-between">
                    <div className="flex items-center gap-3 text-xs text-zinc-500 dark:text-zinc-400">
                      <span className="flex items-center gap-1" title="Employees">
                        <Users className="w-3.5 h-3.5 text-zinc-400" />
                        <span>{wp.employee_count ?? 1}</span>
                      </span>
                      <span className="flex items-center gap-1" title="Documents">
                        <FileText className="w-3.5 h-3.5 text-zinc-400" />
                        <span>{wp.document_count ?? 0}</span>
                      </span>
                    </div>

                    {isSelected ? (
                      <button
                        onClick={onEnterDashboard}
                        className="px-3.5 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1.5 transition shadow-sm"
                      >
                        <span>Open Dashboard</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    ) : (
                      <button
                        onClick={() => onSelectWorkplace(wp.id)}
                        className="px-3 py-1.5 rounded-xl bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-800 dark:text-zinc-200 text-xs font-medium flex items-center gap-1 transition"
                      >
                        <span>Select Workspace</span>
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>

      {/* ─── Create Workspace Modal ─── */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-zinc-950/60 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-lg bg-white dark:bg-[#121418] border border-zinc-200 dark:border-zinc-800 rounded-3xl p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-zinc-100 dark:border-zinc-800">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-emerald-500/10 text-emerald-500 border border-emerald-500/30 flex items-center justify-center">
                  <Building2 className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-base tracking-tight">Create New Workspace</h3>
                  <p className="text-xs text-zinc-500 dark:text-zinc-400">
                    Set up an isolated company or team workspace
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowCreateModal(false)}
                className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition"
              >
                ✕
              </button>
            </div>

            {formError && (
              <div className="mt-4 p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-500 text-xs font-medium">
                {formError}
              </div>
            )}

            <form onSubmit={handleFormSubmit} className="mt-5 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300 mb-1">
                  Workplace Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Acme Health, FinTech Labs, Engineering Team"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-xs font-medium focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300 mb-1">
                    Industry / Domain
                  </label>
                  <input
                    type="text"
                    value={industry}
                    onChange={(e) => setIndustry(e.target.value)}
                    placeholder="e.g. Technology, Healthcare, Finance"
                    className="w-full px-3.5 py-2.5 rounded-xl bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-xs font-medium focus:outline-none focus:border-emerald-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300 mb-1">
                    AI Assistant Name
                  </label>
                  <input
                    type="text"
                    value={assistantName}
                    onChange={(e) => setAssistantName(e.target.value)}
                    placeholder="e.g. Acme AI, Onyx Assistant"
                    className="w-full px-3.5 py-2.5 rounded-xl bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-xs font-medium focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300 mb-1">
                  Description
                </label>
                <textarea
                  rows={2}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Brief summary of workspace scope or organization division..."
                  className="w-full px-3.5 py-2 rounded-xl bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-xs font-medium focus:outline-none focus:border-emerald-500 resize-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300 mb-1">
                  Employee Welcome Greeting
                </label>
                <input
                  type="text"
                  value={welcomeMessage}
                  onChange={(e) => setWelcomeMessage(e.target.value)}
                  placeholder="e.g. Welcome to Acme AI Knowledge Hub."
                  className="w-full px-3.5 py-2.5 rounded-xl bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-xs font-medium focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="pt-4 border-t border-zinc-100 dark:border-zinc-800 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 rounded-xl bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300 text-xs font-medium hover:bg-zinc-200 dark:hover:bg-zinc-700 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-md shadow-emerald-600/20 transition disabled:opacity-50"
                >
                  {isSubmitting ? 'Creating...' : 'Create & Enter Workspace'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
