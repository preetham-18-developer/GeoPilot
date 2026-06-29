/**
 * Centralized API configuration for AIVOP.
 * All components must import from here — never hardcode API_BASE.
 */

export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
export const API_VERSION = "v1";
export const DEFAULT_PAGE_SIZE = 10;

/**
 * Returns the Authorization header for the current workspace user.
 * This is the single source of truth for auth headers.
 */
export function authHeader(userId: string): Record<string, string> {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('token') || 
                  localStorage.getItem('access_token') ||
                  sessionStorage.getItem('token') || '';
    if (token) {
      return { Authorization: token.startsWith('Bearer ') ? token : `Bearer ${token}` };
    }
  }
  return { Authorization: `Bearer mock-${userId}` };
}

/**
 * Typed fetch wrapper that always includes auth headers and handles JSON.
 * Throws on non-OK responses with the API error message.
 */
export async function apiFetch<T = unknown>(
  path: string,
  userId: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...authHeader(userId),
      ...(options.headers as Record<string, string> | undefined),
    },
  });

  if (!res.ok) {
    let message = `API error ${res.status}`;
    try {
      const err = await res.json();
      message = err.detail ?? message;
    } catch {
      // ignore parse error
    }
    throw new Error(message);
  }

  return res.json() as Promise<T>;
}

/**
 * Typed fetch wrapper for text responses (e.g. markdown reports).
 */
export async function apiFetchText(
  path: string,
  userId: string
): Promise<string> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: authHeader(userId),
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.text();
}

/** Statuses that represent an active pipeline run */
export const RUNNING_STATUSES = [
  "pending",
  "queued",
  "crawling",
  "extracting",
  "verifying",
  "analyzing",
  "compiling",
] as const;

export type RunStatus = (typeof RUNNING_STATUSES)[number] | "completed" | "failed";

/** Progress % mapped to each pipeline status */
export const PROGRESS_MAP: Record<string, number> = {
  queued: 5,
  crawling: 20,
  extracting: 40,
  verifying: 60,
  analyzing: 80,
  compiling: 95,
};

/** ETA string mapped to each pipeline status */
export const ETA_MAP: Record<string, string> = {
  queued: "150s",
  crawling: "120s",
  extracting: "90s",
  verifying: "60s",
  analyzing: "30s",
  compiling: "10s",
};

/** Default demo users for the workspace switcher */
export const DEMO_USERS = [
  { id: "00000000-0000-4000-a000-000000000001", label: "Preetham (User 1)" },
  { id: "00000000-0000-4000-a000-000000000002", label: "David Miller (User 2)" },
  { id: "00000000-0000-4000-a000-000000000003", label: "Sarah Connor (User 3)" },
] as const;

export const DEFAULT_USER_ID = DEMO_USERS[0].id;
