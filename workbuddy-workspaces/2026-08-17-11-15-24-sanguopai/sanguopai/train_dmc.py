"""三国牌 · Deep Monte-Carlo (DMC) 训练器 —— 照搬开源成熟方案 DouZero 的架构。

为什么换掉 REINFORCE：
  - REINFORCE(策略梯度) 在「140 个离散动作 + 4 轮信用分配 + 5 人博弈」上样本效率极低，
    小网络 3 万局就坍缩成「无脑选最大牌型」≈ 贪心启发式，没有增量价值。
  - DouZero(kwai/DouZero, ICML 2021, ★4.6k) 用 DMC 在斗地主(动作空间高达 2 万+)上击败 344 个 bot：
      · 价值型：Q(s,a) 用蒙特卡洛回报(实际落袋豆)估计，动作 = argmax Q（ε 探索）
      · 动作编码：把「状态特征」和「候选动作特征」拼一起送进网络，逐动作打分
      · 并行 actor + 经验回放 + 自对弈
  - 关键增益：Q 能学到「上下文相关」的价值——牌大但同类扎堆(kill 连锁)、当老②③④被名次倍率打满
    这些**和上下文有关的风险**，贪心(只看自己牌型分)完全看不到。

★ 本版的两个核心修正（都是"豆量决定策略"的直接后果）

  (1) **按财富档分 head 的 Q 网络（multi-head）**
      结算里输赢两侧都是"分段线性"的：
        · 每份收益上限 U(M) = clamp(max(入场豆,当前豆), 450万, 1800万)   ← 有钱才收得满
        · 每份损失上限 D(M) = min(1800万, M)                            ← 输光为止
      → U/D 比从「穷人的 28:1」单调降到「富人的 1:1」：
          带 16万 的人输光只亏 16万，赢一把每份收 450万、4 家 1800万（112 倍杠杆）→ 该**激进**；
          带 1亿的人输赢对称（各 1800万），还要面对名次②③④(32/24/12)+暴击12×+杀牌16× → 该**保守**。
      一张网络同时拟合这两种目标只会折衷成"谁都不最优"的平均策略。拐点恰在 450万 / 1800万，
      所以按这两个拐点分 3 档 head：共享 trunk，按自己财富档选 head。档内结构同构，折衷被结构性消除。

  (2) **真实的 25 人持久池 + 随机匹配**
      真实牌桌是 25 人一个池子、每局随机抽 5 人成桌、豆跨局持久、破产补 16 万。
      实测稳态：约 73% 的人长期压在 16万 地板，中位数=16万（不是"每局重抽豆"那种均匀分布）。
      旧版把池建在子进程里 → 每批重置 = 持久名存实亡。本版池在主进程，跨批持久。

参考实现：
  kwai/DouZero            https://github.com/kwai/DouZero
  datamallab/rlcard (DMC)  https://github.com/datamllab/rlcard
  论文 Table 4 特征编码    https://arxiv.org/abs/2106.06135
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
from collections import deque
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool

import numpy as np
import torch
import torch.nn as nn

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sanguopai.config import DEFAULT_CONFIG  # noqa: E402
from sanguopai.env.card import Card  # noqa: E402
from sanguopai.env.evaluator import evaluate_five_score  # noqa: E402
from sanguopai.env.game import ACTION_TABLE, N_ACTIONS, SanGuoPaiGame  # noqa: E402

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
CFG = DEFAULT_CONFIG
P13_5 = 13 ** 5
CARD_POOL = [Card.from_code(c) for c in range(52)]

# ---------- 特征维度（改这些必须同步 game.html，并重跑 parity 校验） ----------
# 基础状态 194 = 我的手牌52 + 公共牌52 + 出现过的牌52 + 轮次4 + 我的豆2 + 我的财富档2
#             + 破产距离1 + 本局盈亏1 + 各阵营最强牌型3
#             + 对手豆4 + 对手入场豆4 + 对手收款档12
#             + 相对对手财富2 + 对手穷人比例1 + 存活数1 + 牌库1
# 历史块 512 = 每轮(4) × 每个对手(4) × 32：
#   阵营 one-hot(3) + **他这轮从手牌里花掉的那几张的点数计数(13)** + 牌型 one-hot(9)
#   + 名次 one-hot(5) + 收益符号对数(1) + 破产(1)
#   —— 关键：只记「花掉的手牌」，**不含公共牌**。牌型是"手牌+公共牌"的组合产物，
#      别人看着像大牌可能只是公共牌刚好补了个葫芦，所以打出的 5 张点数没有信息量；
#      有信息量的是"他愿意花掉手里哪几张" → 才能推他的留牌、下轮能凑什么。
#   同时必须记**结果**（名次/被电多少/是否破产）——杀牌与名次都是"相对"量。
HIST_ROUNDS = CFG.n_rounds          # 4
HIST_OPPS = CFG.n_players - 1       # 4
HIST_PER = 3 + 13 + 9 + 5 + 1 + 1   # 32
HIST_DIM = HIST_ROUNDS * HIST_OPPS * HIST_PER
BASE_DIM = 52 * 3 + 4 + 2 + 2 + 2 + 3 + 4 + 4 + 12 + 3 + 2   # 194
S_DIM = BASE_DIM + HIST_DIM         # 194 + 512 = 706
A_DIM = 3 + 8 + 13 + 4 + 9 + 6 + 2  # 45
IN_DIM = S_DIM + A_DIM              # 751

# 回报压缩的尺度按计分方式切换（见 _squash）：
#   豆制  ：单局 |Δ豆| 上限 ≈ 4×cap = 7200万
#   积分制：典型单局 |净积分| 数千（= 合成 牌型×暴击×名次×杀牌，量级 1e3~1e4）

# ---------- 财富档：切在 payoff 的**结构拐点**（450万），而不是封顶（1800万） ----------
# 为什么是 2 档而不是 3 档：写清两侧的收益/损失上限
#     U(M) = clamp(max(入场豆,当前豆), 450万, 1800万)   每份最多收多少
#     D(M) = min(1800万, M)                             每份最多输多少
#   · M ≤ 450万 ：U=450万(常数)、D=M  → 风险收益比 U/D ∈ [1, 28]，越穷越像免费彩票 → **该激进**
#   · M > 450万 ：U=D=min(M,1800万)   → **完全对称**，风险比恒 1:1     → **该保守**
#   450万 以上"M 具体多少"只改绝对尺度、不改结构 → 再切一刀（1800万）得到的中间档在真实持久池里
#   只占 ~3%（实测：穷 77.6% / 中 3.2% / 富 19.2%，因为穷档一赢就直接跳到封顶），样本太少训不动。
#   所以分 2 档：head0 = 高杠杆档，head1 = 对称档。
N_TIERS = 2


def tier_of(entry: int, cur: int) -> int:
    """头路由：算自己该用哪个 head。0 = 高杠杆档（M ≤ 450万，该激进）；1 = 对称档（该保守）。"""
    return 0 if max(int(entry), int(cur)) <= CFG.min_win else 1


def cap_tier_of(entry: int, cur: int) -> int:
    """纯特征用：把「每份收款上限」切 3 档（≤450万 / 450万~1800万 / ≥1800万）。

    这是"对手当赢家时能从我这收多少"的信息，越细越好，与 head 数无关。
    """
    m = max(int(entry), int(cur))
    if m <= CFG.min_win:
        return 0
    if m >= CFG.cap:
        return 2
    return 1


def scale_of(entry: int, cur: int) -> float:
    """该座位「每份能赢到的上限」（= 结算口径），用来把回报归一化/分档。"""
    return float(min(max(max(int(entry), int(cur)), CFG.min_win), CFG.cap))


def _logu(rng, lo: int, hi: int) -> int:
    """对数均匀抽豆（钱的对数尺度才是均匀的）。"""
    lo = max(1, int(lo)); hi = max(lo, int(hi))
    return int(np.exp(rng.uniform(np.log(lo), np.log(hi))))


def _bits52(codes):
    v = np.zeros(52, dtype=np.float32)
    for c in codes:
        if 0 <= c < 52:
            v[c] = 1.0
    return v


def build_action_feats(hand_codes, pub_wei, pub_wu):
    """一次性算出 140 个动作的特征矩阵 + grade/score 辅助数组（DouZero 的「动作编码」）。"""
    feats = np.zeros((N_ACTIONS, A_DIM), dtype=np.float32)
    grades = np.zeros(N_ACTIONS, dtype=np.int64)
    scores = np.zeros(N_ACTIONS, dtype=np.int64)
    cards_list = []
    hand = hand_codes
    for aid in range(N_ACTIONS):
        faction, hand_idx = ACTION_TABLE[aid]
        sel = [hand[i] for i in hand_idx]
        pub = pub_wei if faction == 0 else (pub_wu if faction == 2 else [])
        cards = sel + list(pub)
        score = evaluate_five_score([CARD_POOL[c] for c in cards])
        grade = score // P13_5
        cards_list.append(cards)
        grades[aid] = grade
        scores[aid] = score
        o = 0
        feats[aid, faction] = 1.0                      # 阵营 one-hot(3)
        o += 3
        for i in hand_idx:                             # 用了哪几张手牌(8)
            feats[aid, o + i] = 1.0
        o += 8
        # 注意：card.py 的编码是 code = suit*13 + rank（不是 rank*4+suit！）
        rk = np.zeros(13, dtype=np.float32)            # 5 张点数计数(13)，0=2 … 12=A
        for c in cards:
            rk[c % 13] += 1.0
        feats[aid, o:o + 13] = rk
        o += 13
        su = np.zeros(4, dtype=np.float32)             # 花色计数(4)
        for c in cards:
            su[c // 13] += 1.0
        feats[aid, o:o + 4] = su
        o += 4
        feats[aid, o + grade] = 1.0                    # 牌型 one-hot(9)
        o += 9
        feats[aid, o + CFG.kill_classes[grade]] = 1.0  # 杀牌类 one-hot(6) ← 连锁风险关键
        o += 6
        feats[aid, o] = CFG.type_multipliers[grade] / 1000.0     # 牌型倍率(归一)
        feats[aid, o + 1] = (score % P13_5) / P13_5              # tiebreak 强度
    return feats, grades, scores, cards_list


def build_state_feats(game, pid, action_feats, grades, scores):
    """状态特征（自己的牌/公共牌/已见牌/轮次/豆子/对手豆子/各阵营最好牌型/历史）。"""
    obs_hand = [c.code for c in game.hands[pid]]
    hand = obs_hand + [52] * (CFG.hand_size - len(obs_hand))
    pub = [c.code for c in game.public[0]] + [c.code for c in game.public[2]]
    seen = list(game.public_seen)
    v = np.zeros(S_DIM, dtype=np.float32)
    o = 0
    v[o:o + 52] = _bits52(hand); o += 52
    v[o:o + 52] = _bits52(pub); o += 52
    v[o:o + 52] = _bits52(seen); o += 52
    r = min(game.round, CFG.n_rounds - 1)
    v[o + r] = 1.0; o += 4                                   # 轮次 one-hot
    own = max(0, game.chips[pid])
    v[o] = math.log10(own + 1) / 9.0
    v[o + 1] = min(own / 1e8, 2.0) / 2.0
    o += 2
    E = game.entry_chips[pid]
    tier = tier_of(E, game.chips[pid])                        # 我的财富档（决定用哪个 head）
    v[o + tier] = 1.0; o += 2
    # 破产距离：还能吃几份"自己的封顶"（1 份 ≈ 一次满额支付）—— 直接决定"我敢不敢冒险"
    sc = scale_of(E, game.chips[pid])
    v[o] = min(own / max(1.0, sc), 3.0) / 3.0
    # 本局盈亏（相对入场豆）：已在赢的人更不该冒险，已在亏的人可能要求翻本
    v[o + 1] = max(-1.0, min(1.0, (own - E) / max(1.0, float(E))))
    o += 2
    for f in range(3):                                        # 各阵营我拿得出手的最强牌型
        idx = [a for a in range(N_ACTIONS) if ACTION_TABLE[a][0] == f]
        best = int(scores[idx].max()) if idx else 0
        v[o + f] = best / (P13_5 * 1001.0)
    o += 3
    opp4 = [p for p in range(CFG.n_players) if p != pid]
    # 对手豆用**对数尺度**（线性尺度在 1e6 时≈0.01，网络分辨不出；结算只看"档"）
    for k, q in enumerate(opp4):
        v[o + k] = math.log10(max(0, game.chips[q]) + 1) / 9.0
    o += 4
    for k, q in enumerate(opp4):
        v[o + k] = math.log10(max(0, game.entry_chips[q]) + 1) / 9.0
    o += 4
    for k, q in enumerate(opp4):
        # 对手的「每份收款上限」档 —— 他当赢家时能从我这儿收多少就看这个
        v[o + k * 3 + cap_tier_of(game.entry_chips[q], game.chips[q])] = 1.0
    o += 4 * 3
    # 相对财富：我 vs 对手（"我是不是桌上那个肥羊/穷鬼"）
    others = [max(0, game.chips[q]) for q in opp4]
    omax = max(others) if others else 0
    omean = (sum(others) / len(others)) if others else 0.0
    v[o] = math.log10((own + 1) / (omax + 1)) / 3.0 + 0.5     # 相对最大对手（居中）
    v[o + 1] = math.log10((own + 1) / (omean + 1)) / 3.0 + 0.5
    o += 2
    v[o] = sum(1 for q in opp4 if game.chips[q] <= CFG.min_win) / 4.0   # 对手里穷人的比例
    o += 1
    n_alive = sum(1 for p in range(CFG.n_players) if not game.bankrupt[p])
    v[o] = n_alive / CFG.n_players
    v[o + 1] = min(len(game.deck_pool) / 30.0, 1.0)
    o += 2
    # ---- 历史块：每轮每个对手「出了什么 + 结果如何」----
    opp_ids = [p for p in range(CFG.n_players) if p != pid]
    for r in range(HIST_ROUNDS):
        log = game.history_log[r] if r < len(game.history_log) else None
        for k, q in enumerate(opp_ids):
            base = o + (r * HIST_OPPS + k) * HIST_PER
            if log is None:
                continue
            sub = next((s for s in log["submissions"] if s["player"] == q), None)
            if sub is None:
                continue
            v[base + int(sub["faction_id"])] = 1.0                    # 阵营
            for code in sub.get("hand_codes", ()):                    # 他这轮**花掉的手牌** → 点数计数
                v[base + 3 + (code % 13)] += 1.0
            v[base + 16 + int(sub["grade_id"])] = 1.0                 # 他的牌型
            rk = int(sub.get("rank", 0))                              # 他的名次（相对强弱）
            if 1 <= rk <= 5:
                v[base + 25 + (rk - 1)] = 1.0
            rw = float(sub.get("reward", 0.0))                        # 他被结算了多少（符号+对数）
            if rw:
                v[base + 30] = math.copysign(math.log10(1.0 + abs(rw)) / 8.0, rw)
            v[base + 31] = 1.0 if sub.get("bankrupt") else 0.0        # 是否破产停玩
    o += HIST_DIM
    assert o == S_DIM, (o, S_DIM)
    return v


class QNet(nn.Module):
    """DouZero/RLCard 的 DMCNet + **分财富档多 head**。

    输入 concat(状态, 动作) → 共享 trunk → 按「自己的财富档」选一个 head 出标量 Q。
    trunk 共享 → 样本效率不降；head 分离 → 穷/富策略不再互相折衷。
    """

    def __init__(self, in_dim=IN_DIM, hidden=(256, 256, 256), n_heads=N_TIERS):
        super().__init__()
        layers = []
        d = in_dim
        for h in hidden:
            layers += [nn.Linear(d, h), nn.ReLU()]
            d = h
        self.trunk = nn.Sequential(*layers)
        self.heads = nn.ModuleList([nn.Linear(d, 1) for _ in range(n_heads)])
        self.n_heads = n_heads

    def trunk_out(self, x):
        return self.trunk(x)

    def forward(self, x, head: int):
        """单个 head 前向（推理用）。"""
        return self.heads[head](self.trunk(x)).squeeze(-1)


def q_by_tier(model, x, tiers):
    """批量前向：trunk 只算一次，再按各样本的 tier 分派 head（训练用）。"""
    h = model.trunk(x)
    out = torch.empty(x.shape[0], device=x.device)
    for t in range(model.n_heads):
        sel = (tiers == t)
        if bool(sel.any()):
            out[sel] = model.heads[t](h[sel]).squeeze(-1)
    return out


# ---------------- 权重传输：float32 bytes（比 list 快一个量级） ----------------
def pack_weights(model):
    """state_dict → {name: (shape, bytes)} —— pickle 连续内存，IPC 比 Python list 快 3~10 倍。"""
    out = {}
    for k, v in model.state_dict().items():
        arr = np.ascontiguousarray(v.detach().cpu().numpy(), dtype=np.float32)
        out[k] = (tuple(arr.shape), arr.tobytes())
    return out


def model_from_packed(packed):
    m = QNet().to(DEVICE)
    m.load_state_dict({k: torch.from_numpy(
        np.frombuffer(b, dtype=np.float32).reshape(sh).copy()) for k, (sh, b) in packed.items()})
    m.eval()
    return m


def weights_to_lists(model):
    """给网页用的 json 格式（list 嵌套）。"""
    return {k: v.detach().cpu().numpy().tolist() for k, v in model.state_dict().items()}


def _squash(delta: float) -> float:
    """有符号对数压缩（把"收益尺度"归一，只保序、不改变同一决策内的 argmax）。

    保序 → 同决策内 argmax 不变；但对数压缩让"小赢/大赢"落在同一量级，MSE 不被极端样本主导。
    尺度随计分方式切换：
      · 豆制  ：|Δ豆| 上限 ≈ 4×cap = 7200万，unit=1e5，满格≈7200万
      · 积分制：典型 |净积分| 数千（合成倍率量级 1e3~1e4），unit=1e3，满格≈1万分
    """
    if not delta:
        return 0.0
    if CFG.scoring == "score":
        unit, denom = 1.0e3, math.log1p(1.0e4 / 1.0e3)
    else:
        unit, denom = 1.0e5, math.log1p(4.0 * CFG.cap / 1.0e5)
    return math.copysign(math.log1p(abs(delta) / unit) / denom, delta)


# ---------------- 对手策略（评估/对照用，也可当训练对手） ----------------
def greedy_action(game, pid):
    """选使自己 5 张组合牌型分最高的动作 = 外行直觉（"无脑选最大"）。"""
    best_a, best_s = 0, -1
    for aid in range(N_ACTIONS):
        faction, hand_idx = ACTION_TABLE[aid]
        sel = [game.hands[pid][i] for i in hand_idx]
        pub = game.public[0] if faction == 0 else (game.public[2] if faction == 2 else [])
        s = evaluate_five_score(sel + list(pub))
        if s > best_s:
            best_s, best_a = s, aid
    return best_a


def minrank_action(game, pid):
    """主动求败：选牌型最小的一手，争取垫第⑤名（名次倍率仅 4）。"""
    best_a, best_s = 0, None
    for aid in range(N_ACTIONS):
        faction, hand_idx = ACTION_TABLE[aid]
        sel = [game.hands[pid][i] for i in hand_idx]
        pub = game.public[0] if faction == 0 else (game.public[2] if faction == 2 else [])
        s = evaluate_five_score(sel + list(pub))
        if best_s is None or s < best_s:
            best_s, best_a = s, aid
    return best_a


OPP_POLICIES = {"greedy": greedy_action, "minrank": minrank_action}


# ---------------- Actor：自对弈/陪练跑一局 ----------------
def play_episode(packed, seed, epsilon, starting_chips, opp_policy=None,
                 net_seats=None, collect=True, net=None):
    """所有座位共用同一张 Q 网络（5 人对称）；ε-greedy 选动作；回报=本局最终豆 − 决策前豆。

    opp_policy : None=自对弈；'greedy'/'minrank'/'random' = 陪练策略。
    net_seats  : None=全部座位用网络；否则**只有**这些座位用网络，其余走 opp_policy。
    collect    : False 时不记录 transition（评估省时间）。
    返回 (transitions, 终局豆, 破产标记, 末轮名次 dict)
    """
    if net is None:                       # worker 一批只建一次网络（别每局重建）
        net = model_from_packed(packed)
    starts = ([int(starting_chips)] * CFG.n_players
              if isinstance(starting_chips, (int, float)) else [int(x) for x in starting_chips])
    game = SanGuoPaiGame(config=CFG, seed=seed, initial_chips=max(starts))
    game.reset(starting_chips=starts)
    rng = random.Random(seed ^ 0x9E3779B9)
    rec = []  # (pid, input_vec(list), chips_before, tier)
    use_net_all = net_seats is None
    dev_n = dev_d = 0        # 评估用：模型选择 ≠ 「牌型最大」的次数（= 它有多敢"躲"）

    while not game.done:
        acts = {}
        for pid in range(CFG.n_players):
            if game.bankrupt[pid]:
                continue
            af, grades, scores, _cards = build_action_feats(
                [c.code for c in game.hands[pid]], [c.code for c in game.public[0]],
                [c.code for c in game.public[2]])
            if not (use_net_all or pid in net_seats):
                if opp_policy == "random":
                    acts[pid] = rng.randrange(N_ACTIONS)
                else:
                    acts[pid] = OPP_POLICIES[opp_policy or "greedy"](game, pid)
                continue
            sv = build_state_feats(game, pid, af, grades, scores)
            x = np.concatenate([np.repeat(sv[None, :], N_ACTIONS, axis=0), af], axis=1)
            tier = tier_of(game.entry_chips[pid], game.chips[pid])   # ★ 按自己财富档选 head
            with torch.no_grad():
                q = net(torch.from_numpy(x).to(DEVICE), tier).cpu().numpy()
            if rng.random() < epsilon:
                aid = rng.randrange(N_ACTIONS)
            else:
                aid = int(np.argmax(q))
            if collect:
                inp = np.concatenate([sv, af[aid]]).astype(np.float32)
                rec.append((pid, inp.tolist(), game.chips[pid], tier))
            else:
                # 评估：统计"它选的动作"和"牌型最大的动作"差多少 —— 偏离率高 = 学会躲了
                dev_d += 1
                if aid != int(np.argmax(scores)):
                    dev_n += 1
            acts[pid] = aid
        game.step(acts)

    # 目标回报 = 有符号对数压缩后的 (最终豆 − 决策前豆) —— γ=1 的 MC return-to-go，**无任何塑形**。
    trans = [(inp, _squash(float(game.chips[pid] - before)), tier)
             for (pid, inp, before, tier) in rec]
    last_ranks = {}
    if game.history_log:
        for s in game.history_log[-1]["submissions"]:
            last_ranks[int(s["player"])] = int(s.get("rank", 0))
    stats = {"dev": dev_n, "dec": dev_d}
    return trans, list(game.chips), list(game.bankrupt), last_ranks, stats


def _actor(payload):
    """worker：接一批 (seed, table, starts) 跑局。**池状态在主进程维护**（worker 无状态）。"""
    packed, jobs, epsilon = payload
    net = model_from_packed(packed)       # 每批只建一次（旧版每局重建 = 白烧算力）
    out = []
    for seed, table, starts in jobs:
        trans, chips, bust, ranks, _st = play_episode(packed, seed, epsilon, starts, net=net)
        out.append((trans, chips, bust, ranks, table))
    return out


# ---------------- 训练主循环 ----------------
_EVAL_RNG = random.Random(20260914)
EVAL_STARTS = [
    [int(np.exp(_EVAL_RNG.uniform(np.log(160_000), np.log(200_000_000)))) for _ in range(CFG.n_players)]
    for _ in range(32)
]


def evaluate(packed, n=120, seed0=90000, opp="greedy"):
    """被测座位在 5 个位置**轮换**、其余 4 家固定对手；豆表与种子固定（CRN）→ 可横向比较。

    返回 dict：rel=相对自身最大单局风险的收益（主判据，杜绝"富档重尾"主导均值）、
    net=平均净豆、rank=平均名次、dz=落在②③④"死亡区"的比例、bust=破产率、top1=拿第①比例。
    """
    nets, rels, ranks, dz, bust, top1 = [], [], [], 0, 0, 0
    by_tier = {t: [] for t in range(N_TIERS)}
    dev_n = dev_d = 0
    for k in range(n):
        # 积分制下大家从 0 分开始（与训练一致）；豆制才用财富豆表
        st = (EVAL_STARTS[k % len(EVAL_STARTS)] if CFG.scoring == "chips"
              else [0] * CFG.n_players)
        me = k % CFG.n_players                    # 被测座位轮换（避免位置偏差）
        _t, chips, b, lastr, _st = play_episode(packed, seed0 + k, 0.0, st, opp_policy=opp,
                                                net_seats={me}, collect=False)
        dev_n += _st["dev"]; dev_d += _st["dec"]
        d = chips[me] - st[me]
        nets.append(d)
        # 豆制：分母 = 该座位单局最多可能输掉的（手里的豆，封顶 1800万）→ 穷富同尺度
        # 积分制：没有"财富尺度"这个概念，直接就是净积分
        denom = (max(1.0, min(float(st[me]), float(CFG.cap)))
                 if CFG.scoring == "chips" else 1.0)
        rels.append(d / denom)
        rk = lastr.get(me, 0)
        if 1 <= rk <= 5:
            ranks.append(rk)
            if rk == 1:
                top1 += 1
            if rk in (2, 3, 4):
                dz += 1
        if b[me]:
            bust += 1
        by_tier[tier_of(st[me], st[me])].append(rels[-1])
    m = max(1, len(ranks))
    return {
        "rel": float(np.mean(rels)),
        "net": float(np.mean(nets)),
        "rank": float(np.mean(ranks)) if ranks else 0.0,
        "dz": dz / m,
        "bust": bust / n,
        "top1": top1 / m,
        # 分档收益：穷/非穷两档各自的表现（财富条件策略到底有没有分开，看这个）
        "tier_rel": {t: (float(np.mean(v)) if v else 0.0) for t, v in by_tier.items()},
        # 偏离率 = 模型选择 ≠「牌型最大」的比例。**必须和 rel / rank 一起读**，单看会误判：
        #   未训练或训崩 → 偏离很高(80%+) 但 rel 差、rank 差  （≈瞎选）
        #   练成"无脑选最大" → 偏离 ≈ 0%，rel 平平
        #   真学会躲 → **偏离 20~40%** 且 rank↓、②③④↓、rel↑（这才是上下文智慧）
        "dev": dev_n / max(1, dev_d),
    }


def main():
    ap = argparse.ArgumentParser(description="三国牌 DMC 训练（DouZero 风格 + 分财富档多 head）")
    ap.add_argument("--games", type=int, default=20000, help="总训练局数")
    ap.add_argument("--workers", type=int, default=0, help="并行 actor 数(0=自动,1=单进程)")
    ap.add_argument("--lr", type=float, default=5e-4)
    ap.add_argument("--batch", type=int, default=512)
    ap.add_argument("--buffer", type=int, default=20_000, help="经验回放池（别太大，否则早期垃圾永久污染）")
    ap.add_argument("--epsilon", type=float, default=0.05, help="探索率终值")
    ap.add_argument("--eps_start", type=float, default=0.7, help="探索率初值（NaN=纯随机，纯浪费）")
    ap.add_argument("--warmup_frac", type=float, default=0.15, help="前几成局数内把 ε 从初值退火到终值")
    ap.add_argument("--updates_per_game", type=float, default=2.0, help="每局平均梯度步数")
    ap.add_argument("--games_per_call", type=int, default=16, help="每个 worker 每次跑多少局")
    ap.add_argument("--eval_every", type=int, default=2000)
    ap.add_argument("--eval_games", type=int, default=120, help="每次评估打多少局")
    ap.add_argument("--pool_size", type=int, default=25, help="持久池人数（5 桌 × 5 人）")
    # ★ 入场门槛：真实场次是分级的，豆不够根本坐不下来。0 = 不设门槛（"全服"视角，咸鱼会堆积）
    #   实测（400 局取后 100 局快照，同为贪心）——
    #     门槛 0     ：中位 16万，<50万 占 65.9%，≥1800万 占 29.8%，破产 3.25 人次/局
    #     门槛 1800万：中位 33057万，<50万 占 0%，≥1800万 占 99.4%，破产 0.26 人次/局
    #   即"打匹配感觉没那么多咸鱼"的真相是**门槛把咸鱼挡在外面**。按你实际打的场设置。
    ap.add_argument("--entry_gate", type=int, default=0,
                    help="入场门槛：低于它就离场换人（0=无门槛）")
    ap.add_argument("--rebuy_lo", type=int, default=160_000, help="破产补豆下限（无门槛时生效）")
    ap.add_argument("--rebuy_hi", type=int, default=1_600_000, help="破产补豆上限（无门槛时生效）")
    # ★ 破产退出率：真实玩家输光是**走了**，不会永远补豆留在同一桌当咸鱼。
    #   实测（400 局取后 100 局快照）——这个参数对分布的影响比门槛还大：
    #     退出率 0%（= 假设"人人输了就充钱继续"，我早前模型）→ <50万 占 30.0%，破产 3.06 人次/局
    #     退出率 50%                                        → <50万 占  4.6%，破产 1.12 人次/局
    #     退出率 90%                                        → <50万 占  1.7%，破产 0.80 人次/局
    #   即**真实牌桌"没那么多咸鱼"的主因是破产者退场了**（换新人补位），而不是门槛。
    #   0% 那个假设等价于"人人都输光就充钱"，那样平台确实赚爆——现实不成立。
    ap.add_argument("--bust_quit", type=float, default=0.5,
                    help="破产后有这个概率退出（新玩家补位）；1-它 才是补豆续命")
    ap.add_argument("--starting_lo", type=int, default=160_000)
    # 初始豆上限。**这个值真的影响训练分布**（实测，400 局后 100 局快照，同为贪心策略）：
    #   16万~1亿  → 中位 16万，<50万 占 77.7%，≥1800万 占 13.4%   （池子以咸鱼为主，桌上没钱）
    #   16万~2亿  → 中位 16万，<50万 占 65.6%，≥1800万 占 31.6%   ← 默认
    #   16万~10亿 → 中位 16万，<50万 占 56.6%，≥1800万 占 40.6%
    # 注意**中位数恒为 16万（补豆地板）**：初值抬高的只是"富人圈有多大"，咸鱼永远是咸鱼。
    # 抬高的意义在于：桌上有钱，赢家才能收满（见 RULES_AND_STRATEGY.md「咸鱼陷阱」）。
    ap.add_argument("--starting_hi", type=int, default=200_000_000)
    ap.add_argument("--out_json", type=str, default="sanguopai_dmc_weights.json")
    ap.add_argument("--out_pt", type=str, default="sanguopai_dmc_model.pt")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--serial", action="store_true")
    # ★ 奖励口径：score = 纯积分 ±(牌型×暴击×名次×杀牌)（无封顶/无财富档）；chips = 豆（经济那套）
    #   积分制下"打得好/坏"不再被 1800万封顶抹平（豆制下多数局面 L 都超封顶 → 都付满 → 梯度消失），
    #   更适合练牌。积分模式下每局 5 人从 0 分开始，不维护池、不补豆、不破产。
    ap.add_argument("--reward", choices=["score", "chips"], default=None,
                    help="奖励口径（默认跟随 config.scoring）")
    a = ap.parse_args()

    global CFG
    if a.reward and a.reward != CFG.scoring:
        import dataclasses
        CFG = dataclasses.replace(CFG, scoring=a.reward)

    torch.manual_seed(a.seed)
    np.random.seed(a.seed)
    random.seed(a.seed)

    model = QNet().to(DEVICE)
    opt = torch.optim.RMSprop(model.parameters(), lr=a.lr, alpha=0.99, eps=1e-5)
    buf = deque(maxlen=a.buffer)
    rng = random.Random(a.seed)

    # ★★ 25 人持久池（主进程持有 → 跨批持久，破产补 16 万）。
    #    旧版把池建在子进程里，每批重置 = "持久"名存实亡，学不到"我穷且会一直穷"。
    pool = [_logu(rng, max(a.starting_lo, a.entry_gate), a.starting_hi)
            for _ in range(max(CFG.n_players, a.pool_size))]

    n_workers = 1 if a.serial else (a.workers if a.workers > 0 else max(1, min(8, (os.cpu_count() or 4) - 2)))
    ex = None if n_workers == 1 else ProcessPoolExecutor(max_workers=n_workers)

    if CFG.scoring == "score":
        mode_txt = "积分制 ±(牌型×暴击×名次×杀牌)/4500，无封顶/无财富档/不破产"
    elif a.entry_gate > 0:
        mode_txt = f"豆制/门槛{a.entry_gate//10000}万"
    else:
        mode_txt = f"豆制/无门槛/补豆{a.rebuy_lo//10000}~{a.rebuy_hi//10000}万/破产退出{a.bust_quit:.0%}"
    print(f"[DMC] in_dim={IN_DIM} S={S_DIM} A={A_DIM} workers={n_workers} "
          f"device={DEVICE} games={a.games} [{mode_txt}]", flush=True)

    done_games = 0
    batch_games = max(1, n_workers) * max(1, a.games_per_call)
    best = -1e18
    saved_any = False
    while done_games < a.games:
        # 1) 采样一批局：ε 从 eps_start 线性退火到 --epsilon
        prog = min(1.0, done_games / max(1.0, a.games * a.warmup_frac))
        eps = a.eps_start - (a.eps_start - a.epsilon) * prog
        # 随机匹配：从持久池里抽 5 人开一桌（各人豆不同，穷富混坐）
        jobs = []
        for _ in range(batch_games):
            if CFG.scoring == "score":
                # 积分制：每局 5 人从 0 分开始，无池、无财富差异
                jobs.append((rng.randrange(1 << 30), None, [0] * CFG.n_players))
            else:
                table = rng.sample(range(len(pool)), CFG.n_players)
                jobs.append((rng.randrange(1 << 30), table, [pool[i] for i in table]))
        packed = pack_weights(model)
        chunks = [jobs[i::max(1, n_workers)] for i in range(max(1, n_workers))]
        payload = [(packed, c, eps) for c in chunks if c]
        try:
            if ex is None:
                results = [_actor(p) for p in payload]
            else:
                results = list(ex.map(_actor, payload))
        except BrokenProcessPool:
            print("[DMC] 进程池崩溃，降级串行并重建池", flush=True)
            try:
                ex.shutdown(wait=False)
            except Exception:
                pass
            ex = None
            n_workers = 1
            results = [_actor(p) for p in payload]

        # 2) 池写回（破产补 16 万，跨批持久）+ 入回放
        done_batch = 0
        for chunk_res in results:
            for trans, chips, _b, _r, table in chunk_res:
                buf.extend(trans)
                if table is None:          # 积分模式：无池可写
                    done_batch += 1
                    continue
                for i, c in zip(table, chips):
                    if a.entry_gate > 0:
                        # 门槛场：破产 或 掉到门槛以下 → 离场（去低场），由新玩家补位
                        pool[i] = c if c >= a.entry_gate else _logu(rng, a.entry_gate, a.starting_hi)
                    elif c <= 0:
                        # 破产：以 bust_quit 概率**退出**（新玩家补位），否则补豆续命
                        if rng.random() < a.bust_quit:
                            pool[i] = _logu(rng, a.starting_lo, a.starting_hi)
                        else:
                            pool[i] = _logu(rng, a.rebuy_lo, a.rebuy_hi)
                    else:
                        pool[i] = c
                done_batch += 1
        if done_batch != batch_games:
            print(f"[DMC] 警告：本批实际 {done_batch} 局 != {batch_games}", flush=True)
        done_games += done_batch
        if done_batch == 0:
            break

        # 3) 学习（ε 太大时数据近似随机，跳过，省算力也避免污染）
        if eps <= 0.5 and len(buf) > a.batch:
            n_upd = max(1, int(batch_games * a.updates_per_game))
            for _ in range(n_upd):
                batch = rng.sample(buf, a.batch)
                xs = torch.tensor(np.array([b[0] for b in batch], dtype=np.float32)).to(DEVICE)
                ys = torch.tensor(np.array([b[1] for b in batch], dtype=np.float32)).to(DEVICE)
                tiers = torch.tensor([b[2] for b in batch], dtype=torch.long).to(DEVICE)
                q = q_by_tier(model, xs, tiers)
                loss = torch.nn.functional.mse_loss(q, ys)
                opt.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 40.0)
                opt.step()

        # 4) 评估 + 只保存"历史最好"
        if done_games % a.eval_every < done_batch:
            model.eval()
            pk = pack_weights(model)
            ev = evaluate(pk, n=a.eval_games, seed0=90000, opp="greedy")
            ev2 = evaluate(pk, n=max(20, a.eval_games // 2), seed0=95000, opp="minrank")
            tag = ""
            if ev["rel"] > best:
                best = ev["rel"]
                with open(a.out_json, "w", encoding="utf-8") as f:
                    json.dump(weights_to_lists(model), f)
                torch.save(model.state_dict(), a.out_pt)
                saved_any = True
                tag = "  ← 新最好，已落盘"
            tr = ev["tier_rel"]
            tier_txt = ("" if CFG.scoring == "score"
                        else f" | 分档 rel 穷={tr[0]:+.3f} 非穷={tr[1]:+.3f}")
            print(f"[DMC] games={done_games} eps={eps:.3f} buf={len(buf)} "
                  f"| vs贪心 净分={ev['rel']:+,.0f} rank={ev['rank']:.2f} "
                  f"②③④={ev['dz']*100:.0f}% 偏离={ev['dev']*100:.0f}% "
                  f"| vs求败 净分={ev2['rel']:+,.0f}{tier_txt}{tag}", flush=True)
            model.train()

    if not saved_any:
        model.eval()
        with open(a.out_json, "w", encoding="utf-8") as f:
            json.dump(weights_to_lists(model), f)
        torch.save(model.state_dict(), a.out_pt)
    unit = "净分" if CFG.scoring == "score" else "rel"
    print(f"[DMC] 完成。最好 {unit}(vs 4贪心) = {best:+,.0f}（落盘的是历史最好权重）", flush=True)
    if ex is not None:
        ex.shutdown(wait=True)


if __name__ == "__main__":
    main()
