import { Sparkles } from "lucide-react";

export function QuickAnswerMessage({
  result,
  threadId,
  streaming = false,
}: {
  result?: string | null;
  threadId: string;
  streaming?: boolean;
}) {
  void threadId; // quick 模式目前不暴露反馈/导出，但预留 threadId 接口位
  const content = (result ?? "").trim();

  return (
    <article className={`quick-answer-message ${streaming ? "streaming" : ""}`} aria-label="快速回答">
      <header>
        <span className="quick-icon" aria-hidden>
          <Sparkles size={15} />
        </span>
        <div>
          <span className="eyebrow">{streaming ? "快速回答生成中" : "快速回答"}</span>
          <h2>轻量问答，无需检索与计划</h2>
        </div>
      </header>

      {content ? (
        <p className="report-content">
          {content}
          {streaming && <span className="stream-caret" aria-hidden />}
        </p>
      ) : (
        <p className="report-content quick-placeholder">
          <span className="stream-dot" /> 模型正在组织答案，实时流式输出。
        </p>
      )}

      {!streaming && (
        <footer className="quick-footer">
          需要有来源、可核验、多 Agent 协作的结论？请使用「深度研究」模式。
        </footer>
      )}
      {streaming && (
        <footer className="quick-footer streaming-hint">
          <span className="stream-dot" /> 直接回答，不调用公开检索；如涉及最新动态或专业报告请切换到深度研究。
        </footer>
      )}
    </article>
  );
}
