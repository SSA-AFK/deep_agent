import { Download, ThumbsDown, ThumbsUp } from "lucide-react";
import { useState } from "react";
import { api } from "../api/client";

export function ReportMessage({
  result,
  threadId,
  streaming = false,
}: {
  result?: string | null;
  threadId: string;
  streaming?: boolean;
}) {
  const [notice, setNotice] = useState<string | null>(null);

  const sendFeedback = async (helpful: boolean) => {
    try {
      await api.feedback(threadId, helpful, helpful ? "结果有帮助" : "需要改进");
      setNotice("反馈已记录");
    } catch {
      setNotice("反馈提交失败，请重试");
    }
  };

  const exportPdf = async () => {
    try {
      const response = await api.files(threadId);
      const pdf = response.files.find((file) => file.name.toLowerCase().endsWith(".pdf"));
      if (!pdf) {
        setNotice("暂未生成 PDF，可稍后重试");
        return;
      }
      await api.recordExport(threadId);
      window.location.assign(api.downloadUrl(pdf.path));
    } catch {
      setNotice("导出失败，请重试");
    }
  };

  const finalResult = result ?? null;
  const fallback = (
    <>
      <p>
        <strong>事实：</strong>公开研究可提供近期平台与实践信息；产品数据和知识库在当前演示中使用了透明快照。
      </p>
      <p>
        <strong>推断：</strong>若目标是面试展示，先证明一条稳定任务链路比扩展通用功能更有说服力。
      </p>
    </>
  );

  return (
    <article className={`report-message ${streaming ? "streaming" : ""}`} aria-label="研究报告">
      <span className="eyebrow">{streaming ? "实时生成中" : "研究结论"}</span>
      <h2>优先选择可观察、可接管的工作流</h2>
      {finalResult ? (
        <p className="report-content">
          {finalResult}
          {streaming && <span className="stream-caret" aria-hidden />}
        </p>
      ) : (
        fallback
      )}
      <p className="citations">
        来源：
        <a href="https://www.zhihu.com" target="_blank" rel="noreferrer">
          知乎公开研究（实时）
        </a>{" "}
        · 产品演示数据（demo）
      </p>
      <footer>
        {streaming ? (
          <span className="streaming-hint">
            <span className="stream-dot" /> 模型正在输出，你可以先阅读已有部分
          </span>
        ) : (
          <>
            <span>这份结果有帮助吗？</span>
            <button
              type="button"
              className="fb-btn like"
              aria-label="有帮助"
              onClick={() => sendFeedback(true)}
            >
              <ThumbsUp size={16} />
            </button>
            <button
              type="button"
              className="fb-btn dislike"
              aria-label="需要改进"
              onClick={() => sendFeedback(false)}
            >
              <ThumbsDown size={16} />
            </button>
            <button type="button" className="export" onClick={exportPdf}>
              <Download size={16} /> 导出 PDF
            </button>
          </>
        )}
      </footer>
      {notice && (
        <p className="report-notice" role="status">
          {notice}
        </p>
      )}
    </article>
  );
}
