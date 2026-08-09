from evals.report import aggregate, render_markdown
from evals.schema import EvalRun


def test_report_does_not_treat_missing_reviews_as_zero():
    summary = aggregate([EvalRun(case_id="x", prompt_version="v2", completed=True, duration_ms=1)], [])
    assert summary["mean_score"] is None
    assert "not reviewed" in render_markdown(summary)
