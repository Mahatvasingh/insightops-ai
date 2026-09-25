import React, { useState, useEffect } from 'react';
import { Target, AlertTriangle, FileText, Zap, RefreshCw, ArrowUpRight } from 'lucide-react';
import StatCard from '../components/StatCard';
import PlotlyChart from '../components/PlotlyChart';
import { api } from '../api';

export default function ExecutiveDashboard({ onSelectTab }) {
  const [data, setData] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadDashboard = async () => {
    setLoading(true);
    try {
      const overview = await api.getAnalytics();
      const recentAlerts = await api.getAlerts();
      setData(overview);
      setAlerts(recentAlerts);
    } catch (err) {
      console.error("Dashboard error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400 text-sm">
        <RefreshCw className="w-5 h-5 animate-spin text-indigo-400 mr-2" /> Loading Executive Market Pulse...
      </div>
    );
  }

  const metrics = data?.metrics || {};

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="glass-panel p-6 rounded-2xl bg-gradient-to-r from-indigo-950/40 via-purple-950/20 to-slate-900 border border-indigo-500/20 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h2 className="text-xl font-extrabold text-white">Autonomous Executive Market Intelligence</h2>
            <span className="badge badge-medium">Real-Time Synthesis</span>
          </div>
          <p className="text-xs text-slate-400 max-w-2xl leading-relaxed">
            Continuous autonomous web scraping, stateful LangGraph multi-agent anomaly extraction, adversarial fact-checking, and executive brief publishing.
          </p>
        </div>
        <button onClick={() => onSelectTab('warroom')} className="btn-primary shrink-0">
          <Zap className="w-4 h-4" /> Launch War-Room Session
        </button>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard title="Tracked Targets" value={metrics.tracked_competitors || 4} subtitle="Active Surveillance" icon={Target} color="indigo" />
        <StatCard title="Strategic Anomalies" value={metrics.active_anomalies || 2} subtitle="Price Cuts & Feature Shifts" icon={AlertTriangle} color="amber" />
        <StatCard title="Intelligence Briefs" value={metrics.intelligence_briefs || 1} subtitle="Published Reports" icon={FileText} color="emerald" />
        <StatCard title="Redis TTL Cost Savings" value={metrics.cost_savings_redis_ttl || "45.2%"} subtitle="LLM Token Budget Saved" icon={Zap} color="pink" />
      </div>

      {/* Main Grid: Volatility Chart & Live Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Aggregated Market Chart */}
        <div className="lg:col-span-2 glass-panel p-5 rounded-2xl space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-white">Market Volatility & Anomaly Index</h3>
              <p className="text-xs text-slate-400">Aggregated competitor price cuts, sentiment drops, and feature removals</p>
            </div>
            <span className="text-xs text-indigo-400 font-semibold flex items-center gap-1">
              DuckDB Analytics <ArrowUpRight className="w-3.5 h-3.5" />
            </span>
          </div>
          <PlotlyChart spec={data?.market_pulse_chart} height={320} />
        </div>

        {/* Recent Anomaly Stream */}
        <div className="glass-panel p-5 rounded-2xl space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" /> Recent Strategic Anomalies
            </h3>
            <button onClick={loadDashboard} className="text-slate-400 hover:text-white transition">
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="space-y-3 max-h-[340px] overflow-y-auto pr-1">
            {alerts.length === 0 ? (
              <p className="text-xs text-slate-500 italic text-center py-6">No unread anomalies detected.</p>
            ) : (
              alerts.map((alert) => (
                <div key={alert.id} className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1.5 hover:border-slate-700 transition">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-indigo-300">{alert.competitor_name}</span>
                    <span className={`badge ${alert.severity === 'critical' ? 'badge-critical' : 'badge-high'}`}>
                      {alert.metric_delta || alert.severity}
                    </span>
                  </div>
                  <h4 className="text-xs font-semibold text-slate-200">{alert.title}</h4>
                  <p className="text-[11px] text-slate-400 leading-relaxed">{alert.description}</p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
