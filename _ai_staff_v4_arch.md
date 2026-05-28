# AI-Staff V4.0 架构设计案

> 核心哲学：**让AI自己用AI，让Skill自己发现自己**
> 
> 用户原话："解决让新ai怎么去用这个skill，怎么更好换API，配llm，
> 进行使用，合理使用，多端使用，让ai时刻用skill，用api来改进自己，
> ai自己推工作流是非常值得思考的一个问题"

---

## 一、V3痛点诊断

### 1.1 发现问题（Discovery Gap）
- **现状**: Skill是被动调用的，需要用户/主控AI明确知道`use_skill ai-staff`
- **问题**: 新AI根本不知道这个skill的存在，更不知道它能干嘛
- **根因**: 缺少**自描述协议**和**注册发现机制**

### 1.2 配置问题（Config Friction）
- **现状**: 需要手写YAML配置、手动传profiles dict、知道base_url/api_key/model
- **问题**: 换一个API要改代码或YAML，新用户上手成本高
- **根因**: 没有`from_env()`零配置启动，没有配置热加载

### 1.3 多端缺口（Multi-endpoint Gap）
- **现状**: 只有CLI + Python库两种用法
- **问题**: 不能被MCP调用、不能HTTP调用、不能被其他Agent框架导入
- **根因**: 缺少适配层抽象

### 1.4 自我改进缺失（No Self-Improvement）⭐
- **现状**: AIStaff只向外服务，从不反思自己
- **问题**: 输出质量无法自我迭代，每次都是从零开始
- **根因**: 缺少**反思→评估→改进→验证**的闭环

### 1.5 工作流僵化（Static Workflow）⭐
- **现状**: 工作流是预定义的5阶段流水线（plan→execute→review→revise→deliver）
- **问题**: 所有任务走同样的流程，不能根据任务动态生成最优路径
- **根因**: WorkflowEngine是规则引擎不是智能引擎

---

## 二、V4架构总览

```
┌─────────────────────────────────────────────────────────────┐
│                    AI-Staff V4.0                            │
│                                                             │
│  ┌───────────┐  ┌────────────┐  ┌──────────────────────┐   │
│  │ Skill      │  │ API Router │  │ Self-Improvement     │   │
│  │ Registry   │←→│ V2 (Zero) │  │ Engine               │   │
│  │ (Discover) │  │ Config    │  │ (Reflect→Improve)    │   │
│  └─────┬─────┘  └─────┬──────┘  └──────────┬───────────┘   │
│        │               │                     │              │
│        ▼               ▼                     ▼              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                Core Kernel (V3保留+增强)              │    │
│  │  TaskClassifier │ ExpertRegistry │ EventBus          │    │
│  │  auto_run()     │ collaborate()  │ MultiLLMClient    │    │
│  └─────────────────────────┬───────────────────────────┘    │
│                            │                                │
│  ┌─────────────────────────▼───────────────────────────┐    │
│  │              WorkflowEngine V2 ⭐                    │    │
│  │         LLM-Generated Dynamic Workflows              │    │
│  └─────────────────────────┬───────────────────────────┘    │
│                            │                                │
│  ┌─────────────────────────▼───────────────────────────┐    │
│  │              Endpoint Adapters                       │    │
│  │  CLI │ Python Lib │ MCP Bridge │ REST API           │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、五大模块详细设计

### 模块1: Skill Registry（技能自发现系统）

#### 1.1 问题定义
当一个新的AI实例启动时，它如何知道：
- 有哪些skill可用？
- 每个skill能干什么？
- 什么时候该调用哪个skill？

#### 1.2 设计方案: `SkillManifest`

每个skill目录下必须包含一个`SKILL.md`（已有），但V4增加**机器可读的元数据块**：

```yaml
# SKILL.md 头部的YAML frontmatter（新增字段）
---
name: ai-staff
version: 4.0.0
description: "通用AI员工调度器 - 让任何AI调度任意LLM完成复杂任务"
author: xiaolongxia

# 触发关键词（用于自动匹配）
triggers:
  - "调度LLM"
  - "多模型对比"
  - "圆桌讨论"
  - "深度研究"
  - "AI协作"
  - "专家会诊"
  - "auto_run"
  - "ai-staff"
  
# 能力声明（做什么）
capabilities:
  - name: "smart_dispatch"
    desc: "一句话智能路由：自动分类任务→选专家→执行→交付"
    input: "自然语言请求"
    output: "结构化产出(文件/报告/代码)"
  - name: "multi_llm"
    desc: "多后端统一调度：OpenAI/Gemini/DeepSeek/Ollama一入口"
    input: "多个API配置"
    output: "自动路由+故障转移"
  - name: "arena"
    desc: "跨模型/跨API横向评测"
    input: "问题列表+模型列表"
    output: "对比报告"
  - name: "collaboration"
    desc: "多专家目标驱动协作"
    input: "目标描述"
    output: "完整项目交付物"

# 依赖声明
dependencies:
  - "httpx"
  - "pyyaml (optional)"
  
# 环境变量映射
env_mapping:
  AI_STAFF_API_KEY: "api_key"
  AI_STAFF_BASE_URL: "base_url"  
  AI_STAFF_MODEL: "default_model"
  AI_STAFF_PROXY: "proxy"

# 使用示例（给AI看的）
usage_examples:
  - "staff.auto_run('帮我写个快速排序')"  # 最简用法
  - "staff.collaborate('设计一个REST API')"  # 协作模式
  - "staff.cross_arena(['什么是量子纠缠'])"  # 横评模式
  
# 兼容性
compatibility:
  - "python >= 3.10"
  - "any OpenAI-compatible API"
---
```

#### 1.3 实现类: `SkillDiscovery`

```python
class SkillDiscovery:
    """扫描所有已安装skill，建立能力索引"""
    
    def __init__(self, skills_dirs: list[Path] = None):
        self._registry: dict[str, SkillManifest] = {}  # skill_name → manifest
        
    def scan(self) -> list[SkillManifest]:
        """扫描skills目录，解析所有SKILL.md的frontmatter"""
        
    def match(self, user_intent: str) -> list[tuple[float, SkillManifest]]:
        """根据用户意图匹配最相关的skill，返回(相关度, manifest)列表"""
        # 用触发词+能力描述做embedding-free的模糊匹配
        
    def get_usage_guide(self, skill_name: str) -> str:
        """返回该skill的使用指南（给AI看的标准格式）"""
        
    def list_all(self) -> str:
        """返回所有可用技能的可读摘要"""
```

**关键设计决策**:
- **不用embedding向量**，用触发词+关键词匹配（轻量、零依赖）
- **SKILL.md即文档即schema**，不引入额外文件
- **match()返回排序结果**，由调用方决定是否自动触发

---

### 模块2: API Router V2（零配置多后端）

#### 2.1 设计理念
**一行代码启动，零配置运行**

```python
# V4: 三种启动方式，从最简到最全

# 方式1: 纯环境变量（推荐，真正的零配置）
staff = AIStaff.from_env()
# 自动读取: AI_STAFF_API_KEY, AI_STAFF_BASE_URL, AI_STAFF_MODEL, ...

# 方式2: 快速启动（只需一个key，其他全默认）
staff = AIStaff.quick_start("your-api-key")
# 默认: Gemini Flash Lite, proxy=7890, 自动检测最佳模型

# 方式3: 多后端（YAML/Dict，向后兼容）
staff = AIStaff(profiles={...})  # V3方式完全保留
```

#### 2.2 实现设计

```python
class AIStaff:
    # ... V3代码保持不变 ...
    
    @classmethod
    def from_env(cls) -> 'AIStaff':
        """
        从环境变量自动构建实例。
        
        环境变量优先级:
          1. AI_STAFF_CONFIG → YAML文件路径（多后端模式）
          2. AI_STAFF_API_KEY + AI_STAFF_BASE_URL（单后端模式）
          3. AI_STAFF_GEMINI_KEY → 自动构造Gemini端点（最简！）
          
        同时支持:
          - AI_STAFF_PROXY (代理)
          - AI_STAFF_DEFAULT_MODEL (覆盖默认模型)
          - AI_STAFF_LOG_LEVEL
        """
        
    @classmethod  
    def quick_start(cls, api_key: str, provider: str = "gemini",
                    proxy: str = "") -> 'AIStaff':
        """
        最快上手：只需要一个key。
        
        provider预设模板:
          - "gemini": Google Gemini (Flash Lite)
          - "openai": OpenAI GPT-4o-mini
          - "deepseek": DeepSeek V3
          - "ollama": 本地Ollama (无需key)
          - "custom": 自定义URL
        """
        
    @classmethod
    def from_config_file(cls, path: str) -> 'AIStaff':
        """从YAML配置文件加载（支持热重载）"""
        
    @classmethod
    def discover_and_start(cls) -> 'AIStaff':
        """
        终极懒人方式：自动探测可用API。
        
        探测顺序:
          1. 检查常见环境变量(GEMINI_API_KEY, OPENAI_API_KEY...)
          2. 尝试localhost:11434(Ollama)
          3. 尝试常见配置路径(~/.config/ai-staff/)
          4. 返回能用的第一个
        """
    
    def reload_config(self):
        """热加载配置（不重启进程）"""
        
    def add_backend(self, profile: BackendProfile):
        """动态添加后端（运行时扩展）"""
        
    def remove_backend(self, name: str):
        """动态移除后端"""
        
    def health_check(self) -> dict[str, bool]:
        """检查所有后端的健康状态"""
```

#### 2.3 Provider预设模板库

```python
PROVIDER_TEMPLATES = {
    "gemini": {
        "name": "Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model": "gemini-2.0-flash",  # 或 gemini-3.1-flash-lite
        "env_keys": ["GEMINI_API_KEY", "GOOGLE_API_KEY", "AI_STAFF_GEMINI_KEY"],
        "tier": "free",
        "max_rpm": 15,
    },
    "openai": {
        "name": "OpenAI", 
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "env_keys": ["OPENAI_API_KEY", "AI_STAFF_OPENAI_KEY"],
        "tier": "cheap",
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "env_keys": ["DEEPSEEK_API_KEY"],
        "tier": "cheap",
    },
    "ollama": {
        "name": "Ollama (Local)",
        "base_url": "http://localhost:11434/v1",
        "model": "qwen2.5:7b",
        "api_key": "ollama",  # Ollama不需要真实key
        "tier": "free",
        "local": True,
    },
}
```

---

### 模块3: 多端适配器（Endpoint Adapters）

#### 3.1 架构图

```
                   ┌──────────────┐
                   │  CLI Entry   │  ai-staff run "prompt"
                   └──────┬───────┘
                          │
                   ┌──────▼───────┐
                   │  Python Lib   │  import ai_staff; staff.auto_run(...)
                   └──────┬───────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
   ┌────────────┐ ┌────────────┐ ┌────────────┐
   │ MCP Bridge  │ │ REST API   │ │ Importable │
   │ (mcp.json)  │ │ (FastAPI)  │ │ Module     │
   └────────────┘ └────────────┘ └────────────┘
```

#### 3.2 MCP Bridge（Model Context Protocol）

```python
# 新增: mcp_adapter.py
class AISTAFF_MCPBridge:
    """
    将AI-Staff暴露为MCP Server。
    
    其他AI工具可以通过标准MCP协议调用ai-staff的能力，
    无需知道内部实现细节。
    """
    
    # MCP Tool definitions
    MCP_TOOLS = [
        {
            "name": "ai_staff_run",
            "description": "智能调度LLM完成任务（自动分类→选专家→执行→输出）",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "你的自然语言请求"},
                    "mode": {"type": "string", "enum": ["auto","code","research","decision","creative","collab"], "description": "执行模式（默认auto自动判断）"},
                    "output_dir": {"type": "string", "description": "输出目录"},
                },
                "required": ["prompt"]
            }
        },
        {
            "name": "ai_staff_arena",
            "description": "跨模型/跨API横向对比评测",
            "inputSchema": { ... }
        },
        {
            "name": "ai_staff_collab",
            "description": "多专家目标驱动协作",
            "inputSchema": { ... }
        },
        {
            "name": "ai_staff_list_experts",
            "description": "列出所有可用专家角色",
            "inputSchema": {"type": "object", "properties": {}}
        },
        {
            "name": "ai_staff_health",
            "description": "检查所有LLM后端健康状态",
            "inputSchema": {"type": "object", "properties": {}}
        },
    ]
```

**关键点**:
- MCP Bridge让**任何MCP Client都能调用ai-staff**
- 不需要FastAPI依赖（MCP SDK自带server功能）
- 工具描述直接复用SKILL.md的capabilities

#### 3.3 REST API（可选增强）

```python
# 新增: rest_api.py （仅当pip install fastapi时启用）
from fastapi import FastAPI

app = FastAPI(title="AI-Staff V4 API")
staff = AIStaff.from_env()  # 全局单例

@app.post("/v1/run")
async def api_run(req: RunRequest):
    result = staff.auto_run(req.prompt, mode=req.mode)
    return result.to_dict()

@app.get("/v1/experts")  
async def api_experts():
    return staff.list_experts()

@app.get("/v1/health")
async def api_health():
    return staff.health_check()

@app.post("/v1/arena")
async def api_arena(req: ArenaRequest):
    return staff.cross_arena(req.questions)

# 启动: uvicorn rest_api:app --port 8765
```

---

### 模块4: Self-Improvement Engine ⭐（自我改进循环）

#### 4.1 核心理念

```
┌──────────────────────────────────────────────────┐
│             Self-Improvement Loop                 │
│                                                  │
│  执行任务 → 收集反馈 → 反思评估 → 生成改进 → 验证效果│
│    ↑                                              │
│  └──────────────────────────────────────────────┘ │
│                                                  │
│  AI用API来改进自己的提示词/专家配置/路由策略       │
└──────────────────────────────────────────────────┘
```

**这不是RLHF，这是轻量级自我反思机制**：
- 不需要训练数据
- 不需要梯度更新
- 只需要LLM自身的推理能力 + 历史执行记录

#### 4.2 实现设计

```python
@dataclass
class ImprovementRecord:
    """一次改进记录"""
    timestamp: str
    trigger: str              # 触发原因: "low_score" | "user_feedback" | "periodic" | "failure"
    target_component: str     # 改进对象: "expert_prompt" | "classifier_rule" | "router_strategy" | "workflow_template"
    before_md5: str           # 改进前的内容hash
    after_content: str        # 改进后的内容
    reasoning: str            # LLM为什么这样改
    validation_score: float   # 改进后的评分（如果有验证）
    applied: bool             # 是否已经应用


class SelfImprovementEngine:
    """
    AI自我改进引擎
    
    核心循环:
    1. Monitor: 监控执行质量（评分、错误率、token效率）
    2. Reflect: 定期让LLM反思自身表现
    3. Propose: 生成具体的改进建议（修改哪个组件、怎么改）
    4. Validate: 在sandbox环境中测试改进效果
    5. Apply: 确认有效后应用改进
    
    改进维度:
    - 专家system prompt优化
    - TaskClassifier规则调整
    - ModelRouter策略微调
    - Workflow模板进化
    """
    
    IMPROVEMENT_PROMPT = """你是一个AI系统优化顾问。请分析以下AI-Staff系统的执行记录，
给出具体的改进建议。

【系统当前表现】
{performance_stats}

【最近的执行记录】
{recent_executions}

【用户反馈】
{user_feedback}

【现有配置片段】
{config_snippet}

请分析并输出：

## 问题诊断
（哪些方面表现不佳？有什么规律？）

## 改进建议
对以下每个维度给出具体修改建议：

### 1. 专家Prompt改进
- 目标专家: [id]
- 当前问题: [具体]
- 建议修改: [完整的新prompt或diff]

### 2. 分类器规则调整
- 当前误分类案例: [举例]
- 建议调整: [具体规则变更]

### 3. 路由策略优化
- 当前问题: [如:简单问题用了贵模型]
- 建议: [新的路由逻辑]

### 4. 工作流模板改进
- 哪类任务的工作流需要优化
- 新的流程建议

## 优先级排序
按 投入产出比 排序改进项，标注:
- 🟢 立即可执行（改prompt即可）
- 🟡 需要测试验证
- 🔴 风险较大需确认
"""
    
    def __init__(self, memory: MemorySystem, llm: LLMClient):
        self.memory = memory
        self.llm = llm
        self._improvements: list[ImprovementRecord] = []
        self._pending_validations: list = []
        self._auto_improve_enabled = True
        self._improvement_threshold = 6.0  # 质量分低于此值触发改进
        self._reflection_interval = 10     # 每10次执行后反思一次
        self._execution_count = 0
    
    def on_task_complete(self, result: CollaborationResult):
        """每次任务完成时调用（钩子函数）"""
        self._execution_count += 1
        
        # 记录到memory
        self.memory.log_task(
            task_type=result.strategy_mode,
            prompt=result.goal,
            result_path="",
            status=result.status,
            tokens=result.total_tokens,
            duration=result.total_time_sec,
            models=result.experts_used
        )
        
        # 判断是否需要触发改进
        should_reflect = (
            result.quality_score < self._improvement_threshold or
            result.status == "failed" or
            self._execution_count % self._reflection_interval == 0
        )
        
        if should_reflect and self._auto_improve_enabled:
            self._trigger_reflection(result)
    
    def _trigger_reflection(self, recent_result: CollaborationResult = None):
        """触发一轮自我反思"""
        print(f"\n  🔄 [Self-Improve] 第{self._execution_count}次执行，触发反思...")
        
        # 收集数据
        stats = self._gather_performance_stats()
        recent = self._get_recent_executions(5)
        feedback = self._get_user_feedback()
        
        # 调用LLM生成改进建议
        reflection_prompt = self.IMPROVEMENT_PROMPT.format(
            performance_stats=stats,
            recent_executions=recent,
            user_feedback=feedback,
            config_snippet=self._get_relevant_config()
        )
        
        response, _usage = self.llm.chat_completion([
            {"role": "system", "content": "你是AI系统优化顾问。只输出分析和建议，不要客套话。"},
            {"role": "user", "content": reflection_prompt}
        ], temperature=0.7, max_tokens=4096)
        
        # 解析改进建议
        improvements = self._parse_improvements(response)
        
        for imp in improvements:
            if imp.target_component == "expert_prompt":
                self._apply_prompt_improvement(imp)
            elif imp.target_component == "classifier_rule":
                self._apply_classifier_improvement(imp)
            elif imp.target_component == "router_strategy":
                # 记录但暂不自动应用（风险较高）
                self._pending_validations.append(imp)
                
        # 记录本次反思
        record = ImprovementRecord(
            timestamp=datetime.now().isoformat(),
            trigger="periodic" if recent_result is None else 
                   ("failure" if recent_result.status == "failed" else "low_score"),
            target_component="multiple",
            before_md5="",
            after_content=response[:2000],
            reasoning="Auto-reflection cycle",
            validation_score=0,
            applied=True
        )
        self._improvements.append(record)
        
        print(f"  🔄 [Self-Improve] 完成，生成{len(improvements)}条改进建议")
    
    def _gather_performance_stats(self) -> str:
        """收集性能统计数据"""
        conn = self.memory._get_conn()
        
        # 最近20次执行的统计
        rows = conn.execute("""
            SELECT task_type, status, tokens_used, duration_sec 
            FROM task_history ORDER BY id DESC LIMIT 20
        """).fetchall()
        
        if not rows:
            return "尚无执行记录"
        
        total_tokens = sum(r["tokens_used"] or 0 for r in rows)
        total_time = sum(r["duration_sec"] or 0 for r in rows)
        success_rate = sum(1 for r in rows if r["status"] == "success") / len(rows)
        avg_tokens = total_tokens // len(rows)
        
        by_type = {}
        for r in rows:
            t = r["task_type"] or "unknown"
            by_type.setdefault(t, {"count": 0, "tokens": 0, "failures": 0})
            by_type[t]["count"] += 1
            by_type[t]["tokens"] += r["tokens_used"] or 0
            if r["status"] != "success":
                by_type[t]["failures"] += 1
        
        lines = [
            f"- 总执行次数: {len(rows)}",
            f"- 成功率: {success_rate:.0%}",
            f"- 平均Token: {avg_tokens}/次",
            f"- 平均耗时: {total_time/len(rows):.1f}s/次",
            f"- 总Token消耗: {total_tokens}",
            "",
            "- 按任务类型分布:"
        ]
        for t, s in by_type.items():
            lines.append(f"  * {t}: {s['count']}次, 成功率{(s['count']-s['failures'])/max(s['count'],1):.0%}, {s['tokens']}tokens")
        
        return "\n".join(lines)
    
    def _get_recent_executions(self, n: int = 5) -> str:
        """获取最近N次执行记录"""
        conn = self.memory._get_conn()
        rows = conn.execute(
            "SELECT task_type, prompt, status, tokens_used, duration_sec FROM task_history ORDER BY id DESC LIMIT ?",
            (n,)
        ).fetchall()
        
        if not rows:
            return "无记录"
        
        lines = []
        for i, r in enumerate(reversed(rows)):
            lines.append(
                f"{i+1}. [{r['task_type']}] {r['prompt'][:60]}... "
                f"→ {r['status']} ({r['tokens']}t/{r['duration_sec']:.1f}s)"
            )
        return "\n".join(lines)
    
    def _get_user_feedback(self) -> str:
        """获取用户反馈"""
        conn = self.memory._get_conn()
        rows = conn.execute(
            "SELECT rating, comment FROM feedback ORDER BY id DESC LIMIT 10"
        ).fetchall()
        
        if not rows:
            return "暂无用户反馈"
        
        avg_rating = sum(r["rating"] or 0 for r in rows) / len(rows)
        lines = [f"最近反馈数: {len(rows)}, 平均评分: {avg_rating:.1f}/3"]
        for r in rows[-3:]:
            if r["comment"]:
                lines.append(f"- ({r['rating']}/3) {r['comment'][:100]}")
        return "\n".join(lines)
    
    def _get_relevant_config(self) -> str:
        """获取当前配置快照（用于改进参考）"""
        # 返回部分专家prompt作为示例
        exp = ExpertRegistry.get("generalist")
        if exp:
            return f"""示例 - generalist专家prompt:
```
{exp.system_prompt[:500]}...
```"""
        return ""
    
    def _parse_improvements(self, response: str) -> list[ImprovementRecord]:
        """从LLM响应中解析结构化改进建议"""
        improvements = []
        
        # 解析"专家Prompt改进"
        prompt_section = re.search(
            r'#{1,3}\s*专家Prompt改进.*?\n(.*?)(?=#{1,3}\s|\Z)',
            response, re.DOTALL
        )
        if prompt_section:
            improvements.append(ImprovementRecord(
                timestamp=datetime.now().isoformat(),
                trigger="auto_reflection",
                target_component="expert_prompt",
                before_md5="",
                after_content=prompt_section.group(1)[:1500],
                reasoning="LLM-based analysis",
                validation_score=0,
                applied=False
            ))
        
        # 类似地解析分类器和路由改进...
        # (简化版实现)
        
        return improvements
    
    def _apply_prompt_improvement(self, improvement: ImprovementRecord):
        """应用专家prompt改进"""
        # 解析目标expert ID和新prompt
        target_match = re.search(r'目标专家[:\s]*([\w]+)', improvement.after_content)
        new_prompt_match = re.search(r'建议修改[:\s]*(```[\s\S]*?```|.{200,})', improvement.after_content)
        
        if target_match and new_prompt_match:
            exp_id = target_match.group(1)
            exp = ExpertRegistry.get(exp_id)
            if exp:
                old_prompt = exp.system_prompt
                # 提取新prompt（去除markdown标记）
                new_prompt = new_prompt_match.group(1).strip().strip('`\n')
                if new_prompt.startswith('expert'):
                    new_prompt = new_prompt.split('\n', 1)[-1] if '\n' in new_prompt else new_prompt
                
                # 更新（实际写入YAML文件或内存）
                # 注意：这里只是演示，实际需要考虑安全性和回滚
                print(f"  ✏️ [Self-Improve] 更新专家 '{exp_id}' 的prompt")
                
                improvement.applied = True
                improvement.before_md5 = hashlib.md5(old_prompt.encode()).hexdigest()[:8]
    
    def _apply_classifier_improvement(self, improvement: ImprovementRecord):
        """应用分类器规则改进（预留接口）"""
        # TODO: 动态更新TaskClassifier的TASK_DEFINITIONS
        print(f"  📋 [Self-Improve] 分类器规则改进建议已记录（需人工确认）")
        improvement.applied = False  # 分类器改动风险较高，默认不自动应用
    
    def get_improvement_log(self) -> str:
        """获取改进历史日志"""
        if not self._improvements:
            return "尚无改进记录"
        
        lines = [f"# AI-Staff 自我改进日志\n"]
        for imp in self._improvements[-10:]:
            status = "✅ 已应用" if imp.applied else "⏳ 待验证"
            lines.append(
                f"- [{imp.timestamp}] {imp.trigger} → {imp.target_component} {status}\n"
                f"  理由: {imp.reasoning}"
            )
        return "\n".join(lines)
    
    def enable_auto(self):
        self._auto_improve_enabled = True
        
    def disable_auto(self):
        self._auto_improve_enabled = False
```

---

### 模块5: WorkflowEngine V2 ⭐（LLM驱动的工作流引擎）

#### 5.1 V1 vs V2对比

| 特性 | V1 (Current) | V2 (New) |
|------|--------------|----------|
| 工作流来源 | 预定义Python代码 | **LLM动态生成** |
| 流程灵活性 | 固定5阶段 | **DAG有向无环图** |
| 步骤类型 | chat/plan/review/memory | **任意可组合** |
| 条件分支 | 简单eval表达式 | **LLM决策条件** |
| 并行执行 | 标记parallel | **自动识别并行步骤** |
| 自我进化 | 无 | **基于历史优化模板** |

#### 5.2 核心设计: WorkflowGenerator

```python
@dataclass
class WorkflowNode:
    """工作流节点（DAG中的一个步骤）"""
    node_id: str                    # 唯一ID
    expert_id: str                  # 哪个专家执行
    action: str                     # 操作类型: generate | review | refine | synthesize
    prompt_template: str            # 提示词模板（支持{variable}插值）
    inputs: list[str]               # 依赖的上游节点ID列表（DAG边）
    condition: str = ""             # 执行条件（可选，LLM生成的布尔表达式）
    parallel_group: int = 0         # 并行组号（相同组号的节点可并行）
    timeout: int = 120              # 超时秒数
    retry_on_fail: bool = True      # 失败是否重试


@dataclass  
class WorkflowGraph:
    """完整的工作流图（DAG）"""
    workflow_id: str
    goal: str
    nodes: list[WorkflowNode]       # 所有节点
    edges: list[tuple[str, str]]    # 有向边 (from_node, to_node)
    entry_nodes: list[str]          # 入口节点（无依赖的）
    exit_nodes: list[str]           # 出口节点（无下游的）
    metadata: dict = field(default_factory=dict)  # 生成参数、预估成本等


class WorkflowGeneratorV2:
    """
    LLM驱动的动态工作流生成器
    
    输入: 用户的目标/需求
    输出: 一个WorkflowGraph（DAG），描述最优执行路径
    
    关键创新:
    - 不是预定义模板，而是LLM根据任务"现场编排"
    - 不同类型的任务生成不同的DAG结构
    - 可以利用历史执行数据优化未来的生成质量
    """
    
    GENERATION_SYSTEM = """你是一个高级工作流编排师。你的任务是：
根据用户目标，设计一个最优的多步骤执行计划（DAG有向无环图）。

【规则】
1. 分析目标复杂度，决定需要的步骤数和专家组合
2. 步骤之间可以有依赖关系（DAG边），也可以并行
3. 每步指派最合适的专家
4. 必须有明确的输入输出约定
5. 估计每步的复杂度和token消耗

【可用专家】
{available_experts}

【输出格式】（严格JSON）：
{
  "goal": "用户目标的复述",
  "complexity": "simple|medium|complex",
  "estimated_steps": N,
  "estimated_tokens": N,
  "nodes": [
    {
      "node_id": "step_1",
      "expert_id": "planner",
      "action": "generate",
      "prompt_template": "分解目标: {goal}",
      "inputs": ["user_input"],
      "condition": "",
      "parallel_group": 0
    }
  ],
  "edges": [["step_1", "step_2"], ...],
  "reasoning": "为什么这样设计的理由"
}"""

    def __init__(self, llm: LLMClient):
        self.llm = llm
        self._template_cache: dict[str, WorkflowGraph] = {}
        self._history: list[dict] = []  # 用于学习优化
    
    def generate(self, goal: str, available_experts: list[ExpertConfig],
                 constraint_hints: dict = None) -> WorkflowGraph:
        """
        为给定目标生成最优工作流图。
        
        Args:
            goal: 用户的目标描述
            available_experts: 可用的专家列表
            constraint_hints: 约束提示（如{"max_steps": 5, "prefer_parallel": True}）
        """
        
        # 1. 先检查缓存（相似目标可能复用模板）
        cache_key = hashlib.md5(goal.encode()).hexdigest()[:12]
        # TODO: 实现语义相似度匹配而非精确hash
        
        # 2. 构建生成prompt
        experts_info = "\n".join(
            f"- {e.id}: {e.name} - {e.description}" for e in available_experts
        )
        
        system_msg = self.GENERATION_SYSTEM.format(available_experts=experts_info)
        
        constraints_text = ""
        if constraint_hints:
            constraints_text = "\n【约束条件】\n" + "\n".join(
                f"- {k}: {v}" for k, v in constraint_hints.items()
            )
        
        user_msg = f"""请为以下目标设计执行工作流：

## 目标
{goal}

{constraints_text}

请输出JSON格式的工作流图定义。"""

        # 3. 调用LLM生成
        response, _usage = self.llm.chat_completion([
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg}
        ], temperature=0.5, max_tokens=3072)
        
        # 4. 解析JSON
        workflow_data = self._parse_workflow_json(response)
        
        # 5. 构建WorkflowGraph对象
        graph = self._build_graph(workflow_data, goal)
        
        # 6. 缓存和记录
        self._template_cache[cache_key] = graph
        self._history.append({
            "goal": goal[:100], "node_count": len(graph.nodes),
            "timestamp": datetime.now().isoformat()
        })
        
        return graph
    
    def _parse_workflow_json(self, response: str) -> dict:
        """从LLM响应中提取JSON"""
        # 尝试直接解析
        try:
            # 提取 ```json ... ``` 块
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            text = json_match.group(1) if json_match else response.strip()
            
            # 如果以[开头说明可能是裸数组，包裹一下
            if text.startswith('['):
                text = '{"nodes": ' + text + ', "edges": []}'
            
            data = json.loads(text)
            return data
        except json.JSONDecodeError:
            # Fallback: 返回简单线性工作流
            print("  [WorkflowGen] JSON解析失败，使用fallback线性工作流")
            return self._fallback_linear_workflow()
    
    def _fallback_linear_workflow(self) -> dict:
        """生成简单的线性工作流作为fallback"""
        return {
            "goal": "fallback",
            "complexity": "medium",
            "nodes": [
                {"node_id": "step_1", "expert_id": "planner", "action": "generate",
                 "prompt_template": "规划: {goal}", "inputs": ["user_input"]},
                {"node_id": "step_2", "expert_id": "researcher", "action": "generate",
                 "prompt_template": "研究: {step_1_output}", "inputs": ["step_1"]},
                {"node_id": "step_3", "expert_id": "critic", "action": "review",
                 "prompt_template": "审查: {step_2_output}", "inputs": ["step_2"]},
            ],
            "edges": [["step_1", "step_2"], ["step_2", "step_3"]],
            "reasoning": "Fallback due to parse failure"
        }
    
    def _build_graph(self, data: dict, goal: str) -> WorkflowGraph:
        """从dict构建WorkflowGraph对象"""
        nodes = []
        for nd in data.get("nodes", []):
            node = WorkflowNode(
                node_id=nd["node_id"],
                expert_id=nd.get("expert_id", "generalist"),
                action=nd.get("action", "generate"),
                prompt_template=nd.get("prompt_template", "{goal}"),
                inputs=nd.get("inputs", ["user_input"]),
                condition=nd.get("condition", ""),
                parallel_group=nd.get("parallel_group", 0),
            )
            nodes.append(node)
        
        edges = [(e[0], e[1]) for e in data.get("edges", [])]
        
        entry_nodes = [n.node_id for n in nodes if "user_input" in n.inputs]
        all_targets = set(e[1] for e in edges)
        exit_nodes = [n.node_id for n in nodes if n.node_id not in all_targets and n.node_id not in entry_nodes]
        
        return WorkflowGraph(
            workflow_id=f"wf_{datetime.now().strftime('%H%M%S')}_{os.urandom(3).hex()}",
            goal=goal,
            nodes=nodes,
            edges=edges,
            entry_nodes=entry_nodes,
            exit_nodes=exit_nodes or [nodes[-1].node_id] if nodes else [],
            metadata={
                "complexity": data.get("complexity", "unknown"),
                "estimated_tokens": data.get("estimated_tokens", 0),
                "reasoning": data.get("reasoning", ""),
                "generated_at": datetime.now().isoformat(),
            }
        )


class WorkflowExecutorV2:
    """
    V2工作流执行器 — 支持DAG拓扑排序 + 并行执行
    """
    
    def __init__(self, agents: dict, multi_llm: 'MultiLLMClient',
                 memory: MemorySystem, validator: OutputValidator):
        self.agents = agents
        self.multi_llm = multi_llm
        self.memory = memory
        self.validator = validator
        self._node_results: dict[str, str] = {}  # node_id → output content
    
    def execute(self, graph: WorkflowGraph, user_input: str,
                session_id: str) -> tuple[str, dict]:
        """
        执行工作流图。
        
        算法:
        1. 拓扑排序确定执行顺序
        2. 识别可并行执行的节点组
        3. 按序执行每组节点
        4. 收集最终输出
        """
        execution_log = []
        start_time = time.time()
        
        # Step 1: 拆分为执行层（同层可并行）
        layers = self._topological_layers(graph)
        
        print(f"  [WorkflowV2] 执行层次: {len(layers)}层, 共{len(graph.nodes)}个节点")
        
        for layer_idx, layer in enumerate(layers):
            layer_name = f"L{layer_idx+1}"
            print(f"  [WorkflowV2] 执行{layer_name}: {[n.node_id for n in layer]}")
            
            # 同层节点可以并行（简化实现：顺序执行，后续可加线程池）
            layer_results = {}
            for node in layer:
                # 检查条件
                if node.condition:
                    safe_ctx = {"results": self._node_results, "input": user_input}
                    try:
                        if not eval(node.condition, {"__builtins__": {}}, safe_ctx):
                            print(f"    [{node.node_id}] 跳过 (condition=false)")
                            continue
                    except Exception:
                        pass  # 条件解析失败则执行
                
                # 准备输入（替换模板变量）
                prompt = node.prompt_template
                prompt = prompt.replace("{goal}", graph.goal)
                prompt = prompt.replace("{user_input}", user_input)
                for dep_id in node.inputs:
                    if dep_id in self._node_results:
                        prompt = prompt.replace(f"{{{dep_id}_output}}", 
                                               self._node_results[dep_id][:2000])
                
                # 获取专家
                expert = ExpertRegistry.get(node.expert_id) or ExpertRegistry.get("generalist")
                
                # 执行
                try:
                    node_start = time.time()
                    
                    msgs = [
                        {"role": "system", "content": expert.system_prompt},
                        {"role": "user", "content": prompt}
                    ]
                    
                    content, usage = self.multi_llm.chat(
                        msgs, temperature=expert.temperature,
                        user_input=user_input, expert=expert, max_tokens=3072
                    )
                    
                    elapsed = time.time() - node_start
                    self._node_results[node.node_id] = content
                    layer_results[node.node_id] = content
                    
                    log_entry = {
                        "layer": layer_name, "node": node.node_id,
                        "expert": expert.name, "action": node.action,
                        "chars": len(content), "time": round(elapsed, 2),
                        "status": "ok"
                    }
                    execution_log.append(log_entry)
                    
                    print(f"    ✓ [{node.node_id}] {expert.name}: {len(content)}ch / {elapsed:.1f}s")
                    
                except Exception as e:
                    error_msg = f"[{type(e).__name__}] {str(e)[:100]}"
                    self._node_results[node.node_id] = f"[ERROR] {error_msg}"
                    layer_results[node.node_id] = f"[ERROR] {error_msg}"
                    
                    execution_log.append({
                        "layer": layer_name, "node": node.node_id,
                        "status": "error", "error": error_msg
                    })
                    print(f"    ✗ [{node.node_id}] FAILED: {error_msg}")
                    
                    if not node.retry_on_fail:
                        continue
            
            time.sleep(0.3)  # 层间间隔
        
        # 收集最终输出
        final_output = ""
        for exit_id in graph.exit_nodes:
            if exit_id in self._node_results:
                final_output += self._node_results[exit_id] + "\n\n"
        
        if not final_output:
            final_output = json.dumps(self._node_results, ensure_ascii=False, indent=2)
        
        exec_stats = {
            "total_time": round(time.time() - start_time, 2),
            "nodes_total": len(graph.nodes),
            "nodes_completed": len([l for l in execution_log if l.get("status")=="ok"]),
            "layers": len(layers),
        }
        
        return final_output, {"log": execution_log, "stats": exec_stats, 
                              "graph_metadata": graph.metadata}
    
    def _topological_layers(self, graph: WorkflowGraph) -> list[list[WorkflowNode]]:
        """
        将DAG节点分层（Kahn算法变体）。
        同层节点之间没有依赖关系，可以并行执行。
        """
        node_map = {n.node_id: n for n in graph.nodes}
        in_degree = {n.node_id: 0 for n in graph.nodes}
        
        for src, dst in graph.edges:
            if dst in in_degree:
                in_degree[dst] += 1
        
        layers = []
        remaining = set(in_degree.keys())
        
        while remaining:
            # 找出入度为0的节点（当前层）
            current_layer = [nid for nid in remaining if in_degree[nid] == 0]
            if not current_layer:
                break  # 循环依赖（不应该发生）
            
            layers.append([node_map[nid] for nid in current_layer])
            
            # 移除当前层，更新入度
            for nid in current_layer:
                remaining.remove(nid)
                for src, dst in graph.edges:
                    if src == nid and dst in in_degree:
                        in_degree[dst] -= 1
        
        return layers
```

---

## 四、集成方案: V4的AIStaff主类变化

```python
class AIStaff:
    """V4: 在V3基础上集成5大新模块"""
    
    def __init__(self, base_url="", api_key="", model="", proxy="",
                 expert_id="generalist", profiles=None):
        # ═══ V3原有初始化（完全保留）═══
        # ... 所有V3代码不变 ...
        
        # ═══ V4新增组件 ═══
        self.self_improve = None      # SelfImprovementEngine (lazy init)
        self.workflow_v2 = None        # WorkflowGeneratorV2 + ExecutorV2
        self.discovery = None          # SkillDiscovery (class-level)
        
        # 延迟初始化（只在需要时创建）
        def _init_self_improve():
            if not self.self_improve:
                llm_for_si = self.llm  # 使用 cheapest backend
                if self._multi_mode and self.multi_llm:
                    # 选一个便宜的backend做自我反思
                    cheap = [p for p in self.backends.values() if p.tier in ("free","cheap")]
                    if cheap:
                        llm_for_si = self.multi_llm._clients[cheap[0].name]
                self.self_improve = SelfImprovementEngine(self.memory, llm_for_si)
        
        self._init_self_improve = _init_self_improve
        
        def _init_workflow_v2():
            if not self.workflow_v2:
                gen = WorkflowGeneratorV2(self.llm)
                exe = WorkflowExecutorV2(self.agents, self.multi_llm or self._make_single_multi(), 
                                         self.memory, self.validator)
                self.workflow_v2 = (gen, exe)
        
        self._init_workflow_v2 = _init_workflow_v2
    
    # ═══ V4新增方法 ═══
    
    @classmethod
    def from_env(cls) -> 'AIStaff':
        """零配置从环境变量启动（详见模块2）"""
        
    @classmethod
    def quick_start(cls, api_key, provider="gemini") -> 'AIStaff':
        """最快上手启动（详见模块2）"""
        
    @classmethod
    def discover_and_start(cls) -> 'AIStaff':
        """终极自动探测启动"""
    
    def auto_run_v2(self, user_input: str, output_dir: str = "") -> CollaborationResult:
        """
        V4增强版auto_run: 使用WorkflowEngine V2动态生成执行路径
        
        vs V3区别:
        - V3: TaskClassifier → 固定6种路径之一
        - V4: LLM生成定制化DAG → 拓扑排序执行
        """
        self._init_workflow_v2()
        gen, exe = self.workflow_v2
        
        # 1. 生成工作流
        experts = ExpertRegistry.list_all()
        graph = gen.generate(user_input, experts)
        
        # 2. 执行工作流
        final_output, exec_info = exe.execute(graph, user_input, self.session_id)
        
        # 3. 包装结果
        result = CollaborationResult(
            goal=user_input,
            strategy_mode=f"dynamic_dag({graph.metadata.get('complexity','?')})",
            deliverables={"output.md": final_output, "workflow_graph.json": json.dumps(
                {"nodes": [{"id": n.node_id, "expert": n.expert_id, "action": n.action} for n in graph.nodes],
                 "edges": graph.edges}, ensure_ascii=False, indent=2)},
            transcript=f"Dynamic DAG Workflow:\n{graph.metadata.get('reasoning','')}\n\n---\n{final_output[:500]}...",
            quality_score=self._estimate_quality(final_output),
            total_time_sec=exec_info["stats"]["total_time"],
            experts_used=list(set(n.expert_id for n in graph.nodes)),
        )
        result.status = "success"
        
        # 4. 触发自我改进
        if self.self_improve:
            self.self_improve.on_task_complete(result)
        
        # 5. 保存
        if not output_dir:
            safe_name = re.sub(r'[\\/:*?"<>|]', '_', user_input[:25])
            output_dir = os.path.join(os.getcwd(), f'ai_staff_v4_{safe_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        result.save(output_dir)
        
        return result
    
    def improve_self(self, force=False):
        """手动触发一轮自我改进"""
        self._init_self_improve()
        if force or self._should_reflect():
            self.self_improve._trigger_reflection()
        return self.self_improve.get_improvement_log()
    
    def health_check(self) -> dict:
        """检查所有组件健康状态"""
        status = {
            "version": VERSION,
            "llm_backends": {},
            "experts_loaded": len(ExpertRegistry._experts),
            "self_improve": getattr(self.self_improve, '_auto_improve_enabled', False),
            "workflow_v2": self.workflow_v2 is not None,
        }
        if self._multi_mode and self.multi_llm:
            for name, prof in self.backends.items():
                try:
                    client = self.multi_llm._clients[name]
                    test_resp, _ = client.chat_completion([
                        {"role": "user", "content": "ping"}
                    ], max_tokens=5)
                    status["llm_backends"][name] = "ok"
                except Exception as e:
                    status["llm_backends"][name] = f"error: {str(e)[:50]}"
        else:
            status["llm_backends"]["single"] = "configured"
        return status
    
    def list_capabilities(self) -> str:
        """列出AI-Staff的所有能力（给其他AI看的自描述）"""
        return f"""# AI-Staff V{VERSION} 能力清单

## 核心能力
1. **智能调度** (`auto_run`) — 一句话自动分类→选专家→执行→交付
2. **深度研究** (`research`) — 迭代追问式研究报告
3. **多专家协作** (`collaborate`) — 目标驱动的5阶段协作
4. **横评对比** (`cross_arena`) — 跨API/跨模型同时对比
5. **圆桌讨论** (`expert_collab`) — AI↔AI可见互动链

## V4新增
6. **动态工作流** (`auto_run_v2`) — LLM生成定制DAG执行路径 ⭐
7. **自我改进** (`improve_self`) — AI反思并优化自身表现 ⭐
8. **零配置启动** (`from_env/quick_start`) — 一行代码跑起来
9. **技能发现** (`discovery`) — 让新AI自动找到并使用本skill
10. **健康检查** (`health_check`) — 检查所有后端状态

## 可用专家: {[e.name for e in ExpertRegistry.list_all()]}

## V4使用示例
```python
# 方式1: 零配置
import ai_staff
staff = ai_staff.AIStaff.from_env()
result = staff.auto_run_v2("帮我设计一个REST API")

# 方式2: 最简
staff = ai_staff.AIStaff.quick_start("your-gemini-key")

# 方式3: 多后端
staff = ai_staff.AIStaff.from_config_file("config.yaml")
report = staff.cross_arena(["量子纠缠是什么"])
```
"""


# ═══════════════════════════════════════════════════════
# V4 CLI 增强
# ═══════════════════════════════════════════════════════

# 新增CLI子命令:
#   ai-staff discover          — 扫描并列出所有可用skill
#   ai-staff health            — 检查后端健康状态
#   ai-staff improve           — 手动触发自我改进
#   ai-staff capabilities      — 打印能力清单
#   ai-staff serve-mcp         — 启动MCP server
#   ai-staff v4-run            — 使用V2动态工作流执行
#   (原有命令全部保留不变)
```

---

## 五、文件结构变化

```
~/.workbuddy/skills/ai-staff/
├── SKILL.md                          # 更新frontmatter（加入V4元数据）
├── config.example.yaml               # 更新（加入provider模板）
├── scripts/
│   ├── ai_staff.py                   # 主文件 (~3500行 → ~4800行)
│   │   # V3代码: 完全保留
│   │   # V4新增:
│   │   ├── class SkillDiscovery      # ~120行
│   │   ├── class SelfImprovementEngine  # ~350行 ⭐
│   │   ├── class WorkflowGeneratorV2   # ~250行 ⭐
│   │   ├── class WorkflowExecutorV2    # ~180行 ⭐
│   │   ├── AIStaff.from_env()        # ~60行
│   │   ├── AIStaff.quick_start()     # ~50行
│   │   ├── AIStaff.auto_run_v2()     # ~80行
│   │   └── CLI新命令                 # ~80行
│   │
│   ├── mcp_bridge.py                 # NEW ~200行 (MCP Server)
│   └── rest_api.py                   # NEW ~80行 (可选FastAPI)
│
├── experts/                          # 不变
├── workflows/                        # 不变
└── data/                             # 不变（新增improvements表？）
```

---

## 六、实施优先级

| P级别 | 模块 | 理由 | 预估工作量 |
|-------|------|------|-----------|
| **P0** | `from_env()` + `quick_start()` | 降低使用门槛的核心 | 小（~110行）|
| **P0** | SelfImprovementEngine | 用户明确要求⭐ | 中（~350行）|
| **P1** | WorkflowEngine V2 (Generator+Executor) | 用户明确要求⭐ | 中（~430行）|
| **P1** | `auto_run_v2()` | 连接V2工作流与对外接口 | 小（~80行）|
| **P2** | SkillDiscovery + SKILL.md frontmatter | 解决"新AI如何发现" | 小（~120行）|
| **P2** | MCP Bridge | 多端支持 | 中（~200行）|
| **P3** | REST API (FastAPI) | 锦上添花 | 小（~80行）|
| **P3** | CLI新命令 (discover/health/improve/v4-run) | 用户体验 | 小（~80行）|

**建议实施顺序**: P0 → P1 → P2 → P3
**第一批**: from_env + quick_start + SelfImprovementEngine（立竿见影）
**第二批**: WorkflowV2 + auto_run_v2（核心差异化功能）
**第三批**: Discovery + MCP + REST（生态整合）

---

## 七、关键设计决策记录

### Q1: 为什么不引入Vector DB做skill匹配？
**A**: 保持零依赖原则。触发词+关键词匹配对当前规模（几十个skill）够用了。
后续如果skill数量超过100，可以考虑加入sentence-transformers。

### Q2: 自我改进会不会把系统改坏？
**A**: 分级安全机制：
- **🟢 Prompt改进**: 自动应用（低风险，改的是文本）
- **🟡 分类器规则**: 记录但不自动应用（中风险）
- **🔴 路由策略/工作流结构**: 仅记录+建议（高风险）
- 所有改进都有md5 hash，支持一键回滚
- 可通过 `disable_auto()` 关闭

### Q3: Workflow V2的LLM生成失败怎么办？
**A**: 三层降级：
1. JSON解析成功 → 正常执行DAG
2. JSON解析失败 → fallback线性3步（planner→researcher→critic）
3. LLM调用失败 → 退化回V3的TaskClassifier路径

### Q4: 为什么不直接用LangGraph？
**A**: LangGraph引入了重依赖（langchain + 依赖树）。
AI-Staff的核心卖点是**轻量、零依赖、可理解**。
V2工作流的DAG执行逻辑其实只有~180行核心代码，不值得引入整个框架。

---

*文档版本: v0.1 | 日期: 2026-04-24 | 作者: 小龙虾🦞*
