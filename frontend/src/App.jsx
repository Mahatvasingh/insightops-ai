import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import AuthModal from './components/AuthModal';
import ExecutiveDashboard from './pages/ExecutiveDashboard';
import CompetitorTracker from './pages/CompetitorTracker';
import WarRoom from './pages/WarRoom';
import HumanReview from './pages/HumanReview';
import IntelligenceVault from './pages/IntelligenceVault';
import { api } from './api';

export default function App() {
  const [currentUser, setCurrentUser] = useState(() => api.getUser());
  const [isAuthOpen, setIsAuthOpen] = useState(() => !api.getUser());
  const [activeTab, setActiveTab] = useState('dashboard');
  const [selectedCompForWarRoom, setSelectedCompForWarRoom] = useState(null);
  const [pendingCount, setPendingCount] = useState(0);

  // Sync unauthorized events (e.g. expired tokens)
  useEffect(() => {
    const handleUnauthorized = () => {
      setCurrentUser(null);
      setIsAuthOpen(true);
    };
    window.addEventListener('auth:unauthorized', handleUnauthorized);
    return () => window.removeEventListener('auth:unauthorized', handleUnauthorized);
  }, []);

  const fetchPendingCount = async () => {
    if (!currentUser) return;
    try {
      const pending = await api.getPendingHITL();
      setPendingCount(pending.length);
    } catch (err) {
      // Ignore background auth retry errors
    }
  };

  useEffect(() => {
    if (currentUser) {
      fetchPendingCount();
      const interval = setInterval(fetchPendingCount, 10000);
      return () => clearInterval(interval);
    } else {
      setPendingCount(0);
    }
  }, [currentUser]);

  const handleAuthSuccess = (user) => {
    setCurrentUser(user);
    setIsAuthOpen(false);
  };

  const handleLogout = () => {
    api.logout();
    setCurrentUser(null);
    setIsAuthOpen(true);
  };

  const handleTriggerRunFromTracker = (comp) => {
    setSelectedCompForWarRoom(comp);
    setActiveTab('warroom');
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Navbar 
        currentUser={currentUser} 
        onLogout={handleLogout} 
        onOpenAuth={() => setIsAuthOpen(true)} 
      />

      {/* Show AuthModal if user is not authenticated or explicitly opens auth */}
      {(!currentUser || isAuthOpen) && (
        <AuthModal onAuthSuccess={handleAuthSuccess} />
      )}

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
