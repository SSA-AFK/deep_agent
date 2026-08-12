import { ArrowUp, FileSearch, FileText, MessageCircleQuestion, Paperclip, Plus, Search, Sparkles, Zap, Ellipsis, X } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { PlanMessage } from "./components/PlanMessage";
import { AgentRunMessage } from "./components/AgentRunMessage";
import { ReportMessage } from "./components/ReportMessage";
import { ServiceStatusMenu } from "./components/ServiceStatusMenu";
import { ClarifyMessage } from "./components/ClarifyMessage";
import { QuickAnswerMessage } from "./components/QuickAnswerMessage";
import { api } from "./api/client";
import { TaskSocket } from "./api/socket";
import type { TaskMode, TaskState } from "./api/types";
import {
  ResearchSession,
  addSession,
  createEmptySession,
  deleteSession,
  deriveTitle,
  groupByRelativeTime,
  loadActiveSessionId,
  loadAllSessions,
  saveActiveSessionId,
  saveAllSessions,
  toOrderedList,
  updateSession,
} from "./state/session-store";

const STARTERS = [
  "比较 Coze 与其他 Agent 平台",
  "为 AI 产品实习准备行业研究",
  "根据我的资料生成研究提纲",
];

/** 保证至少有一个会话；并对不存在的激活 id 做纠正 */
function ensureInitialState(): {
  sessions: Record<string, ResearchSession>;
  activeId: string;
} {
  const stored = loadAllSessions();
  const storedActive = loadActiveSessionId();
  const ids = Object.keys(stored);

  if (ids.length === 0) {
    const seed = createEmptySession();
    const next = addSession({}, seed);
    saveAllSessions(next);
    saveActiveSessionId(seed.id);
    return { sessions: next, activeId: seed.id };
  }
  // 纠正无效激活 id
  let activeId = storedActive && stored[storedActive] ? storedActive : ids[0];
  if (activeId !== storedActive) saveActiveSessionId(activeId);
  return { sessions: stored, activeId };
}

export default function App() {
  const [{ sessions, activeId }, setState] = useState(ensureInitialState);
  const [attachment, setAttachment] = useState<File | null>(null);
  // 流式文本：瞬态（不落 localStorage / session-store），按 sessionId 分桶；
  // 切换会话、提交新任务、任务终态都会清掉对应桶。
  const [partialBySession, setPartialBySession] = useState<Record<string, string>>({});

  const list = useMemo(() => toOrderedList(sessions), [sessions]);
  const active = sessions[activeId] ?? list[0] ?? createEmptySession();
  const groups = useMemo(() => groupByRelativeTime(list), [list]);
  // 顶部最多展示前 5 个最近会话为 Tab，保持多 Tab 与新建交互一致
  const tabs = useMemo(() => list.slice(0, 5), [list]);

  // —— taskPartial / setActivePartial 必须在 active 声明之后 ——
  const taskPartial = partialBySession[active.id] ?? "";
  const setActivePartial = useCallback(
    (value: string | ((prev: string) => string)) => {
      setPartialBySession((prev) => {
        const current = prev[active.id] ?? "";
        const next = typeof value === "function" ? value(current) : value;
        if (next === current) return prev;
        return { ...prev, [active.id]: next };
      });
    },
    [active.id]
  );

  /* ========== 统一的状态写入口：自动持久化 ========== */
  const commit = useCallback(
    (nextSessions: Record<string, ResearchSession>, nextActive: string = activeId) => {
      saveAllSessions(nextSessions);
      if (nextSessions[nextActive]) saveActiveSessionId(nextActive);
      else {
        // 激活 id 失效，fallback 到有序列表第一条
        const fallback = toOrderedList(nextSessions)[0];
        if (fallback) saveActiveSessionId(fallback.id);
        else saveActiveSessionId(null);
      }
      setState({ sessions: nextSessions, activeId: nextSessions[nextActive] ? nextActive : (toOrderedList(nextSessions)[0]?.id ?? nextActive) });
    },
    [activeId]
  );

  const patchActive = useCallback(
    (patch: Partial<ResearchSession>) => {
      const next = updateSession(sessions, active.id, patch);
      // 标题在 submitted/draft 改变时重新推导
      if (patch.submitted !== undefined || patch.draft !== undefined) {
        const current = next[active.id];
        if (current) {
          next[active.id] = {
            ...current,
            title: deriveTitle(
              patch.submitted ?? current.submitted,
              patch.draft ?? current.draft,
              current.title
            ),
          };
        }
      }
      commit(next);
    },
    [sessions, active.id, commit]
  );

  /* ========== 新建 / 切换 / 删除会话 ========== */
  const newSession = useCallback(() => {
    const session = createEmptySession();
    const next = addSession(sessions, session);
    commit(next, session.id);
    setAttachment(null);
  }, [sessions, commit]);

  const switchTo = useCallback(
    (id: string) => {
      if (id === active.id || !sessions[id]) return;
      commit(sessions, id);
      setAttachment(null); // 切换会话不共享附件草稿
    },
    [active.id, sessions, commit]
  );

  const closeSession = useCallback(
    (id: string) => {
      const trimmed = deleteSession(sessions, id);
      // 删除后至少保留一个会话，不足则补新建
      let next = trimmed;
      let fallbackActive: string;
      const remaining = toOrderedList(next);
      if (remaining.length === 0) {
        const seed = createEmptySession();
        next = addSession(next, seed);
        fallbackActive = seed.id;
      } else {
        fallbackActive = id === activeId ? remaining[0].id : activeId;
      }
      commit(next, fallbackActive);
    },
    [sessions, activeId, commit]
  );

  /* ========== 任务生命周期：仅对 active 的 threadId 建连/轮询 ========== */
  useEffect(() => {
    const threadId = active.threadId;
    if (!threadId || import.meta.env.MODE === "test") return;
    const socket = new TaskSocket(threadId, (event) => {
      if (event.type === "task_status" && typeof event.data.state === "string") {
        const nextState = event.data.state as TaskState;
        const nextResult = typeof event.data.result === "string" ? event.data.result : undefined;
        // 仅当会话仍为 active 时写回，避免切换会话后过时消息串号
        setState((prev) => {
          if (prev.activeId !== active.id || !prev.sessions[active.id]) return prev;
          const patch: Partial<ResearchSession> = { taskState: nextState };
          if (nextResult !== undefined) patch.taskResult = nextResult;
          if (nextState === "succeeded" || nextState === "failed" || nextState === "cancelled") {
            patch.completed = true;
          }
          const updated = updateSession(prev.sessions, active.id, patch);
          saveAllSessions(updated);
          return { ...prev, sessions: updated };
        });
        // 进入终态后：如果有最终 result，就把流式 partial 让位给正式持久化文本
        if (
          nextState === "succeeded" ||
          nextState === "failed" ||
          nextState === "cancelled"
        ) {
          setPartialBySession((prev) => {
            if (!prev[active.id]) return prev;
            const copy = { ...prev };
            delete copy[active.id];
            return copy;
          });
        }
      } else if (event.type === "task_delta") {
        const delta = typeof event.data.delta === "string" ? event.data.delta : "";
        const partial =
          typeof event.data.partial === "string" ? event.data.partial : undefined;
        // 同样只对当前 active 生效，防止串号
        setState((prev) => {
          if (prev.activeId !== active.id) return prev;
          // 仍在 running 或 succeeded 之前：用 setState 回调只是拿 prev 的身份校验，不需要改 sessions
          return prev;
        });
        setPartialBySession((prev) => {
          // 仅当会话就是当前 active 才写，避免串号
          const current = prev[active.id] ?? "";
          const next = partial !== undefined ? partial : current + delta;
          if (next === current) return prev;
          return { ...prev, [active.id]: next };
        });
      }
    });
    socket.connect();
    const timer = window.setInterval(() => {
      api
        .task(threadId)
        .then((snapshot) => {
          setState((prev) => {
            if (prev.activeId !== active.id || !prev.sessions[active.id]) return prev;
            const patch: Partial<ResearchSession> = {
              taskState: snapshot.state,
            };
            if (typeof snapshot.result === "string") patch.taskResult = snapshot.result;
            if (
              snapshot.state === "succeeded" ||
              snapshot.state === "failed" ||
              snapshot.state === "cancelled"
            ) {
              patch.completed = true;
            }
            const updated = updateSession(prev.sessions, active.id, patch);
            saveAllSessions(updated);
            return { ...prev, sessions: updated };
          });
        })
        .catch(() => undefined);
    }, 3000);
    return () => {
      window.clearInterval(timer);
      socket.close();
    };
    // active.id 或其 threadId 变化才重建 ws / 轮询
  }, [active.id, active.threadId]);

  /* ========== 任务生命周期：提交链路 ========== */

  /** 把用户已填写的澄清答案拼回原 query，作为最终执行 prompt 提交给后端。 */
  function buildQueryWithAnswers(
    baseQuery: string,
    questions: string[] | null,
    answers: Record<number, string> | null
  ) {
    const trimmed = baseQuery.trim();
    if (!questions || questions.length === 0 || !answers) return trimmed;
    const filled = questions
      .map((q, i) => ({ q, a: (answers[i] ?? "").trim() }))
      .filter(({ a }) => a.length > 0);
    if (filled.length === 0) return trimmed;
    const appendix =
      "\n\n补充说明（澄清问答）：\n" +
      filled.map(({ q, a }, idx) => `${idx + 1}. ${q}\n   答：${a}`).join("\n");
    return trimmed + appendix;
  }

  /** 真正执行请求（在 clarify 之后或不需要 clarify 时调用）。
   *  research 模式 → /api/task（生成计划→等待确认）
   *  quick 模式 → /api/chat（直接 RUNNING + 流式返回）
   */
  const executeRequest = useCallback(
    async (opts?: { finalQuery?: string }) => {
      const query = (opts?.finalQuery ?? active.draft).trim();
      const mode: TaskMode = active.mode ?? "research";
      if (!query) return;
      const nextThreadId = active.threadId ?? `test-${active.id.replace(/^sess-/, "")}`;
      try {
        if (attachment) await api.upload(nextThreadId, [attachment]);

        // 提交前重置流式 partial 和上次结果
        setPartialBySession((prev) => {
          if (!prev[active.id]) return prev;
          const copy = { ...prev };
          delete copy[active.id];
          return copy;
        });

        if (mode === "quick") {
          await api.chat(query, nextThreadId);
          patchActive({
            mode: "quick",
            threadId: nextThreadId,
            submitted: query,
            taskState: "running",
            taskResult: null,
            confirmed: true, // quick 模式没有「计划确认」，直接当作已确认
            completed: false,
            error: null,
            clarifyingQuestions: null,
            clarifyAnswers: {},
          });
        } else {
          await api.createTask(query, nextThreadId);
          patchActive({
            mode: "research",
            threadId: nextThreadId,
            submitted: query,
            taskState: "waiting_confirmation",
            taskResult: null,
            confirmed: false,
            completed: false,
            error: null,
            clarifyingQuestions: null,
            clarifyAnswers: {},
          });
        }
        setAttachment(null);
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "任务创建失败，请检查服务状态后重试。";
        patchActive({ error: message });
      }
    },
    [active, attachment, patchActive]
  );

  /** 点击发送：
   *  1) 如果已有澄清问题 → 视为继续执行（等同于 ClarifyMessage 的继续按钮）
   *  2) 否则先调 /api/clarify：信息足直接执行；不足则进入澄清态
   */
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const query = active.draft;
    if (!query.trim()) return;

    // 已经在澄清态 → 把 composer 的提交也视为「按当前答案继续执行」
    if (active.clarifyingQuestions && active.clarifyingQuestions.length > 0 && !active.submitted) {
      const finalQuery = buildQueryWithAnswers(
        query,
        active.clarifyingQuestions,
        active.clarifyAnswers
      );
      await executeRequest({ finalQuery });
      return;
    }

    try {
      const mode: TaskMode = active.mode ?? "research";
      const { questions } = await api.clarify(query.trim(), mode);
      if (!questions || questions.length === 0) {
        await executeRequest();
        return;
      }
      // 进入澄清态：问题列表存入 session，但尚未 submitted
      patchActive({
        mode,
        clarifyingQuestions: questions.slice(0, 3),
        clarifyAnswers: {},
        error: null,
      });
    } catch (error) {
      // 澄清接口失败 → 直接降级为按当前信息执行，不阻塞用户
      await executeRequest();
    }
  };

  const confirm = async () => {
    if (!active.threadId) return;
    try {
      await api.confirm(active.threadId);
      patchActive({ taskState: "running", confirmed: true, error: null });
    } catch (error) {
      const message = error instanceof Error ? error.message : "计划确认失败，请重试。";
      patchActive({ error: message });
    }
  };

  const setComposerMode = useCallback(
    (mode: TaskMode) => {
      patchActive({ mode });
    },
    [patchActive]
  );

  const proceedFromClarify = useCallback(async () => {
    const finalQuery = buildQueryWithAnswers(
      active.draft,
      active.clarifyingQuestions,
      active.clarifyAnswers
    );
    await executeRequest({ finalQuery });
  }, [active, executeRequest]);

  const skipClarify = useCallback(async () => {
    await executeRequest();
  }, [executeRequest]);

  const updateClarifyAnswer = useCallback(
    (index: number, value: string) => {
      const next: Record<number, string> = { ...(active.clarifyAnswers ?? {}), [index]: value };
      patchActive({ clarifyAnswers: next });
    },
    [active.clarifyAnswers, patchActive]
  );

  /* ========== 顶部 Tab 状态颜色：从任务状态映射 ========== */
  function tabStatusColor(s: ResearchSession): string {
    if (!s.submitted) return "#5d5fef"; // 空闲用品牌紫色
    switch (s.taskState) {
      case "running":
      case "planning":
        return "#16a34a"; // 进行中：绿
      case "succeeded":
        return "#1d4ed8"; // 成功：蓝
      case "failed":
        return "#dc2626"; // 失败：红
      case "waiting_confirmation":
        return "#d97706"; // 待确认：橙
      case "cancelled":
        return "#6b7280"; // 取消：灰
      default:
        return "#5d5fef";
    }
  }

  const hasClarifyState =
    !!active.clarifyingQuestions && active.clarifyingQuestions.length > 0 && !active.submitted;
  const showEmpty = !active.submitted && !hasClarifyState;

  const isRunning = active.taskState === "running" || active.taskState === "planning" || active.taskState === "waiting_confirmation";
  const isStreaming = isRunning && !!taskPartial;
  const displayResult = (active.taskResult ?? taskPartial) || null;
  const resultLabel = active.mode === "quick" ? "快速回答" : "研究报告";
  void resultLabel; // reserved for future UI hint; unused right now

  return (
    <main className="workbench">
      {/* ===== 顶部标签栏（多会话） ===== */}
      <header className="top-bar" role="tablist" aria-label="研究会话标签">
        <button
          type="button"
          className="tab-add-btn"
          onClick={newSession}
          title="新建研究标签 (新建会话)"
          aria-label="新建研究标签"
        >
          <Plus size={15} />
        </button>

        <div className="tabs">
          {tabs.map((tab) => {
            const isActive = tab.id === active.id;
            return (
              <div
                className={`tab-item ${isActive ? "active" : ""}`}
                role="tab"
                aria-selected={isActive}
                key={tab.id}
                onClick={() => switchTo(tab.id)}
                title={tab.title}
              >
                <span
                  className="tab-status"
                  aria-hidden
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    background: tabStatusColor(tab),
                  }}
                />
                <span style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", maxWidth: 180 }}>
                  {tab.title}
                </span>
                {tab.submitted && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      closeSession(tab.id);
                    }}
                    title="关闭会话"
                    aria-label="关闭会话"
                    style={{
                      background: "none",
                      border: "none",
                      color: "inherit",
                      cursor: "pointer",
                      padding: 0,
                      display: "inline-flex",
                      opacity: 0.6,
                    }}
                  >
                    <X size={10} />
                  </button>
                )}
              </div>
            );
          })}
        </div>

        <button type="button" className="tab-more" aria-label="更多操作">
          <Ellipsis size={16} />
        </button>
      </header>

      {/* ===== 主体：Sidebar + Conversation ===== */}
      <div className="main-layout">
        <aside className="sidebar" aria-label="研究历史">
          <div className="brand" title="Deep Search Pro">
            <span className="brand-orb" aria-hidden>
              <Search size={14} strokeWidth={2.5} />
            </span>
            <span>Deep Search Pro</span>
          </div>

          <button
            className="new-task"
            type="button"
            onClick={newSession}
            title="新建一项研究 (新建会话)"
          >
            <Plus size={16} strokeWidth={2.5} /> 新建研究
          </button>

          <div className="history-section">
            {groups.map((group) => (
              <div key={group.label} style={{ marginBottom: 6 }}>
                <p className="history-label">{group.label}</p>
                {group.items.map((s) => {
                  const isActive = s.id === active.id;
                  return (
                    <button
                      className="history-item"
                      type="button"
                      key={s.id}
                      onClick={() => switchTo(s.id)}
                      title={s.title}
                      style={
                        isActive
                          ? { background: "rgba(93, 95, 239, 0.08)", color: "#1f1f23", fontWeight: 600 }
                          : undefined
                      }
                    >
                      {s.title}
                    </button>
                  );
                })}
              </div>
            ))}
            {groups.length === 0 && (
              <p className="history-label" style={{ opacity: 0.6 }}>
                暂无历史记录
              </p>
            )}
          </div>
        </aside>

        <section className="conversation" aria-labelledby="page-title">
          <header>
            <div className="title-row">
              <span className="eyebrow">研究工作台</span>
              <ServiceStatusMenu />
            </div>
            <h1 id="page-title">从问题到可追溯结论</h1>
            <p>规划、检索、分析与来源都保留在同一条研究对话中。</p>
          </header>

          {active.error && (
            <p className="inline-error" role="alert">
              {active.error}
            </p>
          )}

          {showEmpty ? (
            <section className="empty-state" aria-label="开始新研究">
              <div className="orb-container" aria-hidden="true" />

              <div className="greeting-text">
                <h2>你好，研究者</h2>
                <h3>
                  今天要 <span>深入探究什么？</span>
                </h3>
              </div>

              <div className="empty-state-body">
                <FileText size={24} style={{ color: "#8e8ea0", opacity: 0.8 }} />
                <h4>普通对话 / 深度研究 二选一</h4>
                <p>下方输入框选择模式：快速问答（单模型）或 深度研究（多 Agent 检索与来源）。</p>
                <div className="starters">
                  {STARTERS.map((starter) => (
                    <button
                      key={starter}
                      type="button"
                      onClick={() => patchActive({ draft: starter })}
                    >
                      {starter}
                    </button>
                  ))}
                </div>
              </div>
            </section>
          ) : hasClarifyState ? (
            <>
              <article className="message user-message">
                <span>你的问题</span>
                <p>{active.draft}</p>
              </article>
              <ClarifyMessage
                questions={active.clarifyingQuestions}
                answers={active.clarifyAnswers ?? {}}
                onAnswerChange={updateClarifyAnswer}
                onProceed={proceedFromClarify}
                onSkip={skipClarify}
              />
            </>
          ) : (
            <>
              <article className="message user-message">
                <span>{active.mode === "quick" ? "你的问题" : "你的研究问题"}</span>
                <p>{active.submitted}</p>
              </article>

              {active.mode === "quick" ? (
                /* Quick 模式：没有计划确认、没有 AgentRun；直接渲染快速回答卡（支持流式） */
                <QuickAnswerMessage
                  result={displayResult}
                  threadId={active.threadId ?? ""}
                  streaming={isStreaming}
                />
              ) : active.completed || active.taskState === "succeeded" ? (
                active.threadId ? (
                  <ReportMessage result={displayResult ?? active.taskResult} threadId={active.threadId} />
                ) : null
              ) : active.confirmed || active.taskState === "running" ? (
                <>
                  <AgentRunMessage
                    onComplete={() => patchActive({ completed: true })}
                  />
                  {taskPartial && active.threadId && (
                    <ReportMessage
                      result={taskPartial}
                      threadId={active.threadId}
                      streaming
                    />
                  )}
                </>
              ) : (
                <PlanMessage
                  onConfirm={confirm}
                  onCancel={() =>
                    patchActive({
                      submitted: null,
                      confirmed: false,
                      completed: false,
                      threadId: null,
                      taskState: null,
                      taskResult: null,
                      clarifyingQuestions: null,
                      clarifyAnswers: {},
                    })
                  }
                />
              )}
            </>
          )}

          {/* ===== Composer 输入区（随当前会话 draft 联动） ===== */}
          <form className="composer" onSubmit={submit}>
            <label htmlFor="research-query">{active.mode === "quick" ? "快速问题" : "研究问题"}</label>
            <div className="input-row">
              {active.mode === "quick" ? (
                <Sparkles size={16} className="bolt-prefix" aria-hidden strokeWidth={2.3} />
              ) : (
                <Zap size={16} className="bolt-prefix" aria-hidden strokeWidth={2.3} />
              )}
              <textarea
                id="research-query"
                value={active.draft}
                onChange={(event) => patchActive({ draft: event.target.value })}
                placeholder={
                  active.mode === "quick"
                    ? "例如：用 3 句话解释「注意力机制」是怎么工作的。"
                    : "例如：比较适合个人研究工作流的 AI Agent 平台，并说明取舍。"
                }
                rows={1}
                onInput={(e) => {
                  const el = e.currentTarget;
                  el.style.height = "auto";
                  el.style.height = Math.min(el.scrollHeight, 200) + "px";
                }}
              />
            </div>
            {attachment && active.mode === "research" ? (
              <span className="attachment-name">已选择：{attachment.name}</span>
            ) : null}
            <div className="composer-actions">
              <div className="composer-left-actions">
                <div className="mode-switcher" role="group" aria-label="任务模式">
                  <button
                    type="button"
                    className={active.mode === "quick" ? "active" : ""}
                    onClick={() => setComposerMode("quick")}
                    title="快速问答（单模型直答）"
                  >
                    <Sparkles size={14} /> 快速问答
                  </button>
                  <button
                    type="button"
                    className={active.mode !== "quick" ? "active" : ""}
                    onClick={() => setComposerMode("research")}
                    title="深度研究（多 Agent 规划+检索+来源）"
                  >
                    <FileSearch size={14} /> 深度研究
                  </button>
                </div>
                {active.mode === "research" && (
                  <label className="attach-button" title="添加附件">
                    <Paperclip size={15} />
                    <span>添加附件</span>
                    <input
                      type="file"
                      accept=".txt,.md,.pdf,.docx,.csv,.xlsx"
                      onChange={(event) =>
                        setAttachment(event.target.files?.[0] ?? null)
                      }
                    />
                  </label>
                )}
                {active.mode === "quick" && (
                  <span style={{ fontSize: 12.5, color: "#6c6c7a", display: "inline-flex", alignItems: "center", gap: 6 }}>
                    <MessageCircleQuestion size={13} /> 不调用检索，如需最新信息与引用请切换至「深度研究」
                  </span>
                )}
              </div>
              <button
                type="submit"
                className="submit-btn"
                aria-label={active.mode === "quick" ? "发送问题" : "提交研究"}
                disabled={!active.draft.trim()}
              >
                <ArrowUp size={17} strokeWidth={2.3} />
              </button>
            </div>
          </form>
        </section>
      </div>
    </main>
  );
}
