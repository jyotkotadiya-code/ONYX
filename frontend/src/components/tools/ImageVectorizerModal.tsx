import React, { useState } from 'react';
import {
  X,
  Sparkles,
  Download,
  Copy,
  Check,
  Layers,
  FileImage,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';

interface ImageVectorizerModalProps {
  isOpen: boolean;
  onClose: () => void;
  token?: string;
  initialDocId?: string;
  initialFilename?: string;
}

export const ImageVectorizerModal: React.FC<ImageVectorizerModalProps> = ({
  isOpen,
  onClose,
  token,
  initialDocId,
  initialFilename,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewSrc, setPreviewSrc] = useState<string | null>(null);
  const [colormode, setColormode] = useState<'color' | 'binary'>('color');
  const [curveMode, setCurveMode] = useState<'spline' | 'polygon'>('spline');
  const [filterSpeckle, setFilterSpeckle] = useState<number>(4);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [result, setResult] = useState<any | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setPreviewSrc(URL.createObjectURL(file));
      setResult(null);
      setErrorMsg(null);
    }
  };

  const handleVectorize = async () => {
    setIsProcessing(true);
    setErrorMsg(null);
    try {
      let resp: Response;
      const headers: Record<string, string> = {};
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      if (initialDocId && !selectedFile) {
        // Vectorize existing document
        resp = await fetch(
          `/api/documents/${initialDocId}/vectorize?colormode=${colormode}`,
          {
            method: 'POST',
            headers,
          }
        );
      } else if (selectedFile) {
        // Vectorize uploaded file
        const formData = new FormData();
        formData.append('file', selectedFile);
        formData.append('colormode', colormode);
        formData.append('mode', curveMode);
        formData.append('filter_speckle', filterSpeckle.toString());

        resp = await fetch('/api/tools/vectorize-image', {
          method: 'POST',
          headers,
          body: formData,
        });
      } else {
        throw new Error('Please select an image file to vectorize.');
      }

      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(errData.detail || 'Vectorization failed.');
      }

      const data = await resp.json();
      setResult(data);
    } catch (err: any) {
      setErrorMsg(err.message || 'An unexpected error occurred during vectorization.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleCopySvg = () => {
    if (result?.svg_markup) {
      navigator.clipboard.writeText(result.svg_markup);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-950">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-500 border border-indigo-500/20">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
                Raster-to-Vector Tracing Engine (SVG)
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                  Local VTracer
                </span>
              </h3>
              <p className="text-xs text-zinc-500 dark:text-zinc-400">
                Convert PNG/JPG bitmaps into genuine mathematical vector geometry with path nodes.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          {errorMsg && (
            <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Controls Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 rounded-xl bg-zinc-100/60 dark:bg-zinc-950/60 border border-zinc-200 dark:border-zinc-800">
            <div>
              <label className="text-[11px] font-bold uppercase tracking-wider text-zinc-400 block mb-1.5">
                Source Image
              </label>
              {initialFilename && !selectedFile ? (
                <div className="text-xs font-medium text-indigo-400 truncate py-1.5 px-3 rounded-lg bg-zinc-900 border border-zinc-800">
                  📄 {initialFilename}
                </div>
              ) : (
                <label className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 cursor-pointer text-xs hover:border-indigo-500 transition">
                  <FileImage className="w-4 h-4 text-zinc-400" />
                  <span className="truncate">{selectedFile ? selectedFile.name : 'Choose PNG/JPG...'}</span>
                  <input
                    type="file"
                    accept=".png,.jpg,.jpeg,.webp,.bmp"
                    onChange={handleFileChange}
                    className="hidden"
                  />
                </label>
              )}
            </div>

            <div>
              <label className="text-[11px] font-bold uppercase tracking-wider text-zinc-400 block mb-1.5">
                Color Mode
              </label>
              <div className="grid grid-cols-2 gap-1.5">
                <button
                  type="button"
                  onClick={() => setColormode('color')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition ${
                    colormode === 'color'
                      ? 'bg-indigo-600 text-white border-indigo-500'
                      : 'bg-zinc-200 dark:bg-zinc-900 border-zinc-300 dark:border-zinc-800 text-zinc-400'
                  }`}
                >
                  Full Color
                </button>
                <button
                  type="button"
                  onClick={() => setColormode('binary')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition ${
                    colormode === 'binary'
                      ? 'bg-indigo-600 text-white border-indigo-500'
                      : 'bg-zinc-200 dark:bg-zinc-900 border-zinc-300 dark:border-zinc-800 text-zinc-400'
                  }`}
                >
                  Black & White
                </button>
              </div>
            </div>

            <div>
              <label className="text-[11px] font-bold uppercase tracking-wider text-zinc-400 block mb-1.5">
                Curve Geometry
              </label>
              <div className="grid grid-cols-2 gap-1.5">
                <button
                  type="button"
                  onClick={() => setCurveMode('spline')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition ${
                    curveMode === 'spline'
                      ? 'bg-indigo-600 text-white border-indigo-500'
                      : 'bg-zinc-200 dark:bg-zinc-900 border-zinc-300 dark:border-zinc-800 text-zinc-400'
                  }`}
                >
                  Smooth Splines
                </button>
                <button
                  type="button"
                  onClick={() => setCurveMode('polygon')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition ${
                    curveMode === 'polygon'
                      ? 'bg-indigo-600 text-white border-indigo-500'
                      : 'bg-zinc-200 dark:bg-zinc-900 border-zinc-300 dark:border-zinc-800 text-zinc-400'
                  }`}
                >
                  Polygon Facets
                </button>
              </div>
            </div>
          </div>

          {/* Action Button */}
          <div className="flex justify-end">
            <button
              onClick={handleVectorize}
              disabled={isProcessing || (!selectedFile && !initialDocId)}
              className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold flex items-center gap-2 shadow-lg shadow-indigo-600/20 disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              {isProcessing ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Tracing Vector Geometry...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Vectorize to SVG</span>
                </>
              )}
            </button>
          </div>

          {/* Results Comparison View */}
          {result && (
            <div className="space-y-4 pt-2 border-t border-zinc-200 dark:border-zinc-800">
              {/* Metrics Badge Strip */}
              <div className="flex flex-wrap items-center gap-3">
                <div className="px-3 py-1.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-xs">
                  <span className="text-zinc-400 font-mono">Vector Paths: </span>
                  <span className="font-bold text-emerald-400 font-mono">
                    {result.path_count} paths
                  </span>
                </div>
                <div className="px-3 py-1.5 rounded-xl bg-blue-500/10 border border-blue-500/20 text-xs">
                  <span className="text-zinc-400 font-mono">File Size: </span>
                  <span className="font-bold text-blue-400 font-mono">
                    {(result.file_size_bytes / 1024).toFixed(1)} KB
                  </span>
                </div>
                <div className="px-3 py-1.5 rounded-xl bg-purple-500/10 border border-purple-500/20 text-xs">
                  <span className="text-zinc-400 font-mono">Processing: </span>
                  <span className="font-bold text-purple-400 font-mono">
                    {result.duration_ms} ms
                  </span>
                </div>

                <div className="ml-auto flex items-center gap-2">
                  <button
                    onClick={handleCopySvg}
                    className="px-3 py-1.5 rounded-lg border border-zinc-300 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-xs flex items-center gap-1.5 transition"
                  >
                    {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copied ? 'Copied SVG' : 'Copy Markup'}</span>
                  </button>
                  <a
                    href={result.download_url}
                    download={result.filename}
                    className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1.5 transition"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Download SVG</span>
                  </a>
                </div>
              </div>

              {/* Side-by-Side Visual Inspection */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Original Raster Bitmap */}
                <div className="p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-950">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-zinc-400 mb-2 flex items-center gap-1.5">
                    <FileImage className="w-3.5 h-3.5" />
                    <span>Original Raster Bitmap</span>
                  </div>
                  <div className="h-64 rounded-lg bg-zinc-100 dark:bg-zinc-900 flex items-center justify-center overflow-hidden border border-zinc-200 dark:border-zinc-800">
                    {previewSrc ? (
                      <img
                        src={previewSrc}
                        alt="Original Raster"
                        className="max-h-full max-w-full object-contain"
                      />
                    ) : (
                      <div className="text-xs text-zinc-500">Source image file</div>
                    )}
                  </div>
                </div>

                {/* Traced Scalable Vector SVG */}
                <div className="p-4 rounded-xl border border-indigo-500/30 bg-zinc-50 dark:bg-zinc-950">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-indigo-400 mb-2 flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5 text-indigo-400" />
                    <span>Traced SVG Vector Geometry</span>
                  </div>
                  <div
                    className="h-64 rounded-lg bg-zinc-100 dark:bg-zinc-900 flex items-center justify-center overflow-hidden border border-indigo-500/20 p-2 [&>svg]:max-h-full [&>svg]:max-w-full [&>svg]:object-contain"
                    dangerouslySetInnerHTML={{ __html: result.svg_markup }}
                  />
                </div>
              </div>

              {/* Limitation Notice */}
              <p className="text-[11px] text-zinc-400 italic">
                {result.warning}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
