import React from 'react';
import { Shield, Cpu, Activity, User, LogOut, LogIn, Crown, BrainCircuit, Eye } from 'lucide-react';

export default function Navbar({ currentUser, onLogout, onOpenAuth }) {
  const roleStyles = {
    Admin: {
      badge: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
      icon: Crown,
      glow: 'shadow-indigo-500/20'
    },
    Analyst: {
      badge: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
      icon: BrainCircuit,
      glow: 'shadow-emerald-500/20'
    },
    Viewer: {
      badge: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
      icon: Eye,
      glow: 'shadow-amber-500/20'
    }
  };

  const role = currentUser?.role || 'Viewer';
  const roleConfig = roleStyles[role] || roleStyles.Viewer;
  const RoleIcon = roleConfig.icon;

  return (
    <header className="h-16 border-b border-slate-800 bg-slate-950/80 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-40">
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

      {/* Authenticated User Session Info & Logout (Role dropdown removed per requirements) */}
      <div className="flex items-center gap-3">
        {currentUser ? (
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2.5 px-3 py-1.5 rounded-xl border border-slate-800 bg-slate-900/70">
              <div className="w-7 h-7 rounded-lg bg-slate-800 border border-slate-700/60 flex items-center justify-center text-slate-300">
                <User className="w-3.5 h-3.5" />
              </div>
              <div className="text-left hidden sm:block">
                <div className="text-xs font-semibold text-slate-200 leading-tight">
                  {currentUser.full_name || currentUser.email}
                </div>
                <div className="text-[10px] text-slate-400 font-mono leading-tight">
                  {currentUser.email}
                </div>
              </div>
              <span className={`px-2 py-0.5 rounded-md border text-[11px] font-semibold flex items-center gap-1 ${roleConfig.badge}`}>
                <RoleIcon className="w-3 h-3" />
                {role}
              </span>
            </div>

            <button
              onClick={onLogout}
              title="Sign Out"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-800 bg-slate-900/60 hover:bg-rose-500/10 hover:border-rose-500/30 hover:text-rose-300 transition text-xs font-semibold text-slate-300"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Sign Out</span>
            </button>
          </div>
        ) : (
          <button
            onClick={onOpenAuth}
            className="btn-primary text-xs py-1.5 px-3.5"
          >
            <LogIn className="w-3.5 h-3.5" />
            <span>Sign In / Sign Up</span>
          </button>
        )}
      </div>
    </header>
  );
}
