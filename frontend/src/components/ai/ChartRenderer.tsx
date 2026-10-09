import React, { useState, useRef } from 'react';
import {
  BarChart3,
  LineChart,
  PieChart,
  Download,
  Table as TableIcon,
  Maximize2,
  Minimize2,
} from 'lucide-react';

type SupportedChartType = 'bar' | 'line' | 'pie' | 'area' | 'scatter';

interface ChartRendererProps {
  id?: string;
  title?: string | null;
  data: {
    chart_type?: SupportedChartType | string;
    title?: string;
    x_axis?: { key: string; label?: string } | string;
    y_axis?: { key: string; label?: string } | string;
    series?: Array<{ key: string; label?: string }>;
    data?: Array<Record<string, any>>;
  };
}

const PALETTE = [
  '#6366f1', // indigo-500
  '#10b981', // emerald-500
  '#f59e0b', // amber-500
  '#ec4899', // pink-500
  '#06b6d4', // cyan-500
  '#8b5cf6', // violet-500
  '#f43f5e', // rose-500
];

export const ChartRenderer: React.FC<ChartRendererProps> = ({ id, title, data }) => {
  const initialType = (data?.chart_type || 'bar').toLowerCase() as SupportedChartType;
  const [chartType, setChartType] = useState<SupportedChartType>(
    ['bar', 'line', 'pie', 'area', 'scatter'].includes(initialType) ? initialType : 'bar'
  );
  const [showRawData, setShowRawData] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);

  // Sync if parent mutates chart_type (e.g. via follow-up command "Change component_01 to a bar chart")
  React.useEffect(() => {
    const incoming = (data?.chart_type || 'bar').toLowerCase() as SupportedChartType;
    if (['bar', 'line', 'pie', 'area', 'scatter'].includes(incoming)) {
      setChartType(incoming);
    }
  }, [data?.chart_type]);

  const rows = Array.isArray(data?.data) ? data.data : [];
  const xKey =
    typeof data?.x_axis === 'string'
      ? data.x_axis
      : data?.x_axis?.key || (rows[0] ? Object.keys(rows[0])[0] : 'label');
  const yKey =
    typeof data?.y_axis === 'string'
      ? data.y_axis
      : data?.y_axis?.key ||
        data?.series?.[0]?.key ||
        (rows[0] ? Object.keys(rows[0])[1] || Object.keys(rows[0])[0] : 'value');

  const xLabel =
    typeof data?.x_axis === 'object' && data?.x_axis?.label ? data.x_axis.label : xKey;
  const yLabel =
    typeof data?.y_axis === 'object' && data?.y_axis?.label ? data.y_axis.label : yKey;

  const points = rows.map((r, i) => {
    const rawY = r[yKey];
    const numY =
      typeof rawY === 'number'
        ? rawY
        : Number(String(rawY ?? 0).replace(/[,₹$%\s]/g, '')) || 0;
    return {
      index: i,
      label: String(r[xKey] ?? `Item ${i + 1}`),
      value: numY,
      raw: r,
    };
  });

  const maxVal = Math.max(1, ...points.map((p) => p.value));
  const minVal = Math.min(0, ...points.map((p) => p.value));
  const valRange = Math.max(1, maxVal - minVal);

  const formatNum = (n: number) => {
    const yLower = yKey.toLowerCase();
    const isCurrency =
      yLower.includes('revenue') ||
      yLower.includes('sales') ||
      yLower.includes('salary') ||
      yLower.includes('budget');
    if (Math.abs(n) >= 100000) {
      return `${isCurrency ? '₹' : ''}${(n / 1000).toFixed(0)}k`;
    }
    return `${isCurrency ? '₹' : ''}${n.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
  };

  const handleDownloadCsv = () => {
    if (!rows.length) return;
    const keys = Object.keys(rows[0]);
    const csv = [
      keys.join(','),
      ...rows.map((r) => keys.map((k) => `"${String(r[k] ?? '').replace(/"/g, '""')}"`).join(',')),
    ].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${(data?.title || title || 'chart_data').toLowerCase().replace(/\s+/g, '_')}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadSvg = () => {
    if (!svgRef.current) return;
    const serializer = new XMLSerializer();
    const svgString = serializer.serializeToString(svgRef.current);
    const blob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${(data?.title || title || 'chart').toLowerCase().replace(/\s+/g, '_')}.svg`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadPng = () => {
    if (!svgRef.current) return;
    const serializer = new XMLSerializer();
    const svgString = serializer.serializeToString(svgRef.current);
    const svgBlob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(svgBlob);
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = 1200;
      canvas.height = 600;
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.fillStyle = '#0f172a';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        const pngUrl = canvas.toDataURL('image/png');
        const a = document.createElement('a');
        a.href = pngUrl;
        a.download = `${(data?.title || title || 'chart').toLowerCase().replace(/\s+/g, '_')}.png`;
        a.click();
      }
      URL.revokeObjectURL(url);
    };
    img.src = url;
  };

  // SVG Layout Constants
  const width = 680;
  const height = expanded ? 380 : 270;
  const padLeft = 68;
  const padRight = 28;
  const padTop = 26;
  const padBottom = 54;
  const plotW = width - padLeft - padRight;
  const plotH = height - padTop - padBottom;

  const renderCartesian = () => {
    if (points.length === 0) {
      return (
        <text x={width / 2} y={height / 2} textAnchor="middle" className="fill-slate-400 text-xs">
          No numeric series available to plot
        </text>
      );
    }

    const stepX = points.length > 1 ? plotW / (points.length - 1) : plotW / 2;
    const barSlot = plotW / Math.max(1, points.length);
    const barW = Math.min(48, Math.max(14, barSlot * 0.62));

    const getX = (idx: number) =>
      chartType === 'bar'
        ? padLeft + idx * barSlot + barSlot / 2
        : points.length > 1
        ? padLeft + idx * stepX
        : padLeft + plotW / 2;

    const getY = (val: number) => padTop + plotH - ((val - minVal) / valRange) * plotH;

    const lineCoords = points.map((p, idx) => `${getX(idx)},${getY(p.value)}`).join(' ');
    const areaCoords = `${getX(0)},${padTop + plotH} ${lineCoords} ${getX(
      points.length - 1
    )},${padTop + plotH}`;

    const yTicks = [0, 0.25, 0.5, 0.75, 1].map((t) => minVal + t * valRange);

    return (
      <>
        {/* Horizontal Grid Lines & Y-Axis Labels */}
        {yTicks.map((tv, i) => {
          const yPos = getY(tv);
          return (
            <g key={i}>
              <line
                x1={padLeft}
                y1={yPos}
                x2={width - padRight}
                y2={yPos}
                stroke="currentColor"
                strokeDasharray="3 3"
                className="text-slate-200 dark:text-slate-800"
              />
              <text
                x={padLeft - 8}
                y={yPos + 4}
                textAnchor="end"
                className="fill-slate-400 text-[10px] font-mono"
              >
                {formatNum(tv)}
              </text>
            </g>
          );
        })}

        {/* Area Fill */}
        {(chartType === 'area' || chartType === 'line') && points.length > 1 && (
          <polygon
            points={areaCoords}
            fill="url(#chartAreaGrad)"
            opacity={chartType === 'area' ? 0.45 : 0.15}
          />
        )}

        {/* Line Path */}
        {(chartType === 'line' || chartType === 'area') && points.length > 1 && (
          <polyline
            fill="none"
            stroke="#6366f1"
            strokeWidth={3}
            strokeLinecap="round"
            strokeLinejoin="round"
            points={lineCoords}
          />
        )}

        {/* Bars or Points */}
        {points.map((p, idx) => {
          const cx = getX(idx);
          const cy = getY(p.value);
          const isHover = hoveredIdx === idx;
          const color = PALETTE[idx % PALETTE.length];

          return (
            <g
              key={idx}
              onMouseEnter={() => setHoveredIdx(idx)}
              onMouseLeave={() => setHoveredIdx(null)}
              className="cursor-pointer"
            >
              {chartType === 'bar' ? (
                <rect
                  x={cx - barW / 2}
                  y={cy}
                  width={barW}
                  height={Math.max(2, padTop + plotH - cy)}
                  rx={5}
                  fill={color}
                  opacity={isHover ? 1 : 0.88}
                />
              ) : (
                <circle
                  cx={cx}
                  cy={cy}
                  r={isHover ? 6.5 : 4.5}
                  fill={chartType === 'scatter' ? color : '#6366f1'}
                  stroke="#ffffff"
                  strokeWidth={2}
                />
              )}

              {/* Value label above bar/point */}
              <text
                x={cx}
                y={Math.max(14, cy - 8)}
                textAnchor="middle"
                className={`text-[10px] font-mono ${
                  isHover
                    ? 'fill-indigo-600 dark:fill-indigo-300 font-bold'
                    : 'fill-slate-500 dark:fill-slate-400'
                }`}
              >
                {formatNum(p.value)}
              </text>

              {/* X-axis category label */}
              <text
                x={cx}
                y={padTop + plotH + 18}
                textAnchor="middle"
                className="fill-slate-600 dark:fill-slate-300 text-[10px] font-medium"
              >
                {p.label.length > 12 ? `${p.label.slice(0, 11)}…` : p.label}
              </text>
            </g>
          );
        })}
      </>
    );
  };

  const renderPie = () => {
    const total = points.reduce((acc, p) => acc + Math.max(0, p.value), 0) || 1;
    const cx = width / 2 - 90;
    const cy = height / 2;
    const r = Math.min(plotW, plotH) * 0.42;
    let startAngle = -Math.PI / 2;

    return (
      <g>
        {points.map((p, idx) => {
          const sliceVal = Math.max(0, p.value);
          const angle = (sliceVal / total) * Math.PI * 2;
          const endAngle = startAngle + angle;
          const x1 = cx + r * Math.cos(startAngle);
          const y1 = cy + r * Math.sin(startAngle);
          const x2 = cx + r * Math.cos(endAngle);
          const y2 = cy + r * Math.sin(endAngle);
          const largeArc = angle > Math.PI ? 1 : 0;
          const pathData =
            points.length === 1
              ? `M ${cx - r} ${cy} A ${r} ${r} 0 1 0 ${cx + r} ${cy} A ${r} ${r} 0 1 0 ${cx - r} ${cy}`
              : `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2} Z`;
          startAngle = endAngle;
          const color = PALETTE[idx % PALETTE.length];
          const pct = ((sliceVal / total) * 100).toFixed(1);

          return (
            <g key={idx}>
              <path
                d={pathData}
                fill={color}
                stroke="#0f172a"
                strokeWidth={1.5}
                opacity={hoveredIdx === idx ? 1 : 0.9}
                onMouseEnter={() => setHoveredIdx(idx)}
                onMouseLeave={() => setHoveredIdx(null)}
              />
              {/* Legend Entry */}
              <g transform={`translate(${cx + r + 36}, ${36 + idx * 24})`}>
                <rect width={12} height={12} rx={3} fill={color} />
                <text x={18} y={10} className="fill-slate-700 dark:fill-slate-200 text-xs font-medium">
                  {p.label}: {formatNum(p.value)} ({pct}%)
                </text>
              </g>
            </g>
          );
        })}
      </g>
    );
  };

  return (
    <div
      data-component-id={id}
      className={`rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/80 shadow-sm overflow-hidden transition-all ${
        expanded ? 'col-span-full' : ''
      }`}
    >
      {/* Header & Interactive Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 border-b border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-900">
        <div className="flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-indigo-500" />
          <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-100">
            {data?.title || title || 'Data Visualization'}
          </h4>
          {id && (
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-200/70 dark:bg-slate-800 text-slate-500">
              {id}
            </span>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          {/* Chart Type Switcher */}
          <div className="inline-flex rounded-lg border border-slate-200 dark:border-slate-700 p-0.5 bg-white dark:bg-slate-800 text-xs">
            {(['bar', 'line', 'area', 'pie', 'scatter'] as SupportedChartType[]).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setChartType(t)}
                className={`px-2 py-0.5 rounded-md capitalize font-medium transition-colors ${
                  chartType === t
                    ? 'bg-indigo-600 text-white'
                    : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'
                }`}
              >
                {t}
              </button>
            ))}
          </div>

          <button
            type="button"
            onClick={() => setShowRawData(!showRawData)}
            title="View underlying data"
            className={`inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs border transition-colors ${
              showRawData
                ? 'border-indigo-500 bg-indigo-500/10 text-indigo-600 dark:text-indigo-300'
                : 'border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
            }`}
          >
            <TableIcon className="w-3.5 h-3.5" />
            <span>Data</span>
          </button>

          <button
            type="button"
            onClick={handleDownloadPng}
            title="Download chart as PNG"
            className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <Download className="w-3.5 h-3.5" />
            <span>PNG</span>
          </button>

          <button
            type="button"
            onClick={handleDownloadSvg}
            title="Download chart as SVG"
            className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <Download className="w-3.5 h-3.5" />
            <span>SVG</span>
          </button>

          <button
            type="button"
            onClick={handleDownloadCsv}
            title="Download underlying data as CSV"
            className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <Download className="w-3.5 h-3.5" />
            <span>CSV</span>
          </button>

          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            title={expanded ? 'Collapse chart' : 'Expand chart'}
            className="p-1 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            {expanded ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* SVG Canvas */}
      <div className="p-4">
        <svg
          ref={svgRef}
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto overflow-visible select-none"
        >
          <defs>
            <linearGradient id="chartAreaGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#6366f1" stopOpacity="0.6" />
              <stop offset="100%" stopColor="#6366f1" stopOpacity="0.0" />
            </linearGradient>
          </defs>
          {chartType === 'pie' ? renderPie() : renderCartesian()}
        </svg>

        <div className="flex items-center justify-between text-[11px] text-slate-400 px-2 pt-1">
          <span>
            X-Axis: <strong className="text-slate-600 dark:text-slate-300">{xLabel}</strong> • Y-Axis:{' '}
            <strong className="text-slate-600 dark:text-slate-300">{yLabel}</strong>
          </span>
          <span>100% Grounded Local Render</span>
        </div>
      </div>

      {/* Collapsible Raw Data View */}
      {showRawData && rows.length > 0 && (
        <div className="border-t border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/50 p-3 overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-500">
                {Object.keys(rows[0]).map((k) => (
                  <th key={k} className="py-1.5 px-2 font-semibold">
                    {k}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
              {rows.map((r, idx) => (
                <tr key={idx}>
                  {Object.keys(rows[0]).map((k) => (
                    <td key={k} className="py-1.5 px-2 font-mono text-slate-700 dark:text-slate-200">
                      {typeof r[k] === 'number' ? r[k].toLocaleString('en-IN') : String(r[k] ?? '')}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
