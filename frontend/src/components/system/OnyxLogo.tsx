import React from 'react';

interface OnyxLogoProps {
  size?: 'sm' | 'md' | 'lg';
  animated?: boolean;
}

/**
 * Minimal abstract geometric AI / knowledge mark crafted in pure SVG.
 * Works cleanly in light mode, dark mode, and small icon sizes without external assets.
 */
export const OnyxLogo: React.FC<OnyxLogoProps> = ({ size = 'md', animated = false }) => {
  const dims =
    size === 'sm' ? 'w-7 h-7' : size === 'lg' ? 'w-11 h-11' : 'w-9 h-9';

  return (
    <div
      className={`${dims} rounded-xl bg-zinc-900 dark:bg-zinc-100 text-zinc-50 dark:text-zinc-950 flex items-center justify-center border border-zinc-800/80 dark:border-zinc-200/80 shadow-sm shrink-0 ${
        animated ? 'animate-onyx-logo' : ''
      }`}
      aria-hidden="true"
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        className="w-5 h-5"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <polygon points="12 2.5 20.5 7.5 20.5 16.5 12 21.5 3.5 16.5 3.5 7.5 12 2.5" />
        <polyline points="3.5 7.5 12 12.5 20.5 7.5" />
        <line x1="12" y1="12.5" x2="12" y2="21.5" />
        <circle cx="12" cy="12.5" r="1.6" fill="currentColor" stroke="none" />
      </svg>
    </div>
  );
};
