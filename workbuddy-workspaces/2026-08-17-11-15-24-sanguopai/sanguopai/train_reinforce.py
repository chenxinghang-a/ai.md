"""REINFORCE with baseline 训练：单 agent 对抗贪心启发式对手（混合随机）。

三大能力：
 1. 算牌 EV 先验杂交 (--hybrid)：blended = logits + λ·EV，梯度只走网络（算牌是 detached 常数偏置）。
 2. 奖励塑形（默认开启），对应老板的打牌智慧：
      · 单轮事件：链别人+（你当回合第一名电了别人）/ 被链−（你当回合是输家被电）
      · 回合后收益：豆子多+ 与 豆子减− 对称等权重；破产放大“减”的恐惧（负收益×(1+fear)）
      · 破产惩罚：默认 = 电4次(4×被链) + 亏1800万豆
      · 划水+：仅当回合落败第4/5名 且 出"小牌型(单张/一对)" → 奖励“没乱上大牌”
      · 整局终局：4轮打完后按总豆名次——第1名额外奖励、第2名额外惩罚
 3. 多进程并行采集 (--workers N)：把环境模拟(CPU 密集)摊到多核真正提速。
    ——本游戏瓶颈是 Python 环境 + 蒙特卡洛算牌探针，不是神经网络，故 GPU 对“采集”帮助有限；
      若日后装了 CUDA torch，梯度聚合阶段会自动走 GPU。
"""

from __future__ import annotations

import os
import random
from typing import Dict, List, Optional

import numpy as np
import torch
import torch.distributions as dist
import torch.nn as nn
import torch.optim as optim
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool

from sanguopai.config import DEFAULT_CONFIG
from sanguopai.env.gym_env import GreedyHeuristic, SanGuoPaiEnv
from sanguopai.env.card_counter import CardCounter

# 算牌 EV 归一化分母：EV(±5千万) → ±1.0 的偏置量级，再乘 cc_lambda 叠到 logits
CC_EVAL_CLIP = 5.0e7
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# 奖励塑形默认权重（单位：豆，或对称系数）。
#   chain_others：单轮 第1名+（你当回合第一名，链别人/赢）
#   chained     ：单轮 被链−（你当回合是输家，净豆<0）
#   gain        ：收益对称系数——豆子多+ 与 豆子减− 等权重（k=1 即按原始净豆计）
#   bankrupt_fear：破产对本回合“豆子减−”的恐惧放大（负收益 ×(1+fear)）
#   bankrupt    ：破产惩罚，默认 = 电4次(4×被链=8M) + 亏1800万 = 2600万
#   paddle4     ：划水+ 第4名（落败且出小牌型/一类牌内）
#   paddle5     ：划水+ 第5名（落败且出小牌型），最大输家憋小牌省得更多 → 权重高于 paddle4
#   match_rank2 ：单轮 第2名额外惩罚——出了大牌却还是被电的输家（第2输的多、浪费大牌）
#                注意：这是“每轮”名次，不是 4 轮总豆终局名次（总豆排名版已废弃）。
DEFAULT_SHAPING = {
    "chain_others": 3_000_000,
    "chained": 2_000_000,
    "gain": 1.0,
    "bankrupt_fear": 1.0,
    "bankrupt": 26_000_000,
    "paddle4": 1_500_000,
    "paddle5": 2_500_000,
    "match_rank2": 4_000_000,    # 每轮 第2名额外惩罚（浪费大牌）
}

# 小牌型阈值：type_multipliers <= 20 即 仅 散牌(单张)/对子(一对) 算“划水搞小”（两对30 已排除）
_PADDLE_SAFE_MULT = 20


class PolicyNet(nn.Module):
    def __init__(self, n_actions: int = 140, card_emb_dim: int = 8):
        super().__init__()
        self.card_embed = nn.Embedding(53, card_emb_dim)  # 0..51 为牌，52 为破产空槽哨兵
        # obs: [0:14)=牌槽(手牌8+公共5+轮次1)，[14:66)=历史公开牌 one-hot(52)，[66:68)=自己豆数(2)
        self.fc = nn.Sequential(
            nn.Linear(14 * card_emb_dim + 52 + 2, 128),
            nn.ReLU(),
            nn.Linear(128, 128),
            nn.ReLU(),
        )
        self.policy_head = nn.Linear(128, n_actions)
        self.value_head = nn.Linear(128, 1)

    def forward(self, obs: torch.Tensor):
        cards = obs[:, :14].long()  # 牌槽 code 0..52
        seen = obs[:, 14:66].float()  # 52 维可见牌
        beans = obs[:, 66:68].float()  # 2 维豆数特征
        emb = self.card_embed(cards).view(cards.size(0), -1)
        x = torch.cat([emb, seen, beans], dim=-1)
        h = self.fc(x)
        logits = self.policy_head(h)
        value = self.value_head(h).squeeze(-1)
        return logits, value


def obs_to_tensor(obs: np.ndarray) -> torch.Tensor:
    return torch.tensor(obs, dtype=torch.float32).unsqueeze(0).to(DEVICE)


def _is_safe_action(score: int, cfg=DEFAULT_CONFIG) -> bool:
    """按 5 张组合牌型倍率判断是否是“小牌型”（划水）。"""
    grade = score // (13 ** 5)
    return cfg.type_multipliers[grade] <= _PADDLE_SAFE_MULT


def apply_shaping(reward, log_entry, agent_id: int, action: int,
                  win_arr, shaping: Dict[str, float]):
    """把单回合原始净收益(豆)塑形为训练奖励。

    单轮事件（链别人+/被链−）按回合结算标志计；回合后收益按本回合净豆对称计；
    破产放大本回合负收益的恐惧；破产再叠一次性重罚；划水仅在落败第4/5名且出小牌型时给加权。
    log_entry: game.step 返回的 {"submissions":[{player,score,rank,reward,bankrupt}...], "chips":[...]}
    win_arr: 算牌器给出的每候选动作胜率(140)；纯 RL 时为 None → 用“幸存小输”作划水代理。
    """
    if log_entry is None or shaping is None:
        return float(reward)
    net = float(reward)  # 本回合净豆变化（env 返回的就是这个）
    subs = log_entry.get("submissions", [])
    sub = next((s for s in subs if s["player"] == agent_id), None)
    if sub is None:
        return net
    rank = sub["rank"]
    bankrupt = sub.get("bankrupt", False)

    r = 0.0
    # 单轮事件：第1名(链别人/赢)+ / 被链(输家)−
    if rank == 1:
        r += shaping["chain_others"]            # 第1名+
    if net < 0:
        r -= shaping["chained"]                 # 被链−
    # 每轮名次（老板点名）：第2名额外惩罚——出了大牌却还是被电的输家，
    # “第2输的多、浪费大牌”，比普通被链更值得躲开（与 chained 叠加）。
    if rank == 2:
        r -= shaping["match_rank2"]             # 第2名额外惩罚

    # 回合后收益：豆子多+ / 豆子减− 对称等权重；破产放大“减”的恐惧
    k = shaping["gain"]
    if net >= 0:
        r += k * net
    else:
        fear = 1.0 + (shaping["bankrupt_fear"] if bankrupt else 0.0)
        r += k * net * fear                     # 豆子减−（破产时放大）

    # 破产惩罚（终局一次性重罚）
    if bankrupt:
        r -= shaping["bankrupt"]

    # 划水：只在“已落败(第4/5名) 且 出小牌型(一类牌内)”时奖励“没乱上大牌”。
    # 4、5 名权重不同：第5名是最大输家，憋小牌省得更多 → paddle5 > paddle4。
    # （不再依赖算牌胜率；纯 RL / hybrid 统一用 名次+牌型 判定，更稳定可解释。）
    if rank in (4, 5) and _is_safe_action(sub["score"]):
        r += shaping["paddle5"] if rank == 5 else shaping["paddle4"]
    return r


def _collect(model, env, starting_chips=None, risk_lambda=0.0,
             counter=None, cc_lambda=0.0, shaping=None):
    """单局采集（保留计算图）。返回 (log_probs, rewards, values, entropies, total)。"""
    obs, info = env.reset(starting_chips=starting_chips)
    raw_obs = info.get("raw_obs")
    log_probs, rewards, values, entropies = [], [], [], []
    total_reward = 0.0
    while True:
        obs_t = obs_to_tensor(obs)
        logits, value = model(obs_t)  # 保留计算图
        win = None
        if counter is not None and raw_obs is not None:
            ev, win, _cands = counter.analyze(raw_obs)
            ev_norm = np.clip(np.array(ev, dtype=np.float64) / CC_EVAL_CLIP, -2.0, 2.0)
            blended = logits + torch.tensor(cc_lambda * ev_norm, dtype=torch.float32, device=DEVICE)
            d = dist.Categorical(logits=blended)
        else:
            d = dist.Categorical(logits=logits)
        action_tensor = d.sample()
        action = action_tensor.item()
        log_prob = d.log_prob(action_tensor)
        entropy = d.entropy()

        next_obs, reward, terminated, truncated, info = env.step(action)
        if risk_lambda > 0 and reward < 0:
            # 高豆(bean_norm 大)时亏损被放大 → 更不愿亏损；低豆时几乎不放大
            reward = reward * (1.0 + risk_lambda * float(obs[67]))
        if shaping is not None:
            reward = apply_shaping(reward, info.get("log"), 0, action, win, shaping)

        log_probs.append(log_prob)
        values.append(value.squeeze(-1))
        entropies.append(entropy)
        rewards.append(reward)
        total_reward += reward
        obs = next_obs
        raw_obs = info.get("raw_obs", raw_obs)
        if terminated or truncated:
            break
    return log_probs, rewards, values, entropies, total_reward


def compute_returns(rewards: List[float], gamma: float) -> List[float]:
    returns = []
    G = 0.0
    for r in reversed(rewards):
        G = r + gamma * G
        returns.insert(0, G)
    return returns


def episode_grad(weights_dict, seed, starting, hybrid, cc_n_sim_train,
                 cc_lambda, opponent_epsilon, shaping, gamma, entropy_coef, risk_lambda):
    """Worker：用给定权重跑一局，计算 REINFORCE+value+entropy 损失并 backward，
    返回 (梯度列表, 总奖励)。供多进程并行与 serial 回退共用。"""
    model = PolicyNet().to(DEVICE)
    model.load_state_dict(weights_dict)
    model.train()
    env = SanGuoPaiEnv(seed=seed, opponent=GreedyHeuristic(epsilon=opponent_epsilon))
    counter = CardCounter(n_sim=cc_n_sim_train, rng=random.Random(seed)) if hybrid else None
    cc_lam = cc_lambda if hybrid else 0.0

    log_probs, rewards, values, entropies, total = _collect(
        model, env, starting, risk_lambda, counter, cc_lam, shaping)

    returns = compute_returns(rewards, gamma)
    returns_t = torch.tensor(returns, dtype=torch.float32)
    # unbiased=False：单步回合(numel=1)的 std 为 0 而非 nan，避免 0/(nan)=nan 污染权重
    returns_t = (returns_t - returns_t.mean()) / (returns_t.std(unbiased=False) + 1e-8)

    values_t = torch.stack(values).float()  # 保留梯度，供 value_head 学习
    log_probs_t = torch.stack(log_probs)
    entropies_t = torch.stack(entropies)

    # baseline 用 detached 值；value 损失用带梯度的值 → value_head 才有梯度
    advantages = returns_t - values_t.detach()
    policy_loss = -(log_probs_t * advantages).mean()
    value_loss = (values_t - returns_t).pow(2).mean()
    # 熵正则：防止策略坍缩成确定性(softmax 饱和到 p=1.0)，让豆数在接近平手时真能翻转动作。
    entropy_loss = -entropies_t.mean()
    loss = policy_loss + 0.5 * value_loss + entropy_coef * entropy_loss

    model.zero_grad()
    loss.backward()
    grads = [p.grad.detach().clone() for p in model.parameters()]
    return grads, total


def sample_starting_chips(lo: int = 160_000, hi: int = 100_000_000, poor_frac: float = 0.4):
    """对数均匀采样本局起始豆，让策略见过从高豆到补豆的各种财富水平。
    poor_frac：以该概率落在「贫穷区间」(16万~200万)，此时 cap_eff 低、损失封顶，
    是「低豆激进博大牌」策略必须被学到的关键局面——默认偏高频采样以保证覆盖。"""
    if np.random.rand() < poor_frac:
        return int(np.exp(np.random.uniform(np.log(lo), np.log(2_000_000))))
    return int(np.exp(np.random.uniform(np.log(lo), np.log(hi))))


def export_weights_json(model: PolicyNet, path: str) -> None:
    """导出权重为 JSON，供网页验证游戏(JS)与 numpy 经济模拟加载推理。"""
    import json

    state = {k: v.detach().cpu().tolist() for k, v in model.state_dict().items()}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f)
    print(f"Weights exported to {path}")


def evaluate_vs(env: SanGuoPaiEnv, model: PolicyNet, n: int = 200) -> float:
    """评估：用当前模型跑 n 局，返回平均单局净收益（豆，已塑形）。"""
    tot = 0.0
    for _ in range(n):
        _, _, _, _, r = _collect(model, env, None, 0.0, None, 0.0, None)
        tot += r
    return tot / n


def train(
    n_episodes: int = 30000,
    lr: float = 3e-4,
    gamma: float = 1.0,
    eval_every: int = 1000,
    variable_wealth: bool = True,
    opponent_epsilon: float = 0.2,
    risk_lambda: float = 0.0,
    entropy_coef: float = 0.01,
    model_path: str = "sanguopai_model.pt",
    weights_json: str = "sanguopai_weights.json",
    hybrid: bool = False,
    cc_lambda: float = 2.0,
    cc_n_sim_train: int = 8,
    workers: int = 0,        # 0 = 自动(min(8, cpu))；1 或 --serial = 单进程
    serial: bool = False,
    shaping: Optional[Dict[str, float]] = DEFAULT_SHAPING,
):
    env = SanGuoPaiEnv(seed=42, opponent=GreedyHeuristic(epsilon=opponent_epsilon))
    model = PolicyNet().to(DEVICE)
    cc_lam = cc_lambda if hybrid else 0.0
    # 复现性
    torch.manual_seed(42)
    np.random.seed(42)
    optimizer = optim.Adam(model.parameters(), lr=lr)

    if serial or workers == 1:
        n_workers = 1
        pool = None
    else:
        n_workers = workers if workers > 1 else min(4, os.cpu_count() or 4)
        pool = ProcessPoolExecutor(max_workers=n_workers)

    print(f"[train] device={DEVICE} workers={n_workers} hybrid={hybrid} "
          f"shaping={'on' if shaping else 'off'} cc_n_sim={cc_n_sim_train}")

    best_eval = -1e18
    base_seed = 1000
    steps = (n_episodes + n_workers - 1) // n_workers  # 每步用 n_workers 局做梯度平均
    for step in range(1, steps + 1):
        weights = model.state_dict()
        starting_list = [sample_starting_chips() if variable_wealth else None
                         for _ in range(n_workers)]
        # 鲁棒采集：worker 猝死(BrokenProcessPool，多为 Windows 分页/内存压力杀进程)
        # 时重建池并重跑本步；连续失败则降级为单进程本步，避免整轮训练作废。
        results = None
        for _attempt in range(3):
            try:
                if pool is not None:
                    futures = [
                        pool.submit(
                            episode_grad, weights, base_seed + step * n_workers + i,
                            starting_list[i], hybrid, cc_n_sim_train, cc_lam,
                            opponent_epsilon, shaping, gamma, entropy_coef, risk_lambda)
                        for i in range(n_workers)
                    ]
                    results = [f.result() for f in futures]
                else:
                    results = [
                        episode_grad(weights, base_seed + step * n_workers + i,
                                     starting_list[i], hybrid, cc_n_sim_train, cc_lam,
                                     opponent_epsilon, shaping, gamma, entropy_coef, risk_lambda)
                        for i in range(n_workers)
                    ]
                break
            except BrokenProcessPool:
                print(f"[WARN] step {step}: 进程池猝死，重建并重试 (attempt {_attempt + 1}/3)", flush=True)
                try:
                    if pool is not None:
                        pool.shutdown(wait=False, cancel_futures=True)
                except Exception:
                    pass
                if _attempt < 2:
                    pool = ProcessPoolExecutor(max_workers=n_workers)
                else:
                    print("[WARN] 进程池不可恢复，本步降级为单进程", flush=True)
                    results = [
                        episode_grad(weights, base_seed + step * n_workers + i,
                                     starting_list[i], hybrid, cc_n_sim_train, cc_lam,
                                     opponent_epsilon, shaping, gamma, entropy_coef, risk_lambda)
                        for i in range(n_workers)
                    ]
                    pool = None

        grads_list = [r[0] for r in results]
        totals = [r[1] for r in results]
        # 平均各局的梯度（等价于一 batch=n_workers 局的 REINFORCE）
        avg_grads = [
            torch.stack([g[li] for g in grads_list]).mean(dim=0)
            for li in range(len(grads_list[0]))
        ]
        model.zero_grad()
        for p, g in zip(model.parameters(), avg_grads):
            p.grad = g
        optimizer.step()

        ep_done = step * n_workers
        if eval_every and (ep_done % eval_every == 0 or step == steps):
            ev = evaluate_vs(env, model, n=60)
            best_eval = max(best_eval, ev)
            avg_total = sum(totals) / len(totals)
            print(
                f"Ep {ep_done:5d}/{n_episodes} | avg total(shaped): {avg_total:+.0f} "
                f"| eval avg/net-game: {ev:+.0f} | best: {best_eval:+.0f}",
                flush=True,
            )
            # 检查点：每轮评估即落盘，防崩溃丢进度
            torch.save(model.state_dict(), model_path)
            export_weights_json(model, weights_json)

    if pool is not None:
        pool.shutdown()
    # 保存模型 + 导出网页权重
    torch.save(model.state_dict(), model_path)
    export_weights_json(model, weights_json)
    print(f"Model saved to {model_path}; weights -> {weights_json}")
    print(f"Best eval avg net per game: {best_eval:+.0f}")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="三国牌 REINFORCE 训练（算牌杂交 + 奖励塑形 + 并行）")
    ap.add_argument("--n_episodes", type=int, default=30000)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--eval_every", type=int, default=1000)
    ap.add_argument("--entropy_coef", type=float, default=0.01)
    ap.add_argument("--risk_lambda", type=float, default=0.0)
    ap.add_argument("--hybrid", action="store_true", help="开启算牌 EV 先验杂交（logits+λ·EV）")
    ap.add_argument("--cc_lambda", type=float, default=2.0, help="算牌偏置权重 λ")
    ap.add_argument("--cc_n_sim_train", type=int, default=8, help="训练时算牌蒙特卡洛采样数")
    ap.add_argument("--workers", type=int, default=0, help="并行采集进程数(0=自动,1=单进程)")
    ap.add_argument("--serial", action="store_true", help="强制单进程(调试用)")
    ap.add_argument("--no_shaping", action="store_true", help="关闭奖励塑形(纯原始净豆)")
    # 奖励塑形可调权重
    ap.add_argument("--rw_chain", type=float, default=DEFAULT_SHAPING["chain_others"])
    ap.add_argument("--rw_chained", type=float, default=DEFAULT_SHAPING["chained"])
    ap.add_argument("--rw_gain", type=float, default=DEFAULT_SHAPING["gain"])
    ap.add_argument("--rw_bankrupt_fear", type=float, default=DEFAULT_SHAPING["bankrupt_fear"])
    ap.add_argument("--rw_bankrupt", type=float, default=DEFAULT_SHAPING["bankrupt"])
    ap.add_argument("--rw_paddle4", type=float, default=DEFAULT_SHAPING["paddle4"])
    ap.add_argument("--rw_paddle5", type=float, default=DEFAULT_SHAPING["paddle5"])
    ap.add_argument("--rw_match2", type=float, default=DEFAULT_SHAPING["match_rank2"],
                    help="每轮第2名额外惩罚(浪费大牌)")
    ap.add_argument("--weights_json", type=str, default=None)
    ap.add_argument("--model_path", type=str, default=None)
    a = ap.parse_args()

    shaping = None if a.no_shaping else {
        "chain_others": a.rw_chain,
        "chained": a.rw_chained,
        "gain": a.rw_gain,
        "bankrupt_fear": a.rw_bankrupt_fear,
        "bankrupt": a.rw_bankrupt,
        "paddle4": a.rw_paddle4,
        "paddle5": a.rw_paddle5,
        "match_rank2": a.rw_match2,
    }
    wj = a.weights_json or ("sanguopai_hybrid_weights.json" if a.hybrid else "sanguopai_weights.json")
    mp = a.model_path or ("sanguopai_hybrid_model.pt" if a.hybrid else "sanguopai_model.pt")
    train(
        n_episodes=a.n_episodes,
        lr=a.lr,
        eval_every=a.eval_every,
        entropy_coef=a.entropy_coef,
        risk_lambda=a.risk_lambda,
        hybrid=a.hybrid,
        cc_lambda=a.cc_lambda,
        cc_n_sim_train=a.cc_n_sim_train,
        workers=a.workers,
        serial=a.serial,
        shaping=shaping,
        weights_json=wj,
        model_path=mp,
    )
