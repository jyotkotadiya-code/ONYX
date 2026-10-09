import React from 'react';

interface LoadingSkeletonProps {
  variant?: 'documents' | 'collections' | 'analytics' | 'chats' | 'workspace';
  count?: number;
}

/**
 * Progressive skeleton placeholders for Level 2 data loading (documents, collections, analytics, chats).
 */
export const LoadingSkeleton: React.FC<LoadingSkeletonProps> = ({
  variant = 'documents',
  count = 4,
}) => {
  if (variant === 'analytics') {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4" aria-busy="true">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="p-5 rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/60 space-y-3"
          >
            <div className="h-3 w-24 rounded bg-zinc-200 dark:bg-zinc-800 animate-pulse" />
            <div className="h-7 w-16 rounded bg-zinc-200 dark:bg-zinc-800 animate-pulse" />
            <div className="h-2.5 w-20 rounded bg-zinc-100 dark:bg-zinc-800/70 animate-pulse" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-3" aria-busy="true">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/60 space-y-2.5"
        >
          <div className="h-3.5 w-2/5 rounded bg-zinc-200 dark:bg-zinc-800 animate-pulse" />
          <div className="h-2.5 w-3/4 rounded bg-zinc-100 dark:bg-zinc-800/70 animate-pulse" />
        </div>
      ))}
    </div>
  );
};
