import React from 'react';

export default function StatCard({ title, value, subtitle, icon: Icon, trend, color = 'indigo' }) {
  const glowColors = {
    indigo: 'from-indigo-500/10 to-indigo-500/0 border-indigo-500/20 text-indigo-400',
    amber: 'from-amber-500/10 to-amber-500/0 border-amber-500/20 text-amber-400',
    emerald: 'from-emerald-500/10 to-emerald-500/0 border-emerald-500/20 text-emerald-400',
    pink: 'from-pink-500/10 to-pink-500/0 border-pink-500/20 text-pink-400'
  };

  return (
    <div className={`glass-panel p-5 rounded-2xl bg-gradient-to-b ${glowColors[color]} relative overflow-hidden`}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{title}</span>
        {Icon && <Icon className={`w-5 h-5 ${glowColors[color].split(' ').pop()}`} />}
      </div>
      <div className="text-2xl font-extrabold text-white tracking-tight mb-1">{value}</div>
      <div className="flex items-center justify-between text-xs">
        <span className="text-slate-400">{subtitle}</span>
        {trend && <span className="font-semibold text-emerald-400">{trend}</span>}
      </div>
    </div>
  );
}
