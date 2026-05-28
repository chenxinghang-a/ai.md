# Agent/AI驱动构建成果描述

## 项目：LoomLLM — 多后端AI智能体协作框架

### 核心痛点

在实际开发中，我面临三个关键痛点：**一是多LLM后端切换成本高**，每次切换API（DeepSeek/Gemini/Qwen等）需要重写调用逻辑和错误处理，效率极低；**二是单模型能力有边界**，简单问答浪费高端模型token，复杂推理用低端模型质量不够，缺乏按任务复杂度自动路由的机制；**三是多Agent协作缺乏质量闭环**，传统pipeline式协作只做"分工-拼接"，没有迭代审查，输出质量不可控。

### 核心逻辑流

**1. 长链推理：V5闭环协作循环（CollabLoop）**

不同于单次生成，V5循环包含完整的「规划→执行→审查→修订」四阶段闭环。规划器（Planner）将用户意图拆解为子任务链；执行器（Executor）按专家角色（8个内置专家）分别完成；审查器（Reviewer）从完整性、准确性、格式三个维度评分，低于阈值则自动触发修订轮。典型链路：用户输入→TaskClassifier分类→ExpertRegistry匹配专家→Planner生成策略→Executor多轮执行→Reviewer评分→（不达标则回退修订）→输出。最复杂的research模式支持多轮自动追问，单次任务可触发5+轮LLM调用。

**2. 多Agent协作：Arena横评 + Backend自动路由**

Arena模式下，同一问题并行投递到多个LLM后端（如DeepSeek和Gemini），收集各模型回复后进行横向对比评测，输出综合分析报告。日常使用中，TaskClassifier基于规则引擎（关键词+长度启发式）零token消耗地将任务分为direct/code/research/decision/creative五类，自动选择最优后端。新增的`chat(backend="gemini")`参数支持手动指定后端，切换时自动处理代理配置差异（国产直连、海外走proxy），失败自动fallback到备选后端。

**3. 质量门控：Score驱动迭代**

Reviewer对每次输出进行0-100分评估，低于quality_threshold（默认80）自动触发修订。修订不是简单重试，而是将审查意见（缺失点、错误修正建议）注入下一轮prompt，形成真正的迭代优化。实测中，代码类任务平均1.3轮达标，研究类任务平均2.1轮。

**成果量化**：框架已支持10个LLM Provider（含国产直连和海外代理），8个专家角色，5种执行模式，单后端最低延迟1.0s/56tok，多后端横评可并行3+模型。项目已开源至GitHub（LoomLLM仓库）。
