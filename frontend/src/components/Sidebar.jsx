import React from 'react';
import { LayoutDashboard, Target, Flame, CheckSquare, BookOpen, Layers } from 'lucide-react';

export default function Sidebar({ activeTab, setActiveTab, pendingCount }) {
  const navItems = [
    { id: 'dashboard', label: 'Executive Dashboard', icon: LayoutDashboard },
    { id: 'competitors', label: 'Competitor Tracker', icon: Target },
    { id: 'warroom', label: 'War-Room (Live Graph)', icon: Flame, badge: 'SSE Stream' },
    { id: 'hitl', label: 'Human Review Inbox', icon: CheckSquare, count: pendingCount },
    { id: 'reports', label: 'Intelligence Vault', icon: BookOpen },
  ];

  return (
    <aside className="w-64 border-r border-slate-800/80 bg-slate-950/40 p-4 flex flex-col justify-between hidden md:flex min-h-[calc(100vh-4rem)]">
      <div className="space-y-1">
        <div className="px-3 py-2 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
          Intelligence SaaS Pipeline
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold transition ${
                isActive
                  ? 'bg-gradient-to-r from-indigo-600/20 to-indigo-600/5 text-indigo-300 border border-indigo-500/30 shadow-lg shadow-indigo-500/10'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
              }`}
            >
              <div className="flex items-center gap-3">
                <Icon className={`w-4 h-4 ${isActive ? 'text-indigo-400' : 'text-slate-400'}`} />
                <span>{item.label}</span>
              </div>

              {item.badge && (
                <span className="badge badge-medium text-[9px] px-1.5 py-0.5">
                  {item.badge}
                </span>
              )}

              {item.count > 0 && (
                <span className="badge badge-critical text-[10px] px-2 py-0.5 animate-pulse">
                  {item.count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Footer system spec indicator */}
      <div className="glass-panel p-3 rounded-xl text-[11px] text-slate-400 space-y-1">
        <div className="flex items-center justify-between text-slate-300 font-semibold">
          <span className="flex items-center gap-1.5"><Layers className="w-3.5 h-3.5 text-indigo-400" /> LangGraph Workflow</span>
          <span className="text-[10px] text-emerald-400 font-mono">v1.2.6</span>
        </div>
        <p className="text-[10px] text-slate-400 leading-relaxed">
          Stateful Multi-Agent Cyclical StateGraph with PostgresSaver/MemorySaver checkpointer & Redis TTL.
        </p>
      </div>
    </aside>
  );
}
