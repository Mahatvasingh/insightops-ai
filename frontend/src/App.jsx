import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import ExecutiveDashboard from './pages/ExecutiveDashboard';
import CompetitorTracker from './pages/CompetitorTracker';
import WarRoom from './pages/WarRoom';
import HumanReview from './pages/HumanReview';
import IntelligenceVault from './pages/IntelligenceVault';
import { api } from './api';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [currentRole, setCurrentRole] = useState(api.getRole());
  const [selectedCompForWarRoom, setSelectedCompForWarRoom] = useState(null);
  const [pendingCount, setPendingCount] = useState(0);

  const fetchPendingCount = async () => {
    try {
      const pending = await api.getPendingHITL();
      setPendingCount(pending.length);
    } catch (err) {
      // Ignore background auth retry errors
    }
  };

  useEffect(() => {
    fetchPendingCount();
    const interval = setInterval(fetchPendingCount, 10000);
    return () => clearInterval(interval);
  }, [currentRole]);

  const handleTriggerRunFromTracker = (comp) => {
    setSelectedCompForWarRoom(comp);
    setActiveTab('warroom');
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Navbar currentRole={currentRole} onRoleChange={setCurrentRole} />

      <div className="flex-1 flex max-w-[1600px] w-full mx-auto">
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} pendingCount={pendingCount} />

        <main className="flex-1 p-6 overflow-y-auto">
          {activeTab === 'dashboard' && <ExecutiveDashboard onSelectTab={setActiveTab} />}
          {activeTab === 'competitors' && <CompetitorTracker onTriggerRun={handleTriggerRunFromTracker} />}
          {activeTab === 'warroom' && <WarRoom selectedCompetitor={selectedCompForWarRoom} />}
          {activeTab === 'hitl' && <HumanReview />}
          {activeTab === 'reports' && <IntelligenceVault />}
        </main>
      </div>
    </div>
  );
}
