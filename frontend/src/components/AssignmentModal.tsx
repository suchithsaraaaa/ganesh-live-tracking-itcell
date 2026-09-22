import React, { useState } from 'react';
import { X, UserCheck, AlertCircle, ShieldCheck } from 'lucide-react';
import { assignConstable, handoverAssignment } from '../api/client';

interface AssignmentModalProps {
  isOpen: boolean;
  gpid: string;
  currentAssignmentId?: number | null;
  currentConstableName?: string | null;
  onClose: () => void;
  onSuccess: () => void;
}

export const AssignmentModal: React.FC<AssignmentModalProps> = ({
  isOpen,
  gpid,
  currentAssignmentId,
  currentConstableName,
  onClose,
  onSuccess,
}) => {
  const [constableId, setConstableId] = useState<string>('');
  const [reason, setReason] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const isHandover = Boolean(currentAssignmentId && currentConstableName);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const parsedId = parseInt(constableId, 10);
    if (isNaN(parsedId)) {
      setError('Please provide a valid Constable User ID.');
      return;
    }

    setLoading(true);
    setError(null);
    setSuccessMsg(null);

    try {
      if (isHandover && currentAssignmentId) {
        if (!reason.trim()) {
          setError('Reason is mandatory for duty handover.');
          setLoading(false);
          return;
        }
        await handoverAssignment(currentAssignmentId, parsedId, reason.trim());
        setSuccessMsg(`Duty successfully handed over for GPID ${gpid}.`);
      } else {
        await assignConstable(gpid, parsedId);
        setSuccessMsg(`Constable assigned successfully to GPID ${gpid}.`);
      }
      setTimeout(() => {
        onSuccess();
        onClose();
      }, 1200);
    } catch (err: any) {
      setError(err.message || 'Action failed. Ensure constable is not already assigned to another idol.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
      <div className="w-full max-w-md bg-slate-900 border border-slate-700 rounded-lg shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-150">
        {/* Header */}
        <div className="px-5 py-3.5 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <UserCheck className="w-5 h-5 text-emerald-400" />
            <h2 className="text-sm font-bold text-white uppercase tracking-wider">
              {isHandover ? 'Handover Constable Duty' : 'Assign Ground Constable'}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4 text-xs">
          <div>
            <span className="text-slate-400 text-[11px] block">Target Idol GPID:</span>
            <span className="text-sm font-bold text-blue-400 mono">{gpid}</span>
          </div>

          {isHandover && (
            <div className="p-3 bg-slate-950 rounded border border-slate-800">
              <span className="text-slate-500 text-[10px] block">Current Officer on Duty:</span>
              <span className="font-semibold text-white">{currentConstableName}</span>
            </div>
          )}

          <div>
            <label className="block text-slate-300 font-semibold mb-1">
              {isHandover ? 'New Constable User ID' : 'Constable User ID'}
            </label>
            <input
              type="number"
              value={constableId}
              onChange={(e) => setConstableId(e.target.value)}
              placeholder="e.g. 104"
              required
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded text-slate-100 mono text-xs focus:outline-none focus:border-emerald-400"
            />
            <p className="text-[10px] text-slate-500 mt-1">
              Enter database ID of the registered Constable user.
            </p>
          </div>

          {isHandover && (
            <div>
              <label className="block text-slate-300 font-semibold mb-1">
                Handover Reason / Station Log Notes
              </label>
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                rows={2}
                placeholder="e.g. Shift rotation at Charminar junction"
                required
                className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded text-slate-100 text-xs focus:outline-none focus:border-emerald-400"
              />
            </div>
          )}

          {error && (
            <div className="p-3 bg-rose-950/60 border border-rose-800 rounded flex items-start space-x-2 text-rose-300 text-xs">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {successMsg && (
            <div className="p-3 bg-emerald-950/60 border border-emerald-800 rounded flex items-center space-x-2 text-emerald-300 text-xs">
              <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>{successMsg}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 px-4 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 text-white font-semibold rounded flex items-center justify-center space-x-2 transition-colors cursor-pointer text-xs"
          >
            <span>{loading ? 'Processing Transaction...' : isHandover ? 'Authorize Duty Handover' : 'Confirm Assignment'}</span>
          </button>
        </form>
      </div>
    </div>
  );
};
