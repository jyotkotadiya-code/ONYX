import React, { useState, useMemo } from 'react';
import {
  Table as TableIcon,
  ArrowUpDown,
  Search,
  Download,
  Copy,
  Check,
  ChevronLeft,
  ChevronRight,
  BarChart3,
} from 'lucide-react';

interface ColumnSpec {
  key: string;
  label: string;
}

interface DataTableProps {
  id?: string;
  title?: string | null;
  data: {
    title?: string;
    columns?: Array<ColumnSpec | string>;
    rows?: Array<Record<string, any> | any[]>;
  };
  onConvertToChart?: (componentId: string) => void;
}

export const DataTable: React.FC<DataTableProps> = ({ id, title, data, onConvertToChart }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortAsc, setSortAsc] = useState(true);
  const [page, setPage] = useState(1);
  const [copied, setCopied] = useState(false);
  const pageSize = 8;

  const columns: ColumnSpec[] = useMemo(() => {
    const rawCols = Array.isArray(data?.columns) ? data.columns : [];
    if (rawCols.length > 0) {
      return rawCols.map((c) =>
        typeof c === 'string'
          ? { key: c, label: c.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()) }
          : { key: String(c.key), label: String(c.label || c.key) }
      );
    }
    const firstRow = Array.isArray(data?.rows) && data.rows.length > 0 ? data.rows[0] : null;
    if (firstRow && typeof firstRow === 'object' && !Array.isArray(firstRow)) {
      return Object.keys(firstRow).map((k) => ({
        key: k,
        label: k.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()),
      }));
    }
    return [];
  }, [data]);

  const normalizedRows: Array<Record<string, any>> = useMemo(() => {
    const rawRows = Array.isArray(data?.rows) ? data.rows : [];
    return rawRows.map((r) => {
      if (Array.isArray(r)) {
        const obj: Record<string, any> = {};
        columns.forEach((col, i) => {
          obj[col.key] = r[i];
        });
        return obj;
      }
      return r || {};
    });
  }, [data, columns]);

  const filteredAndSorted = useMemo(() => {
    let list = [...normalizedRows];
    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      list = list.filter((row) =>
        columns.some((col) => String(row[col.key] ?? '').toLowerCase().includes(q))
      );
    }
    if (sortKey) {
      list.sort((a, b) => {
        const va = a[sortKey];
        const vb = b[sortKey];
        const na = typeof va === 'number' ? va : Number(String(va).replace(/[,₹$%]/g, ''));
        const nb = typeof vb === 'number' ? vb : Number(String(vb).replace(/[,₹$%]/g, ''));
        if (!Number.isNaN(na) && !Number.isNaN(nb)) {
          return sortAsc ? na - nb : nb - na;
        }
        return sortAsc
          ? String(va ?? '').localeCompare(String(vb ?? ''))
          : String(vb ?? '').localeCompare(String(va ?? ''));
      });
    }
    return list;
  }, [normalizedRows, columns, searchTerm, sortKey, sortAsc]);

  const totalPages = Math.max(1, Math.ceil(filteredAndSorted.length / pageSize));
  const paginatedRows = filteredAndSorted.slice((page - 1) * pageSize, page * pageSize);

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(key);
      setSortAsc(true);
    }
  };

  const toCsvString = () => {
    const header = columns.map((c) => `"${c.label.replace(/"/g, '""')}"`).join(',');
    const body = filteredAndSorted
      .map((row) =>
        columns
          .map((c) => `"${String(row[c.key] ?? '').replace(/"/g, '""')}"`)
          .join(',')
      )
      .join('\n');
    return `${header}\n${body}`;
  };

  const handleExportCsv = () => {
    const csv = toCsvString();
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${(data?.title || title || 'table_data').toLowerCase().replace(/\s+/g, '_')}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleCopyTable = () => {
    navigator.clipboard.writeText(toCsvString());
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  const formatCellValue = (val: any, colKey: string) => {
    if (val === null || val === undefined) return '—';
    if (typeof val === 'number') {
      const k = colKey.toLowerCase();
      if (k.includes('salary') || k.includes('revenue') || k.includes('sales') || k.includes('budget')) {
        return `₹${val.toLocaleString('en-IN')}`;
      }
      return val.toLocaleString('en-IN');
    }
    return String(val);
  };

  return (
    <div
      data-component-id={id}
      className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/80 shadow-sm overflow-hidden"
    >
      {/* Header & Controls */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 border-b border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-900">
        <div className="flex items-center gap-2">
          <TableIcon className="w-4 h-4 text-indigo-500" />
          <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-100">
            {data?.title || title || 'Structured Data Table'}
          </h4>
          <span className="text-xs text-slate-400">({filteredAndSorted.length} rows)</span>
          {id && (
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-200/70 dark:bg-slate-800 text-slate-500">
              {id}
            </span>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setPage(1);
              }}
              placeholder="Filter rows..."
              className="pl-7 pr-2.5 py-1 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500"
            />
          </div>

          {onConvertToChart && id && (
            <button
              type="button"
              onClick={() => onConvertToChart(id)}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-600 dark:text-indigo-300 transition-colors"
              title="Visualize this table as a chart"
            >
              <BarChart3 className="w-3.5 h-3.5" />
              <span>Chart</span>
            </button>
          )}

          <button
            type="button"
            onClick={handleCopyTable}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>

          <button
            type="button"
            onClick={handleExportCsv}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300"
          >
            <Download className="w-3.5 h-3.5" />
            <span>CSV</span>
          </button>
        </div>
      </div>

      {/* Table Body */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50/90 dark:bg-slate-800/50 text-slate-600 dark:text-slate-300">
              {columns.map((col) => (
                <th
                  key={col.key}
                  onClick={() => handleSort(col.key)}
                  className="py-2.5 px-3 font-semibold cursor-pointer select-none hover:text-indigo-600 dark:hover:text-indigo-400 whitespace-nowrap"
                >
                  <div className="inline-flex items-center gap-1">
                    <span>{col.label}</span>
                    <ArrowUpDown className="w-3 h-3 opacity-60" />
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
            {paginatedRows.length === 0 ? (
              <tr>
                <td colSpan={Math.max(1, columns.length)} className="py-6 text-center text-slate-400">
                  No matching records found.
                </td>
              </tr>
            ) : (
              paginatedRows.map((row, rIdx) => (
                <tr
                  key={rIdx}
                  className="hover:bg-indigo-50/30 dark:hover:bg-slate-800/40 transition-colors"
                >
                  {columns.map((col) => {
                    const rawVal = row[col.key];
                    const isNum = typeof rawVal === 'number';
                    return (
                      <td
                        key={col.key}
                        className={`py-2.5 px-3 ${
                          isNum
                            ? 'font-mono text-slate-900 dark:text-slate-100 font-medium'
                            : 'text-slate-700 dark:text-slate-200'
                        }`}
                      >
                        {formatCellValue(rawVal, col.key)}
                      </td>
                    );
                  })}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-4 py-2 border-t border-slate-200 dark:border-slate-800 bg-slate-50/40 dark:bg-slate-900 text-xs text-slate-500">
          <span>
            Page {page} of {totalPages}
          </span>
          <div className="flex items-center gap-1">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-800 disabled:opacity-40"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              type="button"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              className="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-800 disabled:opacity-40"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
