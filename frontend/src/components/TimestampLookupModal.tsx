import React, { useState, useEffect } from 'react';
import { X, Search, Clock, MapPin, AlertCircle, CheckCircle2 } from 'lucide-react';
import { TimestampLookupResult } from '../types';
import { fetchTimestampLookup } from '../api/client';

interface TimestampLookupModalProps {
  isOpen: boolean;
  initialGpid: string;
  onClose: () => void;
  onPlotPoint: (result: TimestampLookupResult) => void;
}

export const TimestampLookupModal: React.FC<TimestampLookupModalProps> = ({
  isOpen,
  initialGpid,
  onClose,
  onPlotPoint,
}) => {
  const [gpid, setGpid] = useState(initialGpid);
  const [targetDate, setTargetDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [targetTime, setTargetTime] = useState(() => {
    const now = new Date();
    return `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TimestampLookupResult | null>(null);

  useEffect(() => {
    if (initialGpid) {
      setGpid(initialGpid);
    }
  }, [initialGpid]);

  if (!isOpen) return null;

  const handleLookup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!gpid.trim()) {
      setError('Please provide a valid GPID.');
      return;
    }

    const isoString = `${targetDate}T${targetTime}:00Z`;
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetchTimestampLookup(gpid.trim(), isoString);
      setResult(res);
    } catch (err: any) {
      setError(err.message || 'Failed to locate historical record.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg bg-slate-900 border border-slate-700 rounded-lg shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-150">
        {/* Modal Header */}
        <div className="px-5 py-3.5 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Clock className="w-5 h-5 text-amber-400" />
            <h2 className="text-sm font-bold text-white uppercase tracking-wider">
              Historical Timestamp Lookup
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Form */}
        <form onSubmit={handleLookup} className="p-5 space-y-4 text-xs">
          <div>
            <label className="block text-slate-300 font-semibold mb-1">
              Idol GPID
            </label>
            <input
              type="text"
              value={gpid}
              onChange={(e) => setGpid(e.target.value)}
              placeholder="e.g. HYDCMRZCMNR1749"
              required
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded text-slate-100 mono text-xs focus:outline-none focus:border-amber-400"
            />
            <p className="text-[10px] text-slate-500 mt-1">
              Enter the authoritative Ganesh Procession Identifier (GPID).
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-slate-300 font-semibold mb-1">
                Target Date
              </label>
              <input
                type="date"
                value={targetDate}
                onChange={(e) => setTargetDate(e.target.value)}
                required
                className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded text-slate-100 text-xs focus:outline-none focus:border-amber-400"
              />
            </div>
            <div>
              <label className="block text-slate-300 font-semibold mb-1">
                Target Time (24h)
              </label>
              <input
                type="time"
                value={targetTime}
                onChange={(e) => setTargetTime(e.target.value)}
                required
                className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded text-slate-100 text-xs focus:outline-none focus:border-amber-400"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 px-4 bg-amber-600 hover:bg-amber-500 disabled:bg-slate-800 text-white font-semibold rounded flex items-center justify-center space-x-2 transition-colors cursor-pointer"
          >
            <Search className="w-4 h-4" />
            <span>{loading ? 'Querying Historical GPS Ledger...' : 'Find Nearest Historical Location'}</span>
          </button>
        </form>

        {/* Error Feedback */}
        {error && (
          <div className="mx-5 mb-4 p-3 bg-rose-950/60 border border-rose-800 rounded flex items-start space-x-2 text-rose-300 text-xs">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {/* Results Panel */}
        {result && (
          <div className="mx-5 mb-5 p-4 bg-slate-950 border border-amber-500/40 rounded-md space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <span className="text-[11px] font-bold text-amber-400 uppercase tracking-wide flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" /> Nearest Verified GPS Fix
              </span>
              <span className="text-[10px] text-slate-400 mono">
                Delta: ±{result.nearest_point.time_difference_seconds}s
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <span className="text-slate-500 text-[10px]">GPID:</span>
                <p className="font-bold text-white mono">{result.gpid}</p>
              </div>
              <div>
                <span className="text-slate-500 text-[10px]">Idol Name:</span>
                <p className="font-semibold text-slate-200 truncate">{result.idol_name}</p>
              </div>
              <div>
                <span className="text-slate-500 text-[10px]">Fix Timestamp:</span>
                <p className="font-medium text-slate-200">{new Date(result.nearest_point.recorded_at).toLocaleString()}</p>
              </div>
              <div>
                <span className="text-slate-500 text-[10px]">GPS Accuracy:</span>
                <p className="font-medium text-slate-200">{result.nearest_point.accuracy !== null ? `±${result.nearest_point.accuracy}m` : 'N/A'}</p>
              </div>
              <div className="col-span-2">
                <span className="text-slate-500 text-[10px]">Coordinates:</span>
                <p className="mono font-semibold text-emerald-400">
                  {result.nearest_point.latitude.toFixed(6)}, {result.nearest_point.longitude.toFixed(6)}
                </p>
              </div>
              <div className="col-span-2 border-t border-slate-800/80 pt-2 flex items-center justify-between">
                <div>
                  <span className="text-slate-500 text-[10px]">Duty Officer on Record:</span>
                  <p className="font-semibold text-slate-200">
                    {result.constable.name} ({result.constable.police_id})
                  </p>
                </div>
                <span className="text-[10px] text-slate-500">Session #{result.session_id}</span>
              </div>
            </div>

            <button
              onClick={() => {
                onPlotPoint(result);
                onClose();
              }}
              className="w-full py-2 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded flex items-center justify-center space-x-2 transition-colors cursor-pointer text-xs"
            >
              <MapPin className="w-4 h-4" />
              <span>Plot & Center on Live Map</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
