import React, { useState, useEffect } from 'react';
import { CheckSquare, ShieldCheck, XCircle, CheckCircle, RefreshCw, MessageSquare } from 'lucide-react';
import { api } from '../api';

export default function HumanReview() {
  const [pendingRuns, setPendingRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState({});

  const fetchPending = async () => {
    setLoading(true);
    try {
      const list = await api.getPendingHITL();
      setPendingRuns(list);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPending();
  }, []);

  const handleAction = async (thread_id, approved) => {
    const fb = feedback[thread_id] || (approved ? "Approved by Lead Market Analyst." : "Rejected for refinement.");
    try {
      await api.resumeHITL(thread_id, approved, fb);
      fetchPending();
    } catch (err) {
      alert("Failed to resume graph: " + err.message);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400 text-sm">
        <RefreshCw className="w-5 h-5 animate-spin text-indigo-400 mr-2" /> Loading HITL Inbox...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Title */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-extrabold text-white flex items-center gap-2">
            <CheckSquare className="w-5 h-5 text-indigo-400" /> Human-in-the-Loop Review Inbox
          </h2>
          <p className="text-xs text-slate-400">
            LangGraph checkpointer breakpoints paused high-threat or low-confidence agent runs for human verification.
          </p>
        </div>
        <button onClick={fetchPending} className="btn-secondary">
          <RefreshCw className="w-3.5 h-3.5" /> Refresh Inbox
        </button>
      </div>

      {pendingRuns.length === 0 ? (
        <div className="glass-panel p-12 rounded-2xl text-center space-y-3">
          <ShieldCheck className="w-12 h-12 text-emerald-400 mx-auto" />
          <h3 className="text-base font-bold text-white">All Agent Runs Verified & Approved</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            No agent threads are currently paused at the checkpointer breakpoint. All extracted market threats met confidence thresholds.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {pendingRuns.map((run) => (
            <div key={run.id} className="glass-panel p-6 rounded-2xl border border-amber-500/30 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="badge badge-high text-xs">HITL Breakpoint Paused</span>
                  <span className="text-xs font-mono text-slate-400">Thread ID: {run.thread_id}</span>
                </div>
                <div className="text-xs font-semibold text-amber-300">
                  Confidence Score: {(run.confidence_score * 100).toFixed(1)}%
                </div>
              </div>

              {/* Extracted Facts & Anomaly Summary */}
              <div className="bg-slate-900/80 p-4 rounded-xl space-y-2 border border-slate-800 text-xs text-slate-300">
                <div className="font-bold text-white">Extracted Findings Pending Human Confirmation:</div>
                <pre className="whitespace-pre-wrap font-mono text-[11px] text-slate-400">
                  {JSON.stringify(run.quantitative_analysis || run.extracted_facts, null, 2)}
                </pre>
              </div>

              {/* Action Form */}
              <div className="flex flex-col sm:flex-row items-center gap-3 pt-2">
                <div className="flex-1 w-full flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-xl px-3 py-1.5">
                  <MessageSquare className="w-4 h-4 text-slate-400 shrink-0" />
                  <input
                    type="text"
                    placeholder="Enter optional analyst review feedback..."
                    value={feedback[run.thread_id] || ''}
                    onChange={(e) => setFeedback({ ...feedback, [run.thread_id]: e.target.value })}
                    className="w-full bg-transparent text-xs text-white focus:outline-none"
                  />
                </div>

                <div className="flex items-center gap-2 w-full sm:w-auto">
                  <button
                    onClick={() => handleAction(run.thread_id, false)}
                    className="flex-1 sm:flex-none btn-secondary text-rose-400 border-rose-500/30 hover:bg-rose-500/10"
                  >
                    <XCircle className="w-4 h-4" /> Reject & Re-Route
                  </button>
                  <button
                    onClick={() => handleAction(run.thread_id, true)}
                    className="flex-1 sm:flex-none btn-primary bg-emerald-600 hover:bg-emerald-500 shadow-emerald-500/20"
                  >
                    <CheckCircle className="w-4 h-4" /> Approve & Resume Graph
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
