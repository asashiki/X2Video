import type { MemoryCandidate, RunRow, Snapshot } from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(body.detail ?? `HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{
    ok: boolean;
    version: string;
    mode: string;
    live_ready?: boolean;
    source_provider?: string | null;
    auth_logged_in?: boolean;
    checks: Record<string, boolean>;
  }>("/api/health"),
  runs: () => request<{ items: RunRow[] }>("/api/runs"),
  run: (id: string) => request<Snapshot>(`/api/runs/${id}`),
  createRun: (payload: Record<string, unknown>) =>
    request<Snapshot>("/api/runs", { method: "POST", body: JSON.stringify(payload) }),
  start: (id: string, background = true) =>
    request<Snapshot | { run_id: string; worker_pid: number }>(`/api/runs/${id}/start`, {
      method: "POST",
      body: JSON.stringify({ background }),
    }),
  action: (id: string, action: string, payload: Record<string, unknown> = {}) =>
    request<Snapshot>(`/api/runs/${id}/actions`, {
      method: "POST",
      body: JSON.stringify({ action, payload }),
    }),
  replay: (id: string) => request<{ run_id: string; event_count: number }>(`/api/runs/${id}/replay`),
  memories: () => request<{ items: MemoryCandidate[] }>("/api/memories"),
  memoryStatus: (id: string, status: "approved" | "rejected") =>
    request<MemoryCandidate>(`/api/memories/${id}`, {
      method: "POST",
      body: JSON.stringify({ status }),
    }),
};
