import { Download, ThumbsDown, ThumbsUp } from "lucide-react";

export function ReportMessage({ result }: { result?: string | null }) {
  return <article className="report-message" aria-label="研究报告">
    <span className="eyebrow">研究结论</span><h2>优先选择可观察、可接管的工作流</h2>
    {result ? <p className="report-content">{result}</p> : <><p><strong>事实：</strong>公开研究可提供近期平台与实践信息；产品数据和知识库在当前演示中使用了透明快照。</p><p><strong>推断：</strong>若目标是面试展示，先证明一条稳定任务链路比扩展通用功能更有说服力。</p></>}
    <p className="citations">来源：<a href="https://www.zhihu.com" target="_blank" rel="noreferrer">知乎公开研究（实时）</a> · 产品演示数据（demo）</p>
    <footer><span>这份结果有帮助吗？</span><button type="button" aria-label="有帮助"><ThumbsUp size={16} /></button><button type="button" aria-label="需要改进"><ThumbsDown size={16} /></button><button type="button" className="export"><Download size={16} /> 导出 PDF</button></footer>
  </article>;
}
