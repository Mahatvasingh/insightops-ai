import React, { useState, useEffect } from 'react';
import { BookOpen, Download, Search, FileText, Calendar, ShieldCheck } from 'lucide-react';
import PlotlyChart from '../components/PlotlyChart';
import { api } from '../api';

export default function IntelligenceVault() {
  const [reports, setReports] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);

  const fetchReports = async () => {
    setLoading(true);
    try {
      const list = await api.getReports();
      setReports(list);
      if (list.length > 0) {
        const detail = await api.getReportDetail(list[0].id);
        setSelectedReport(detail);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const handleSelect = async (id) => {
    try {
      const detail = await api.getReportDetail(id);
      setSelectedReport(detail);
    } catch (err) {
      console.error(err);
    }
  };

  const filteredReports = reports.filter(
    (r) => r.title.toLowerCase().includes(searchQuery.toLowerCase()) || r.competitor_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-extrabold text-white flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-indigo-400" /> Intelligence Vault & Executive Reports
          </h2>
          <p className="text-xs text-slate-400">Searchable repository of finalized executive briefs with embedded Plotly charts and PDF export.</p>
        </div>
      </div>

      {/* Search Bar */}
      <div className="flex items-center gap-3 bg-slate-900/80 border border-slate-800 rounded-xl px-4 py-2 text-xs">
        <Search className="w-4 h-4 text-slate-400" />
        <input
          type="text"
          placeholder="Search intelligence briefs by competitor or keyword..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full bg-transparent text-white focus:outline-none"
        />
      </div>

      {/* Main Grid: Reports Master-Detail View */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Master List */}
        <div className="space-y-3">
          {filteredReports.length === 0 ? (
            <p className="text-xs text-slate-500 italic p-4 text-center">No reports match search criteria.</p>
          ) : (
            filteredReports.map((rep) => {
              const isSelected = selectedReport?.id === rep.id;
              return (
                <div
                  key={rep.id}
                  onClick={() => handleSelect(rep.id)}
                  className={`glass-panel p-4 rounded-xl cursor-pointer transition space-y-2 border ${
                    isSelected ? 'border-indigo-500 bg-indigo-950/20' : 'border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-indigo-300">{rep.competitor_name}</span>
                    <span className="badge badge-medium text-[10px]">v{rep.version}.0</span>
                  </div>
                  <h4 className="text-xs font-bold text-white leading-snug">{rep.title}</h4>
                  <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">{rep.summary}</p>
                  <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1">
                    <span className="flex items-center gap-1"><Calendar className="w-3 h-3" /> {new Date(rep.created_at).toLocaleDateString()}</span>
                    <span className="text-indigo-400 font-medium flex items-center gap-1"><FileText className="w-3 h-3" /> Read Brief</span>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Right Detail Reader */}
        <div className="lg:col-span-2 glass-panel p-6 rounded-2xl space-y-6">
          {selectedReport ? (
            <>
              <div className="flex items-center justify-between pb-4 border-b border-slate-800">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="badge badge-success text-xs">Fact-Check Verified</span>
                    <span className="text-xs text-slate-400 font-mono">ID: {selectedReport.id.slice(0, 8)}</span>
                  </div>
                  <h3 className="text-lg font-extrabold text-white">{selectedReport.title}</h3>
                </div>
                <button
                  onClick={() => api.exportReportPDF(selectedReport.id)}
                  className="btn-primary shrink-0"
                >
                  <Download className="w-4 h-4" /> Export PDF Brief
                </button>
              </div>

              {/* Embedded Plotly Spec Chart */}
              {selectedReport.plotly_spec_json && (
                <div className="glass-panel p-4 rounded-xl border border-slate-800">
                  <PlotlyChart spec={selectedReport.plotly_spec_json} height={260} />
                </div>
              )}

              {/* Markdown Executive Brief Output */}
              <div className="prose prose-invert max-w-none text-xs text-slate-300 leading-relaxed font-sans space-y-3 bg-slate-950/60 p-5 rounded-xl border border-slate-800/80 whitespace-pre-wrap">
                {selectedReport.executive_brief_md}
              </div>

              {/* Citations Footer */}
              {selectedReport.citations_json && (
                <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-xs space-y-2">
                  <div className="font-bold text-white flex items-center gap-1.5">
                    <ShieldCheck className="w-4 h-4 text-emerald-400" /> Fact-Checker Verification Citations
                  </div>
                  <div className="space-y-1 text-[11px] text-slate-400">
                    {selectedReport.citations_json.map((c, i) => (
                      <div key={i} className="flex items-center justify-between">
                        <span className="font-mono text-indigo-300">{c.source}</span>
                        <span className="text-emerald-400 font-semibold">{(c.confidence * 100).toFixed(1)}% Match</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="h-64 flex items-center justify-center text-slate-500 text-xs italic">
              Select an intelligence brief from the vault list to view.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
