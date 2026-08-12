import type { ClarifyResponse, HealthResponse, TaskMode, TaskSnapshot } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  let response: Response;
  try {
    response = await fetch(url, init);
  } catch (error) {
    // 网络层失败：跨域 / 后端未启动 / 证书 / DNS
    // eslint-disable-next-line no-console
    console.warn(`[api] Network error on ${init?.method ?? "GET"} ${url}`, error);
    throw new Error("无法连接到后端服务，请确认后端是否启动、代理是否配置正确。");
  }
  if (!response.ok) {
    // HTTP 层失败
    // eslint-disable-next-line no-console
    console.warn(`[api] HTTP ${response.status} on ${init?.method ?? "GET"} ${url}`);
    switch (response.status) {
      case 404:
        throw new Error("接口不存在（HTTP 404）。请确认后端服务启动、或 Vite 代理 /api 是否生效。");
      case 409:
        throw new Error("任务已存在或状态冲突（HTTP 409），请稍后重试或新建会话。");
      case 413:
        throw new Error("上传内容过大（HTTP 413），请缩小文件或分多次上传。");
      case 415:
        throw new Error("不支持的文件类型（HTTP 415），请使用 txt / md / pdf / docx / csv / xlsx。");
      case 422:
        throw new Error("参数校验失败（HTTP 422），请检查输入内容。");
      case 500:
      case 502:
      case 503:
      case 504:
        throw new Error(`后端服务异常（HTTP ${response.status}），请稍后重试。`);
      default:
        throw new Error(`请求失败（HTTP ${response.status}），请检查服务状态后重试。`);
    }
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<HealthResponse>("/api/health"),
  task: (threadId: string) => request<TaskSnapshot>(`/api/tasks/${threadId}`),
  createTask: (query: string, threadId: string) => request<{ thread_id: string }>("/api/task", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query, thread_id: threadId }) }),
  chat: (query: string, threadId: string) => request<{ thread_id: string; status: string }>("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query, thread_id: threadId }) }),
  clarify: (query: string, mode: TaskMode) => request<ClarifyResponse>("/api/clarify", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query, mode }) }),
  upload: (threadId: string, files: File[]) => {
    const body = new FormData();
    body.append("thread_id", threadId);
    files.forEach((file) => body.append("files", file));
    return request<{ files: string[] }>("/api/upload", { method: "POST", body });
  },
  confirm: (threadId: string) => request(`/api/tasks/${threadId}/confirm`, { method: "POST" }),
  cancel: (threadId: string) => request(`/api/tasks/${threadId}/cancel`, { method: "POST" }),
  feedback: (threadId: string, helpful: boolean, reason?: string) => request(`/api/tasks/${threadId}/feedback`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ helpful, reason }) }),
  recordExport: (threadId: string) => request(`/api/tasks/${threadId}/export`, { method: "POST" }),
  files: (threadId: string) => request<{ files: Array<{ name: string; path: string }> }>(`/api/files?path=${encodeURIComponent(`session_${threadId}`)}`),
  downloadUrl: (path: string) => `${API_BASE}/api/download?path=${encodeURIComponent(path)}`,
};
