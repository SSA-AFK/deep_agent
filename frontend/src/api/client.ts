import type { HealthResponse, TaskSnapshot } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) throw new Error(`Request failed (${response.status})`);
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<HealthResponse>("/api/health"),
  task: (threadId: string) => request<TaskSnapshot>(`/api/tasks/${threadId}`),
  createTask: (query: string, threadId: string) => request<{ thread_id: string }>("/api/task", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query, thread_id: threadId }) }),
  upload: (threadId: string, files: File[]) => {
    const body = new FormData();
    body.append("thread_id", threadId);
    files.forEach((file) => body.append("files", file));
    return request<{ files: string[] }>("/api/upload", { method: "POST", body });
  },
  confirm: (threadId: string) => request(`/api/tasks/${threadId}/confirm`, { method: "POST" }),
  cancel: (threadId: string) => request(`/api/tasks/${threadId}/cancel`, { method: "POST" }),
};
