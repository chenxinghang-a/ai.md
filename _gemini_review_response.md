# Gemini Review (gemini-3.1-flash-lite-preview, 6.3s)

作为AI系统架构师，针对 `ai-staff V4` 项目的审查意见如下：

### 1. 代码质量：Top 3 坏味道
1. **`staff.py` 的“上帝类”倾向**：1900行代码承担了路由、初始化、状态管理、日志显示等职责。
   - **建议**：将 `AIStaff` 拆分为 `Dispatcher`（路由）、`Manager`（生命周期管理）和 `Reporter`（格式化输出）。
2. **硬编码的逻辑依赖**：`collab_loop.py` 内部耦合了 `StructuredFeedback` 的解析逻辑（正则匹配）。一旦模型输出格式微调，正则极易失效。
   - **建议**：引入 `Pydantic` 进行结构化输出校验，利用 LLM 的 `response_format={"type": "json_object"}` 强制约束。
3. **脆弱的错误处理**：`rest_api.py` 和 `staff.py` 中存在大量的 `try-except` 吞掉异常或简单返回 `None`。
   - **建议**：定义统一的 `StaffException` 体系，区分“网络错误”、“模型拒绝”、“格式解析错误”，以便在 API 层返回对应的 HTTP 状态码。

### 2. 产品落地：缺口优先级
1. **P0 (可用性)**：**流式响应（Streaming）**。目前 API 是同步等待整个循环结束，用户体验极差。必须支持 `Server-Sent Events (SSE)`。
2. **P1 (鲁棒性)**：**会话持久化**。目前 `MemorySystem` 看起来是内存驻留，重启即丢失。需要接入 `SQLite` 或 `TinyDB` 存储 `trace_id` 和上下文。
3. **P2 (配置化)**：**YAML 配置文件**。不要在代码里写死 `profiles`，支持 `config.yaml` 热更新，方便用户切换模型而无需改代码。

### 3. AI 互动性：从“轮流发言”到“真正讨论”
当前的 `CollabLoop` 是单向的：`Executor → Reviewer`。
- **改进方案：引入“辩论协议”**。
  - 在 `StructuredFeedback` 中增加一个 `debate_rounds` 字段。
  - 当 Reviewer 给出低分时，不直接进入 `Revising`，而是触发一个 `Refutation` 阶段：允许 `Executor` 对 `Reviewer` 的批评进行辩解（例如：“因为上下文限制，无法实现功能X，建议方案Y”）。
  - 让 `Reviewer` 看到辩解后再下最终结论。这能显著降低“AI 盲目听从错误指令”的概率。

### 4. 部署与开源：必须做的
1. **环境变量管理**：接入 `python-dotenv`，代码中严禁出现任何 API Key 的硬编码逻辑，必须强制读取 `.env`。
2. **依赖隔离**：目前使用 `http.server` 这种玩具方案，开源需提供 `requirements.txt` 和 `Dockerfile`，并提供一个基于 `FastAPI` 的 `server.py` 替代方案作为推荐生产部署方式。
3. **示例库**：在 `examples/` 目录下提供 3 个具体场景：`code_gen.py` (代码重构), `research.py` (深度搜索), `creative.py` (文案策划)。

### 5. 架构风险：技术债
- **状态机的不可控增长**：随着 `CollabPhase` 增加，`collab_loop.py` 将成为下一个 1000 行的“上帝类”。
- **缓解策略**：将每个 `Phase` 的处理逻辑移至独立的 `Handler` 类（策略模式），`CollabLoop` 只负责状态转换调度，不负责具体逻辑。

### 6. 下一步：1小时内最该做的 3 件事
1. **解耦正则解析**：将 `collab_loop.py` 中解析反馈的正则逻辑抽离成独立的 `Parser` 类，并编写至少 5 个单元测试（测试不同风格的回复是否能被正确解析）。
2. **引入 Pydantic**：将所有 `dataclass` 升级为 `pydantic.BaseModel`，利用其校验能力替代手动解析，这是提升系统稳定性的最快手段。
3. **增加 `trace_id` 注入**：确保所有日志输出和异常抛出都带上 `trace_id`，否则在生产环境中排查“某次循环为何失败”将是噩梦。

**架构师寄语**：V4 已经完成了“能动”的阶段，V5 的核心目标应该是“可观测”与“可控”。不要试图让一个模型解决所有问题，而要让你的 `CollabLoop` 成为一个“协议层”，确保任何模型进入该协议都能按预期协作。