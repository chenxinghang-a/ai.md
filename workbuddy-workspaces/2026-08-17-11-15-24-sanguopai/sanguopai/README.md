# 欢乐斗地主「三国牌」仿真 + 强化训练环境

项目路径：`C:\Users\cxx\WorkBuddy\2026-08-17-11-15-24\sanguopai`

## 快速开始

```bash
# 进入项目目录
cd /c/Users/cxx/WorkBuddy/2026-08-17-11-15-24/sanguopai

# 安装依赖（已装 gymnasium + numpy；训练需 torch）
pip install -r requirements.txt

# 运行一局随机对局
python -m sanguopai.test_game

# 测试 Gym 接口
python -m sanguopai.test_gym

# Heuristic vs Random 基线
python -m sanguopai.benchmark

# 单 agent REINFORCE 训练（需 torch）
python -m sanguopai.train_reinforce
```

## 文件结构

```
sanguopai/
├── math_model.md          # 数学模型与形式化定义（已按真实规则更新）
├── config.py              # 全局配置：倍率、底分、封顶等
├── requirements.txt
├── env/
│   ├── __init__.py
│   ├── card.py            # 牌表示、洗牌
│   ├── evaluator.py       # 德州 5 张牌型评估（复用）
│   ├── game.py            # 三国牌核心逻辑
│   └── gym_env.py         # Gymnasium 单 agent + 5 人并行 self-play 接口
├── test_game.py           # 随机对局测试
├── test_gym.py            # Gym 接口测试
├── benchmark.py           # Heuristic vs Random 基线
└── train_reinforce.py     # REINFORCE 训练示例
```

## 已实现的规则

- 5 人、4 轮、**共用一副 52 张牌循环**：每轮用掉的牌（自己出的 k 张 + 用到阵营的公共牌）返回公共库洗混，再补满（手牌补到 8、被用阵营公共牌补到固定张数）。未被选用的阵营公共牌保留不换。「留牌」与「出牌」是核心策略。
- 阵营：魏（公共 3 + 手牌 2）、蜀（手牌 5）、吴（公共 2 + 手牌 3）。
- 9 种牌型 = 德州扑克 5 张，倍率已按截图配置：单张10/对子20/两对30/三张40/顺子60/同花80/三带二100/四炸400/同花顺1000。
- 排名倍率：第2名32、第3名24、第4名12、第5名4。
- 暴击/杀牌倍率：同阵营/同类牌型人数 1→1、2→2、3→4、4→8、5→16。
- 杀牌分类：单张/对子/两对/三张 属同一类；其余各为一类。
- 结算公式：`欢乐豆 = 赢家牌型倍数 × 暴击倍数 × 排名倍数 × 杀牌倍数 × 底分`。
- 封顶与最小输赢：多名第一名时输家对每个第一名各付一份；单份支付 `pay = min(计算值, cap_eff, 当前剩余豆)`，单份上限 `cap_eff` 由入场豆 `E` 与当前豆 `C` 决定——`E≥1800万`恒定吃满、`450万≤E<1800万`取 `min(max(E,C),1800)`、`E<450万`时 `cap_eff=450万`（**上限保护利好低豆，非地板**：计算值不足 450 万按实付，例技巧局输 200 万内即付 200 万）。**豆不为负**：付到 0 即停；豆归 0 即破产停玩（手牌回归公共牌库、不参与后续轮次）。第一名收入 = 各输家实付之和（单轮最高 4×cap）。入场最少16万豆。
- 信息：结算后所有人可见彼此提交的牌组（阵营 + 5 张牌），观察向量已包含历史公开牌 one-hot。

## 训练接口

### 单 agent Gym 环境

```python
from sanguopai.env.gym_env import SanGuoPaiEnv

env = SanGuoPaiEnv(seed=42)
obs, info = env.reset(seed=42)
for _ in range(4):
    action = env.action_space.sample()  # 0..139
    obs, reward, terminated, truncated, info = env.step(action)
```

### 5 人并行 self-play

```python
from sanguopai.env.gym_env import SanGuoPaiParallelEnv

env = SanGuoPaiParallelEnv(seed=42)
obs = env.reset()  # dict {player_id: obs_dict}
actions = {pid: random.choice(...) for pid in range(5)}
obs, rewards, done, info = env.step(actions)
```

## 强化训练路线建议

1. **单 agent vs 随机**：先跑 `train_reinforce.py` 验证 pipeline。
2. **Self-play**：把 `SanGuoPaiParallelEnv` 接 PPO/CFR+，5 个策略网络互相对抗。
3. **对手建模**：观察空间加入历史出牌/名次，让 agent 学习他人倾向。
4. **动作抽象**：当前 140 个离散动作；若网络大，可先按"阵营+关键手牌"做分层策略。

## 注意

- 数学模型见 `math_model.md`。
- 当前 `train_reinforce.py` 只是最小可跑示例，离"最优解"差很远；真正有效需要 self-play + 大量对局。
- 多第一名/平局的处理已在代码中实现，若与游戏内实际不符请告诉我具体对局截图。
