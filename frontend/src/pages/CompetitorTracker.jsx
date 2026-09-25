import React, { useState, useEffect } from 'react';
import { Target, Plus, Trash2, Globe, Clock, ShieldCheck, Zap, X } from 'lucide-react';
import { api } from '../api';

export default function CompetitorTracker({ onTriggerRun }) {
  const [competitors, setCompetitors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    domain: '',
    industry: 'Enterprise Cloud Management',
    pricing_url: '',
    tier: 'Tier 1 Direct',
    scraping_cadence: 'Hourly'
  });

  const fetchCompetitors = async () => {
    setLoading(true);
    try {
      const list = await api.getCompetitors();
      setCompetitors(list);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCompetitors();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      await api.createCompetitor(formData);
      setIsModalOpen(false);
      setFormData({ name: '', domain: '', industry: 'Enterprise Cloud Management', pricing_url: '', tier: 'Tier 1 Direct', scraping_cadence: 'Hourly' });
      fetchCompetitors();
    } catch (err) {
      alert("Failed to track competitor: " + err.message);
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm("Are you sure you want to stop tracking this competitor?")) {
      try {
        await api.deleteCompetitor(id);
        fetchCompetitors();
      } catch (err) {
        alert("Delete failed: " + err.message);
      }
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-extrabold text-white flex items-center gap-2">
            <Target className="w-5 h-5 text-indigo-400" /> Tracked Competitors & Data Sources
          </h2>
          <p className="text-xs text-slate-400">Configure target URLs, web scraping cadences, and health status indicators.</p>
        </div>
        <button onClick={() => setIsModalOpen(true)} className="btn-primary">
          <Plus className="w-4 h-4" /> Track New Competitor
        </button>
      </div>

      {/* Table Panel */}
      <div className="glass-panel overflow-hidden rounded-2xl">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-900/80 text-slate-400 border-b border-slate-800 uppercase font-semibold text-[11px] tracking-wider">
            <tr>
              <th className="px-5 py-3.5">Company Name & Domain</th>
              <th className="px-5 py-3.5">Industry & Tier</th>
              <th className="px-5 py-3.5">Target Landing Page URL</th>
              <th className="px-5 py-3.5">Scrape Cadence</th>
              <th className="px-5 py-3.5">Health Status</th>
              <th className="px-5 py-3.5 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 text-slate-300">
            {competitors.map((comp) => (
              <tr key={comp.id} className="hover:bg-slate-900/40 transition">
                <td className="px-5 py-4 font-semibold text-white">
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 font-bold text-xs">
                      {comp.name[0]}
                    </div>
                    <div>
                      <div className="text-xs font-bold text-white">{comp.name}</div>
                      <div className="text-[11px] text-slate-400 font-mono flex items-center gap-1">
                        <Globe className="w-3 h-3 text-slate-500" /> {comp.domain}
                      </div>
                    </div>
                  </div>
                </td>
                <td className="px-5 py-4">
                  <div className="text-xs">{comp.industry}</div>
                  <span className="badge badge-medium text-[10px] mt-1">{comp.tier}</span>
                </td>
                <td className="px-5 py-4 font-mono text-[11px] text-indigo-300 max-w-xs truncate">
                  {comp.pricing_url || `https://${comp.domain}/pricing`}
                </td>
                <td className="px-5 py-4 font-semibold">
                  <span className="flex items-center gap-1.5 text-slate-300">
                    <Clock className="w-3.5 h-3.5 text-slate-400" /> {comp.scraping_cadence}
                  </span>
                </td>
                <td className="px-5 py-4">
                  <span className={`badge ${comp.health_status === 'Healthy' ? 'badge-success' : 'badge-high'}`}>
                    <ShieldCheck className="w-3 h-3" /> {comp.health_status}
                  </span>
                </td>
                <td className="px-5 py-4 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <button
                      onClick={() => onTriggerRun(comp)}
                      className="px-2.5 py-1.5 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/40 text-indigo-300 border border-indigo-500/30 text-[11px] font-semibold transition flex items-center gap-1"
                    >
                      <Zap className="w-3 h-3" /> Run War Room
                    </button>
                    <button
                      onClick={() => handleDelete(comp.id)}
                      className="p-1.5 rounded-lg hover:bg-rose-500/20 text-slate-400 hover:text-rose-400 transition"
                      title="Deactivate Competitor"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Modal for Adding New Competitor */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-panel p-6 rounded-2xl max-w-md w-full border border-slate-800 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Target className="w-4 h-4 text-indigo-400" /> Track Target Competitor
              </h3>
              <button onClick={() => setIsModalOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreate} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-300 mb-1">Company Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Acme Cloud"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-300 mb-1">Domain Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. acme.com"
                  value={formData.domain}
                  onChange={(e) => setFormData({ ...formData, domain: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-300 mb-1">Target Pricing URL</label>
                <input
                  type="url"
                  placeholder="https://acme.com/pricing"
                  value={formData.pricing_url}
                  onChange={(e) => setFormData({ ...formData, pricing_url: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-300 mb-1">Competitor Tier</label>
                  <select
                    value={formData.tier}
                    onChange={(e) => setFormData({ ...formData, tier: e.target.value })}
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="Tier 1 Direct">Tier 1 Direct</option>
                    <option value="Tier 2 Emerging">Tier 2 Emerging</option>
                    <option value="Indirect Threat">Indirect Threat</option>
                  </select>
                </div>
                <div>
                  <label className="block font-semibold text-slate-300 mb-1">Scrape Cadence</label>
                  <select
                    value={formData.scraping_cadence}
                    onChange={(e) => setFormData({ ...formData, scraping_cadence: e.target.value })}
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="Hourly">Hourly</option>
                    <option value="Daily">Daily</option>
                    <option value="Weekly">Weekly</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3">
                <button type="button" onClick={() => setIsModalOpen(false)} className="btn-secondary">
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  Start Surveillance
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
