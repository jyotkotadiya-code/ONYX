import React from 'react';
import { Check } from 'lucide-react';
import { ServiceStatus, ServiceStatusItem } from './ServiceStatus';

interface BootStatusProps {
  heading?: string;
  subheading?: string;
  services: ServiceStatusItem[];
  isReady?: boolean;
}

export const BootStatus: React.FC<BootStatusProps> = ({
  heading = 'Preparing your workspace',
  subheading = 'Initializing local AI...',
  services,
  isReady = false,
}) => {
  const completedCount = services.filter(
    (s) => s.state === 'success' || s.state === 'warning'
  ).length;
  const progressPct = Math.round((completedCount / Math.max(1, services.length)) * 100);

  return (
    <div className="w-full max-w-sm rounded-2xl border border-zinc-200/90 dark:border-zinc-800/90 bg-white dark:bg-zinc-900/90 p-6 shadow-sm animate-onyx-content">
      <div className="flex items-center justify-between mb-1">
        <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
          {isReady ? 'Workspace ready' : heading}
        </h2>
        {isReady ? (
          <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600 dark:text-emerald-400">
            <Check className="w-3.5 h-3.5 stroke-[2.5]" />
            <span>Ready</span>
          </span>
        ) : (
          <span className="text-[11px] font-mono text-zinc-400 dark:text-zinc-500">
            {completedCount}/{services.length}
          </span>
        )}
      </div>

      <p className="text-xs text-zinc-500 dark:text-zinc-400 mb-4">{subheading}</p>

      {/* Subtle Real Service Progress Bar */}
      <div className="h-1 w-full rounded-full bg-zinc-100 dark:bg-zinc-800 overflow-hidden mb-4">
        <div
          className="h-full bg-zinc-900 dark:bg-zinc-100 transition-all duration-300 ease-out"
          style={{ width: `${progressPct}%` }}
        />
      </div>

      {/* Live Service Checklist */}
      <div className="divide-y divide-zinc-100 dark:divide-zinc-800/70">
        {services.map((srv) => (
          <ServiceStatus key={srv.id} item={srv} />
        ))}
      </div>
    </div>
  );
};

export const SystemInitialization = BootStatus;
