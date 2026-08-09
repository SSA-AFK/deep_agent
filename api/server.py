import uuid
import asyncio
import uvicorn
from pathlib import Path
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import shutil
import json
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from analytics.events import ProductEvent, append_event

# Add project root to sys.path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent

# Import agent runner and monitor
# 注意：agent.main_agent 导入时会初始化 main_agent，这可能需要几秒钟
from agent.main_agent import run_deep_agent
from api.monitor import manager
from api.health import get_service_registry
from api.settings import get_settings
from api.task_manager import TaskState, task_manager

async def _broadcast_task_event(event: dict) -> None:
    state = event.get("data", {}).get("state")
    if state == TaskState.SUCCEEDED:
        _record_product_event("task_completed", event["thread_id"])
    elif state == TaskState.FAILED:
        _record_product_event("task_failed", event["thread_id"])
    await manager.send_to_thread(event, event["thread_id"])


@asynccontextmanager
async def lifespan(_: FastAPI):
    manager.set_loop(asyncio.get_running_loop())
    task_manager.subscribe(_broadcast_task_event)
    yield


app = FastAPI(title="DeepAgents API", lifespan=lifespan)


@app.get("/api/health")
async def health_check(refresh: bool = False):
    return get_service_registry().check(refresh=refresh)

# 挂载输出目录，以便前端访问生成的静态文件
# 假设输出目录位于项目根目录下的 output
output_dir = project_root / "output"
output_dir.mkdir(exist_ok=True)

# 定义上传目录 updated
updated_dir = project_root / "updated"
updated_dir.mkdir(exist_ok=True)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
class TaskRequest(BaseModel):
    query: str
    thread_id: str = None


class FeedbackRequest(BaseModel):
    helpful: bool
    reason: str | None = None

@app.post("/api/task")
async def run_task(request: TaskRequest):
    # 1. [ID 初始化]
    thread_id = request.thread_id or str(uuid.uuid4())

    try:
        await task_manager.create(thread_id, request.query)
        await task_manager.transition(thread_id, TaskState.WAITING_CONFIRMATION, {"plan": ["确认研究目标", "检索并汇总来源"]})
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    _record_product_event("task_submitted", thread_id)

    # 3. [立即响应]
    return {"status": "waiting_confirmation", "thread_id": thread_id}


@app.get("/api/tasks/{thread_id}")
async def get_task(thread_id: str):
    try:
        return await task_manager.snapshot(thread_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Task not found.")


@app.post("/api/tasks/{thread_id}/confirm")
async def confirm_task(thread_id: str):
    try:
        task = await task_manager.transition(thread_id, TaskState.RUNNING)
    except KeyError:
        raise HTTPException(status_code=404, detail="Task not found.")
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    task.background_task = asyncio.create_task(run_deep_agent(task.query, thread_id))
    _record_product_event("plan_confirmed", thread_id)
    return {"status": task.state, "thread_id": thread_id}


@app.post("/api/tasks/{thread_id}/cancel")
async def cancel_task(thread_id: str):
    try:
        task = await task_manager.cancel(thread_id)
        return {"status": task.state, "thread_id": thread_id}
    except KeyError:
        raise HTTPException(status_code=404, detail="Task not found.")
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.post("/api/tasks/{thread_id}/feedback")
async def submit_feedback(thread_id: str, feedback: FeedbackRequest):
    try:
        await task_manager.snapshot(thread_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Task not found.")
    record = {
        "thread_id": thread_id,
        "helpful": feedback.helpful,
        "reason": feedback.reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    feedback_path = output_dir / "feedback.jsonl"
    with feedback_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")
    _record_product_event("feedback_submitted", thread_id)
    return {"status": "recorded"}


@app.post("/api/tasks/{thread_id}/export")
async def record_export(thread_id: str):
    try:
        await task_manager.snapshot(thread_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Task not found.")
    _record_product_event("report_exported", thread_id)
    return {"status": "recorded"}


def _record_product_event(name: str, thread_id: str) -> None:
    append_event(
        output_dir / "analytics.jsonl",
        ProductEvent(name=name, task_id=thread_id, timestamp=datetime.now(timezone.utc)),
    )


@app.post("/api/upload")
async def upload_files(files: List[UploadFile] = File(...), thread_id: str = Form(...)):
    """
    文件上传接口 (File Upload)。

    目标：
    1. 接收用户上传的一个或多个文件。
    2. 保存到 `updated/session_{thread_id}` 目录。
    3. 供 Agent 在后续任务中读取和分析。

    Args:
        files (List[UploadFile]): 文件对象列表。
        thread_id (str): 关联的任务会话 ID。
    """
    _validate_thread_id(thread_id)
    settings = get_settings()
    if len(files) > settings.upload_max_files:
        raise HTTPException(status_code=413, detail="Too many uploaded files.")

    # 1. [目录准备] 确保上传目录存在
    target_dir = updated_dir / f"session_{thread_id}"
    target_dir.mkdir(parents=True, exist_ok=True)

    saved_files = []
    # 2. [保存] 遍历并写入文件
    for file in files:
        filename = file.filename or ""
        basename = Path(filename).name
        if basename != filename or "/" in filename or "\\" in filename or "%2f" in filename.lower() or "%5c" in filename.lower():
            raise HTTPException(status_code=422, detail="Invalid filename.")
        if Path(basename).suffix.lower() not in settings.upload_allowed_extensions:
            raise HTTPException(status_code=415, detail="Unsupported file type.")
        content = await file.read(settings.upload_max_bytes + 1)
        if len(content) > settings.upload_max_bytes:
            raise HTTPException(status_code=413, detail="Uploaded file is too large.")
        (target_dir / basename).write_bytes(content)
        saved_files.append(basename)

    # 3. [响应] 返回成功保存的文件列表
    return {"status": "uploaded", "files": saved_files}


def _validate_thread_id(thread_id: str) -> None:
    try:
        uuid.UUID(thread_id)
    except (ValueError, AttributeError):
        if not thread_id.startswith("test-") or not thread_id[5:].replace("-", "").isalnum():
            raise HTTPException(status_code=422, detail="Invalid thread ID.")


@app.get("/api/download")
async def download_file(path: str):
    """
    文件下载接口 (File Download)。

    目标：
    1. 根据绝对路径下载文件。
    2. 严格的安全检查，防止越权访问。

    Args:
        path (str): 文件的绝对路径 (通常从 list_files 接口获取)。
    """
    # 1. [安全检查] 路径解析与越权校验
    try:
        abs_path = _resolve_output_path(path)
    except Exception:
        return {"error": "无效的路径参数"}
    # 2. [存在性检查]
    if not abs_path.exists():
        return {"error": "文件不存在"}

    # 3. [响应] 返回文件流 (浏览器自动触发下载)
    return FileResponse(abs_path, filename=abs_path.name)


@app.get("/api/files")
async def list_files(path: str):
    """
    文件列表查询接口 (File Explorer)。

    目标：
    1. 列出指定目录下的所有生成文件。
    2. 提供文件元数据（大小、时间、下载链接）。
    3. 严格的安全检查，防止路径遍历攻击。

    Args:
        path (str): 目标目录的绝对路径 (必须在 output 目录下)。
    """
    # 1. [调试] 打印请求路径
    print(f"[DEBUG] 请求文件列表: {path}")

    try:
        # 2. [解析] 获取绝对路径对象
        abs_path = _resolve_output_path(path)

    except Exception as e:
        print(f"[ERROR] 路径解析失败: {e}")
        return {"error": f"路径无效: {e}"}

    # 4. [检查] 目录是否存在
    if not abs_path.exists():
        return {"error": "目录不存在"}

    files = []
    try:
        # 5. [遍历] 递归查找所有文件
        for file_path in abs_path.rglob("*"):
            if file_path.is_file():
                # 计算相对路径，生成下载 URL
                stat = file_path.stat()
                files.append({
                    "name": file_path.name,
                    "type": "file",
                    "path": file_path.relative_to(output_dir.resolve()).as_posix(),
                    # "url": f"/outputs/{url_path}",
                    "size": stat.st_size,
                    "mtime": stat.st_mtime
                })

    except Exception as e:
        print(f"[ERROR] 遍历文件失败: {e}")
        return {"error": str(e)}

    # 6. [排序] 按修改时间倒序排列 (最新的在前)
    files.sort(key=lambda x: x.get("mtime", 0), reverse=True)
    print(f"[DEBUG] 找到 {len(files)} 个文件")
    return {"files": files}


def _resolve_output_path(path: str) -> Path:
    candidate_path = Path(path)
    if candidate_path.is_absolute() or ":" in path or "%2f" in path.lower() or "%5c" in path.lower():
        raise ValueError("Only relative output paths are allowed.")
    output_abs = output_dir.resolve()
    candidate = (output_abs / path).resolve()
    if not candidate.is_relative_to(output_abs):
        raise ValueError("Output path escaped the output directory.")
    return candidate


# 当浏览器请求 ws://localhost:8000/ws/thread_123 时：
# 1. 路由匹配 ：FastAPI 发现这个 URL 匹配了你写的 @app.websocket("/ws/{thread_id}") 。
# 2. 创建对象 ：FastAPI (基于 Starlette) 会立刻在 主事件循环 中实例化一个 WebSocket 对象。
#    - 这个对象封装了底层的 TCP 连接、HTTP 握手信息、以及后续的消息收发方法 ( send_text , receive_text 等)。
# 3. 注入参数 ：FastAPI 自动把这个刚创建好的 WebSocket 对象，作为参数传给你的 websocket_endpoint(websocket, ...) 函数。
@app.websocket("/ws/{thread_id}")
async def websocket_endpoint(websocket: WebSocket, thread_id: str):
    print(f"会话向我们发起了请求，要求简历连接：{thread_id} 对应：{websocket}")
    """
    WebSocket 实时通讯核心接口 (Real-time Communication)。

    目标：
    1. 建立长连接，实现服务端与前端的双向通信。
    2. 绑定 `thread_id`，实现会话级消息隔离。
    3. 维持心跳 (Keep-Alive)，防止连接超时。

    执行步骤：
    1. 握手：接受 WebSocket 连接请求。
    2. 注册：将连接实例绑定到 `monitor.manager`，关联 `thread_id`。
    3. 循环：进入消息监听循环，处理前端发送的心跳或指令。
    4. 异常：捕获断开连接异常，清理资源。

    Args:
        websocket (WebSocket): WebSocket 连接实例。
        thread_id (str): 当前会话的唯一标识。
    """
    # 1. [注册] 建立连接并绑定到管理器
    await manager.connect(websocket, thread_id)

    try:
        # 2. [循环] 保持连接活跃
        while True:
            # 3. [监听] 接收前端消息 (通常是 ping 心跳)
            data = await websocket.receive_text()

            # 4. [响应] 回复 pong 消息
            await websocket.send_json({
                "type": "pong",
                "message": f"服务端已收到: {data}"
            })

    except WebSocketDisconnect:
        # 5. [清理] 客户端主动断开
        manager.disconnect(websocket, thread_id)
        print(f"[WebSocket] 客户端已断开: {thread_id}")

    except Exception as e:
        # 6. [异常] 发生错误时断开
        print(f"[WebSocket] 连接异常: {e}")
        manager.disconnect(websocket, thread_id)

if __name__ == "__main__":
    uvicorn.run("api.server:app", host="0.0.0.0", port=8000, reload=True)
