# Deep Search Pro Agent Instructions

本文件是项目级、可持续迭代的 Agent 指令与事实基线，作用域覆盖仓库根目录及所有子目录。

任何 Agent 在分析、设计、修改、测试或清理本项目之前，必须先完整阅读本文件。若代码现状与本文冲突，以实际代码和最新验证结果为准，并在任务完成时同步更新本文。

## 1. 项目目标

当前项目是一个多智能体深度研究与文档生成原型，正在被整理为面向 **Coze AI 产品实习生**岗位的面试项目。

面试版项目优先证明以下能力：

1. C 端 Agent 核心任务链路设计与体验优化。
2. 多 Agent 的意图识别、任务规划、工具路由与协作过程。
3. Agent 回复质量、任务完成效果和失败案例的评估方法。
4. Prompt、路由策略或工作流策略的版本化迭代。
5. 基于埋点、漏斗、用户反馈和评测数据进行产品判断。
6. 对 AI Native 产品、可解释过程、人工介入和结果可信度的理解。

不要把项目继续扩展为无边界的“万能 Agent 平台”。在 1-2 周面试准备周期内，优先交付一个清晰场景、一条完整链路、一套评测方法和一个稳定演示。

## 2. 当前产品定位

推荐面试定位：

> 面向个人复杂任务的多 Agent 深度研究工作台。用户提交问题和资料后，系统自动规划任务，调度网络搜索、个人知识库和数据分析 Agent，展示执行过程与来源，最终生成可追问、评价和导出的研究报告。

目标体验链路：

```text
输入复杂任务
-> 识别意图与生成执行计划
-> 用户确认或调整计划
-> 多 Agent 执行检索与分析
-> 实时展示进度、来源和异常
-> 用户可补充信息、暂停、重试或接管
-> 生成结构化结果与文档
-> 用户追问、评价、纠错或导出
-> 反馈进入评测与策略迭代
```

当前代码中的业务叙事并不一致：主 Agent 面向空调公司，数据库 Agent 的描述却是药品、库存和销售数据。任何面试版改造都必须先统一目标用户、业务场景、示例数据和 Prompt，不得继续保留互相矛盾的业务设定。

## 3. 当前系统流程

1. 调用方生成或提交 `thread_id`。
2. 调用方可通过 `POST /api/upload` 上传附件。
3. 调用方连接 `WS /ws/{thread_id}` 接收过程事件。
4. 调用方通过 `POST /api/task` 提交任务。
5. 后端创建 `output/session_{thread_id}/` 并复制上传文件。
6. `run_deep_agent()` 设置会话目录与线程上下文。
7. 主 Agent 根据 Prompt 调用网络搜索、数据库或 RAGFlow 子 Agent。
8. 主 Agent 汇总结果，并可调用文件工具生成 Markdown/PDF。
9. `ToolMonitor` 通过 WebSocket 推送工具调用、子 Agent 和最终结果。
10. 任务结束后重置 `ContextVar`。

当前没有可靠的任务状态持久化、事件重放、取消、重试或多连接支持。WebSocket 建连前产生的事件可能丢失。

## 4. 仓库结构与职责

```text
agent/       主 Agent、子 Agent、模型和 Prompt 加载
api/         FastAPI、WebSocket、会话上下文和过程事件
prompt/      主/子 Agent 的 YAML Prompt 配置
tools/       MySQL、Tavily、RAGFlow、文件读取与文档生成工具
utils/       路径解析和 Word/PDF 转换等复用实现
rawflow/     RAGFlow 示例与实验代码，不属于生产主链路
test/        测试目录；当前 test_01.py 为空
updated/     用户上传的运行时文件
output/      Agent 生成的运行时文件
```

模块边界：

- `api/` 负责协议、鉴权、输入校验、任务生命周期和事件传输。
- `agent/` 负责规划、路由、决策和结果汇总。
- `tools/` 负责外部能力，必须自行处理参数校验、权限、超时和结构化错误。
- `utils/` 不应包含业务状态和外部服务编排。
- `prompt/prompts.yml` 是 Agent 行为配置来源；修改时必须同步评测用例。
- `rawflow/` 中的代码不得被生产入口隐式调用。
- `output/`、`updated/`、`.venv/` 和缓存目录不属于源码。

## 5. 核心文件

- `api/server.py`：HTTP/WebSocket 入口。
- `api/monitor.py`：过程事件和 WebSocket 连接管理。
- `api/context.py`：`thread_id` 与会话目录的 `ContextVar`。
- `agent/main_agent.py`：主 Agent 创建和异步执行链路。
- `agent/llm.py`：模型初始化。
- `agent/prompts.py`：加载 YAML Prompt。
- `prompt/prompts.yml`：主/子 Agent 的角色和策略。
- `tools/db_tools.py`：MySQL 工具。
- `tools/tavily_tool.py`：公开网络搜索工具。
- `tools/ragflow_tools.py`：内部知识库工具。
- `tools/upload_file_read_tool.py`：上传文件读取。
- `tools/markdown_tools.py`：Markdown 生成。
- `tools/pdf_tools.py`、`utils/word_converter.py`：Markdown 转 PDF。
- `utils/path_utils.py`：工具路径解析。

`AGENTS.md` 是唯一持续更新的项目事实与 Agent 规范入口。`docs/superpowers/specs/` 和 `docs/superpowers/plans/` 只保存已批准的阶段设计与实施计划快照，不承担持续同步项目现状的职责。不得再创建第二份持续迭代的项目上下文文档。

## 6. 开发环境

项目使用 Windows 和 Python 3.13。

仓库内已有隔离环境 `.venv`。所有 Python、pip、测试和服务命令必须优先使用该环境，不得默认使用系统 Python。

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m uvicorn api.server:app --host 127.0.0.1 --port 8000
```

PDF 转换依赖 Windows、Microsoft Word 和 COM。仅安装 Python 依赖不代表 PDF 链路可用。

环境变量只能记录名称和用途，禁止在日志、文档、测试输出或回复中暴露实际值。主要变量包括：

- `LLM_QWEN_MAX`
- `LLM_QWEN3`（默认优先于 `LLM_QWEN_MAX`）
- `LLM_MODEL`（显式指定时优先于所有候选）
- `DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL`（DeepSeek OpenAI 兼容配置；默认模型为 `deepseek-v4-flash`）
- `OPENAI_API_KEY`
- `DASHSCOPE_API_KEY`（`OPENAI_API_KEY` 的 DashScope 兼容别名）
- `OPENAI_BASE_URL`
- `ZHIHU_ACCESS_SECRET`
- `TAVILY_API_KEY`（遗留 Tavily 工具使用；面试版将由知乎全网搜索替换）
- `MYSQL_HOST`、`MYSQL_PORT`、`MYSQL_USER`、`MYSQL_PASSWORD`、`MYSQL_DATABASE`
- `RAGFLOW_API_KEY`、`RAGFLOW_API_URL`

## 7. 当前验证基线

最后更新：2026-08-09。

已确认：

- `.venv` 已创建。
- `requirements.txt` 可在 Python 3.13 的 `.venv` 中完成安装。
- `.venv` 中 `pip check` 返回无依赖冲突。
- Python 源码可完成语法编译。
- FastAPI、DeepAgents、LangChain/LangGraph、MySQL、RAGFlow、文档相关包可导入。
- `api.server` 可导入并创建名为 `DeepAgents API` 的 FastAPI 应用。
- 项目已初始化 Git，当前分支为 `main`。
- 后端自动化测试基线为 61 条，覆盖设置、模型兼容、契约、知乎搜索、健康检查、路径与上传安全、只读 SQL、RAGFlow 降级、任务生命周期、真实评测执行边界、埋点与离线端到端流程。
- 前端具有 React/TypeScript 桌面工作台、Vitest 组件/状态测试、生产构建和 Playwright 浏览器流程。
- 评测目录包含 30 条固定样本和 V1/V2 Prompt 快照；两版均已在 DeepSeek V4 Flash、相同 90 秒超时和相同外部服务状态下真实运行 30 条，脱敏聚合结果见 `docs/interview/evaluation-report.md`。

进一步实测已确认：

- FastAPI 可实际监听，Swagger 与 OpenAPI 可访问。
- WebSocket 可建立连接并完成中文 `ping/pong`。
- 文件上传可保存到对应会话目录。
- 知乎开放平台全网搜索 API 真实请求返回 HTTP 200、API Code 0 和有效内容。
- Word COM 可完成 Markdown 到 PDF 转换。
- 真实服务可创建等待确认的任务、读取恢复快照，并通过版本化事件管理任务状态。
- 确定性离线端到端流程已覆盖任务创建、计划确认、WebSocket、终态结果、反馈、文件列表、PDF 下载和导出埋点。
- 浏览器级模拟流程覆盖任务提交、计划确认、多 Agent 过程、透明降级、报告、反馈和导出失败恢复，并在 1024×768、1440×900、1920×1080 三个视口生成并检查截图。
- Figma 文件 `8GP7rnke9XmoqQuAUJ3JiX` 已创建计划确认、透明降级执行和带来源报告三个可编辑关键画面，并逐帧渲染检查。

当前未通过或处于阻塞状态：

- MySQL 返回 1045 `Access denied`，面试版先使用透明 demo 降级。
- RAGFlow 服务地址返回 502，面试版先使用透明 demo 降级。
- Windows GBK 控制台 Unicode 输出问题已改为 ASCII 安全日志，并有回归覆盖。
- 当前环境未配置知乎凭据，网络研究会透明降级；因此 V1/V2 的 URL 型引用指标均为 0，不能把自动评分等同于事实正确或引用完整性。
- 人工盲评尚未执行；不得把自动评分描述为人工评审结论。

不得把“模块可导入”描述成“项目端到端可运行”。每次更新通过状态时必须附有当次实际执行命令和结果。

## 8. 安全红线

以下问题在公开部署或正式演示前优先处理：

1. 服务缺少认证、授权、会话归属和调用限额。
2. 任务状态、事件缓存和连接管理仍是单进程内存实现，不适合多实例部署。
3. WebSocket 当前每个任务只保存一个活动连接，尚不支持同任务多客户端。
4. 上传已限制标识、文件名、大小、数量和类型，但尚无全局并发与用户配额。
5. `.env` 和 `(1).env` 含敏感配置；不得提交、打印或复制其值。

已落地的代码级约束：会话路径拒绝绝对路径与越界；文件 API 仅返回输出目录相对路径；SQL 工具仅允许有限的单条只读查询；公开错误不回传原始服务异常。

测试数据库能力时：

- 只允许执行只读查询。
- 优先调用 `list_sql_tables`，再做有限行数的 `SELECT`。
- 不执行 `INSERT`、`UPDATE`、`DELETE`、`DROP`、`ALTER`、`TRUNCATE` 或存储过程。
- 不以“测试”为由修改外部数据库或 RAGFlow 数据。

## 9. 严谨递归删除文件

项目存在 `(1)` 重复副本、缓存、运行产物和会话文件。任何删除都必须遵守：

1. 未经用户明确授权，不删除任何文件或目录。
2. 删除前解析并展示目标绝对路径，确认目标位于本仓库明确子目录内。
3. 禁止对仓库根目录、磁盘根目录、用户目录、未解析变量、通配符根路径执行递归删除。
4. 删除 `(1)` 副本前重新计算哈希，并确认源码、配置、IDE 和外部脚本无引用。
5. 优先使用可恢复操作；无法恢复时，先生成完整删除清单并再次确认范围。
6. PowerShell 下使用单一 Shell 和 `-LiteralPath`，不得跨 Shell 拼接删除目标。
7. 删除后记录删除对象、验证结果和恢复方式。

## 10. 变更原则

- 先读取相关文件和当前工作区状态，不覆盖用户已有修改。
- 改动保持局部，遵循现有模块边界，不做无关重构。
- 修复缺陷前先复现并定位根因。
- 新功能和缺陷修复必须补充与风险相称的测试。
- 路径、SQL、上传、外部工具和 WebSocket 改动必须包含异常和边界用例。
- 不通过 Prompt 代替代码级安全约束。
- 外部工具结果应逐步改为结构化 schema，不依赖普通字符串判断成功或失败。
- 不在模块导入阶段执行不必要的网络请求或打印完整 Prompt。
- 面试版优先交付可演示闭环，不扩展账号、计费、多租户等非核心能力。

## 11. 面试版产品验收

面试版至少应提供：

1. 一条 5 分钟内可稳定完成的核心任务链路。
2. 任务输入、计划确认、执行过程、结果与反馈的关键界面或高保真原型。
3. 明确的目标用户、问题、现有替代方案和价值指标。
4. 约 20-30 条代表性 Agent 评测样本。
5. 意图识别、工具路由、任务完成、事实正确、引用完整和用户体验的评测维度。
6. 至少一组 Prompt/策略迭代前后对比。
7. 核心漏斗和埋点设计，例如任务提交、计划确认、首次有效结果、任务完成、追问、导出和反馈。
8. 对失败案例、安全边界、成本和时延的复盘。

## 12. 验证要求

按改动范围选择并实际运行：

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m compileall -q agent api tools utils rawflow test
.\.venv\Scripts\python.exe -m pytest -q
```

若测试目录仍无用例，必须明确报告 `no tests ran`，不得声称测试通过。

涉及 API 时，还应验证：

- 服务启动与关闭。
- `/docs` 或 OpenAPI 可访问。
- 上传、任务、文件列表和下载接口。
- WebSocket 建连、心跳、事件顺序、断开和重连。

涉及 Agent 时，还应记录：

- 输入样本和预期工具路由。
- 实际工具调用序列。
- 最终结果、引用、耗时和失败原因。
- 外部调用是否真实执行，还是使用 mock/stub。

## 13. 文档维护规则

每次任务完成后，检查是否需要更新本文件：

- 产品定位或目标用户改变。
- 新增、删除或重命名模块。
- API、WebSocket 事件或任务状态改变。
- 新增环境变量或外部依赖。
- 验证基线发生变化。
- 新发现或解决安全风险。
- 面试版范围、评测指标或演示流程改变。

更新时直接修正文档中的现状，不要只追加流水账。必要时在下方记录关键变化。

## 14. 关键变更记录

| 日期 | 变化 | 验证 |
| --- | --- | --- |
| 2026-08-08 | 创建项目级 `AGENTS.md`，确立 Coze 面试目标、项目边界、安全规则和验证基线 | 对照当前仓库结构、`.venv`、Git 状态和既有项目调研记录 |
| 2026-08-08 | 批准 Coze 面试版设计；确定 ChatGPT 式桌面工作台、知乎全网搜索、真实服务优先与透明 demo 降级；将本文件设为唯一持续迭代文档 | 知乎 API 真实请求通过；FastAPI/WebSocket/上传/Word PDF 通过；模型、MySQL、RAGFlow 阻塞原因已定位 |
| 2026-08-09 | `(1).env` 加载、DashScope 变量别名与模型优先级已兼容；Qwen3 候选优先于旧的 Qwen Max 候选 | `pytest` 58 条通过；`pip check` 和编译通过；切换后健康检查仍返回 `LLM_AUTH_FAILED`（HTTP 401），未输出任何密钥 |
| 2026-08-09 | 接入 DeepSeek V4 Flash 并关闭该模型的 thinking 模式以兼容工具强制调用；完成 V1/V2 各 30 条真实评测与固定任务三次 API 验证 | DeepSeek 直连和工具调用通过；V1 完成 8/30，V2 完成 24/30；固定任务三次均 `succeeded`（70.0、12.3、8.2 秒）；详情见 `docs/interview/evaluation-report.md`，人工盲评仍未开始 |
