import React, { useState } from 'react';
import { 
  Shield, 
  Cpu, 
  User, 
  Mail, 
  Lock, 
  ArrowRight, 
  Sparkles, 
  CheckCircle2, 
  AlertCircle, 
  Eye, 
  EyeOff, 
  Crown, 
  BrainCircuit, 
  BarChart3, 
  Loader2 
} from 'lucide-react';
import { api, DEMO_PRESETS } from '../api';

export default function AuthModal({ onAuthSuccess }) {
  const [mode, setMode] = useState('login'); // 'login' | 'signup'
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  // Form states
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [selectedRole, setSelectedRole] = useState('Analyst'); // default for signup

  const roleDefinitions = [
    {
      id: 'Admin',
      name: 'Admin',
      icon: Crown,
      tag: 'Full Access',
      color: 'from-indigo-500 to-purple-600',
      borderActive: 'border-indigo-500 bg-indigo-500/10 shadow-indigo-500/20',
      description: 'System control, competitor management, pipeline deletion & execution.'
    },
    {
      id: 'Analyst',
      name: 'Analyst',
      icon: BrainCircuit,
      tag: 'Operator',
      color: 'from-emerald-500 to-teal-600',
      borderActive: 'border-emerald-500 bg-emerald-500/10 shadow-emerald-500/20',
      description: 'Trigger autonomous agent runs, conduct HITL human review, generate briefs.'
    },
    {
      id: 'Viewer',
      name: 'Viewer',
      icon: Eye,
      tag: 'Read Only',
      color: 'from-amber-500 to-orange-600',
      borderActive: 'border-amber-500 bg-amber-500/10 shadow-amber-500/20',
      description: 'Inspect executive dashboards, browse intelligence vault & review metrics.'
    }
  ];

  const handleQuickLogin = async (preset) => {
    setError('');
    setEmail(preset.email);
    setPassword(preset.password);
    setLoading(true);
    try {
      const user = await api.login(preset.email, preset.password);
      onAuthSuccess(user);
    } catch (err) {
      setError(err.message || 'Quick login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (mode === 'login') {
        if (!email || !password) {
          throw new Error('Please enter both email and password');
        }
        const user = await api.login(email, password);
        onAuthSuccess(user);
      } else {
        if (!fullName || !email || !password) {
          throw new Error('Please fill in all required fields');
        }
        if (password.length < 6) {
          throw new Error('Password must be at least 6 characters');
        }
        const user = await api.register({
          full_name: fullName,
          email,
          password,
          role: selectedRole
        });
        onAuthSuccess(user);
      }
    } catch (err) {
      setError(err.message || 'Authentication error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-xl animate-in fade-in duration-200">
      <div className="w-full max-w-xl glass-panel border border-slate-800 bg-slate-900/90 shadow-2xl rounded-2xl overflow-hidden relative">
        {/* Ambient Top Glow */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500"></div>

        {/* Brand Header */}
        <div className="p-8 pb-4 text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-gradient-to-tr from-indigo-600 via-purple-600 to-pink-500 p-0.5 shadow-lg shadow-indigo-500/30 mb-3">
            <div className="w-full h-full bg-slate-950 rounded-[14px] flex items-center justify-center">
              <Cpu className="w-6 h-6 text-indigo-400" />
            </div>
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-white flex items-center justify-center gap-2">
            InsightOps <span className="gradient-text font-black">AI</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
            Autonomous Market Intelligence & Competitor War-Room System
          </p>

          {/* Tab Switcher */}
          <div className="mt-6 p-1 bg-slate-950/80 rounded-xl border border-slate-800 flex gap-1 max-w-xs mx-auto">
            <button
              type="button"
              onClick={() => { setMode('login'); setError(''); }}
              className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition ${
                mode === 'login'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => { setMode('signup'); setError(''); }}
              className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition ${
                mode === 'signup'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Create Account
            </button>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mx-8 mb-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
        )}

        {/* Body Content */}
        <div className="p-8 pt-2">
          {mode === 'login' ? (
            <div className="space-y-6">
              {/* Quick Preset Logins */}
              <div>
                <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-2.5">
                  1-Click Role Login (JWT Authenticated)
                </label>
                <div className="grid grid-cols-3 gap-2.5">
                  {DEMO_PRESETS.map((p) => {
                    const isSelected = email === p.email;
                    const roleBadgeColor = 
                      p.role === 'Admin' ? 'text-indigo-400 border-indigo-500/30 bg-indigo-500/10' :
                      p.role === 'Analyst' ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10' :
                      'text-amber-400 border-amber-500/30 bg-amber-500/10';

                    return (
                      <button
                        key={p.role}
                        type="button"
                        onClick={() => handleQuickLogin(p)}
                        disabled={loading}
                        className={`text-left p-2.5 rounded-xl border transition group relative ${
                          isSelected
                            ? 'border-indigo-500 bg-slate-800/80 shadow-md'
                            : 'border-slate-800/90 bg-slate-950/50 hover:bg-slate-800/50 hover:border-slate-700'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs font-bold text-white group-hover:text-indigo-300 transition">
                            {p.role}
                          </span>
                          <span className={`text-[10px] px-1.5 py-0.2 rounded border font-mono ${roleBadgeColor}`}>
                            {p.badge}
                          </span>
                        </div>
                        <p className="text-[10px] text-slate-400 line-clamp-1 leading-snug">
                          {p.desc}
                        </p>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="relative flex items-center justify-center">
                <div className="border-t border-slate-800 w-full"></div>
                <span className="bg-slate-900 px-3 text-[11px] text-slate-500 uppercase tracking-wider font-semibold">
                  Or enter credentials
                </span>
                <div className="border-t border-slate-800 w-full"></div>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">Email Address</label>
                  <div className="relative">
                    <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="admin@insightops.ai"
                      required
                      className="w-full bg-slate-950/70 border border-slate-800 rounded-xl pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">Password</label>
                  <div className="relative">
                    <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      required
                      className="w-full bg-slate-950/70 border border-slate-800 rounded-xl pl-9 pr-9 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition"
                    >
                      {showPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full btn-primary justify-center py-2.5 text-xs shadow-lg mt-2"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" /> Authenticating...
                    </>
                  ) : (
                    <>
                      Sign In with JWT <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </form>
            </div>
          ) : (
            /* Sign Up View */
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">Full Name</label>
                <div className="relative">
                  <User className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="e.g. John Doe"
                    required
                    className="w-full bg-slate-950/70 border border-slate-800 rounded-xl pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">Work Email</label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="john@example.com"
                    required
                    className="w-full bg-slate-950/70 border border-slate-800 rounded-xl pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">Password</label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Minimum 6 characters"
                    required
                    className="w-full bg-slate-950/70 border border-slate-800 rounded-xl pl-9 pr-9 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition"
                  >
                    {showPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>

              {/* Role Selection Option Cards */}
              <div>
                <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-2">
                  Select Role & Permissions
                </label>
                <div className="grid grid-cols-3 gap-2.5">
                  {roleDefinitions.map((roleDef) => {
                    const isSelected = selectedRole === roleDef.id;
                    const Icon = roleDef.icon;
                    return (
                      <div
                        key={roleDef.id}
                        onClick={() => setSelectedRole(roleDef.id)}
                        className={`p-3 rounded-xl border cursor-pointer transition relative flex flex-col justify-between ${
                          isSelected
                            ? roleDef.borderActive + ' shadow-md'
                            : 'border-slate-800/90 bg-slate-950/50 hover:bg-slate-800/50 hover:border-slate-700'
                        }`}
                      >
                        <div>
                          <div className="flex items-center justify-between mb-1.5">
                            <div className="flex items-center gap-1.5">
                              <Icon className="w-3.5 h-3.5 text-indigo-400" />
                              <span className="text-xs font-bold text-white">{roleDef.name}</span>
                            </div>
                            {isSelected && (
                              <CheckCircle2 className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                            )}
                          </div>
                          <p className="text-[10px] text-slate-400 leading-snug line-clamp-2">
                            {roleDef.description}
                          </p>
                        </div>
                        <div className="mt-2 text-[10px] font-mono text-slate-400 font-semibold">
                          {roleDef.tag}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full btn-primary justify-center py-2.5 text-xs shadow-lg mt-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" /> Provisioning Account...
                  </>
                ) : (
                  <>
                    Sign Up as {selectedRole} <Sparkles className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          )}
        </div>

        {/* Footer info */}
        <div className="px-8 py-3 bg-slate-950/50 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
          <span className="flex items-center gap-1">
            <Shield className="w-3.5 h-3.5 text-emerald-400" /> Cryptographic Bearer Token (JWT HS256)
          </span>
          <span className="font-mono text-[10px] text-slate-400">Role-Based Access Control</span>
        </div>
      </div>
    </div>
  );
}
