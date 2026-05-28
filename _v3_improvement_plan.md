# AI-Staff V2.3 → V3.0 改造方案

> 基于Gemini Round 1 深度诊断 + 自主分析
> 时间: 2026-04-24 12:25

---

## 🔴 Gemini原话（最核心的批评）

> **"你的AI专家不是在'协作'，而是在'排队朗读自己的台词'"**
>
> **"将'信息共享'等同于'智能协作'"**
> **"输出只是过程，不应该是结果"**
> **"缺乏真正的Agentic Behavior和动态问题解决能力"**

---

## 📊 差距总结（vs CrewAI/AutoGen/LangGraph/MetaGPT）

| 维度 | 竞品 | ai-staff V2.3 | 差距 |
|------|------|--------------|------|
| Agent自主性 | ✅ 自主决定行动 | ❌ 固定for循环 | **致命** |
| 目标导向 | ✅ 有明确产出目标 | ❌ 只"讨论话题" | **致命** |
| 互动机制 | 提问/委托/修正/投票 | ❌ 只能顺序发言 | **严重** |
| 任务→策略映射 | 自动识别+路由 | 只有简单复杂度分 | 中等 |
| 开箱即用 | pip install即可 | 需要手动配API写脚本 | 高 |
| 可玩性/有趣 | 可视化/有趣交互 | 纯txt输出 | **高** |

---

## 🎯 V3.0 改造方案（P0优先级，5项）

### P0-1: 从"圆桌讨论"升级为"目标驱动协作引擎"

**问题**: 当前expert_collab只接受topic参数，目标是"聊天"
**改为**: 接受goal + deliverable参数，目标是"交付成果"

```
# 旧接口
staff.expert_collab(topic="如何设计AI原生OS")

# 新接口
staff.collaborate(
    goal="设计一个AI原生操作系统的核心架构",      # 要解决什么问题
    deliverables=["架构图.md", "技术选型表.csv"],   # 交付什么产物
    participants=["planner", "coder", "researcher", "critic"],
    max_rounds=4
)
```

**实现思路**:
```python
def collaborate(self, goal, deliverables=None, ...):
    # Phase 1: 规划师分解任务
    plan = self._call_expert("planner", f"将以下目标分解为可执行步骤:\n{goal}")
    
    # Phase 2: 各领域能人认领+执行
    for step in plan.steps:
        best_expert = self._match_expert(step)  # 自动匹配最合适的人
        result = self._execute_step(best_expert, step)
        
        # Phase 3: 审查员审查产出
        review = self._call_expert("critic", f"审查以下产出:\n{result}")
        
        # Phase 4: 如果不通过，打回重做
        if not review.passed:
            revision = self._call_expert(best_expert.id, f"根据以下反馈修改:\n{review.feedback}\n原文:{result}")
    
    # Phase 5: 汇总所有deliverables
    return self._package_deliverables()
```
**复杂度**: 中 | **预期效果**: 从"聊天记录"变成"可交付的工作成果"

---

### P0-2: 引入互动协议（Interaction Protocol）

**问题**: 专家只能顺序发言，没有提问/反驳/修正等动作
**改为**: LLM选择下一个动作类型，而非固定流程

**设计5种互动动作**:
```python
@dataclass
class InteractionAction:
    action_type: str    # speak / question / challenge / refine / delegate
    target: str = ""    # 向谁提问/反驳/委托（专家ID）
    content: str = ""   # 内容
    confidence: float = 0.0  # 对自己观点的置信度
```

**协议流程**:
```
每轮每个专家不是直接"发言"，而是：
1. 先看当前讨论状态（谁说了什么、有没有冲突、离目标多远）
2. 选择动作：我是该发言？还是反驳某人？还是向某人提问？
3. 执行动作
4. 下一个专家基于新状态继续...
```

**伪代码**:
```python
def collaboration_loop(self, goal, experts):
    state = CollaborationState(goal=goal)
    
    while not state.is_complete and state.round < max_rounds:
        current_expert = state.next_speaker()  # 不固定顺序！LLM决策
        
        # 让LLM决定做什么动作
        action = self._decide_action(current_expert, state)
        
        if action.type == "speak":
            response = self._call_llm(expert, state.context)
            state.add_message(expert, response)
            
        elif action.type == "question":
            response = self._call_llm(expert, f"向{action.target}提问: {action.content}")
            state.add_question(expert, action.target, response)
            # 被问者自动获得下一轮发言权
            state.set_next_speaker(action.target)
            
        elif action.type == "challenge":
            response = self._call_llm(expert, f"对{action.target}的观点提出质疑...")
            state.add_challenge(expert, action.target, response)
            
        elif action.type == "refine":
            # 根据他人反馈改进自己的观点
            original = state.get_expert_last_msg(expert)
            feedback = state.get_feedback_for(expert)
            improved = self._call_llm(expert, f"根据反馈改进:\n原文:{original}\n反馈:{feedback}")
            state.replace_last_message(expert, improved)
    
    return state.to_report()  # 结构化报告，不只是txt
```
**复杂度**: 高 | **预期效果**: 从"排队念稿"变成"真正的AI辩论与协作"

---

### P0-3: TaskClassifier — 任意任务→最优策略自动映射

**问题**: 用户输入任务后，不知道该用什么专家组合和提示词策略
**改为**: 自动分类+最优配置推荐

```python
class TaskClassifier:
    """自动识别任务类型并推荐最优执行策略"""
    
    TASK_PATTERNS = {
        "code": {
            "keywords": ["写代码", "实现", "function", "debug", "bug", "程序", "算法"],
            "experts": ["planner", "coder", "critic"],
            "prompt_strategy": "先规划再编码再审查",
            "output_format": "code + explanation",
        },
        "analysis": {
            "keywords": ["分析", "对比", "评估", "研究", "原因", "趋势", "数据"],
            "experts": ["researcher", "analyst", "critic"],
            "prompt_strategy": "深度挖掘→多维分析→质量把关",
            "output_format": "markdown report with tables",
        },
        "creative": {
            "keywords": ["创意", "设计", "文案", "故事", "脑暴", "想法", "命名"],
            "experts": ["writer", "planner", "critic"],
            "prompt_strategy": "发散思维→结构化表达→审美审查",
            "output_format": "rich text with visual elements",
        },
        "decision": {
            "keywords": ["应该", "选择", "建议", "哪个好", "优缺点", "比较"],
            "experts": ["researcher", "planner", "critic"],
            "prompt_strategy": "信息收集→方案对比→权衡决策",
            "output_format": "comparison table + recommendation",
        },
        "qa_learning": {
            "keywords": ["解释", "什么是", "为什么", "怎么", "原理", "教程"],
            "experts": ["teacher", "researcher"],
            "prompt_strategy": "概念拆解→类比举例→检验理解",
            "output_format": "structured lesson with examples",
        },
    }
    
    def classify(self, user_input: str) -> TaskStrategy:
        # 用关键词+LLM双重分类
        keyword_match = self._keyword_match(user_input)
        llm_refinement = self._llm_classify(user_input) if needs_llm else None
        return self._merge(keyword_match, llm_refinement)


# 使用方式（用户零配置）:
# staff.auto_run("帮我写一个Python爬虫抓取微博热搜") 
# → 自动识别为code任务 → planner分解需求 → coder写代码 → critic审查
# staff.auto_run("我应该买Mac还是Windows笔记本?")
# → 自动识别为decision任务 → researcher收集信息 → planner对比分析 → critic给建议
```
**复杂度**: 中 | **预期效果**: 用户只需说"我要什么"，框架自动搞定一切

---

### P0-4: 一键体验模式（Zero-config Quick Start）

**问题**: 新用户需要配API Key、装依赖、写脚本才能跑
**改为**: 开箱即用的交互体验

```bash
# 安装
pip install ai-staff

# 一键启动交互模式（自动读取环境变量或引导配置）
ai-staff run

# 或者一行命令出结果
ai-staff quick "帮我分析一下React vs Vue的选择" -o report.txt

# 内置示例（无需任何API配置就能看到效果）
ai-staff demo          # 用内置mock数据展示完整能力
ai-staff demo-collab   # 展示圆桌讨论效果
```

**首次运行引导**:
```
$ ai-staff run
🦞 AI-Staff V3.0 首次启动

检测到未配置API。请选择:
  [1] Gemini (免费，推荐新手)     ← 输入Key即可
  [2] OpenAI (GPT-4o)             ← 需要付费Key  
  [3] DeepSeek (性价比高)         ← 国内可用
  [4] Ollama本地模型              ← 完全免费但需GPU
  [5] 我有多个API想一起用          ← 进阶玩法

选择 [1-5]: 1
请输入你的Gemini API Key: ____________________

✅ 配置完成！已保存到 ~/.ai-staff/config.yaml

现在可以试试:
  ai-staff quick "你的问题"           # 快速问答
  ai-staff collab -t "讨论话题"        # 圆桌讨论
  ai-staff research -t "研究主题"      # 深度研究
```
**复杂度**: 低 | **预期效果**: 5分钟内从安装到跑通第一个结果

---

### P0-5: 输出从"过程记录"升级为"价值交付"

**问题**: 当前只输出txt聊天记录，用户拿到手不知道有什么用
**改为**: 多格式结构化产出

```python
# collaborate() 返回的不是纯文本字符串，而是:
@dataclass
class CollaborationResult:
    goal: str
    status: str  # success / partial / failed
    
    # 核心交付物
    deliverables: dict[str, str]  # {"architecture.md": "...", "decision.csv": "..."}
    
    # 完整过程记录（可选查看）
    transcript: str               # 完整对话txt
    interaction_log: list[dict]   # 结构化互动日志 JSON
    decision_trace: list[dict]    # 决策链（谁说了什么→导致什么结论）
    
    # 质量指标
    quality_score: float          # 0-10
    expert_agreement: float       # 专家共识度 0-1
    rounds_used: int
    
    def save(self, output_dir):
        """一键保存所有产出"""
        os.makedirs(output_dir, exist_ok=True)
        # 保存每个deliverable
        for name, content in self.deliverables.items():
            with open(f"{output_dir}/{name}", 'w') as f:
                f.write(content)
        # 保存完整报告
        self.save_report(f"{output_dir}/report.md")
        # 保存互动可视化
        self.save_interaction_graph(f"{output_dir}/interaction.html")
```

用户拿到的不再是一个txt，而是一个完整的文件夹:
```
my_project/
├── report.md              # 总报告
├── architecture.md        # 架构文档（规划师生成）
├── code_implementation.py # 代码（工程师生成）
├── review_notes.md        # 审查意见（审查员生成）
├── interaction.html       # 互动可视化（可浏览器打开）
└── full_transcript.txt    # 完整聊天记录
```
**复杂度**: 中 | **预期效果**: 拿到的是**可交付的工作成果**，不是聊天记录

---

## 🔄 改造路线图

### Phase 1（本次完成）: P0-1 + P0-3 + P0-5
- `collaborate()` 方法替代/增强 `expert_collab()`
- TaskClassifier 自动分类系统
- CollaborationResult 结构化输出

### Phase 2（后续）: P0-2 + P0-4
- Interaction Protocol 互动协议（复杂度高，需仔细设计）
- CLI一键体验 + 首次引导配置

### Phase 3（未来）:
- Web UI（Streamlit/FastAPI）
- 更多内置专家模板库
- 社区分享的prompt marketplace

---

*基于 Gemini 2.5 Flash 深度诊断 + 自主分析生成*
