# AI-Staff V4.0 架构设计方案

> 审查时间: 2026-04-24 | 基于V3代码深度审查(4929行/26类)

---

## 一、现状诊断（痛点清单）

### P0 — 必须修复
1. **单文件4929行**：26个类全部塞在`ai_staff.py`，无法维护
2. **AIStaff上帝类1869行**：主调度器承担路由/编排/执行/记忆/改进等所有职责
3. **零测试覆盖**：没有任何单元/集成测试
4. **TaskClassifier误分类**："Python vs Go"被分为code而非decision

### P1 — 需要增强
5. **SelfImprovementEngine**：骨架完整(411行)，但`_parse_improvements`正则解析脆弱
6. **WorkflowEngine V2**：完整实现(323行)，但JSON解析fallback太简单
7. **SkillDiscovery**：只有文档描述，无实际实现
8. **MCPBridge / REST API**：完全缺失
9. **BOM字符/语法错误**：已修复但反映开发质量问题

### P2 — 可选优化
10. **httpx代理参数传递方式不兼容**：新版本需要`proxy=`dict形式
11. **pyproject.toml版本号过时**：仍写2.2.0

---

## 二、V4模块化架构设计

### 2.1 目标目录结构

```
ai-staff/
├── __init__.py              # 版本导出 + 快捷函数
├── core/                     # 核心引擎层
│   ├── __init__.py
│   ├── staff.py             # AIStaff主类（精简版，~400行，只做编排）
│   ├── task_classifier.py   # 任务分类器（独立）
│   └── types.py             # 所有dataclass/type定义集中
├── backends/                # API后端层
│   ├── __init__.py
│   ├── client.py            # LLMClient（OpenAI兼容）
│   ├── multi_client.py      # MultiLLMClient（多后端统一）
│   ├── router.py            # ModelRouter（智能路由）
│   ├── fallback.py          # FallbackManager（级联降级）
│   └── profiles.py         # BackendProfile定义
├── experts/                  # 专家系统
│   ├── __init__.py
│   ├── registry.py          # ExpertRegistry（YAML加载+热加载）
│   └── builtin.yaml         # 内置专家配置
├── agents/                   # Agent子代理
│   ├── __init__.py
│   ├── base.py              # BaseAgent
│   ├── cot_agent.py         # 思维链Agent
│   ├── executor.py          # 执行Agent
│   ├── reviewer.py           # 审查Agent
│   └── memory.py            # 记忆Agent
├── workflow/                 # 工作流引擎
│   ├── __init__.py
│   ├── engine_v1.py         # V1静态管道（保留兼容）
│   ├── engine_v2.py         # V2动态DAG（LLM生成）
│   ├── generator_v2.py       # DAG生成器
│   ├── executor_v2.py       # DAG拓扑排序执行
│   └── checkpoint.py        # 断点续传
├── self_improve/             # 自我改进引擎
│   ├── __init__.py
│   ├── engine.py            # SelfImprovementEngine
│   └── records.py          # ImprovementRecord
├── skills/                   # 技能发现系统（NEW）
│   ├── __init__.py
│   ├── registry.py          # SkillRegistry（发现/注册/热加载）
│   └── protocol.py         # Skill协议定义
├── endpoints/                # 多端点支持（NEW）
│   ├── __init__.py
│   ├── rest_api.py         # REST-like HTTP接口
│   ├── mcp_bridge.py       # MCP协议桥接（基础版）
│   └── cli.py               # 增强CLI
├── infra/                    # 基础设施
│   ├── __init__.py
│   ├── event_bus.py         # 事件总线
│   ├── budget.py            # Token预算管理
│   ├── validator.py         # 输出质量校验
│   ├── memory.py            # SQLite记忆系统
│   └── checkpoint.py        # 断点管理
├── config.example.yaml       # 配置模板
├── examples/                 # 示例脚本
│   ├── v4_full_demo.py      # V4全链路Demo ⭐
│   ├── v4_self_improve.py  # 自我改进Demo
│   └── v4_dag_workflow.py  # 动态工作流Demo
├── tests/                    # 测试（NEW！）
│   ├── test_classifier.py
│   ├── test_router.py
│   ├── test_workflow_v2.py
│   ├── test_self_improve.py
│   └── test_e2e.py
└── README.md                 # 重写文档
```

### 2.2 核心数据流

```
用户输入 → TaskClassifier → 策略选择
                              │
                              ├─ direct → LLMClient.chat() → 输出
                              │
                              ├─ code   → coder→critic → 输出
                              │
                              ├─ research → researcher迭代追问 → report
                              │
                              ├─ decision → 多专家分析→综合结论
                              │
                              ├─ collaborate → 5阶段协作流程
                              │
                              └─ auto_v2 → WF-GenV2生成DAG → WF-ExecV2执行
                                         │
                                    ↓ (每完成一个任务)
                              SelfImprovementEngine.on_task_complete()
                              → 质量评分 < 6.0? → 触发反思循环
```

### 2.3 关键接口定义

```python
# 核心接口: SkillProtocol (skills/protocol.py)
class SkillProtocol:
    """技能自描述协议 — AI-to-AI发现的基础"""
    skill_id: str
    name: str
    version: str
    description: str
    capabilities: list[Capability]     # 每个能力=名称+输入+输出
    compatibility: list[str]           # 可协作的skill ID列表
    
    def discover(query: str) -> bool: ...
    def manifest(self) -> dict: ...

# SkillRegistry (skills/registry.py)
class SkillRegistry:
    """动态技能注册表"""
    _skills: dict[str, SkillProtocol]
    
    def register(skill: SkillProtocol): ...     # 注册
    def unregister(skill_id: str): ...         # 注销
    def hot_reload(skill_id: str): ...        # 热重载
    def search(query: str) -> list: ...        # 意图匹配
    def all_manifests(self) -> str: ...         # AI可读的能力总览

# REST API (endpoints/rest_api.py)
class RestAPI:
    """轻量HTTP接口（基于标准库，无额外依赖）"""
    routes = {
        "POST /run": auto_run,
        "POST /v2/run": auto_run_v2,       # 动态DAG
        "GET /experts": list_experts,
        "GET /health": health_check,
        "POST /improve": improve_self,
        "GET /capabilities": capabilities,
        "POST /chat": chat_single,
    }
```

---

## 三、各模块详细设计

### 3.1 Skill Registry（新增⭐）

**核心理念**: 每个Skill是一个自描述的Python包/模块，ai-staff运行时扫描并加载。

```python
# 使用示例
staff = AIStaff.quick_start("your-key")
staff.skills.search("写代码")  # → 返回匹配的skill
staff.skills.all_manifests()     # → 返回所有能力的AI-readable描述

# 自定义skill
@ai_staff.skill(name="calculator", version="1.0")
class CalculatorSkill:
    """计算器技能 - 支持数学运算和单位转换"""
    capabilities = [
        Capability("calculate", "数学表达式", "计算结果"),
        Capability("convert", "值+源单位+目标单位", "转换结果"),
    ]
```

**实现策略**: V4先用简化版（基于YAML文件扫描），不做完整的插件系统。够用就好。

### 3.2 API Router 增强

当前状态：
- ✅ `from_env()` — 自动检测环境变量
- ✅ `quick_start(key)` — 一键启动
- ✅ `discover_and_start()` — 终极懒模式
- ✅ `from_config_file(yaml)` — YAML多后端
- ✅ `reload_config()` — 热重载

需要增强：
- 🔧 `add_backend(profile)` 运行时动态添加后端
- 🔧 健康检查增加延迟测试（不只是ping）
- 🔧 后端优先级调整接口

### 3.3 Self-Improvement Cycle 增强

当前问题：`_parse_improvements()` 用正则从LLM文本中提取结构化建议，脆弱且不可靠。

增强方案：
1. 要求LLM输出JSON格式（已在REFLECTION_PROMPT中要求但未强制执行）
2. JSON解析失败时用更智能的fallback
3. 改进记录持久化到SQLite（当前只在内存）
4. 增加`rollback()` 回滚能力

### 3.4 Workflow Engine V2

当前实现已较完整（Generator + Executor + TopoSort）。

需要增强：
1. JSON解析失败时的线性workflow fallback已实现✅
2. 并行节点执行目前是串行的🔧（需asyncio或线程池）
3. 条件表达式执行用eval()有安全风险🔧（需限制__builtins__)

### 3.5 多端点支持

**REST API**（基于标准库`http.server`）:
```python
# 启动服务
python ai_staff.py serve --port 8080 --api-key KEY

# 调用
curl -X POST http://localhost:8080/v2/run \
  -H "Content-Type: application/json" \
  -d '{"prompt": "帮我写个快排"}'
```

**MCP Bridge**（基础版，仅暴露核心方法）:
```python
# mcp.json 配置
{
    "mcpServers": {
        "ai-staff": {
            "command": "python",
            "args": ["-m", "ai_staff.mcp_server"],
            "env": {"AI_STAFF_API_KEY": "..."}
        }
    }
}
```

---

## 四、实施路线图

### Phase 1: 架构重构（拆分单文件）
- [ ] 创建包结构（core/backends/experts/agents/workflow/...）
- [ ] 将26个类按职责拆分到对应模块
- [ ] 保持向后兼容（`from ai_staff import AIStaff` 仍然可用）
- [ ] 修复TaskClassifier误分类bug

### Phase 2: 新功能实现
- [ ] Skill Registry（YAML扫描版）
- [ ] REST API端点（http.server实现）
- [ ] MCP Bridge基础版
- [ ] SelfImprovement增强（JSON输出+SQLite持久化）

### Phase 3: Demo + 文档
- [ ] V4全链路Demo（验证所有新模式）
- [ ] 更新README.md
- [ ] 更新config.example.yaml
- [ ] 补充基础测试

---

## 五、关键决策记录

| 决策 | 选择 | 原因 |
|------|------|------|
| 拆分粒度 | 8个子包 | 平衡模块化和复杂度 |
| REST框架 | 标准库http.server | 零依赖，够用 |
| 并行执行 | 暂不实现(asyncio改动大) | V4.1再考虑 |
| Skill格式 | YAML（非Python包） | 降低使用门槛 |
| 测试框架 | pytest（已在dev-dependencies） | 主流选择 |
