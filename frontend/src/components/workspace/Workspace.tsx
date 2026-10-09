import React, { useState } from 'react';
import {
  X,
  Undo2,
  Wand2,
  Maximize2,
  Minimize2,
  BarChart3,
  LineChart,
  Table as TableIcon,
  Percent,
  Filter,
  Trash2,
  History,
} from 'lucide-react';
import { StructuredResponse } from '../../types/structured';
import { ComponentRenderer } from './ComponentRenderer';
import { SourceCard } from '../ai/SourceCard';

interface WorkspaceProps {
  workspace: StructuredResponse;
  onClose: () => void;
  onMutate: (command: string) => Promise<void>;
  onRestoreVersion: (versionSnapshot: StructuredResponse) => void;
  onSelectSource?: (docId: string, chunkId?: string, page?: number) => void;
}

export const Workspace: React.FC<WorkspaceProps> = ({
  workspace,
  onClose,
  onMutate,
  onRestoreVersion,
  onSelectSource,
}) => {
  const [customCmd, setCustomCmd] = useState('');
  const [isMutating, setIsMutating] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);

  const historyList = Array.isArray(workspace.history_versions) ? workspace.history_versions : [];
  const components = Array.isArray(workspace.components) ? workspace.components : [];
  const statComponents = components.filter((c) => c.type === 'stat');
  const otherComponents = components.filter((c) => c.type !== 'stat');

  const triggerCommand = async (cmd: string) => {
    if (!cmd.trim() || isMutating) return;
    setIsMutating(true);
    try {
      await onMutate(cmd);
      setCustomCmd('');
    } finally {
      setIsMutating(false);
    }
  };

  const handleUndo = () => {
    if (historyList.length === 0) return;
    const prev = historyList[historyList.length - 1] as StructuredResponse;
    onRestoreVersion({
      ...prev,
      history_versions: historyList.slice(0, -1),
    });
  };

  return (
    <div
      className={`${
        fullscreen
          ? 'fixed inset-4 z-50 rounded-2xl shadow-2xl'
          : 'w-full lg:w-[48%] xl:w-[50%] shrink-0 rounded-2xl'
      } border border-indigo-500/30 bg-white dark:bg-slate-900 flex flex-col overflow-hidden transition-all`}
    >
      {/* Top Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 bg-slate-900 text-white border-b border-slate-800">
        <div className="flex items-center gap-2">
          <span className="px-2 py-0.5 rounded bg-indigo-600 text-[11px] font-bold uppercase tracking-wider">
            Workspace Canvas
          </span>
          <h3 className="text-sm font-semibold truncate max-w-[220px] sm:max-w-xs">
            {workspace.title}
          </h3>
          <span className="text-xs font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
            v{workspace.version || 1}
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          {/* Version History Pill Selector */}
          {historyList.length > 0 && (
            <div className="inline-flex items-center gap-1 bg-slate-800 px-2 py-1 rounded-lg text-xs">
              <History className="w-3.5 h-3.5 text-indigo-400" />
              {historyList.map((snap: any, idx: number) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() =>
                    onRestoreVersion({
                      ...(snap as StructuredResponse),
                      history_versions: historyList.slice(0, idx),
                    })
                  }
                  className="px-1.5 py-0.5 rounded hover:bg-slate-700 text-slate-300 font-mono text-[11px]"
                  title={`Revert to v${snap.version || idx + 1}`}
                >
                  v{snap.version || idx + 1}
                </button>
              ))}
              <span className="px-1.5 py-0.5 rounded bg-indigo-600 text-white font-mono text-[11px]">
                v{workspace.version}
              </span>
            </div>
          )}

          <button
            type="button"
            disabled={historyList.length === 0}
            onClick={handleUndo}
            title="Undo last workspace change"
            className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-200"
          >
            <Undo2 className="w-3.5 h-3.5" />
            <span>Undo</span>
          </button>

          <button
            type="button"
            onClick={() => setFullscreen(!fullscreen)}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300"
            title={fullscreen ? 'Exit full screen' : 'Expand full screen'}
          >
            {fullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>

          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-rose-600/80 text-slate-300 hover:text-white"
            title="Close Workspace"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Quick Transformation Bar */}
      <div className="px-4 py-2.5 bg-slate-50 dark:bg-slate-950/60 border-b border-slate-200 dark:border-slate-800 flex flex-wrap items-center gap-1.5">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mr-1">
          Transform:
        </span>
        <button
          type="button"
          onClick={() => triggerCommand('Make this a table')}
          className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:border-indigo-500 text-slate-700 dark:text-slate-200"
        >
          <TableIcon className="w-3 h-3 text-indigo-500" />
          <span>Make Table</span>
        </button>
        <button
          type="button"
          onClick={() => triggerCommand('Show this as a bar chart')}
          className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:border-indigo-500 text-slate-700 dark:text-slate-200"
        >
          <BarChart3 className="w-3 h-3 text-indigo-500" />
          <span>Bar Chart</span>
        </button>
        <button
          type="button"
          onClick={() => triggerCommand('Show this as a line chart')}
          className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:border-indigo-500 text-slate-700 dark:text-slate-200"
        >
          <LineChart className="w-3 h-3 text-indigo-500" />
          <span>Line Chart</span>
        </button>
        <button
          type="button"
          onClick={() => triggerCommand('Only show the top 5')}
          className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:border-indigo-500 text-slate-700 dark:text-slate-200"
        >
          <Filter className="w-3 h-3 text-indigo-500" />
          <span>Top 5</span>
        </button>
        <button
          type="button"
          onClick={() => triggerCommand('Add percentage change')}
          className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:border-indigo-500 text-slate-700 dark:text-slate-200"
        >
          <Percent className="w-3 h-3 text-indigo-500" />
          <span>+ % Change</span>
        </button>
        <button
          type="button"
          onClick={() => triggerCommand('Remove the chart')}
          className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:border-rose-500 text-slate-700 dark:text-slate-200"
        >
          <Trash2 className="w-3 h-3 text-rose-500" />
          <span>Remove Chart</span>
        </button>
      </div>

      {/* Main Scrollable Canvas Body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {statComponents.length > 0 && (
          <div
            className={`grid gap-3 ${
              statComponents.length >= 2 ? 'grid-cols-1 sm:grid-cols-2' : 'grid-cols-1'
            }`}
          >
            {statComponents.map((comp, idx) => (
              <ComponentRenderer
                key={comp.id || `ws_stat_${idx}`}
                component={comp}
                onSelectSource={onSelectSource}
                onMutateCommand={triggerCommand}
              />
            ))}
          </div>
        )}

        {otherComponents.map((comp, idx) => (
          <ComponentRenderer
            key={comp.id || `ws_comp_${idx}`}
            component={comp}
            onSelectSource={onSelectSource}
            onMutateCommand={triggerCommand}
          />
        ))}

        {workspace.sources && workspace.sources.length > 0 && (
          <SourceCard sources={workspace.sources} onSelectSource={onSelectSource} />
        )}
      </div>

      {/* Bottom Follow-up Command Input */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          triggerCommand(customCmd);
        }}
        className="p-3 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/80 flex items-center gap-2"
      >
        <Wand2 className="w-4 h-4 text-indigo-500 shrink-0" />
        <input
          type="text"
          value={customCmd}
          onChange={(e) => setCustomCmd(e.target.value)}
          placeholder='Follow-up command (e.g. "Change chart_01 to a bar chart", "Only show the top 3")'
          className="flex-1 text-xs px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-100 focus:outline-none focus:border-indigo-500"
        />
        <button
          type="submit"
          disabled={isMutating || !customCmd.trim()}
          className="px-3 py-2 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white"
        >
          {isMutating ? 'Updating...' : 'Apply'}
        </button>
      </form>
    </div>
  );
};
