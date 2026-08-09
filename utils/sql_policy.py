"""Small, conservative SQL policy for the read-only database tool."""

import re


class SqlPolicyError(ValueError):
    pass


_BLOCKED = re.compile(r"\b(insert|update|delete|drop|alter|truncate|call|load|grant|revoke|create|replace)\b", re.I)
_TABLE_REFERENCE = re.compile(r"\b(?:from|join)\s+`?([a-zA-Z_][a-zA-Z0-9_]*)`?", re.I)
_CTE_NAME = re.compile(r"\bwith\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+as\b|,\s*([a-zA-Z_][a-zA-Z0-9_]*)\s+as\b", re.I)


def validate_read_only_sql(query: str, allowed_tables: set[str]) -> None:
    normalized = query.strip()
    if not normalized or ";" in normalized or "--" in normalized or "/*" in normalized:
        raise SqlPolicyError("Only one comment-free read-only statement is allowed.")
    if not re.match(r"^(select|with)\b", normalized, re.I) or _BLOCKED.search(normalized):
        raise SqlPolicyError("Only SELECT queries are allowed.")
    references = {match.group(1) for match in _TABLE_REFERENCE.finditer(normalized)}
    cte_names = {name for match in _CTE_NAME.finditer(normalized) for name in match.groups() if name}
    physical_tables = references - cte_names
    if not physical_tables or not physical_tables.issubset(allowed_tables):
        raise SqlPolicyError("Query references a table that was not discovered.")
