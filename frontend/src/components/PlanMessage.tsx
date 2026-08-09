interface PlanMessageProps { onConfirm(): void; onCancel(): void; }

export function PlanMessage({ onConfirm, onCancel }: PlanMessageProps) {
  return <article className="plan-message" aria-label="执行计划">
    <span className="eyebrow">建议执行计划</span>
    <h2>先确认范围，再开始检索</h2>
    <ol><li>明确比较维度与约束</li><li>检索公开资料与来源</li><li>汇总取舍并标注推断</li></ol>
    <div className="plan-actions"><button type="button" className="secondary" onClick={onCancel}>取消</button><button type="button" className="primary" onClick={onConfirm}>确认并开始</button></div>
  </article>;
}
