import { CircleAlert, CircleCheck, ServerCrash } from "lucide-react";

type Service = { name: string; status: "available" | "unavailable"; mode: "live" | "demo" | "required" };
const services: Service[] = [
  { name: "语言模型", status: "available", mode: "required" },
  { name: "知乎全网搜索", status: "available", mode: "live" },
  { name: "产品数据", status: "unavailable", mode: "demo" },
  { name: "知识库", status: "unavailable", mode: "demo" },
];

export function ServiceStatusMenu() {
  return <details className="service-status"><summary><CircleAlert size={15} /> 服务状态</summary><div>{services.map((service) => <p key={service.name}>{service.status === "available" ? <CircleCheck size={15} /> : <ServerCrash size={15} />}<span>{service.name}</span><small>{service.status === "available" ? service.mode : `已降级为 ${service.mode}`}</small></p>)}</div></details>;
}
