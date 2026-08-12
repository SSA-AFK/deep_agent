import { CircleAlert, CircleCheck, ServerCrash } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { HealthResponse } from "../api/types";

const labels: Record<string, string> = {
  llm: "语言模型", zhihu: "知乎全网搜索", mysql: "产品数据", word: "文档导出",
};

export function ServiceStatusMenu() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  useEffect(() => { api.health().then(setHealth).catch(() => setHealth(null)); }, []);
  const entries = Object.entries(health?.services ?? {});
  return <details className="service-status">
    <summary><CircleAlert size={15} /> 服务状态</summary>
    <div>
      {entries.length === 0 ? <p><ServerCrash size={15} className="icon-warn" /><span>状态暂不可用</span><small>可重试</small></p> : entries.map(([key, service]) => {
        const available = service.status === "available" || service.status === "configured";
        const isNonLive = service.mode !== "live";
        return <p key={key}>{available ? <CircleCheck size={15} className="icon-ok" /> : <ServerCrash size={15} className={isNonLive ? "icon-warn" : "icon-err"} />}<span>{labels[key] ?? key}</span><small>{available ? service.mode : `已降级为 ${service.mode}`}</small></p>;
      })}
    </div>
  </details>;
}
