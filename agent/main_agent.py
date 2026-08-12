from agent.subagents.database_query_agent import database_query_agent
from agent.subagents.network_search_agent import network_search_agent
from langgraph.checkpoint.memory import InMemorySaver

# main_agent tool导入
from tools.markdown_tools import generate_markdown
from tools.pdf_tools import convert_md_to_pdf
from tools.upload_file_read_tool import read_file_content

from deepagents import create_deep_agent

from agent.llm import get_model
from agent.prompts import main_agent_content

from api.monitor import monitor
import asyncio
import json
import re
import uuid
import shutil
from pathlib import Path

from api.context import set_session_context, reset_session_context, set_thread_context
from api.task_manager import TaskState, task_manager
from utils.citations import append_source_links
from utils.citations import requests_public_sources
from utils.citations import render_public_source_fallback

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

_main_agent = None


def get_main_agent():
    """Build the Agent only after model readiness is required by a task."""
    global _main_agent
    if _main_agent is None:
        _main_agent = create_deep_agent(
            model=get_model(),
            system_prompt=main_agent_content['system_prompt'],
            tools=[generate_markdown, convert_md_to_pdf, read_file_content],
            checkpointer=InMemorySaver(),
            subagents=[database_query_agent, network_search_agent],
        )
    return _main_agent

# 执行
"""
  1. 执行主智能体 一定选异步，原因：对应多个客户端
  2. 什么时候触发我们智能体的调用或者执行？？？
  3. 客户端 -》 api/task -> fastapi 接口 -》 异步执行 -》 main_agent的运行 （异步方法）
  4. main_agent执行stream流式处理 -》 调用工具 -》 已经埋好了点  
                                   调用子智能体 -》 结果解析 -》 name = task -> monitor -> 发送子智能体
                                   调用最终结果 -》 结果 -》 monitor -> 发送结果的方法
                                   开启调用以后 -》 当前会话 -》 文件夹地址 -》 推送到前端
"""



project_root_path = Path(__file__).parents[1].resolve() # 绝对 解析路径标识以及软连接
# project_root_path = Path(__file__).parents[1].absolute() # 绝对
# main_agent.invoke()
# main_agent.stream()
# main_agent.astream() [选他]
async def run_deep_agent(task_query,session_id):
    """
    定义流式+异步执行主智能体！！
    执行过程中，返回  会话文件化返回  调用子智能体  调用最终结果 （monitor）
    task_query: 前端提问的问题
    session_id: 每个前端会话对应的标识 （1.存储session_id ContextVars 2.session_id 给他创建对应的output输出地址）
    """
    print(f"当前会话的main_agent开始执行了！ 会话id:{session_id}")
    # 准备工作 【1. session_dir（前端） 2. relative_session_dir (大模型) 3. 上传的文件拼接上传文件专属提示词】
    # project_root_path / output / session_session_id(uuid)
    # 当前会话存储生成文件的专属文件夹
    session_dir = project_root_path / "output" / f"session_{session_id}"
    # 文件夹可能没有，第一次请求要创建
    session_dir.mkdir(parents=True, exist_ok=True)
    # \  \n \t -> /
    session_dir_str = str(session_dir).replace("\\","/")
    # 获取相对文件夹
    # session_dir : project_root_path / output / session_session_id(uuid)
    # project_root_path : project_root_path
    # relative_session_dir_str: / output / session_session_id(uuid)
    relative_session_dir_str = str(session_dir.relative_to(project_root_path)).replace("\\","/")

    #处理上传文件 （updated / session_session_id）
    updated_dir_path = project_root_path / "updated" / f"session_{session_id}"
    updated_info_prompt = "" # 有上传文件，拼接上传文件专属解析位置的提示词
    if updated_dir_path.exists():
        # 有
        files = [ f.name  for f in updated_dir_path.iterdir()  if f.is_file()]
        # 将上传文件统一赋值到 output_dir 方便前端统一读取 session_dir
        if files:
            for filename in files:
                # 将原文件 -》 复制 -》 目标文件中  （copy2 保留原文件修改时间和权限等元数据）
                shutil.copy2(updated_dir_path / filename, session_dir / filename)
            # 构建提示词！告诉大模型，有上传文件，你要读取上传文件！！
            updated_info_prompt = (f"\n    [已上传文件] 已加载到工作目录:\n" +
                             "\n".join([f"    - {f}" for f in files]) +
                             "\n    请优先使用工具（read_file_content）读取并参考这些文件。")

    # 继续准备 1. 当前会话的对应的session_id session_dir 存储到contextVars [后续工具获取，socket -> 推送消息] 2.调用monitor给前端推送session_dir信息
    session_dir_token = set_session_context(session_dir_str)  # 存储的当前会话对应的文件夹地址
    session_id_token = set_thread_context(session_id)  #获取当前会话的session_id对应socket
    monitor.clear_source_urls(session_id)

    monitor.report_session_dir(session_dir_str)  # 当前会话对应的文件夹地址推送给起前端！

    # 执行main_agent
    config = {
        "recursion_limit": 32,
        "configurable":{
            "thread_id":session_id
        }
    }

    # 构建提示词
    path_instruction = f"""
    【工作环境指令】
    工作目录: {relative_session_dir_str}
    {updated_info_prompt}

    规则：
    1. 新生成文件必须保存到工作目录：'{relative_session_dir_str}/filename'
    2. 读取已上传的文件时，请直接将文件名（例如：'开篇.txt'）作为 filename 参数传入（read_file_content）读取工具，不要带上任何目录前缀。
    3. 使用相对路径，禁止使用绝对路径
    4. 若存在上传文件，请先分析内容
    """
    # 反馈结果
    try:
        final_result = None
        message_contents = []
        emitted_text_len = 0  # 已经通过 report_delta 推给前端的累积文本长度，用于算 diff
        # 执行
        try:
            async with asyncio.timeout(45):
                async for chunk in get_main_agent().astream({
                    "messages":[
                        {
                            "role":"user","content":task_query+path_instruction
                        }
                    ]
                },config=config):
                    # {"model [大模型决定调用工具 子智能体  最终结果] / tools" : {messages:[xxx...]}}
                    for node_name,state in chunk.items():
                        if not state or "messages" not in state: continue
                        messages = state["messages"]
                        if messages and isinstance(messages,list):
                            last_msg = messages[-1]
                            message_contents.extend(message.content for message in messages if getattr(message, "content", None))
                            if node_name == 'model' and last_msg.tool_calls:
                                for tool_call in last_msg.tool_calls:
                                    if tool_call['name'] == 'task':
                                        monitor.report_assistant(tool_call['args']['subagent_type'], {'description': tool_call['args']['description']})
                            elif last_msg.content:
                                content = last_msg.content if isinstance(last_msg.content, str) else ""
                                if content:
                                    final_result = content
                                    if len(content) > emitted_text_len:
                                        delta = content[emitted_text_len:]
                                        emitted_text_len = len(content)
                                        monitor.report_delta(delta, partial=content)
        except TimeoutError:
            from api.settings import get_settings
            from tools.zhihu_search_tool import ZhihuSearchClient

            # 模型超时未必代表没结果：若已检索到公开来源，或 query 明确要求来源，
            # 则降级返回可直接核验的检索结果，避免无谓失败。
            if not (requests_public_sources(task_query) or monitor.peek_source_urls(session_id)):
                raise

            search_result = ZhihuSearchClient(
                get_settings().zhihu_access_secret,
                timeout_seconds=get_settings().request_timeout_seconds,
            ).search(task_query, count=3)
            final_result = render_public_source_fallback([
                (item.title, item.snippet, item.url)
                for item in search_result.items
                if item.url
            ])
            # 超时降级也按增量推送（从头发，emitted_text_len 此时一般为 0）
            if len(final_result) > emitted_text_len:
                delta = final_result[emitted_text_len:]
                emitted_text_len = len(final_result)
                monitor.report_delta(delta, partial=final_result)
            message_contents = []

        source_urls = monitor.take_source_urls(session_id)
        if not source_urls and requests_public_sources(task_query):
            from api.settings import get_settings
            from tools.zhihu_search_tool import ZhihuSearchClient

            search_result = ZhihuSearchClient(
                get_settings().zhihu_access_secret,
                timeout_seconds=get_settings().request_timeout_seconds,
            ).search(task_query, count=3)
            source_urls = [item.url for item in search_result.items if item.url]
        final_result = append_source_links(final_result or "", message_contents + source_urls)
        # 追加来源后的最终文本与上次推送的差值，再推一次 delta 保证正文流末尾就是最终展示内容
        if len(final_result) > emitted_text_len:
            delta = final_result[emitted_text_len:]
            monitor.report_delta(delta, partial=final_result)
        monitor.report_task_result(final_result)

        try:
            await task_manager.transition(session_id, TaskState.SUCCEEDED, {"result": final_result or ""})
        except (KeyError, ValueError):
            pass

    except Exception as e :
        # 报错推送错误信息给前端
        # asyncio.TimeoutError 等异常 str(e) 可能为空，此时给出可读的语义化提示，便于前端展示与排查
        detail = str(e).strip()
        if not detail:
            if isinstance(e, TimeoutError):
                detail = "任务在 45 秒时间内未完成，已终止执行。"
            else:
                detail = "任务执行失败，未返回可读的错误详情。"
        monitor._emit("error", f"执行主智能发生异常信息：{detail}")
        try:
            await task_manager.transition(session_id, TaskState.FAILED, {"error": {"code": "AGENT_EXECUTION_FAILED", "message": "The research task failed.", "source": "agent", "retryable": True}})
        except (KeyError, ValueError):
            pass
    finally:
        monitor.take_source_urls(session_id)
        monitor.clear_search_flag(session_id)
        # 释放存储的地址和session_id
        reset_session_context(session_dir_token, session_id_token)


_QUICK_CHAT_PROMPT = (
    "你是 Deep Search Pro 工作台内置的轻量助手，用来回答用户不需要公开检索或多步骤分析的简单问题。"
    "回答须清晰、简洁、中文优先；不要编造事实，若问题涉及最新动态、实时数据、对比研究或专业报告，"
    "请如实说明「建议使用「深度研究」模式以获得有来源、可核验的结论」。"
)


async def run_quick_chat(chat_query: str, session_id: str):
    """Quick Chat 模式：直接调用单模型 astream，输出走同一套 delta/result WS 事件，任务走 task_manager 状态机。

    对比 run_deep_agent：
    - 不创建 output 工作目录、不读上传文件、不调用工具或子智能体
    - 不做 45s 透明降级（聊天链路要低时延，超时失败直接在终端提示）
    """
    print(f"[quick_chat] start thread={session_id}")
    thread_token = set_thread_context(session_id)
    emitted_len = 0
    final_text = ""
    try:
        async with asyncio.timeout(30):
            async for chunk in get_model().astream(
                [SystemMessage(content=_QUICK_CHAT_PROMPT), HumanMessage(content=chat_query)]
            ):
                content = chunk.content if isinstance(chunk.content, str) else ""
                if not content:
                    continue
                final_text = final_text + content
                if len(final_text) > emitted_len:
                    delta = final_text[emitted_len:]
                    emitted_len = len(final_text)
                    monitor.report_delta(delta, partial=final_text)
        monitor.report_task_result(final_text)
        try:
            await task_manager.transition(session_id, TaskState.SUCCEEDED, {"result": final_text})
        except (KeyError, ValueError):
            pass
    except Exception as e:
        detail = str(e).strip() or (
            "问答在 30 秒内未完成，已终止。" if isinstance(e, TimeoutError) else "问答执行失败，未返回可读详情。"
        )
        monitor._emit("error", f"[quick_chat] 执行失败：{detail}")
        try:
            await task_manager.transition(
                session_id,
                TaskState.FAILED,
                {
                    "error": {
                        "code": "CHAT_EXECUTION_FAILED",
                        "message": detail,
                        "source": "chat",
                        "retryable": True,
                    }
                },
            )
        except (KeyError, ValueError):
            pass
    finally:
        # 注意：quick chat 不设置 session_dir，仅 reset thread 部分（避免给 reset 传 None 报错）
        from api.context import _thread_id_ctx  # noqa: PLC2701 internal cleanup
        try:
            _thread_id_ctx.reset(thread_token)
        except (ValueError, LookupError):
            pass


_CLARIFY_SYSTEM_PROMPT = (
    "你是研究问题的澄清助手。判断用户的问题是否缺少关键要素（例如：对比的对象、研究的时间范围、"
    "地域、目标人群、评估指标、需要用到的资料范围等）。\n"
    "输出规则：\n"
    "1. 如果信息充足，直接输出空数组：[]\n"
    "2. 如果信息不足，输出最多 3 条、最少 1 条澄清问题，使用严格 JSON 数组，例如："
    '[\"你想用哪个城市和北京对比？\",\"对比的维度是什么（房价/教育/就业/生活成本）？\"]\n'
    "3. 只输出 JSON，不要输出额外解释、代码块、前后缀或自然语言。\n"
    "4. 问题要具体、可直接由用户一句话回答；不要重复用户已经明确给出的信息。"
)

# 从模型文本输出里稳妥地截出第一个 JSON 数组（兼容前后垃圾文本、``` 代码块等）
_JSON_ARRAY_RE = re.compile(r"\[[\s\S]*\]")


async def ask_clarifying_questions(task_query: str, task_mode: str) -> list[str]:
    """基于用户问题判断是否信息不足，返回需要用户补充的澄清问题。空数组表示"信息已充足，可直接执行"。

    不修改 task_manager 状态、不走 WebSocket，作为研究/聊天链路的前置探针接口。
    """
    prompt = f"用户选择的模式：{task_mode}\n用户问题：{task_query}"
    try:
        response = await get_model().ainvoke(
            [SystemMessage(content=_CLARIFY_SYSTEM_PROMPT), HumanMessage(content=prompt)],
            config={"max_tokens": 512},
        )
    except Exception as exc:  # noqa: BLE001
        # 任何 LLM 认证/网络问题都降级为「信息已充足」，不阻断用户继续。
        print(f"[clarify] LLM call failed, treating as sufficient: {exc}")
        return []

    raw = (response.content if isinstance(response.content, str) else "").strip()
    if not raw:
        return []

    # 优先尝试直接 JSON.parse
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(q).strip() for q in parsed if str(q).strip()][:3]
    except json.JSONDecodeError:
        pass

    # 去掉 ```json / ``` 包裹
    stripped = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    stripped = re.sub(r"\s*```$", "", stripped)
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, list):
            return [str(q).strip() for q in parsed if str(q).strip()][:3]
    except json.JSONDecodeError:
        pass

    # 最后兜底：正则抓第一个 [ ... ] 段
    match = _JSON_ARRAY_RE.search(stripped)
    if match:
        try:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, list):
                return [str(q).strip() for q in parsed if str(q).strip()][:3]
        except json.JSONDecodeError:
            pass
    return []

