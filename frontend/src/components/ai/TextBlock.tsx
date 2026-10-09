import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';

interface TextBlockProps {
  id?: string;
  title?: string | null;
  data: {
    markdown?: string;
    content?: string;
    text?: string;
  };
}

/**
 * Safely renders Markdown-formatted text without using dangerouslySetInnerHTML
 * or executing any embedded HTML/JS.
 */
export const TextBlock: React.FC<TextBlockProps> = ({ id, title, data }) => {
  const [copied, setCopied] = useState(false);
  const rawText = String(data?.markdown || data?.content || data?.text || '');

  const handleCopy = () => {
    navigator.clipboard.writeText(rawText);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  const renderInline = (line: string) => {
    const parts = line.split(/(\*\*.*?\*\*|`.*?`)/g);
    return parts.map((part, idx) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return (
          <strong key={idx} className="font-semibold text-slate-900 dark:text-white">
            {part.slice(2, -2)}
          </strong>
        );
      }
      if (part.startsWith('`') && part.endsWith('`')) {
        return (
          <code
            key={idx}
            className="px-1.5 py-0.5 rounded bg-slate-200/80 dark:bg-slate-800 text-indigo-600 dark:text-indigo-300 font-mono text-xs"
          >
            {part.slice(1, -1)}
          </code>
        );
      }
      return <React.Fragment key={idx}>{part}</React.Fragment>;
    });
  };

  const lines = rawText.split('\n');

  return (
    <div
      data-component-id={id}
      className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/70 p-4 shadow-sm transition-all"
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {title && (
            <h4 className="text-xs font-semibold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
              {title}
            </h4>
          )}
          {id && (
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500">
              {id}
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={handleCopy}
          title="Copy text"
          className="text-xs flex items-center gap-1 px-2 py-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
          <span>{copied ? 'Copied' : 'Copy'}</span>
        </button>
      </div>

      <div className="space-y-1.5 text-sm leading-relaxed text-slate-700 dark:text-slate-200">
        {lines.map((line, idx) => {
          const trimmed = line.trim();
          if (!trimmed) return <div key={idx} className="h-1.5" />;
          if (trimmed.startsWith('### ')) {
            return (
              <h3 key={idx} className="text-sm font-bold text-slate-900 dark:text-white pt-1">
                {renderInline(trimmed.slice(4))}
              </h3>
            );
          }
          if (trimmed.startsWith('## ')) {
            return (
              <h2 key={idx} className="text-base font-bold text-slate-900 dark:text-white pt-1">
                {renderInline(trimmed.slice(3))}
              </h2>
            );
          }
          if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
            return (
              <div key={idx} className="flex items-start gap-2 pl-2">
                <span className="text-indigo-500 mt-1">•</span>
                <span>{renderInline(trimmed.slice(2))}</span>
              </div>
            );
          }
          return <p key={idx}>{renderInline(line)}</p>;
        })}
      </div>
    </div>
  );
};
