const API_BASE = '/api/v1';

let authToken = localStorage.getItem('insightops_token') || '';
let currentUserRole = localStorage.getItem('insightops_role') || 'Admin';

export const setAuthRole = async (role) => {
  currentUserRole = role;
  localStorage.setItem('insightops_role', role);
  // Auto-authenticate as chosen demo role (Admin, Analyst, Viewer)
  const emailMap = {
    Admin: 'admin@insightops.ai',
    Analyst: 'analyst@insightops.ai',
    Viewer: 'viewer@insightops.ai'
  };
  const passwordMap = {
    Admin: 'admin123',
    Analyst: 'analyst123',
    Viewer: 'viewer123'
  };

  try {
    const formData = new URLSearchParams();
    formData.append('username', emailMap[role]);
    formData.append('password', passwordMap[role]);

    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData
    });

    if (res.ok) {
      const data = await res.json();
      authToken = data.access_token;
      localStorage.setItem('insightops_token', authToken);
      return data;
    }
  } catch (err) {
    console.error("Auth role switch error:", err);
  }
};

const authFetch = async (url, options = {}) => {
  if (!authToken) {
    await setAuthRole(currentUserRole);
  }

  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${authToken}`,
    ...(options.headers || {})
  };

  let res = await fetch(`${API_BASE}${url}`, { ...options, headers });

  if (res.status === 401) {
    // Retry login token
    await setAuthRole(currentUserRole);
    headers['Authorization'] = `Bearer ${authToken}`;
    res = await fetch(`${API_BASE}${url}`, { ...options, headers });
  }

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorBody.detail || 'API request failed');
  }

  return res.json();
};

export const api = {
  getRole: () => currentUserRole,
  setRole: setAuthRole,

  // Analytics
  getAnalytics: () => authFetch('/analytics/overview'),

  // Alerts
  getAlerts: () => authFetch('/alerts'),
  markAlertRead: (id) => authFetch(`/alerts/${id}/read`, { method: 'POST' }),

  // Competitors CRUD
  getCompetitors: () => authFetch('/competitors'),
  createCompetitor: (data) => authFetch('/competitors', { method: 'POST', body: JSON.stringify(data) }),
  updateCompetitor: (id, data) => authFetch(`/competitors/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteCompetitor: (id) => authFetch(`/competitors/${id}`, { method: 'DELETE' }),

  // Agent Runs & Streaming
  triggerAgentRun: (competitor_id, target_url, user_query) => 
    authFetch('/agent/run', {
      method: 'POST',
      body: JSON.stringify({ competitor_id, target_url, user_query })
    }),

  connectSSE: (jobId, onEvent, onError) => {
    const eventSource = new EventSource(`${API_BASE}/agent/stream/${jobId}`);
    
    eventSource.onmessage = (e) => {
      try {
        const payload = JSON.parse(e.data);
        onEvent(payload);
        if (payload.step === 'finish' || payload.step === 'error') {
          eventSource.close();
        }
      } catch (err) {
        console.error("SSE parse error:", err);
      }
    };

    eventSource.onerror = (err) => {
      if (onError) onError(err);
      eventSource.close();
    };

    return eventSource;
  },

  // HITL Inbox & Approvals
  getPendingHITL: () => authFetch('/agent/pending'),
  resumeHITL: (thread_id, approved, feedback) => 
    authFetch(`/agent/resume/${thread_id}`, {
      method: 'POST',
      body: JSON.stringify({ approved, feedback })
    }),

  // Reports Vault & Export
  getReports: () => authFetch('/reports'),
  getReportDetail: (id) => authFetch(`/reports/${id}`),
  exportReportPDF: (id) => window.open(`${API_BASE}/reports/${id}/export`, '_blank')
};
