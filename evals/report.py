"""Generate sanitized aggregate evaluation reports from recorded runs."""

from collections import Counter

from evals.schema import EvalRun, GradeResult


def aggregate(runs: list[EvalRun], grades: list[GradeResult]) -> dict[str, object]:
    completed = sum(run.completed for run in runs)
    by_version = Counter(run.prompt_version for run in runs)
    reviewed = [grade.score for grade in grades]
    return {
        "sample_count": len(runs),
        "completed_count": completed,
        "prompt_versions": dict(by_version),
        "reviewed_count": len(reviewed),
        "mean_score": sum(reviewed) / len(reviewed) if reviewed else None,
    }


def render_markdown(summary: dict[str, object]) -> str:
    score = "not reviewed" if summary["mean_score"] is None else f'{summary["mean_score"]:.2f}'
    return f"""# Agent evaluation report

- Recorded runs: {summary['sample_count']}
- Completed runs: {summary['completed_count']}
- Human-reviewed runs: {summary['reviewed_count']}
- Mean reviewed score: {score}

No uplift is claimed unless both prompt versions have recorded runs under the same settings.
"""
