"""Lazy RAGFlow tools with deterministic internal-knowledge fallback."""

import time
from functools import lru_cache
from pathlib import Path

from langchain_core.tools import tool
from ragflow_sdk import RAGFlow

from api.errors import PublicError
from api.monitor import monitor
from api.settings import get_settings
from tools.contracts import DataMode, SourceItem, ToolResult, ToolStatus


_DEMO_KNOWLEDGE = Path(__file__).resolve().parents[1] / "data" / "demo" / "knowledge.md"


@lru_cache
def get_ragflow_client() -> RAGFlow:
    settings = get_settings()
    if not settings.ragflow_api_key or not settings.ragflow_api_url:
        raise RuntimeError("RAGFlow is not configured")
    return RAGFlow(api_key=settings.ragflow_api_key, base_url=settings.ragflow_api_url)


def _demo(started: float) -> str:
    result = ToolResult(
        status=ToolStatus.DEGRADED,
        source="ragflow",
        mode=DataMode.DEMO,
        duration_ms=int((time.monotonic() - started) * 1000),
        items=[SourceItem(title="演示内部知识库", source="ragflow", snippet=_DEMO_KNOWLEDGE.read_text(encoding="utf-8"))],
        error=PublicError(code="RAGFLOW_UNAVAILABLE", message="Knowledge base is unavailable; using demo knowledge.", source="ragflow"),
    )
    return result.model_dump_json()


@tool
def get_assistant_list() -> str:
    """List available RAGFlow assistants, or an explicitly marked demo source."""
    monitor.report_tool("RAGFlow assistant list", {})
    started = time.monotonic()
    try:
        chats = get_ragflow_client().list_chats()
        result = ToolResult(
            status=ToolStatus.SUCCESS,
            source="ragflow",
            mode=DataMode.LIVE,
            duration_ms=int((time.monotonic() - started) * 1000),
            items=[SourceItem(title=str(chat.name), source="ragflow", snippet=str(getattr(chat, "description", ""))) for chat in chats],
        )
        return result.model_dump_json()
    except Exception:
        return _demo(started)


@tool
def create_ask_delete(chat_name: str, question: str) -> str:
    """Ask one assistant and always delete the temporary RAGFlow session."""
    monitor.report_tool("RAGFlow ask", {"chat_name": chat_name})
    started = time.monotonic()
    session = None
    chat = None
    try:
        chats = get_ragflow_client().list_chats(name=chat_name)
        if not chats:
            raise RuntimeError("assistant not found")
        chat = chats[0]
        session = chat.create_session(name="single_research_question")
        answer = "".join(str(getattr(part, "content", "")) for part in session.ask(question=question, stream=True))
        result = ToolResult(status=ToolStatus.SUCCESS, source="ragflow", mode=DataMode.LIVE, duration_ms=int((time.monotonic() - started) * 1000), items=[SourceItem(title=chat_name, source="ragflow", snippet=answer)])
        return result.model_dump_json()
    except Exception:
        return _demo(started)
    finally:
        if chat is not None and session is not None:
            try:
                chat.delete_sessions(ids=[session.id])
            except Exception:
                pass
