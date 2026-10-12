const rawBase = import.meta.env.VITE_API_BASE || '';
const API_BASE = rawBase ? `${rawBase.replace(/\/$/, '')}/api/v1` : '/api/v1';

export const DEMO_PRESETS = [
  {
    role: 'Admin',
    email: 'admin@insightops.ai',
    password: 'admin123',
    badge: 'Full Access',
    desc: 'Autonomous agent execution, competitor management & deletion.'
  },
  {
    role: 'Analyst',
    email: 'analyst@insightops.ai',
    password: 'analyst123',
    badge: 'Operator',
    desc: 'Trigger intelligence runs, human review inbox & report generation.'
  },
  {
    role: 'Viewer',
    email: 'viewer@insightops.ai',
    password: 'viewer123',
    badge: 'Read Only',
    desc: 'Executive dashboard, intelligence vault & metrics viewing.'
  }
];

let authToken = localStorage.getItem('insightops_token') || '';
let currentUser = null;
try {
  const savedUser = localStorage.getItem('insightops_user');
  if (savedUser) {
    currentUser = JSON.parse(savedUser);
  }
} catch (e) {
  currentUser = null;
}

export const authFetch = async (url, options = {}) => {
  const token = localStorage.getItem('insightops_token');
  if (!token) {
    throw new Error('Authentication required');
  }

  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
    ...(options.headers || {})
  };

  const res = await fetch(`${API_BASE}${url}`, { ...options, headers });

  if (res.status === 401) {
    localStorage.removeItem('insightops_token');
    localStorage.removeItem('insightops_user');
    authToken = '';
    currentUser = null;
    window.dispatchEvent(new CustomEvent('auth:unauthorized'));
    const errorBody = await res.json().catch(() => ({ detail: 'Session expired. Please sign in again.' }));
    throw new Error(errorBody.detail || 'Session expired');
  }

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorBody.detail || 'API request failed');
  }

  return res.json();
};

export const api = {
  // Authentication
  getToken: () => localStorage.getItem('insightops_token'),
  getUser: () => {
    try {
      const saved = localStorage.getItem('insightops_user');
      return saved ? JSON.parse(saved) : null;
    } catch (e) {
      return null;
    }
  },
  getRole: () => {
    const u = api.getUser();
    return u?.role || null;
  },

  login: async (email, password) => {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: email, password })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Login failed' }));
      throw new Error(err.detail || 'Incorrect email or password');
    }

    const data = await res.json();
    authToken = data.access_token;
    currentUser = {
      email,
      full_name: data.full_name,
      role: data.role
    };

    localStorage.setItem('insightops_token', data.access_token);
    localStorage.setItem('insightops_user', JSON.stringify(currentUser));
    return currentUser;
  },

  register: async ({ full_name, email, password, role = 'Viewer' }) => {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ full_name, email, password, role })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Registration failed' }));
      throw new Error(err.detail || 'Registration failed');
    }

    const data = await res.json();
    authToken = data.access_token;
    currentUser = {
      email,
      full_name: data.full_name,
      role: data.role
    };

    localStorage.setItem('insightops_token', data.access_token);
    localStorage.setItem('insightops_user', JSON.stringify(currentUser));
    return currentUser;
  },

  logout: () => {
    authToken = '';
    currentUser = null;
    localStorage.removeItem('insightops_token');
    localStorage.removeItem('insightops_user');
  },

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
  triggerAgentRun: (competitor_id, target_url, user_query, force_refresh = false) => 
    authFetch('/agent/run', {
      method: 'POST',
      body: JSON.stringify({ competitor_id, target_url, user_query, force_refresh })
    }),

  connectSSE: async (jobId, onEvent, onError) => {
    let streamUrl = `${API_BASE}/agent/stream/${jobId}`;
    try {
      const res = await authFetch(`/agent/stream-token/${jobId}`, { method: 'POST' });
      if (res?.stream_token) {
        streamUrl += `?token=${encodeURIComponent(res.stream_token)}`;
      }
    } catch (e) {
      console.warn("Could not fetch stream token, fallback to direct stream:", e);
    }

    const eventSource = new EventSource(streamUrl);
    
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
