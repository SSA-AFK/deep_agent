import { Check, CircleDashed, Database, Search, ShieldAlert } from "lucide-react";

type Mode = "live" | "demo";
const agents = [
  { name: "公开研究助手", action: "正在检索公开资料", mode: "live" as Mode, icon: Search },
  { name: "产品数据助手", action: "已加载透明演示数据", mode: "demo" as Mode, icon: Database },
  { name: "知识库助手", action: "等待相关问题", mode: "demo" as Mode, icon: CircleDashed },
];

export function AgentRunMessage({ onComplete }: { onComplete(): void }) {
  return <article className="agent-run" aria-label="多 Agent 执行进度">
    <header><div><span className="eyebrow">执行过程</span><h2>研究正在进行</h2></div><span className="elapsed">00:18</span></header>
    <div className="agent-rows">{agents.map(({ name, action, mode, icon: Icon }, index) => <div className="agent-row" key={name}><Icon size={17} /><div><strong>{name}</strong><span>{action}</span></div><span className={`mode ${mode}`}>{mode === "live" ? "实时来源" : "演示来源"}</span>{index === 1 ? <ShieldAlert size={16} aria-label="已降级" /> : <Check size={16} aria-label="状态正常" />}</div>)}</div>
    <p className="degradation">部分来源正使用演示快照；最终报告会清楚标记其影响范围。</p><button type="button" className="secondary show-report" onClick={onComplete}>查看模拟报告</button>
  </article>;
}
