import { MessageCircleQuestion, ArrowRight } from "lucide-react";

export function ClarifyMessage({
  questions,
  answers,
  onAnswerChange,
  onProceed,
  onSkip,
}: {
  questions: string[];
  answers: Record<number, string>;
  onAnswerChange: (index: number, value: string) => void;
  onProceed: () => void;
  onSkip: () => void;
}) {
  const answered = questions.filter((_, i) => (answers[i] ?? "").trim().length > 0).length;

  return (
    <article className="clarify-message" aria-label="需要补充的信息">
      <header>
        <div className="clarify-head">
          <span className="clarify-icon" aria-hidden>
            <MessageCircleQuestion size={18} />
          </span>
          <div>
            <span className="eyebrow">信息不足</span>
            <h2>先回答以下问题，结果会更准确</h2>
          </div>
        </div>
        <span className="clarify-progress">已补充 {answered} / {questions.length}</span>
      </header>

      <ol className="clarify-list">
        {questions.map((q, i) => (
          <li key={i}>
            <label htmlFor={`clarify-${i}`}>{i + 1}. {q}</label>
            <textarea
              id={`clarify-${i}`}
              value={answers[i] ?? ""}
              onChange={(e) => onAnswerChange(i, e.target.value)}
              placeholder="在此补充你希望的限定条件、范围或对比对象……"
              rows={2}
              onInput={(e) => {
                const el = e.currentTarget;
                el.style.height = "auto";
                el.style.height = Math.min(el.scrollHeight, 160) + "px";
              }}
            />
          </li>
        ))}
      </ol>

      <footer>
        <button type="button" className="secondary" onClick={onSkip}>
          先按现有信息执行
        </button>
        <button type="button" className="submit-btn small" onClick={onProceed}>
          信息补全，继续执行 <ArrowRight size={14} strokeWidth={2.3} />
        </button>
      </footer>
    </article>
  );
}
