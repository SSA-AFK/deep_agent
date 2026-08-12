import type { TaskState } from "../api/types";

/** 任务模式：普通快速对话 / 深度研究工作流 */
export type TaskMode = "quick" | "research";

/**
 * 单个研究会话的完整状态。
 *
 * 设计意图：
 * - 前端是会话的 SSoT（后端暂无 list_sessions API），通过 localStorage 持久化。
 * - 每个 Session = 一个研究任务，拥有独立的 threadId、任务状态、显示状态。
 * - 会话切换是"纯前端行为"——仅恢复 UI 状态；若要重新拉取后端快照，由组件层通过 threadId 触发。
 */
export interface ResearchSession {
  /** 前端生成的稳定会话 ID（与任务 thread_id 区分，后者在提交后才分配或复用） */
  id: string;
  /** 可选的后端 thread_id；未提交任务时为 null */
  threadId: string | null;
  /** 任务模式：quick 直接模型单答；research 走计划确认 → 多 Agent → 报告 */
  mode: TaskMode;
  /** 展示标题；取自用户首次提交的研究问题或预设占位 */
  title: string;
  /** 当前输入框内容（未提交的草稿） */
  draft: string;
  /** 已提交的研究问题文本（确认展示态） */
  submitted: string | null;
  /** 用户是否已确认执行计划（research 模式专用；quick 模式不使用） */
  confirmed: boolean;
  /** 研究是否已结束（成功/失败/取消皆算 completed） */
  completed: boolean;
  /** 后端返回的任务状态快照 */
  taskState: TaskState | null;
  /** 后端返回的任务结果文本 */
  taskResult: string | null;
  /** 用户最近收到的内联错误提示（会话隔离） */
  error: string | null;
  /** LLM 识别到信息不足后提出的澄清问题；null 表示未进入澄清态 */
  clarifyingQuestions: string[] | null;
  /** 用户对澄清问题的回答（与 clarifyingQuestions 同序对应） */
  clarifyAnswers: Record<number, string>;
  /** 会话创建时间（ms epoch） */
  createdAt: number;
  /** 会话最后活跃时间（创建、提交、收到结果皆更新） */
  updatedAt: number;
}

const STORAGE_KEY = "deep-search-pro:sessions:v1";
const ACTIVE_KEY = "deep-search-pro:active-session:v1";
const MAX_SESSIONS = 50;

function now() {
  return Date.now();
}

/** 生成稳定的前端会话 ID */
export function createSessionId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return `sess-${crypto.randomUUID()}`;
  return `sess-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

/** 创建一个全新的空白会话 */
export function createEmptySession(overrides: Partial<ResearchSession> = {}): ResearchSession {
  const id = overrides.id ?? createSessionId();
  const ts = now();
  return {
    id,
    threadId: null,
    mode: "research",
    title: "新的研究",
    draft: "",
    submitted: null,
    confirmed: false,
    completed: false,
    taskState: null,
    taskResult: null,
    error: null,
    clarifyingQuestions: null,
    clarifyAnswers: {},
    createdAt: ts,
    updatedAt: ts,
    ...overrides,
  };
}

/* ---------- 持久化层 ---------- */

/** 把 JSON 反序列化后的旧结构补齐到最新 schema（向后兼容） */
function hydrate(raw: Record<string, unknown>): ResearchSession {
  const base = createEmptySession();
  return {
    ...base,
    ...(raw as Partial<ResearchSession>),
    // mode 是 v1 存储里可能没有的新字段：未迁移会话默认 research（和之前行为一致）
    mode: (raw.mode as TaskMode | undefined) === "quick" ? "quick" : "research",
    clarifyingQuestions: Array.isArray(raw.clarifyingQuestions)
      ? (raw.clarifyingQuestions as string[]).filter((q) => typeof q === "string")
      : null,
    clarifyAnswers:
      raw.clarifyAnswers && typeof raw.clarifyAnswers === "object"
        ? (raw.clarifyAnswers as Record<number, string>)
        : {},
  } as ResearchSession;
}

export function loadAllSessions(): Record<string, ResearchSession> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === "object") {
      const result: Record<string, ResearchSession> = {};
      for (const [id, value] of Object.entries(parsed)) {
        if (value && typeof value === "object") result[id] = hydrate(value as Record<string, unknown>);
      }
      return result;
    }
  } catch {
    /* 损坏或禁用存储时静默降级为内存态 */
  }
  return {};
}

export function saveAllSessions(sessions: Record<string, ResearchSession>): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
  } catch {
    /* 存储失败（例如隐私模式、配额用尽）时不抛错，保持当前会话可用 */
  }
}

export function loadActiveSessionId(): string | null {
  try {
    return localStorage.getItem(ACTIVE_KEY);
  } catch {
    return null;
  }
}

export function saveActiveSessionId(id: string | null): void {
  try {
    if (id) localStorage.setItem(ACTIVE_KEY, id);
    else localStorage.removeItem(ACTIVE_KEY);
  } catch {
    /* 忽略存储失败 */
  }
}

/* ---------- 纯函数：会话集合操作 ---------- */

/** 新增会话；超过 MAX_SESSIONS 时淘汰最旧（按 updatedAt） */
export function addSession(
  sessions: Record<string, ResearchSession>,
  session: ResearchSession
): Record<string, ResearchSession> {
  const next = { ...sessions, [session.id]: session };
  const ids = Object.keys(next);
  if (ids.length <= MAX_SESSIONS) return next;
  const sorted = ids
    .map((id) => next[id])
    .sort((a, b) => b.updatedAt - a.updatedAt)
    .slice(0, MAX_SESSIONS);
  const trimmed: Record<string, ResearchSession> = {};
  for (const s of sorted) trimmed[s.id] = s;
  return trimmed;
}

export function updateSession(
  sessions: Record<string, ResearchSession>,
  id: string,
  patch: Partial<ResearchSession>
): Record<string, ResearchSession> {
  const current = sessions[id];
  if (!current) return sessions;
  return { ...sessions, [id]: { ...current, ...patch, updatedAt: now() } };
}

export function deleteSession(
  sessions: Record<string, ResearchSession>,
  id: string
): Record<string, ResearchSession> {
  const next = { ...sessions };
  delete next[id];
  return next;
}

/** 按更新时间倒序的会话数组，用于侧边栏与 Tab 展示 */
export function toOrderedList(sessions: Record<string, ResearchSession>): ResearchSession[] {
  return Object.values(sessions).sort((a, b) => b.updatedAt - a.updatedAt);
}

/* ---------- 标题与时间分组辅助 ---------- */

const MAX_TITLE_LEN = 28;

/**
 * 从用户输入生成会话标题。
 * - 优先取提交的研究问题；否则取草稿；否则"新的研究"。
 * - 截断到 MAX_TITLE_LEN，避免历史记录条过宽。
 */
export function deriveTitle(submitted: string | null, draft: string | null, fallback = "新的研究"): string {
  const raw = submitted?.trim() || draft?.trim();
  if (!raw) return fallback;
  const compact = raw.replace(/\s+/g, " ").trim();
  if (compact.length <= MAX_TITLE_LEN) return compact;
  return compact.slice(0, MAX_TITLE_LEN - 1) + "…";
}

/**
 * 将会话按相对时间分组，用于侧边栏"今天 / 昨天 / 7 天前 / 更早"。
 */
export function groupByRelativeTime(
  list: ResearchSession[]
): Array<{ label: string; items: ResearchSession[] }> {
  const todayStart = new Date();
  todayStart.setHours(0, 0, 0, 0);
  const todayMs = todayStart.getTime();
  const oneDay = 24 * 60 * 60 * 1000;

  const groups = new Map<string, ResearchSession[]>();
  for (const session of list) {
    const ts = session.updatedAt;
    let key: string;
    if (ts >= todayMs) key = "今天";
    else if (ts >= todayMs - oneDay) key = "昨天";
    else if (ts >= todayMs - 7 * oneDay) key = "7 天前";
    else key = "更早";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(session);
  }

  // 稳定输出顺序
  const order = ["今天", "昨天", "7 天前", "更早"];
  return order
    .map((label) => ({ label, items: groups.get(label) ?? [] }))
    .filter((g) => g.items.length > 0);
}
