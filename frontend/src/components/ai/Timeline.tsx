import React from 'react';
import { Calendar, CheckCircle2, Clock, CircleDot } from 'lucide-react';

interface TimelineEvent {
  date: string;
  title: string;
  description?: string;
  status?: 'completed' | 'in_progress' | 'planned' | string;
}

interface TimelineProps {
  id?: string;
  title?: string | null;
  data: {
    title?: string;
    events?: TimelineEvent[];
  };
}

export const Timeline: React.FC<TimelineProps> = ({ id, title, data }) => {
  const events = Array.isArray(data?.events) ? data.events : [];
  const heading = data?.title || title || 'Chronological Timeline';

  return (
    <div
      data-component-id={id}
      className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/80 p-4 shadow-sm"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Calendar className="w-4 h-4 text-indigo-500" />
          <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-100">{heading}</h4>
        </div>
        {id && (
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500">
            {id}
          </span>
        )}
      </div>

      <div className="relative pl-6 space-y-4 before:content-[''] before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-indigo-500/30">
        {events.map((ev, idx) => {
          const st = (ev.status || 'planned').toLowerCase();
          return (
            <div key={idx} className="relative">
              <div className="absolute -left-6 top-1 w-5 h-5 rounded-full bg-white dark:bg-slate-900 flex items-center justify-center">
                {st === 'completed' ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                ) : st === 'in_progress' ? (
                  <Clock className="w-4 h-4 text-amber-500" />
                ) : (
                  <CircleDot className="w-4 h-4 text-indigo-500" />
                )}
              </div>
              <div className="p-3 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-800/40">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
                    {ev.date}
                  </span>
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                      st === 'completed'
                        ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
                        : st === 'in_progress'
                        ? 'bg-amber-500/15 text-amber-600 dark:text-amber-400'
                        : 'bg-indigo-500/15 text-indigo-600 dark:text-indigo-400'
                    }`}
                  >
                    {st.replace('_', ' ')}
                  </span>
                </div>
                <div className="text-sm font-semibold text-slate-900 dark:text-white mt-1">
                  {ev.title}
                </div>
                {ev.description && (
                  <div className="text-xs text-slate-600 dark:text-slate-300 mt-1">
                    {ev.description}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
