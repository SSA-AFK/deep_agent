import { ArrowUp, FileText, Plus, Search } from "lucide-react";
import { FormEvent, useState } from "react";

const STARTERS = ["比较 Coze 与其他 Agent 平台", "为 AI 产品实习准备行业研究", "根据我的资料生成研究提纲"];

export default function App() {
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState<string | null>(null);
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (query.trim()) setSubmitted(query.trim());
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
      <header><span className="eyebrow">研究工作台</span><h1 id="page-title">从问题到可追溯结论</h1><p>规划、检索、分析与来源都保留在同一条研究对话中。</p></header>
      {submitted ? <article className="message user-message"><span>你的研究问题</span><p>{submitted}</p><small>计划将在确认后开始执行。</small></article> : <section className="empty-state"><FileText size={28} /><h2>开始一项复杂研究</h2><p>说明目标、限制条件和你希望得到的输出。</p><div className="starters">{STARTERS.map((starter) => <button key={starter} type="button" onClick={() => setQuery(starter)}>{starter}</button>)}</div></section>}
      <form className="composer" onSubmit={submit}><label htmlFor="research-query">研究问题</label><textarea id="research-query" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="例如：比较适合个人研究工作流的 AI Agent 平台，并说明取舍。" rows={3} /><div><span>Enter 发送 · Shift + Enter 换行</span><button type="submit" aria-label="提交研究" disabled={!query.trim()}><ArrowUp size={17} /></button></div></form>
    </section>
  </main>;
}
