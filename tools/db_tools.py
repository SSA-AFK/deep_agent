"""Read-only MySQL tools with an explicit deterministic demo fallback."""

import json
import time
from pathlib import Path

from langchain_core.tools import tool
from mysql.connector import Error, connect

from api.errors import PublicError
from api.monitor import monitor
from api.settings import get_settings
from tools.contracts import DataMode, SourceItem, ToolResult, ToolStatus
from utils.sql_policy import SqlPolicyError, validate_read_only_sql


_DISCOVERED_TABLES: set[str] = set()
_DEMO_PRODUCTS = Path(__file__).resolve().parents[1] / "data" / "demo" / "products.json"


def _demo_result(started: float, code: str, message: str) -> ToolResult:
    rows = json.loads(_DEMO_PRODUCTS.read_text(encoding="utf-8"))
    return ToolResult(
        status=ToolStatus.DEGRADED,
        source="mysql",
        mode=DataMode.DEMO,
        duration_ms=int((time.monotonic() - started) * 1000),
        items=[SourceItem(title=row["name"], source="mysql", snippet=row["best_for"], metadata=row) for row in rows],
        error=PublicError(code=code, message=message, source="mysql"),
    )


def _connection_config() -> dict:
    settings = get_settings()
    if not settings.mysql_user or not settings.mysql_password or not settings.mysql_database:
        raise ValueError("MySQL is not configured")
    return {
        "host": settings.mysql_host,
        "port": settings.mysql_port,
        "user": settings.mysql_user,
        "password": settings.mysql_password,
        "database": settings.mysql_database,
        "connection_timeout": int(settings.request_timeout_seconds),
        "autocommit": False,
    }


@tool
def list_sql_tables() -> str:
    """List discovered MySQL tables; use this before querying a table."""
    monitor.report_tool("数据库表名查询工具", {})
    started = time.monotonic()
    try:
        with connect(**_connection_config()) as connection, connection.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables = {str(row[0]) for row in cursor.fetchall()}
            _DISCOVERED_TABLES.clear()
            _DISCOVERED_TABLES.update(tables)
            result = ToolResult(status=ToolStatus.SUCCESS, source="mysql", mode=DataMode.LIVE, duration_ms=int((time.monotonic() - started) * 1000), items=[SourceItem(title=table, source="mysql") for table in sorted(tables)])
    except (Error, ValueError):
        _DISCOVERED_TABLES.clear()
        _DISCOVERED_TABLES.add("products")
        result = _demo_result(started, "MYSQL_UNAVAILABLE", "Database is unavailable; using demo products.")
    return result.model_dump_json()


@tool
def get_table_data(table_name: str) -> str:
    """Preview up to 100 rows from an already discovered table."""
    return execute_sql_query.invoke({"query": f"SELECT * FROM `{table_name}` LIMIT 100"})


@tool
def execute_sql_query(query: str) -> str:
    """Execute one discovered-table, read-only SELECT query with a row limit."""
    monitor.report_tool("数据库只读查询工具", {"query": query})
    started = time.monotonic()
    try:
        validate_read_only_sql(query, _DISCOVERED_TABLES)
    except SqlPolicyError as error:
        return ToolResult(status=ToolStatus.FAILED, source="mysql", mode=DataMode.LIVE, duration_ms=0, error=PublicError(code="SQL_POLICY_REJECTED", message=str(error), source="mysql")).model_dump_json()
    try:
        with connect(**_connection_config()) as connection, connection.cursor(dictionary=True) as cursor:
            cursor.execute(query)
            rows = cursor.fetchmany(100)
        result = ToolResult(status=ToolStatus.SUCCESS, source="mysql", mode=DataMode.LIVE, duration_ms=int((time.monotonic() - started) * 1000), items=[SourceItem(title=str(row), source="mysql", metadata=row) for row in rows])
    except (Error, ValueError):
        result = _demo_result(started, "MYSQL_UNAVAILABLE", "Database is unavailable; using demo products.")
    return result.model_dump_json()
