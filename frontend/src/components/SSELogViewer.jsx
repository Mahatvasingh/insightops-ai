import React, { useRef, useEffect } from 'react';
import { Terminal, ShieldCheck, AlertCircle, Bot } from 'lucide-react';

export default function SSELogViewer({ logs = [], isRunning = false }) {
  const logEndRef = useRef(null);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <div className="glass-panel p-4 rounded-2xl bg-slate-900 text-slate-200 border border-slate-700 font-mono text-xs flex flex-col h-96 shadow-md">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
        <div className="flex items-center gap-2 text-slate-200 font-semibold">
          <Terminal className="w-4 h-4 text-emerald-400" />
          <span>LangGraph Real-Time SSE Telemetry Stream</span>
        </div>
        {isRunning && (
          <span className="flex items-center gap-1.5 text-cyan-400 text-[11px] font-medium">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping"></span>
            Streaming Agent Execution...
          </span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto space-y-2 pr-2">
        {logs.length === 0 ? (
          <div className="h-full flex items-center justify-center text-slate-600 text-xs italic">
            Waiting for agent execution trigger...
          </div>
        ) : (
          logs.map((log, idx) => {
            const isError = log.step === 'error';
            const isFinish = log.step === 'finish';
            return (
              <div
                key={idx}
                className={`p-2 rounded-lg border text-[11px] leading-relaxed transition ${
                  isError
                    ? 'bg-rose-950/30 border-rose-800/40 text-rose-300'
                    : isFinish
                    ? 'bg-emerald-950/30 border-emerald-800/40 text-emerald-300'
                    : 'bg-slate-900/60 border-slate-800 text-slate-300'
                }`}
              >
                <div className="flex items-center justify-between gap-2 mb-1 text-[10px] text-slate-400">
                  <span className="font-semibold text-emerald-400 flex items-center gap-1">
                    <Bot className="w-3 h-3 text-emerald-400" /> [{log.node || 'Supervisor'}]
                  </span>
                  <span>{log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : ''}</span>
                </div>
                <div className="flex items-start gap-2">
                  {isError ? (
                    <AlertCircle className="w-3.5 h-3.5 text-rose-400 shrink-0 mt-0.5" />
                  ) : (
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                  )}
                  <span>{log.message}</span>
                </div>
                {log.confidence !== undefined && log.confidence < 1.0 && (
                  <div className="mt-1 text-[10px] text-amber-400 font-semibold">
                    Fact-Check Confidence Score: {(log.confidence * 100).toFixed(1)}%
                  </div>
                )}
              </div>
            );
          })
        )}
        <div ref={logEndRef} />
      </div>
    </div>
  );
}
