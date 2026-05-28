# OpenClaw 执行摘要 - 优化任务清单

## 任务概览
本文档将OpenClaw AI助手网关的部署与优化分解为12个核心任务点,涵盖环境准备、安装部署、配置管理、模型集成、成本控制、运维保障等全流程。

---

## 1. 环境准备与依赖检查

### 1.1 系统要求
- **Node.js**: 20+ (推荐22 LTS)
- **基础工具**: npm, git, curl
- **硬件资源**: 最低4GB内存(推荐8GB), 10GB磁盘空间
- **编译环境**: Linux/WSL2需安装 `build-essential`、`python3-pip`

### 1.2 验证步骤
```bash
node --version  # ≥20
npm --version
git --version
curl --version
```

### 1.3 注意事项
- Windows用户确保PowerShell执行策略允许脚本运行
- 检查端口占用(默认WebSocket端口18789)
- 确保网络访问GitHub和API服务商

---

## 2. OpenClaw快速安装部署

### 2.1 方案一:官方一键安装脚本(推荐)
```bash
curl -fsSL https://openclaw.ai/install.sh | bash
```

### 2.2 方案二:手动源码部署
```bash
git clone https://github.com/openclaw/openclaw.git ~/.openclaw
cd ~/.openclaw
npm install
npm run build
openclaw config init  # 生成默认配置文件
```

### 2.3 验证安装
```bash
openclaw --version
openclaw doctor  # 检查配置合法性
```

### 2.4 启动Gateway
```bash
openclaw start  # 前台运行
# 或使用PM2守护进程
pm2 start openclaw --name openclaw-gateway
```

---

## 3. 核心配置文件设置

### 3.1 配置文件位置
- 主配置: `~/.openclaw/config.yaml`

### 3.2 必配项清单

#### 3.2.1 Agent基础配置
```yaml
agents:
  defaults:
    name: assistant
    provider: openai  # 或 anthropic/custom/ollama
    model: openai/gpt-5.4
    apiKey: ${OPENAI_API_KEY}  # 使用环境变量
    systemMessage: |
      你是一个友好的AI助手。
```

#### 3.2.2 记忆存储配置
```yaml
    memory:
      engine: memory-core  # 或 custom
      namespace: default
    compaction:
      targetTokenCount: 4096  # 接近上限时压缩
      mode: safeguard
```

#### 3.2.3 渠道集成配置
```yaml
channels:
  - provider: whatsapp
    token: ${WHATSAPP_TOKEN}
    requireMention: false
  - provider: telegram
    token: ${TELEGRAM_BOT_TOKEN}
```

#### 3.2.4 工具权限配置
```yaml
tools:
  - browser
  - terminal
  - memory_search
  # 根据需求启用
```

### 3.3 安全配置
```yaml
# WebSocket仅监听本地
gateway:
  host: 127.0.0.1
  port: 18789

# 启用日志审计
logging:
  level: info
  audit: true
```

---

## 4. 记忆系统配置与优化

### 4.1 记忆结构说明
- **长期记忆**: `~/.openclaw/workspace/memory/MEMORY.md` - 永久性信息
- **每日记忆**: `~/.openclaw/workspace/memory/YYYY-MM-DD.md` - 临时会话记录
- **自动加载**: 启动时加载长期记忆+最近2天临时记忆

### 4.2 配置优化策略

#### 4.2.1 启用语义搜索
```yaml
tools:
  - memory_search
```
调用示例:
```yaml
toolCalls:
  - name: memory_search
    arguments:
      query: "用户上次提到的项目需求"
```

#### 4.2.2 设置压缩阈值
```yaml
agents:
  defaults:
    compaction:
      targetTokens: 4096  # 留足余量
      model: openrouter/anthropic/claude-sonnet-4-6  # 用小模型压缩
```

#### 4.2.3 自动记忆写入
OpenClaw会在达到摘要阈值前自动触发记忆写入,防止重要信息丢失。

### 4.3 手动管理操作
```bash
# 查看记忆文件
cat ~/.openclaw/workspace/memory/MEMORY.md

# 清理过期记忆(>30天)
find ~/.openclaw/workspace/memory -name "*.md" -mtime +30 -delete
```

---

## 5. 模型选择与集成

### 5.1 主流模型对比表

| 模型 | 上下文 | 价格(\$/千Token) | 延迟 | 适用场景 | Chain-of-Thought | 多模态 |
|------|--------|------------------|------|----------|------------------|--------|
| GPT-5.4 | ~270K | 输入\$2.5 输出\$15 | 较高 | 通用对话/创作/代码 | ✅ | ✅ |
| GLM-5V-Turbo | 200K | 输入\$1.2 输出\$4.0 | 中等 | 多模态设计 | ✅(思考模式) | ✅ |
| Claude Opus 4.6 | 1M | 输入\$5 输出\$25 | 较高 | 安全敏感场景 | ✅(强) | ❌ |
| DeepSeek-V3.2 | 128K | 输入\$0.028 输出\$0.42 | 中等 | 任务型代理 | ✅(Reasoner) | ❌ |
| LLaMA-3 (大) | ~128K | 免费(自托管) | 取决硬件 | 私有部署 | ⚠️(需技巧) | ✅(3.2+) |
| 文心 X1-Turbo | 几万 | 输入\$0.12 输出\$0.48 | 中等 | 中文创作 | ⚠️(链式提示) | ✅ |

### 5.2 集成方案

#### 5.2.1 OpenAI集成
```yaml
agents:
  defaults:
    provider: openai
    model: openai/gpt-5.4
    apiKey: ${OPENAI_API_KEY}
```

#### 5.2.2 Anthropic集成
```yaml
agents:
  defaults:
    provider: anthropic
    model: claude-sonnet-4-6
    apiKey: ${ANTHROPIC_API_KEY}
providers:
  claude:
    type: anthropic
    batch: true  # 启用批处理享50%折扣
```

#### 5.2.3 本地模型(Ollama)
```yaml
agents:
  defaults:
    provider: ollama
    model: llama:70b
```

#### 5.2.4 自定义代理(OpenRouter等)
```yaml
agents:
  defaults:
    provider: custom
    model: openrouter/anthropic/claude-sonnet-4-6
    baseURL: https://openrouter.ai/api/v1
    apiKey: ${OPENROUTER_API_KEY}
```

### 5.3 多Agent配置(成本优化)
```yaml
agents:
  defaults:
    model: openai/gpt-5.4  # 主用高端模型
  simple_tasks:
    model: openai/gpt-5.4-mini  # 简单任务用廉价模型
  coding:
    model: openai/gpt-5.4-turbo  # 编码用
```

---

## 6. Token成本监控与控制

### 6.1 实时Token计数(Python示例)
```python
import tiktoken

def count_tokens(text, model="gpt-5.4"):
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(text))

# 使用
prompt = "请总结今天的会议记录"
tokens = count_tokens(prompt)
print(f"输入包含 {tokens} 个Token")
```

### 6.2 每日限额控制(Node.js示例)
```javascript
let dailyTokens = 0;
const DAILY_LIMIT = 1000000;  // 每日100万Token

function canSendRequest(requestTokens) {
  if (dailyTokens + requestTokens > DAILY_LIMIT) {
    throw new Error("今日Token使用已达上限");
  }
  dailyTokens += requestTokens;
  return true;
}

// 每次请求后
function onModelResponse(response) {
  dailyTokens += response.usage.total_tokens;
}

// 每日清零(通过cron任务)
```

### 6.3 对话历史裁剪(Python)
```python
MAX_TOKENS = 10000
enc = tiktoken.encoding_for_model("gpt-5.4")

dialogue = [...]  # list of {role, content}

def trim_dialogue(dialogue):
  # 计算总Token数
  total_tokens = sum(
    len(enc.encode(msg["content"])) 
    for msg in dialogue
  )
  
  # 逐条移除直至满足限额
  while total_tokens > MAX_TOKENS and dialogue:
    removed = dialogue.pop(0)
    total_tokens -= len(enc.encode(removed["content"]))
  
  return dialogue
```

### 6.4 成本优化策略
1. **Prompt缓存**: Anthropic可缓存重复内容至10%计费
2. **批处理API**: 合并请求享50%折扣
3. **模型混用**: 简单任务用廉价模型
4. **分层摘要**: 定期压缩历史对话

---

## 7. 对话历史管理与优化

### 7.1 自动压缩机制
OpenClaw内置"Compaction"功能,当接近上下文限制时:
1. 将早期对话摘要为一句
2. 替换原记录
3. 保留最近消息原文

### 7.2 手动分层摘要(Python)
```python
import openai

def summarize_history(messages, max_new_tokens=200):
  """摘要早期对话"""
  summary = openai.ChatCompletion.create(
    model="gpt-5.4",
    messages=[
      {"role": "system", "content": "请简要总结以下对话:"}
    ] + messages[-10:],  # 只用最近10条
    max_tokens=max_new_tokens
  )
  return summary.choices[0].message.content

# 使用
old_messages = messages[:-10]
summary_msg = summarize_history(old_messages)
new_messages = [
  {"role": "system", "content": f"历史摘要: {summary_msg}"},
  *messages[-10:]
]
```

### 7.3 智能裁剪策略
- **保留最近N条**: `dialogue = dialogue[-20:]`
- **基于Token裁剪**: 见任务6.3
- **基于重要性**: 保留包含关键词/关键操作的消息

---

## 8. 工具链与插件配置

### 8.1 内置工具列表

| 工具 | 功能 | 依赖 |
|------|------|------|
| browser | 网页浏览/抓取 | Chromium/Playwright |
| terminal | 执行系统命令 | - |
| memory_search | 语义记忆检索 | 嵌入服务(OpenAI/Gemini) |
| file_ops | 文件操作 | - |
| web_search | 网络搜索 | 搜索API |

### 8.2 启用/禁用工具
```yaml
tools:
  - browser  # 启用
  # - terminal  # 禁用(生产环境慎用)
  - memory_search
```

### 8.3 安全沙箱配置
```yaml
tools:
  terminal:
    allowedCommands:
      - ls
      - cat
      - grep
    blockedCommands:
      - rm
      - sudo
      - chmod
    workingDirectory: /safe/path
```

### 8.4 自定义Skill开发
```bash
# 创建Skill目录
mkdir ~/.openclaw/skills/my-skill

# 编写SKILL.md
cat > ~/.openclaw/skills/my-skill/SKILL.md << 'EOF'
# My Custom Skill

## 描述
自定义功能说明

## 使用场景
何时触发此技能

## 执行逻辑
1. 步骤一
2. 步骤二
EOF

# 编写执行脚本
# (根据Skill规范实现)
```

---

## 9. 渠道集成与多端接入

### 9.1 支持的渠道

| 渠道 | 配置项 | 授权方式 |
|------|--------|----------|
| WhatsApp | token | Bot Token |
| Telegram | token | Bot Token |
| Slack | token + channel | OAuth |
| Discord | token | Bot Token |
| Web | - | 配对码 |

### 9.2 WhatsApp集成示例
```yaml
channels:
  - provider: whatsapp
    token: ${WHATSAPP_TOKEN}
    requireMention: false
    allowedNumbers:  # 白名单
      - +8613800000000
```

### 9.3 跨设备配对
```bash
# 在Gateway生成配对码
openclaw pair generate

# 在移动端/Mac app输入配对码
# (客户端操作)
```

### 9.4 多渠道消息同步
```yaml
channels:
  - provider: whatsapp
    syncTo:
      - slack
      - discord
```

---

## 10. 故障排查与诊断

### 10.1 常见问题及解决方案

#### 问题1: 安装失败
```
症状: npm install报错
原因: Node版本过低或缺少编译环境
解决:
  1. 升级Node: nvm install 22
  2. 安装编译工具: apt install build-essential python3-pip
  3. 检查配置: openclaw doctor
```

#### 问题2: Gateway启动失败
```
症状: openclaw start后立即退出
原因: 配置文件错误或端口被占用
解决:
  1. 验证YAML语法
  2. 检查端口: netstat -tulpn | grep 18789
  3. 查看日志: tail -f ~/.openclaw/logs/gateway.log
```

#### 问题3: API调用超时
```
症状: 对话无响应或报错429/503
原因: 网络问题或限流
解决:
  1. 检查网络连通性
  2. 降低并发QPS
  3. 启用重试机制
  4. 检查API额度
```

#### 问题4: 记忆写入失败
```
症状: "记住XXX"无反应
原因: 文件权限或磁盘空间
解决:
  1. 检查目录权限: ls -la ~/.openclaw/workspace/memory/
  2. 检查磁盘空间: df -h
  3. 手动测试写入: echo "test" >> ~/.openclaw/workspace/memory/test.md
```

### 10.2 诊断工具
```bash
# 健康检查
openclaw doctor

# 查看实时日志
openclaw logs

# 测试配置
openclaw config validate

# 重启Gateway
openclaw restart
```

### 10.3 日志级别调整
```yaml
logging:
  level: debug  # debug/info/warn/error
  file: ~/.openclaw/logs/gateway.log
  maxFiles: 7
  maxSize: 10M
```

---

## 11. 性能与安全优化

### 11.1 性能优化措施

#### 11.1.1 水平扩展
```yaml
# 部署多个Gateway实例
# 使用Nginx负载均衡
upstream openclaw {
  server 127.0.0.1:18789;
  server 127.0.0.1:18790;
  server 127.0.0.1:18791;
}
```

#### 11.1.2 API缓存
```yaml
agents:
  defaults:
    cache:
      enabled: true
      ttl: 3600  # 缓存1小时
```

#### 11.1.3 批处理启用
```yaml
providers:
  anthropic:
    batch: true  # Claude批处理
  openai:
    batch: false  # OpenAI暂不支持
```

### 11.2 安全防护措施

#### 11.2.1 网络隔离
```yaml
gateway:
  host: 127.0.0.1  # 仅本地监听
  # 或通过防火墙限制访问
```

#### 11.2.2 API密钥管理
```yaml
# ❌ 错误:明文写密钥
apiKey: sk-abc123xyz

# ✅ 正确:使用环境变量
apiKey: ${OPENAI_API_KEY}

# 设置环境变量
export OPENAI_API_KEY="sk-abc123xyz"
```

#### 11.2.3 访问控制
```yaml
channels:
  - provider: whatsapp
    allowedNumbers:  # 白名单
      - +8613800000000
      - +8613800000001
    requireMention: true  # 需要@提及
```

#### 11.2.4 审计日志
```yaml
logging:
  level: info
  audit: true  # 记录所有对话
  retention: 90  # 保留90天
```

### 11.3 数据隐私保护

| 隐私级别 | 推荐方案 |
|----------|----------|
| 低(公开数据) | 云API(GPT/Claude) |
| 中(业务数据) | 国产API(GLM/文心) |
| 高(敏感数据) | 自托管模型(LLaMA) |

脱敏处理:
```python
def sanitize_text(text):
  """脱敏敏感信息"""
  import re
  
  # 手机号
  text = re.sub(r'1[3-9]\d{9}', '[PHONE]', text)
  # 身份证
  text = re.sub(r'\d{15,18}[X0-9]', '[ID]', text)
  # 邮箱
  text = re.sub(r'[\w.-]+@[\w.-]+', '[EMAIL]', text)
  
  return text
```

---

## 12. 监控与运维

### 12.1 监控指标

| 指标 | 监控工具 | 告警阈值 |
|------|----------|----------|
| Token消耗 | OpenClaw内部计数器 | 日限额80% |
| API错误率 | 日志分析 | >5% |
| 响应延迟 | 时间戳统计 | P95>3s |
| 内存占用 | 系统监控 | >80% |
| 磁盘空间 | 系统监控 | <10% |

### 12.2 日志分析脚本
```python
import re
from collections import Counter

def analyze_logs(log_file):
  """分析OpenClaw日志"""
  with open(log_file) as f:
    logs = f.read()
  
  # 统计API调用次数
  api_calls = len(re.findall(r'API call: (\w+)', logs))
  
  # 统计错误
  errors = re.findall(r'ERROR: (.+)', logs)
  error_counter = Counter(errors)
  
  # 统计Token消耗
  tokens = re.findall(r'tokens: (\d+)', logs)
  total_tokens = sum(int(t) for t in tokens)
  
  return {
    "api_calls": api_calls,
    "errors": dict(error_counter),
    "total_tokens": total_tokens
  }
```

### 12.3 备份策略
```bash
# 备份配置和记忆
backup_dir="/backup/openclaw/$(date +%Y%m%d)"

mkdir -p $backup_dir
cp -r ~/.openclaw/config.yaml $backup_dir/
cp -r ~/.openclaw/workspace/memory $backup_dir/

# 保留最近7天
find /backup/openclaw -mtime +7 -delete
```

### 12.4 自动化运维脚本
```bash
#!/bin/bash
# openclaw-healthcheck.sh

# 检查进程
if ! pgrep -f "openclaw" > /dev/null; then
  echo "OpenClaw未运行,尝试重启"
  openclaw start
fi

# 检查磁盘空间
disk_usage=$(df ~/.openclaw | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $disk_usage -gt 90 ]; then
  echo "磁盘空间不足,清理旧记忆"
  find ~/.openclaw/workspace/memory -name "*.md" -mtime +30 -delete
fi

# 检查API额度(需自定义)
# check_api_quota.sh
```

### 12.5 定期维护任务

| 任务 | 频率 | 脚本 |
|------|------|------|
| 健康检查 | 每小时 | openclaw-healthcheck.sh |
| Token限额检查 | 每日 | check_token_limit.sh |
| 日志清理 | 每周 | clean_logs.sh |
| 备份 | 每日 | backup.sh |
| 过期记忆清理 | 每月 | clean_memory.sh |

---

## 快速检查清单

### 部署前
- [ ] Node.js版本≥20
- [ ] 已获取API密钥
- [ ] 网络可访问GitHub和API服务商
- [ ] 端口18789未被占用

### 配置后
- [ ] config.yaml格式正确
- [ ] API密钥已配置(环境变量)
- [ ] 记忆目录权限正常
- [ ] 工具权限已设置

### 启动后
- [ ] Gateway进程运行中
- [ ] 日志无ERROR
- [ ] 测试对话响应正常
- [ ] 记忆写入正常

### 运维期
- [ ] 每日检查Token消耗
- [ ] 每周检查磁盘空间
- [ ] 每月清理过期记忆
- [ ] 定期备份配置

---

## 参考资料

1. [OpenClaw官方文档](https://docs.openclaw.ai/)
2. [OpenAI API文档](https://platform.openai.com/docs)
3. [Anthropic Claude文档](https://docs.anthropic.com)
4. [Zhipu GLM文档](https://open.bigmodel.cn/dev/api)
5. [DeepSeek API文档](https://platform.deepseek.com/api-docs)

---

## 附录:成本估算示例

### 场景1:小型团队(10人,日均1000次对话)
- 模型选择: GPT-5.4-mini
- 每次对话平均: 500输入Token + 200输出Token
- 日消耗: 1000×(500+200)=70万Token
- 月消耗: 21百万Token
- 月费用: 输入21M×\$0.75/M= \$15.75 + 输出4.2M×\$4.5/M= \$18.90
- **总计: ~\$35/月**

### 场景2:中型团队(50人,日均5000次对话)
- 模型选择: DeepSeek-V3.2 + GLM-5.4混用
- 日消耗: 5000×700=3.5M Token
- 月消耗: 105M Token
- 月费用: 输入52.5M×\$0.028/M= \$1.47 + 输出21M×\$0.42/M= \$8.82
- **总计: ~\$10/月**(DeepSeek为主)

### 场景3:私有部署(高隐私要求)
- 模型选择: LLaMA-3-70B自托管
- 硬件: 2×RTX 5060 Laptop(或云GPU)
- 月费用: 云GPU租费 ~\$200-500
- Token成本: \$0(仅需电力)

---

**文档版本**: v1.0
**更新日期**: 2026-04-14
**适用版本**: OpenClaw latest
