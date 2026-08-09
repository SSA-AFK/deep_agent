export type TaskState = "planning" | "waiting_confirmation" | "running" | "succeeded" | "failed" | "cancelled";

export interface PublicError { code: string; message: string; source: string; user_action?: string; retryable: boolean; }
export interface TaskEvent { version: 1; sequence: number; type: string; thread_id: string; timestamp: string; data: Record<string, unknown>; }
export interface TaskSnapshot { thread_id: string; state: TaskState; sequence: number; result: string | null; error: PublicError | null; events: TaskEvent[]; }
export interface HealthResponse { overall: "ready" | "blocked"; services: Record<string, { status: string; mode: string }>; error?: PublicError; }
