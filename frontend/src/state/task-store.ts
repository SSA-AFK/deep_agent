import type { TaskEvent, TaskSnapshot, TaskState } from "../api/types";

export interface TaskView { threadId: string; state: TaskState; sequence: number; events: TaskEvent[]; result: string | null; }

export function fromSnapshot(snapshot: TaskSnapshot): TaskView {
  return { threadId: snapshot.thread_id, state: snapshot.state, sequence: snapshot.sequence, events: snapshot.events, result: snapshot.result };
}

export function applyEvent(task: TaskView, event: TaskEvent): TaskView {
  if (event.thread_id !== task.threadId || event.sequence <= task.sequence) return task;
  const state = event.type === "task_status" && typeof event.data.state === "string" ? event.data.state as TaskState : task.state;
  return { ...task, state, sequence: event.sequence, events: [...task.events, event].slice(-100) };
}
