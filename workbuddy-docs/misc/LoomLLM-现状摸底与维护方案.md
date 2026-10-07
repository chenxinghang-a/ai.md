# LoomLLM 现状摸底与维护方案

> 摸底时间：2026-09-15
> 范围：`C:\Users\cxx`（已排除 `AppData`、`node_modules`、`.git` 内部对象）
> 方式：**全程只读**。未修改/移动/删除任何文件，未 commit/push，未 pip install，未解压 zip。

---

## 0. 结论速览（先看这段）

| 问题 | 结论 |
|---|---|
| LoomLLM 是不是成型项目？ | **是**。真项目、有 git 历史、有 README/论文/PyPI 打包，不是下载的第三方包 |
| 作者是谁？ | 就是你自己。论文作者「陈星行」= GitHub `chenxinghang-a`，仓库 remote 指向你自己的仓库 |
| 活仓库在哪？ | `C:\Users\cxx\WorkBuddy\Claw\loomllm-pkg\ai_staff_v4`（唯一带 `.git` + GitHub remote 的目录） |
| 队列说的「10 Provider」属实吗？ | **属实**，`backends/smart_init.py:172-288` 明确列了 10 个。但**只有 9 个真能用**，Anthropic 鉴权未适配 |
| 🔴 最紧急的事 | **一个真实 Gemini API Key 已明文提交并 push 到公开仓库**（详见 §5.1）。这比代码维护重要得多，请优先处理 |
| 本机能跑吗？ | **不能直接跑**。Python 3.13.14 有，但 `httpx`/`pyyaml`/`pytest` 都没装，`ai_staff_v4` 也没装 |
| 推荐维护路线 | **路线 A：最小维护**（先安全止血 → 同步远程 → 补一个 CI）。不建议现在重构 |

---

## 1. 定位真身

### 1.1 找到的所有 LoomLLM 相关物

全盘 `find` 结果（`C:\Users\cxx`，排除 AppData/node_modules/.git 内部）：

| # | 路径 | 性质 | 判定依据 |
|---|---|---|---|
| A | `C:\Users\cxx\WorkBuddy\Claw\loomllm-pkg\ai_staff_v4\` | ✅ **活仓库（唯一真身）** | 含 `.git/`，remote = `https://github.com/chenxinghang-a/LoomLLM.git`，branch `main`，工作区干净，13 个 commit |
| B | `C:\Users\cxx\Downloads\LoomLLM-main.zip` | 📦 **下载副本（GitHub 归档）** | 123,957 字节，61 个条目。zip 注释 = `c1d6a3d3524c4271987e9add0a92baad37eaf15d`（GitHub 归档会写入 commit SHA），该 SHA 经 GitHub API 确认存在（2026-04-25T09:03:58Z），但**不在本地仓库历史里** |
| C | `C:\Users\cxx\WorkBuddy\Claw\loomllm-pkg\` | 📤 **导出/打包目录** | = A 的父目录 + `dist/loomllm-1.0.0-py3-none-any.whl` + `dist/loomllm-1.0.0.tar.gz` + `loomllm.egg-info/`，构建于 2026-04-25 16:18 |
| D | `C:\Users\cxx\WorkBuddy\Claw\LoomLLM_毕业论文.docx` | 📄 **本项目的论文**（不是别的项目） | 已提取正文验证：标题《基于多模型协作的迭代式大语言模型应用框架设计与实现》，摘要明确写「本文设计并实现了 LoomLLM」，作者「陈星行」。另有副本在 `C:\Users\cxx\Documents\xwechat_files\...\2026-04\LoomLLM_毕业论文(1).docx` |
| E | `C:\Users\cxx\WorkBuddy\Claw\_test_loomllm_gemini.py` | 🧪 **手写测试脚本** | 24 行，`from ai_staff_v4 import AIStaff` + `staff.chat("1+1等于几？")` |
| F | `C:\Users\cxx\WorkBuddy\Claw\.git\` | 🔗 **外层备份仓库** | remote = `https://github.com/chenxinghang-a/ai.md.git`，里面也提交了一份 `loomllm-pkg/` 的拷贝 |

**关键结论**：**只有 A 是「活」的**。B 是 2026-04-25 17:03 从 GitHub 下的一份快照（内容对应 79cde11 那一版，`main_mod/staff.py` blob 大小 75681 与 commit 79cde11 完全一致）；C 是 A 的打包产物目录。三者内容基本同源，**不存在「两个不同的 LoomLLM 项目」**。

> ⚠️ 顺带纠正一条旧记忆：`C:\Users\cxx\WorkBuddy\Claw\.workbuddy\memory\2026-04-29.md:13` 写着「LoomLLM 和 ai_staff_v4 是两个独立 GitHub 仓库」——**这是错的**。`ai_staff_v4` 就是 LoomLLM 仓库里的 Python 包名（`pyproject.toml:6` name = `loomllm`，`pyproject.toml:56` 打包 `ai_staff_v4*`）。是**一个项目，包名和项目名不一致**，不是两个仓库。

### 1.2 本地 vs GitHub 的同步状态

| 项 | 值 |
|---|---|
| 本地 HEAD | `79cde11` "feat: English-first codebase + PyPI packaging"（2026-04-25） |
| 本地 `origin/main` 引用 | `79cde11`（同上，说明最后一次 fetch 停在这） |
| GitHub 真实 `main` | `cd34cd58` "fix: strip newlines in auto-save directory names (WinError 123)"（2026-04-26T07:53:19Z） |
| 差异 | **本地落后远程 1 个 commit** |
| 佐证 | `C:\Users\cxx\WorkBuddy\Claw\.workbuddy\memory\2026-04-26.md:4` 记录「LoomLLM(main分支): commit cd34cd5, 3处 `re.sub(...)` → 加 `\n\r`, 已push」 |

> 注：`git fetch --dry-run` 因代理 `127.0.0.1:7890` 未启动而失败；上表 GitHub 侧数据来自 GitHub REST API（只读）。

---

## 2. 结构盘点

### 2.1 目录树（2–3 层）

```
C:\Users\cxx\WorkBuddy\Claw\loomllm-pkg\
├── ai_staff_v4/                    ← 活仓库（Python 包）
│   ├── .git/                       ← 13 commits, remote: chenxinghang-a/LoomLLM
│   ├── .gitignore
│   ├── .cache/                     ← 运行时缓存（已 gitignore）
│   │   └── smart_init_v2_cache.json
│   ├── .ai_staff_memory.db         ← SQLite 会话记忆（585 KB，已 gitignore）
│   ├── agents/                     ← AI 子智能体
│   │   ├── base.py  cot.py  executor.py  memory_agent.py  reviewer.py  types.py
│   │   └── collab_loop.py          ← ★ 826 行，V5 协作闭环核心
│   ├── backends/                   ← LLM 后端层
│   │   ├── client.py               ← ★ 通用 OpenAI 兼容 HTTP 客户端
│   │   ├── multi_client.py  router.py  fallback.py  profile.py
│   │   └── smart_init.py           ← ★ 929 行，10 Provider 定义 + 零配置扫描
│   ├── core/                       ← 基础设施
│   │   ├── budget.py  constants.py  events.py  memory.py  validation.py  verbose.py
│   ├── experts/                    ← 专家角色
│   │   ├── classifier.py  registry.py  experts.yaml（6 个角色）
│   ├── examples/                   ← 6 个示例
│   │   └── simple.py  code_gen.py  creative.py  research.py  research_flow.py  expert_task.py
│   ├── main_mod/                   ← 编排层
│   │   ├── staff.py                ← ★★ 1629 行，AIStaff 主类（上帝类）
│   │   └── startup.py              ← 365 行
│   ├── tests/
│   │   └── test_core.py            ← 246 行，20 个测试方法
│   ├── output/                     ← 运行产物（已 gitignore）
│   │   └── arena_demo.md  chat_log.txt
│   ├── __init__.py  __main__.py  getting_started.py
│   ├── _count_code_lines.py  _count_lines.py   ← 开发脚本（已 gitignore，但被打进了 whl）
│   ├── config_template.yaml  pyproject.toml  requirements.txt  MANIFEST.in  py.typed
│   ├── README.md  README_CN.md  DESIGN.md  GUIDE.md  USAGE.md  ARCH_FLOWCHART.html  LICENSE
├── dist/
│   ├── loomllm-1.0.0-py3-none-any.whl    ← 104,731 B
│   └── loomllm-1.0.0.tar.gz              ← 93,859 B
├── loomllm.egg-info/
├── DESIGN.md  LICENSE  README.md  README_CN.md  pyproject.toml  requirements.txt
```

### 2.2 代码规模

统计口径：`find . -name "*.py" -not -path "./.git/*" -not -path "*__pycache__*"`

- **文件数：40 个 `.py`**
- **总行数：6,804 行**

按文件排序（Top 15）：

| 行数 | 文件 |
|---:|---|
| 1629 | `main_mod/staff.py` |
| 929 | `backends/smart_init.py` |
| 826 | `agents/collab_loop.py` |
| 365 | `main_mod/startup.py` |
| 291 | `core/verbose.py` |
| 247 | `experts/classifier.py` |
| 246 | `tests/test_core.py` |
| 236 | `core/memory.py` |
| 219 | `backends/multi_client.py` |
| 200 | `experts/registry.py` |
| 169 | `agents/types.py` |
| 153 | `backends/client.py` |
| 145 | `getting_started.py` |
| 140 | `backends/router.py` |
| 92 | `core/validation.py` |

其余：`agents/reviewer.py` 85、`__init__.py` 81、`agents/cot.py` 76、`_count_code_lines.py` 71、`core/events.py` 69、`core/budget.py` 63、`__main__.py` 62、`agents/memory_agent.py` 52、`backends/fallback.py` 51、`_count_lines.py` 42、`agents/executor.py` 37、`examples/*` 17–35、`backends/profile.py` 26、`core/constants.py` 29、4 个 `__init__.py` 各 1 行。

**语言构成**：100% Python（无 JS/TS/Rust/Go）。另有 5 个 Markdown 文档、1 个 HTML 架构图。

> 注：6,804 行里含 `_count_code_lines.py`(71) + `_count_lines.py`(42) 两个**自用的统计脚本**，它们已被 `.gitignore` 排除（`.gitignore` 末段），不算产品代码。剔除后约 **6,691 行**。

### 2.3 入口文件

| 入口 | 位置 | 说明 |
|---|---|---|
| CLI 入口 | `pyproject.toml:53` → `loomllm = "ai_staff_v4.__main__:main"` | 装完后可 `loomllm setup/chat/scan/health/version` |
| CLI 实现 | `__main__.py:4` `def main()` | 支持 `setup` / `chat` / `scan` / `health` / `version` 五个子命令 |
| 包级工厂 | `__init__.py:58` `from_env()`、`:64` `quick_start()`、`:70` `discover_and_start()` | 零配置入口 |
| 核心类 | `main_mod/staff.py:30` `class AIStaff` | 主编排类，`chat()` 在 `:153` |
| 首次向导 | `getting_started.py:53` `def main()` | 交互式配 Key（`input()` at `:121,:125`） |
| 示例 | `examples/simple.py` 等 6 个 | 可直接 `python examples/simple.py` |

### 2.4 依赖清单

`requirements.txt:1-2`：
```
httpx>=0.27
pyyaml>=6.0
```

`pyproject.toml:34-37` 运行时依赖同上；`:45-50` dev 依赖：`pytest>=7.0`、`build>=1.0`、`twine>=5.0`；`:11` `requires-python = ">=3.10"`。

**依赖极简**（只有 2 个），这是个优点——没有 LangChain 那种依赖地狱。但也意味着**没有 `openai` SDK、没有 `anthropic` SDK**，全靠裸 HTTP，这直接导致了 §5.3 的 Anthropic 问题。

---

## 3. Provider 清单

全部定义在 `backends/smart_init.py:172-288` 的 `PROVIDER_DEFS` 字典。鉴权方式统一走 `backends/client.py:22-25`：

```python
self.headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}
```

调用端点统一为 `{base_url}/chat/completions`（`backends/client.py:62`）。

| # | Provider | 实现/定义位置 | base_url | 鉴权方式 | env 变量 | 可用性 |
|---|---|---|---|---|---|---|
| 1 | **DeepSeek** | `smart_init.py:174-184` | `https://api.deepseek.com/v1` | Bearer | `DEEPSEEK_API_KEY`, `AI_STAFF_DEEPSEEK_KEY` | ✅ 完整 |
| 2 | **Moonshot (Kimi)** | `smart_init.py:185-195` | `https://api.moonshot.cn/v1` | Bearer | `MOONSHOT_API_KEY`, `KIMI_API_KEY` | ✅ 完整 |
| 3 | **Qwen (DashScope)** | `smart_init.py:196-207` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | Bearer | `DASHSCOPE_API_KEY`, `QWEN_API_KEY`, `ALIBABA_API_KEY` | ✅ 完整 |
| 4 | **Zhipu GLM** | `smart_init.py:208-219` | `https://open.bigmodel.cn/api/paas/v4` | Bearer | `ZHIPU_API_KEY`, `ZAI_API_KEY`, `GLM_API_KEY` | ✅ 完整（有免费 `glm-4-flash`） |
| 5 | **SiliconFlow** | `smart_init.py:220-230` | `https://api.siliconflow.cn/v1` | Bearer | `SILICONFLOW_API_KEY`, `SF_API_KEY` | ✅ 完整（有免费模型） |
| 6 | **Google Gemini** | `smart_init.py:232-238` | `https://generativelanguage.googleapis.com/v1beta/openai` | Bearer | `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `AI_STAFF_API_KEY` | ✅ 完整（走 OpenAI 兼容端点；`can_list_models=True`） |
| 7 | **OpenAI** | `smart_init.py:239-250` | `https://api.openai.com/v1` | Bearer | `OPENAI_API_KEY`, `AI_STAFF_OPENAI_KEY` | ✅ 完整 |
| 8 | **Groq** | `smart_init.py:251-261` | `https://api.groq.com/openai/v1` | Bearer | `GROQ_API_KEY` | ✅ 完整 |
| 9 | **Anthropic (Claude)** | `smart_init.py:262-273` | `https://api.anthropic.com/v1` | ❌ **应为 `x-api-key` 头，代码用的是 `Bearer`** | `ANTHROPIC_API_KEY` | ⚠️ **不可用**（会 401） |
| 10 | **Ollama** | `smart_init.py:275-287` | `http://localhost:11434/v1` | 无（key 固定填 `"ollama"`，见 `:800`） | 无（本地） | ⚠️ 需本机跑 `ollama serve`，代码路径存在（`:800-830`） |

### 3.1 关于「10 个」的诚实说明

- **配置层面确实是 10 个**，README `:68-81` 和 `config_template.yaml:26-125` 也都列了 10 个。
- **代码层面真正能打的只有 9 个**。Anthropic 的问题**代码里自己承认了**——`smart_init.py:272` 有一行注释：
  > `"note": "Anthropic使用x-api-key头而非Bearer，LLMClient需适配"`
  
  但 `backends/client.py:22-25` 至今没适配，所以这个「note」是**已知未修**。

### 3.2 TODO / NotImplemented 扫描结果

| 扫描项 | 结果 |
|---|---|
| `TODO` / `FIXME` / `XXX` / `HACK` | **0 处**（全仓库） |
| `NotImplementedError` | **1 处**：`agents/base.py:24` `BaseAgent.run()` —— 这是**正常的抽象方法**，不是遗留坑 |
| `pass  #` 占位 | 1 处：`agents/collab_loop.py:543` `pass  # rejudge失败，继续正常revising`（有意的容错分支） |

**结论：代码里没有「写着 TODO 没做」的半成品**。这是加分项——项目不是「画饼型」。

### 3.3 Provider 实战状态（有历史记录佐证）

`C:\Users\cxx\WorkBuddy\Claw\.workbuddy\memory\2026-04-29.md:7-10` 记录了 4 月 29 日的真实测试：
- 「Gemini 免费额度全部 429，23 个模型无一可用」
- 「gemini-3-flash-preview 返回 400（模型参数不兼容 OpenAI 格式）」
- 「LoomLLM 架构本身工作正常（自动发现 + 自动降级 + 多后端 fallback）」
- 「建议：加智谱 GLM 做免费 fallback（国内直连，glm-4-flash 免费）」

也就是说：**框架机制是好的，但免费额度策略没落地**——GLM 的免费 fallback 建议至今没实现（`config_template.yaml:61-67` 里 zhipu 整段是**注释掉的**）。

---

## 4. 可运行性评估（纯静态判断，未实际执行）

### 4.1 有没有测试？——有

| 项 | 结论 |
|---|---|
| 测试文件 | `tests/test_core.py`，246 行 |
| 测试方法数 | **20 个**（分布在 9 个 `TestCase` 类中） |
| 覆盖模块 | verbose 日志、ExpertRegistry、SmartInit、TokenBudget、EventBus、LLMClient、CollabLoop 导入、Validation |
| 是否需要 API Key | **不需要**。文件头 `test_core.py:5` 明确写 "No API key needed — all tests are local unit tests." |
| 是否真的离线 | ✅ 确认。`test_core.py:106-110` 的 `test_auto_configure` 只断言 `hasattr(SmartInit, 'auto_configure')`，注释说明「makes real API calls, just test it doesn't crash on import」——**刻意避开了网络** |
| 声明通过率 | 20/20。佐证：`.workbuddy\memory\2026-05-06.md:5`「V4.2 版本 7187 行代码，20/20 测试全绿」 |

**⚠️ 一个隐患**：`tests/` 目录下**没有 `__init__.py`**（`ls tests/` 只有 `test_core.py` + `__pycache__`）。README `:259` 推荐的命令 `python -m unittest ai_staff_v4.tests.test_core -v` 依赖命名空间包才能跑通；更稳的是 `test_core.py:4` 里写的 `python tests/test_core.py`（文件内 `:14-19` 已写好 sys.path 兜底）。

### 4.2 有没有 README 说明怎么跑？——有，而且很全

| 文档 | 行数/大小 | 内容 |
|---|---|---|
| `README.md` | 296 行 / 9,562 B | 英文主文档。Quick Start（`:123-170`）、Testing（`:255-263`）、Requirements（`:267-271`） |
| `README_CN.md` | 7,913 B | 中文版 |
| `DESIGN.md` | 6,455 B | 设计哲学，8 节 |
| `GUIDE.md` | 5,143 B | 中文使用指南：模式选择、返回值解读 |
| `USAGE.md` | 7,223 B | 中文手册 + 踩坑指南（含「已死模型名」黑名单） |
| `ARCH_FLOWCHART.html` | 9,170 B | 架构流程图 |

文档质量**明显高于同类个人项目**。README `:126-128` 给出 `pip install httpx pyyaml`，`:168-170` 给出 `python -m ai_staff_v4 setup`。

### 4.3 能不能在本机跑起来？——**不能直接跑**

静态判断依据（全部只读验证）：

| 检查项 | 实测结果 | 结论 |
|---|---|---|
| Python 版本 | `Python 3.13.14` | ✅ 满足 `>=3.10` |
| `httpx` | `find_spec` → **MISSING** | ❌ 必需依赖缺失 |
| `pyyaml` | `find_spec` → **MISSING** | ❌ 必需依赖缺失 |
| `pytest` | `find_spec` → **MISSING** | ❌ dev 依赖缺失 |
| `ai_staff_v4` 是否已安装 | **NOT INSTALLED** | ❌ 未 `pip install -e .` |
| 环境变量 API Key | `DEEPSEEK/ZHIPU/SILICONFLOW/MOONSHOT/DASHSCOPE/QWEN/GEMINI/GOOGLE/OPENAI/GROQ/ANTHROPIC_API_KEY` **全部 not set** | ❌ 一个 Key 都没有 |
| 代理 | `HTTP_PROXY` / `HTTPS_PROXY` 已设置（len=22，形如 `http://127.0.0.1:7890`） | ⚠️ 已配置，但摸底时 7890 端口**未监听**（`git fetch` 报 `Failed to connect to github.com:443 over proxy 127.0.0.1`） |

**判断**：
1. **离线单元测试**：只要 `pip install httpx pyyaml`，`python tests/test_core.py` **应该能直接跑通**（测试不联网）。
2. **实际调 LLM**：**跑不了**。缺依赖 + 缺 Key + 代理未启动，三重阻塞。
3. **打包产物可用**：`dist/loomllm-1.0.0-py3-none-any.whl` 已存在（104,731 B），理论上 `pip install dist/*.whl` 即可，但**未验证**（未执行安装）。

### 4.4 有没有硬编码 API Key？——🔴 **有，而且泄露了**

> 按你的要求，**报告只写位置和性质，不写 Key 原文**。

| # | 位置 | 内容 | 是否已推到 GitHub | 严重度 |
|---|---|---|---|---|
| 1 | `C:\Users\cxx\WorkBuddy\Claw\_test_loomllm_gemini.py:3` | 一个**完整长度（39 字符）的 Google API Key**，`os.environ["GEMINI_API_KEY"] = "..."` | 🔴 **是**。该文件已 commit 且 push 到**公开**仓库 `github.com/chenxinghang-a/ai.md`（HEAD == origin/main == `95027e6`） | **严重** |
| 2 | `C:\Users\cxx\WorkBuddy\Claw\loomllm-pkg\ai_staff_v4\.cache\smart_init_v2_cache.json:5` | **同一个 Key**，明文 JSON | ✅ 否。`.cache/` 已被 `.gitignore` 排除，未进 LoomLLM 仓库 | 中 |
| 3 | `C:\Users\cxx\WorkBuddy\Claw\.workbuddy\memory\2026-05-06.md:9` | Gemini / DeepSeek / MiMo 三个 Key 的**部分片段**（形如 `sk-9059...`） | ✅ 否。`.workbuddy/memory/` 已被 `.gitignore:32` 排除 | 低 |

**两个公开仓库的可见性已用 GitHub API 确认**：
- `github.com/chenxinghang-a/LoomLLM` → `"private": false`
- `github.com/chenxinghang-a/ai.md` → `"private": false`

**没有发现的**：
- LoomLLM 仓库的 git 历史里 `USAGE.md` 出现过 `AIza...`，但经逐 commit 校验，那里是 **6 字符的占位符**（`AIzaSy` + 省略号），**不是真 Key**。该占位符在 commit `f5f4b03` 已被清掉。
- `.ai_staff_memory.db`（585 KB，6 张表）扫描 Key 特征 → **0 行命中**。
- `dist/*.whl`、`LoomLLM-main.zip` → 未含 Key（zip 只含仓库源码，不含 `_test_*.py`）。

---

## 5. 问题清单（按严重度分级）

### 5.1 🔴 P0 — 安全（必须先做，与代码维护无关）

**P0-1：真实 API Key 泄露到公开仓库**
- 位置：`_test_loomllm_gemini.py:3`（`C:\Users\cxx\WorkBuddy\Claw\`）
- 事实：39 字符完整 Google API Key，已 push 到公开仓库 `ai.md`（commit `95027e6`）。
- 风险：任何人 `git clone` 该公开仓库即可拿到 Key，可盗刷你的 Gemini 额度（而且记录显示你的 Gemini 免费额度本来就常年 429）。
- **注意**：单纯「改文件 + 再 commit」**不够**——Key 仍留在 git 历史里。必须**先去 Google AI Studio 吊销/轮换该 Key**，再清理历史。

**P0-2：密钥明文落盘缓存**
- 位置：`backends/smart_init.py:903-914`，`_save_cache()`
- 代码原文：`:909` `"provider": p.provider, "api_key": p.api_key,  # 保留完整key`
- 事实：这是**有意设计**（注释明写"保留完整key"），把全部 Provider 的 Key 明文写进 `.cache/smart_init_v2_cache.json`。文件本身已被 gitignore，但**磁盘上是裸的**，任何本机进程/同步盘/备份都能读到。
- 建议：缓存只存 Key 的指纹（如 sha256 前 8 位）或直接不存，需要时重新从 env 读。

**P0-3：测试脚本用硬编码 Key 而非 env 注入**
- 同类文件模式：`_test_loomllm_gemini.py:3-5` 直接把 Key + 代理写死在源码里。
- `.gitignore` 只挡了 `_live_test_*.py`（见 `.gitignore` 末段），**没挡 `_test_*.py`**，所以这个文件被外层 `ai.md` 仓库正常提交了。这是 P0-1 的**根因**。

### 5.2 🟠 P1 — 功能正确性

**P1-1：Anthropic Provider 实际不可用**
- 位置：`backends/smart_init.py:262-273` 定义，`backends/client.py:22-25` 实现
- 事实：Anthropic 官方 API 要求 `x-api-key` 请求头，代码统一发 `Authorization: Bearer`。`smart_init.py:272` 的注释自己承认「LLMClient需适配」，但从未适配。
- 影响：10 Provider 实际只有 9 个能用。README `:68` 宣称的「10 Providers」在 Anthropic 这一项上是**虚标**。

**P1-2：本地仓库落后远程 1 个 commit**
- 本地 HEAD `79cde11`，GitHub main `cd34cd58`（2026-04-26 的 WinError 123 修复）。
- 影响：`main_mod/staff.py` 的自动保存目录名在 Windows 上可能因换行符报 `WinError 123`——**这个 bug 你当时修了并 push 了，但本地这份没同步到**。

**P1-3：GLM 免费 fallback 建议未落地**
- 位置：`config_template.yaml:61-67`，zhipu 整段被注释掉
- 事实：`.workbuddy\memory\2026-04-29.md:10` 明确建议「加智谱 GLM 做免费 fallback（国内直连，glm-4-flash 免费）」，且 `smart_init.py:215` 已经把 `glm-4-flash` 标为 `tier: "free"`。代码支持已就绪，只是配置没开。
- 影响：主力 Gemini 免费额度耗尽时无免费兜底，直接 429 到底。

**P1-4：`chat_all` 并行模式的超时处理会丢结果**
- 位置：`backends/multi_client.py:207` `for future in as_completed(futures, timeout=120):`
- 事实：`as_completed` 抛 `TimeoutError` 时，整个 `chat_all()` 直接向外抛异常，**已经收集到的 results 全部丢失**。该调用未包在 try 内。

**P1-5：`tests/` 缺 `__init__.py`**
- 位置：`tests/` 目录
- 影响：README `:259` 推荐的 `python -m unittest ai_staff_v4.tests.test_core -v` 依赖命名空间包行为，不够稳。文件内自带的 `python tests/test_core.py` 反而更可靠。

### 5.3 🟡 P2 — 架构与可维护性

**P2-1：`AIStaff` 上帝类（1629 行）**
- 位置：`main_mod/staff.py:30`
- 事实：单类里塞了 `chat`、`chat_single`、`cross_arena`、`research`、`auto_run`、`auto_run_v5`、`collaborate`、`health_check`、`capabilities`、`list_experts`、`get_audit_log`、`show_memory_stats`、5 个 `_execute_*`、`from_env`/`quick_start`/`discover_and_start`/`from_config_file` 等**40+ 个方法**。职责从「会话编排」一直延伸到「格式化报表」「成本估算」。
- 同类问题：`agents/collab_loop.py:244` 的 `run()` 单方法从 244 行到 570 行（约 **326 行**）。

**P2-2：库代码直接 `print()`**
- 位置：`main_mod/staff.py`（**25 处** `print(`）、`backends/smart_init.py`（**7 处**）
- 事实：项目已经有 `core/verbose.py`（291 行）专门做日志和彩色输出，但主流程仍在裸 `print`。作为**库**被 import 时会污染调用方的 stdout。

**P2-3：宽泛异常捕获泛滥**
- 全仓库 `except Exception` / 裸 `except:` 共 **54 处**
- 其中真正的裸 `except:` 只有 2 处，且都在已 gitignore 的开发脚本里（`_count_code_lines.py:58`、`_count_lines.py:18`），产品代码里没有裸 except——这点还算干净。但 54 处 `except Exception` 意味着大量错误被静默降级，调试时很难定位。

**P2-4：全同步 IO，无 async**
- 事实：`httpx.Client`（同步）用遍全仓库，**0 处** `httpx.AsyncClient` / `async def`。
- 影响：并发只能靠 `multi_client.py:205` 的 `ThreadPoolExecutor`（上限 6）。作为「多后端框架」，这是明显的扩展性天花板。

**P2-5：命名体系混乱**
- `pyproject.toml:6` 包名 = `loomllm`，但 `pyproject.toml:56` 打包 `ai_staff_v4*`，import 也是 `ai_staff_v4`。
- 残留旧品牌：`experts/experts.yaml:1` 写「AI-Staff V4.2 专家角色定义」、`USAGE.md:1` 写「AI-Staff V4 使用手册」、`tests/test_core.py:2` 写「AI-Staff V4 核心功能单元测试」。
- 影响：新人（包括三个月后的你自己）会困惑「LoomLLM / AI-Staff / ai_staff_v4 到底几个东西」。

### 5.4 🔵 P3 — 工程规范

| 项 | 事实 | 位置 |
|---|---|---|
| 无 CI | 仓库里没有任何 `.github/`、`.gitlab-ci.yml`、`.travis.yml` | `git ls-files` 无命中 |
| 无 CHANGELOG | 无 `CHANGELOG*` 文件 | `git ls-files` 无命中 |
| 打包卫生 | 已 gitignore 的 `_count_code_lines.py`(71行) / `_count_lines.py`(42行) **仍被打进 wheel** | `dist/loomllm-1.0.0-py3-none-any.whl` 条目列表 |
| 备份仓库夹带产物 | 公开仓库 `ai.md` 里提交了 `loomllm-pkg/dist/loomllm-1.0.0.tar.gz` 和 `loomllm-pkg/loomllm.egg-info/*` | `git ls-files` @ `Claw/` |
| 死代码 | `backends/client.py:148` `return "", usage_info` 在 `for attempt in range(MAX_RETRIES)` 循环之后，正常路径永远走不到（循环内必 return 或 raise） | `backends/client.py:148` |
| 版本号冻结 | `pyproject.toml:7` `version = "1.0.0"`，自 2026-04-25 未变 | — |

---

## 6. 维护方案：3 条路线对比

### 路线 A：最小维护（止血 + 保活）—— ⭐ **推荐**

**做什么**
1. **【最高优先】吊销并轮换泄露的 Gemini Key**（Google AI Studio 后台删除旧 Key，生成新 Key）。
2. 从 `_test_loomllm_gemini.py` 移除硬编码 Key，改为 `os.environ.get("GEMINI_API_KEY")`；并把 `_test_*.py` 加进 `.gitignore`。
3. 用 `git filter-repo`（或 BFG）清理 `ai.md` 仓库历史中的该文件，然后 force-push。（历史清理是破坏性操作，**执行前必须确认**。）
4. `git pull` 同步 LoomLLM 到 `cd34cd58`（拿回 WinError 123 修复）。
5. `config_template.yaml:61-67` 取消 zhipu 段注释，落地免费 fallback。
6. 给 LoomLLM 加一个最小 GitHub Actions：`pip install httpx pyyaml && python tests/test_core.py`。
7. `tests/__init__.py` 补一个空文件，让 README 里的命令真正可用。

**工作量**：半天以内。步骤 1–3 是安全操作（1 小时），步骤 4–7 各 10–30 分钟。
**收益**：风险归零 + 本地/远程一致 + 免费兜底可用 + 有 CI 防回归。
**风险**：force-push 会重写公开历史（步骤 3），如果 `ai.md` 仓库有别人 fork/clone 过，需要知会。**建议先做步骤 1（吊销 Key），吊销之后历史清理的紧迫性就下降了，可以慢慢来。**

### 路线 B：补功能（把「10 Provider」做成真的）

**做什么**
1. 在 `backends/client.py:22-25` 加 provider 感知的鉴权分支：`anthropic` → `x-api-key` + `anthropic-version` 头。
2. 补 Provider 的**真实模型名校验**（`USAGE.md:1-30` 已经有一份「已死模型名」黑名单，把它变成代码里的自动探测）。
3. 给 `multi_client.py:207` 的 `as_completed` 加 try/except，超时时保留已收集结果。
4. 加**真·集成测试**（标记 `@unittest.skipUnless(os.environ.get("X_API_KEY"))`），让 20 个纯离线测试之外有一层联网验证。
5. 修 `backends/client.py:148` 的死代码。

**工作量**：2–3 天。第 1、3、5 项是小时级；第 2、4 项要真花钱调 API 验证。
**收益**：README 的「10 Providers」不再虚标；Anthropic 真能用；超时不丢数据。
**风险**：联网测试会消耗额度，且你的 Gemini 免费额度长期 429，验证成本不可控。

### 路线 C：重构

**做什么**
1. 拆 `AIStaff`（1629 行）→ `SessionOrchestrator` / `ArenaRunner` / `ResearchRunner` / `ConfigLoader` / `HealthReporter` 等。
2. 拆 `collab_loop.py:244` 的 326 行 `run()` → 按 phase 拆成 `_draft()` / `_review()` / `_revise()` / `_judge()`。
3. 全链路 `httpx.Client` → `AsyncClient`，`chat_all` 改 `asyncio.gather`。
4. 用 `core/verbose.py` 彻底替换 32 处裸 `print()`。
5. 统一命名：`ai_staff_v4` → `loomllm`（会破坏所有现有 import 和外部引用）。

**工作量**：1–2 周，且**必须**有路线 B 的集成测试兜底，否则重构完无法验证没坏。
**收益**：长期可维护性、真并发、干净的库边界。
**风险**：**这是个人毕业设计项目**，你已经在 `.workbuddy\memory\2026-04-29.md:42` 明确说过「砍掉 LoomLLM，做纯电气自动化项目，LLM 当加分项」。花两周重构一个已经结项、且你已决定不再投入主线的项目，**投入产出比很差**。

### 6.1 推荐

**推荐路线 A**，理由：

1. **P0 安全问题与代码质量无关，但优先级压倒一切。** 一个能盗刷的 Key 挂在公开仓库上，比任何架构问题都紧急。路线 A 把它放在第一位。
2. **这个项目的「价值锚点」是论文和简历，不是持续迭代。** 论文《基于多模型协作的迭代式大语言模型应用框架设计与实现》已完成；`docs/resume_content.json:14` 和 `docs/token_application.md:3` 都已在用它做履历背书。这些**已经发生**，不会因为代码不再演进而贬值。
3. **项目的核心机制是好的，不需要重构来救。** 证据：`.workbuddy\memory\2026-04-29.md:9`「LoomLLM 架构本身工作正常（自动发现+自动降级+多后端 fallback）」；代码里 `TODO/FIXME` 为 **0**；20/20 测试全绿。问题集中在「配置没开」「鉴权没适配」这类**补丁级**事项，而不是「设计错了」。
4. **路线 A 的 7 步里有 5 步是纯机械操作**，风险极低，做完就能让项目进入「随时可演示」状态——这对一个「毕设加分项」是最优终局。
5. **路线 B 可以顺带做掉第 1、3、5 项**（都是小时级），如果哪天要拿这个项目面试，把 Anthropic 修好、README 不再虚标，性价比很高。第 2、4 项要烧额度，**建议不做**。

**执行顺序建议**：
```
立即   → 吊销 Gemini Key（不管走哪条路线，先做这个）
今天   → 清理脚本硬编码 + 补 .gitignore 规则
本周内 → 同步远程 + 开 zhipu fallback + 加 CI
有空   → 顺手修 Anthropic 鉴权（路线 B 的 1/3/5）
不做   → 重构（路线 C）
```

### 6.2 是否值得继续投入？——**值得「保」，不值得「投」**

- **值得保**：项目本身是**真东西**——6,691 行产品代码、10 Provider 配置、20 个测试、完整文档体系、已上 PyPI 打包、有配套毕业论文。它不是「下载的第三方包」，是你自己从零写的。**放着不管的沉没成本为零，但删掉或放任泄露的代价很高。**
- **不值得投**：作为一个已结项的个人项目，路线 C（重构）的边际收益远低于你的时间成本。你已经在记忆里明确转向「纯电气自动化 + LLM 当加分项」，这个判断是对的——**LoomLLM 现在的定位应该是「履历资产 + 电气项目的 LLM 增强组件」，而不是「持续演进的产品」**。
- **一个例外**：如果 `ModbusDiag` / `industrial_scada` 那两个电气项目需要 LLM 能力（比如自然语言查寄存器、自动生成诊断报告），**LoomLLM 的 `MultiLLMClient` + `FallbackManager` 可以直接复用**（`backends/multi_client.py:14`，219 行，依赖只有 httpx）。这种情况下路线 B 的「修 Anthropic + 加 fallback」就有了实际用途，值得做。

---

## 附录 A：本次摸底执行的只读命令清单

```bash
# 定位
find C:/Users/cxx -iname "*loomllm*" -not -path "*/AppData/*" -not -path "*/node_modules/*" -not -path "*/.git/*"
find C:/Users/cxx -maxdepth 4 -type d -iname "*loom*" -not -path "*/AppData/*"
unzip -l "C:/Users/cxx/Downloads/LoomLLM-main.zip"      # 仅列清单，未解压
unzip -z "C:/Users/cxx/Downloads/LoomLLM-main.zip"      # 读 zip 注释
unzip -l "loomllm-pkg/dist/loomllm-1.0.0-py3-none-any.whl"

# git 只读
git -C <repo> remote -v
git -C <repo> branch -a
git -C <repo> log --oneline --format="%h %ad %s" --date=short
git -C <repo> status --short
git -C <repo> ls-files
git -C <repo> rev-list --left-right --count HEAD...origin/main
git -C <repo> cat-file -t <sha>
git -C <repo> grep -l "AIza" <commit>
git -C <repo> log --all -S "AIza" --oneline
git -C <repo> show <commit>:USAGE.md

# 密钥扫描（只统计，不输出原文）
grep -rnE "(sk-[A-Za-z0-9]{16,}|AIza[0-9A-Za-z_-]{30,}|ghp_[A-Za-z0-9]{20,})"
python -c "import sqlite3,re; ..."   # 扫 .ai_staff_memory.db，命中 0 行

# 环境（只读）
python --version
python -c "import importlib.util as u; u.find_spec('httpx')"
python -c "import os; os.environ.get('GEMINI_API_KEY')"   # 仅打印 是否设置 / 长度

# 远端可见性（只读 API）
curl -s https://api.github.com/repos/chenxinghang-a/LoomLLM
curl -s https://api.github.com/repos/chenxinghang-a/ai.md
curl -s https://api.github.com/repos/chenxinghang-a/LoomLLM/branches
curl -s https://api.github.com/repos/chenxinghang-a/LoomLLM/commits?per_page=5
```

**未执行**：任何 `pip install` / `python setup.py` / `git commit` / `git push` / `git fetch`（实际网络拉取）/ 解压 zip / 修改文件。

## 附录 B：明确「未找到」的项

| 查询项 | 结果 |
|---|---|
| 第二个独立的 LoomLLM 仓库 | **未找到**。全盘只有 `loomllm-pkg/ai_staff_v4` 一个带 `.git` 的 LoomLLM 仓库 |
| `tests/__init__.py` | **未找到** |
| `.github/` CI 配置（LoomLLM 仓库内） | **未找到** |
| `CHANGELOG` / `CHANGELOG.md` | **未找到** |
| `config.yaml`（含真实 Key 的配置文件） | **未找到**，仓库里只有 `config_template.yaml`（✅ 这是好事） |
| `.env` / `.env.*` | **未找到** |
| LoomLLM 仓库当前树或历史中的真实 API Key | **未找到**。历史里的 `AIza...` 是 6 字符占位符，非真 Key |
| `.ai_staff_memory.db` 中的 Key | **未找到**（6 张表全扫，0 命中） |
| `dist/*.whl` 与 `LoomLLM-main.zip` 中的 Key | **未找到** |
| 其他 `*loom*` 目录（除 `loomllm-pkg`） | **未找到** |
| TODO / FIXME / XXX / HACK 标记 | **未找到**（0 处） |
| 硬编码的 DeepSeek / OpenAI / Anthropic Key | **未找到**（只有 Gemini 一个泄露） |

---

*报告结束。所有事实均标注了文件路径 + 行号或命令来源；无法验证的一律标注「未找到」，未做推测性补全。*
