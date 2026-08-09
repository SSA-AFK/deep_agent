import { ArrowUp, FileText, Plus, Search } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { PlanMessage } from "./components/PlanMessage";
import { AgentRunMessage } from "./components/AgentRunMessage";
import { ReportMessage } from "./components/ReportMessage";
import { ServiceStatusMenu } from "./components/ServiceStatusMenu";
import { api } from "./api/client";
import { TaskSocket } from "./api/socket";
import type { TaskState } from "./api/types";

const STARTERS = ["比较 Coze 与其他 Agent 平台", "为 AI 产品实习准备行业研究", "根据我的资料生成研究提纲"];

export default function App() {
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [taskState, setTaskState] = useState<TaskState | null>(null);
  useEffect(() => {
    if (!threadId || import.meta.env.MODE === "test") return;
    const socket = new TaskSocket(threadId, (event) => {
      if (event.type === "task_status" && typeof event.data.state === "string") setTaskState(event.data.state as TaskState);
    });
    socket.connect();
    const timer = window.setInterval(() => api.task(threadId).then((snapshot) => setTaskState(snapshot.state)).catch(() => undefined), 3000);
    return () => { window.clearInterval(timer); socket.close(); };
  }, [threadId]);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!query.trim()) return;
    const nextThreadId = `test-${crypto.randomUUID()}`;
    try {
      await api.createTask(query.trim(), nextThreadId);
      setThreadId(nextThreadId); setTaskState("waiting_confirmation"); setSubmitted(query.trim()); setConfirmed(false); setCompleted(false); setError(null);
    } catch { setError("任务创建失败，请检查服务状态后重试。"); }
  };
  const confirm = async () => {
    if (!threadId) return;
    try { await api.confirm(threadId); setTaskState("running"); setConfirmed(true); setError(null); }
    catch { setError("计划确认失败，请重试。"); }
  };
  return <main className="workbench">
    <aside className="sidebar" aria-label="研究历史">
      <div className="brand"><Search size={18} /> Deep Search Pro</div>
      <button className="new-task" type="button"><Plus size={16} /> 新建研究</button>
      <p className="history-label">最近研究</p>
      <button className="history-item" type="button">AI Agent 平台选型</button>
      <button className="history-item" type="button">产品实习面试准备</button>
    </aside>
    <section className="conversation" aria-labelledby="page-title">
      <header><div className="title-row"><span className="eyebrow">研究工作台</span><ServiceStatusMenu /></div><h1 id="page-title">从问题到可追溯结论</h1><p>规划、检索、分析与来源都保留在同一条研究对话中。</p></header>
      {error && <p className="inline-error" role="alert">{error}</p>}
      {submitted ? <><article className="message user-message"><span>你的研究问题</span><p>{submitted}</p></article>{completed || taskState === "succeeded" ? <ReportMessage /> : confirmed || taskState === "running" ? <AgentRunMessage onComplete={() => setCompleted(true)} /> : <PlanMessage onConfirm={confirm} onCancel={() => setSubmitted(null)} />}</> : <section className="empty-state"><FileText size={28} /><h2>开始一项复杂研究</h2><p>说明目标、限制条件和你希望得到的输出。</p><div className="starters">{STARTERS.map((starter) => <button key={starter} type="button" onClick={() => setQuery(starter)}>{starter}</button>)}</div></section>}
      <form className="composer" onSubmit={submit}><label htmlFor="research-query">研究问题</label><textarea id="research-query" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="例如：比较适合个人研究工作流的 AI Agent 平台，并说明取舍。" rows={3} /><div><span>Enter 发送 · Shift + Enter 换行</span><button type="submit" aria-label="提交研究" disabled={!query.trim()}><ArrowUp size={17} /></button></div></form>
    </section>
  </main>;
}
