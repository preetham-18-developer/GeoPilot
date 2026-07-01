const rawBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
export const API_BASE = rawBase.endsWith('/api/v1') ? rawBase.slice(0, -7) : rawBase;

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
  
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 30000);
  
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
      }
    });
    
    clearTimeout(timeout);
    
    if (response.status === 401) {
      window.location.href = '/login';
      return null;
    }
    
    if (!response.ok) {
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
