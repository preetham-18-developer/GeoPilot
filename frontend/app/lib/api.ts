const rawApi = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
export const API_BASE = rawApi.replace(/\/api\/v1\/?$/, '').replace(/\/$/, '');

function getToken(): string {
  if (typeof window === 'undefined') return '';
  return (
    localStorage.getItem('token') ||
    localStorage.getItem('access_token') ||
    sessionStorage.getItem('token') ||
    ''
  );
}

export async function apiGet(path: string) {
  const token = getToken();
  const userId = typeof window !== 'undefined' ? (localStorage.getItem('userId') || '00000000-0000-4000-a000-000000000001') : '';
  const authVal = token ? `Bearer ${token}` : (userId ? `Bearer mock-${userId}` : '');
  
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 30000);
  
  try {
    console.log(`[AIVOP API] GET Request: ${API_BASE}${path}`);
    const response = await fetch(`${API_BASE}${path}`, {
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': authVal
      }
    });
    
    clearTimeout(timeout);
    
    if (response.status === 401) {
      console.warn(`[AIVOP API] Unauthorized (401), redirecting to /login`);
      window.location.href = '/login';
      return null;
    }
    
    if (!response.ok) {
      console.error(`[AIVOP API] GET Failed: ${API_BASE}${path} - Status: ${response.status}`);
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Error ${response.status}`);
    }
    
    return response.json();
    
  } catch (err: any) {
    clearTimeout(timeout);
    if (err.name === 'AbortError') {
      throw new Error('Request timeout - server may be waking up');
    }
    throw err;
  }
}

// All backend route paths in one place
export const ROUTES = {
  questions: (projectId: string) =>
    `/api/v1/analysis/questions/${projectId}`,
  keywords: (projectId: string) =>
    `/api/v1/analysis/keywords/${projectId}`,
  results: (projectId: string) =>
    `/api/v1/analysis/results/${projectId}`,
  facts: (projectId: string) =>
    `/api/v1/analysis/facts/${projectId}`,
  projects: {
    list: () => `/api/v1/projects`,
    single: (id: string) => `/api/v1/projects/${id}`,
    analyze: () => `/api/v1/analysis/run`,
  }
};
