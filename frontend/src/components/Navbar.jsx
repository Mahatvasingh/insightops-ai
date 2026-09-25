import React, { useState } from 'react';
import { Shield, Cpu, Activity, User, ChevronDown, Sparkles } from 'lucide-react';
import { api } from '../api';

export default function Navbar({ currentRole, onRoleChange }) {
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const handleSelectRole = async (role) => {
    setDropdownOpen(false);
    await api.setRole(role);
    onRoleChange(role);
  };

  const roleColors = {
    Admin: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
    Analyst: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
    Viewer: 'bg-amber-500/20 text-amber-300 border-amber-500/30'
  };

  return (
    <header className="h-16 border-b border-slate-800 bg-slate-950/80 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-50">
      {/* Brand Logo */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 via-purple-600 to-pink-500 p-0.5 shadow-lg shadow-indigo-500/20 flex items-center justify-center">
          <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
            <Cpu className="w-5 h-5 text-indigo-400" />
          </div>
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-bold text-lg tracking-tight text-white flex items-center gap-1.5">
              InsightOps <span className="gradient-text font-extrabold">AI</span>
            </h1>
            <span className="badge badge-success text-[10px] py-0.5 px-2">
              <Activity className="w-3 h-3 animate-pulse" /> Live Multi-Agent
            </span>
          </div>
          <p className="text-[11px] text-slate-400 font-medium">Autonomous Market Intelligence & Competitor War-Room</p>
        </div>
      </div>

      {/* RBAC Role Switcher */}
      <div className="relative">
        <button
          onClick={() => setDropdownOpen(!dropdownOpen)}
          className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-slate-800 bg-slate-900/60 hover:bg-slate-800/60 transition text-xs font-semibold text-slate-200"
        >
          <Shield className="w-4 h-4 text-indigo-400" />
          <span>Role:</span>
          <span className={`px-2 py-0.5 rounded-md border text-[11px] ${roleColors[currentRole]}`}>
            {currentRole}
          </span>
          <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
        </button>

        {dropdownOpen && (
          <div className="absolute right-0 mt-2 w-56 rounded-xl border border-slate-800 bg-slate-900 p-2 shadow-2xl z-50 animate-in fade-in slide-in-from-top-2 duration-150">
            <div className="px-2 py-1.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Switch Role Context (RBAC)
            </div>
            {['Admin', 'Analyst', 'Viewer'].map((role) => (
              <button
                key={role}
                onClick={() => handleSelectRole(role)}
                className={`w-full text-left px-3 py-2 rounded-lg text-xs font-medium flex items-center justify-between transition ${
                  currentRole === role ? 'bg-indigo-600/20 text-indigo-300 font-semibold' : 'text-slate-300 hover:bg-slate-800'
                }`}
              >
                <span>{role}</span>
                {currentRole === role && <Sparkles className="w-3.5 h-3.5 text-indigo-400" />}
              </button>
            ))}
          </div>
        )}
      </div>
    </header>
  );
}
