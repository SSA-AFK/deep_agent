from evals.schema import EvalCase, EvalRun, GradeResult


def grade(case: EvalCase, run: EvalRun) -> GradeResult:
    used = {trace.agent for trace in run.traces}
    route_correct = set(case.expected_agents).issubset(used)
    coverage = sum(fact.lower() in run.answer.lower() for fact in case.required_facts) / len(case.required_facts)
    forbidden = any(item.lower() in run.answer.lower() for item in case.forbidden_behavior)
    return GradeResult(case_id=case.id, intent_correct=run.completed, route_correct=route_correct, required_fact_coverage=coverage, citation_supported="http" in run.answer, score=0 if forbidden else 5 * coverage)
