import React, { useState } from 'react';
import { Code2, Copy, Check } from 'lucide-react';

interface CodeBlockProps {
  id?: string;
  title?: string | null;
  data: {
    language?: string;
    code?: string;
    content?: string;
  };
}

/**
 * Displays code snippets safely as read-only text. Never executes code.
 */
export const CodeBlock: React.FC<CodeBlockProps> = ({ id, title, data }) => {
  const [copied, setCopied] = useState(false);
  const code = String(data?.code || data?.content || '');
  const language = String(data?.language || 'text');

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  return (
    <div
      data-component-id={id}
      className="rounded-xl border border-slate-800 bg-slate-950 text-slate-100 overflow-hidden shadow-sm"
    >
      <div className="flex items-center justify-between px-4 py-2 bg-slate-900 border-b border-slate-800 text-xs">
        <div className="flex items-center gap-2">
          <Code2 className="w-3.5 h-3.5 text-indigo-400" />
          <span className="font-mono uppercase text-slate-400">{language}</span>
          {title && <span className="text-slate-300 font-medium">— {title}</span>}
          {id && (
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
              {id}
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1 px-2 py-1 rounded hover:bg-slate-800 text-slate-300"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          <span>{copied ? 'Copied' : 'Copy Code'}</span>
        </button>
      </div>
      <pre className="p-4 text-xs font-mono overflow-x-auto leading-relaxed">
        <code>{code}</code>
      </pre>
    </div>
  );
};
