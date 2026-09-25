import React, { useState, useEffect } from 'react';
import { Flame, Play, Bot, CheckCircle2, RefreshCw, Cpu, ShieldAlert, FileCheck, Layers } from 'lucide-react';
import SSELogViewer from '../components/SSELogViewer';
import PlotlyChart from '../components/PlotlyChart';
import { api } from '../api';

export default function WarRoom({ selectedCompetitor }) {
  const [competitors, setCompetitors] = useState([]);
  const [selectedCompId, setSelectedCompId] = useState('');
  const [targetUrl, setTargetUrl] = useState('');
  const [userQuery, setUserQuery] = useState('Analyze sneaky pricing hikes, silent feature removals, or negative user churn spikes.');
  const [activeJobId, setActiveJobId] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const [sseLogs, setSseLogs] = useState([]);
  const [activeNode, setActiveNode] = useState('Supervisor');
  const [plotlySpec, setPlotlySpec] = useState(null);
  const [writerDraft, setWriterDraft] = useState('');
  const [hitlPrompt, setHitlPrompt] = useState(false);

  useEffect(() => {
    api.getCompetitors().then((list) => {
      setCompetitors(list);
      if (selectedCompetitor) {
        setSelectedCompId(selectedCompetitor.id);
        setTargetUrl(selectedCompetitor.pricing_url || `https://${selectedCompetitor.domain}/pricing`);
      } else if (list.length > 0) {
        setSelectedCompId(list[0].id);
        setTargetUrl(list[0].pricing_url || `https://${list[0].domain}/pricing`);
      }
    });
  }, [selectedCompetitor]);

  const handleSelectComp = (e) => {
    const cid = e.target.value;
    setSelectedCompId(cid);
    const comp = competitors.find((c) => c.id === cid);
    if (comp) {
      setTargetUrl(comp.pricing_url || `https://${comp.domain}/pricing`);
    }
  };

  const startAgentRun = async () => {
    if (!selectedCompId) return;
    setIsRunning(true);
    setSseLogs([]);
    setPlotlySpec(null);
    setWriterDraft('');
    setHitlPrompt(false);
    setActiveNode('Supervisor');

    try {
      const res = await api.triggerAgentRun(selectedCompId, targetUrl, userQuery);
      setActiveJobId(res.job_id);

      // Connect SSE Stream
      api.connectSSE(
        res.job_id,
        (evt) => {
          setSseLogs((prev) => [...prev, evt]);
          if (evt.node) setActiveNode(evt.node);
          if (evt.data?.plotly_spec) setPlotlySpec(evt.data.plotly_spec);
          if (evt.data?.writer_draft) setWriterDraft(evt.data.writer_draft);
          if (evt.data?.status === 'awaiting_hitl') setHitlPrompt(true);

          if (evt.step === 'finish' || evt.step === 'error') {
            setIsRunning(false);
          }
        },
        (err) => {
          console.error("SSE Connection error:", err);
          setIsRunning(false);
        }
      );
    } catch (err) {
      alert("Failed to run agent workflow: " + err.message);
      setIsRunning(false);
    }
  };

  const agentNodes = [
    { name: 'Supervisor', title: 'State Supervisor', icon: Cpu, desc: 'Orchestrates cyclical StateGraph' },
    { name: 'Researcher', title: 'Scraper / Extractor', icon: Bot, desc: 'Collects live web HTML & strips noise' },
    { name: 'Quantitative Analyst', title: 'Pandas & DuckDB Analyst', icon: Layers, desc: 'Computes metrics & Plotly specs' },
    { name: 'Adversarial Fact-Checker', title: 'Self-Correction Checker', icon: ShieldAlert, desc: 'Evaluates claim confidence' },
    { name: 'Executive Writer', title: 'Report Writer', icon: FileCheck, desc: 'Synthesizes executive brief' },
  ];

  return (
    <div className="space-y-6">
      {/* Title Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-extrabold text-white flex items-center gap-2">
            <Flame className="w-5 h-5 text-amber-400" /> Competitor War-Room (Live Graph Run)
          </h2>
          <p className="text-xs text-slate-400">Trigger multi-agent LangGraph workflow and observe step-by-step state execution via SSE streaming.</p>
        </div>
      </div>

      {/* Control Panel Card */}
      <div className="glass-panel p-5 rounded-2xl grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1">Target Competitor</label>
          <select
            value={selectedCompId}
            onChange={handleSelectComp}
            disabled={isRunning}
            className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
          >
            {competitors.map((c) => (
              <option key={c.id} value={c.id}>{c.name} ({c.domain})</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1">Target Landing Page URL</label>
          <input
            type="url"
            value={targetUrl}
            onChange={(e) => setTargetUrl(e.target.value)}
            disabled={isRunning}
            className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500 font-mono"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1">Agent Query Objective</label>
          <input
            type="text"
            value={userQuery}
            onChange={(e) => setUserQuery(e.target.value)}
            disabled={isRunning}
            className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
          />
        </div>

        <button
          onClick={startAgentRun}
          disabled={isRunning || !selectedCompId}
          className="btn-primary w-full justify-center disabled:opacity-50 py-2.5"
        >
          {isRunning ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin text-white" /> Agents Executing...
            </>
          ) : (
            <>
              <Play className="w-4 h-4 fill-white" /> Trigger LangGraph Run
            </>
          )}
        </button>
      </div>

      {/* Visual State Graph Flow Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-5 gap-3">
        {agentNodes.map((node) => {
          const NodeIcon = node.icon;
          const isActive = activeNode.includes(node.name);
          return (
            <div
              key={node.name}
              className={`glass-panel p-4 rounded-xl border text-left transition ${
                isActive
                  ? 'border-indigo-500 bg-indigo-950/30 shadow-lg shadow-indigo-500/20'
                  : 'border-slate-800/80 bg-slate-900/40 opacity-75'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <NodeIcon className={`w-5 h-5 ${isActive ? 'text-indigo-400 animate-pulse' : 'text-slate-500'}`} />
                {isActive && <span className="w-2 h-2 rounded-full bg-emerald-400"></span>}
              </div>
              <h4 className="text-xs font-bold text-white mb-0.5">{node.title}</h4>
              <p className="text-[10px] text-slate-400 leading-tight">{node.desc}</p>
            </div>
          );
        })}
      </div>

      {/* Main Grid: SSE Stream Terminal & Live Output */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* SSE Stream Viewer */}
        <SSELogViewer logs={sseLogs} isRunning={isRunning} />

        {/* Live Plotly / Draft Preview */}
        <div className="glass-panel p-5 rounded-2xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
              <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                Live Output & Plotly Spec Stream
              </h3>
              {plotlySpec && <span className="badge badge-success text-[10px]">Plotly Rendered</span>}
            </div>

            {plotlySpec ? (
              <PlotlyChart spec={plotlySpec} height={280} />
            ) : writerDraft ? (
              <div className="bg-slate-900/80 p-4 rounded-xl text-xs font-mono text-slate-300 max-h-64 overflow-y-auto whitespace-pre-wrap border border-slate-800">
                {writerDraft}
              </div>
            ) : (
              <div className="h-64 flex flex-col items-center justify-center text-slate-500 text-xs italic space-y-2">
                <Cpu className="w-8 h-8 text-slate-600 animate-pulse" />
                <span>Trigger run to view live Plotly spec output and generated executive draft.</span>
              </div>
            )}
          </div>

          {hitlPrompt && (
            <div className="mt-4 p-3 rounded-xl bg-amber-950/40 border border-amber-500/40 flex items-center justify-between">
              <div className="text-xs text-amber-300 font-semibold">
                Graph Paused: Human-in-the-Loop approval breakpoint reached.
              </div>
              <a href="#hitl" className="badge badge-high text-xs cursor-pointer">Review in HITL Inbox</a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
