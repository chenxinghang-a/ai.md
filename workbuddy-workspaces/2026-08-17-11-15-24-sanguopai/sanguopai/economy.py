"""经济模拟：1000 AI × 100 局，统计破产次数与追高豆（峰值豆）。

三种策略对比：
- random：完全随机出牌（基线，最差）
- greedy：每轮选自己牌型分最高的组合（贪心启发式）
- trained：REINFORCE 训练出的策略网络（豆子数进观测 → 低豆激进/高豆保守）

规则机制（来自 game.py）：
- 每局入口扣门票 6w 入系统池（不进玩家）
- 当前局内豆归 0 = 破产停玩（elimination，不参与本局剩余回合）
- 局间若豆 < 门票 → 视为破产，补 16w 续打（破产次数 +1）
- 入口豆决定 cap_eff：高豆玩家单轮最多输 18M；低豆玩家（<4.5M）损失被上限保护

输出：economy_results.json + 打印对比表。
"""

from __future__ import annotations

import argparse
import json
import math
import random
from typing import Callable, Dict, List, Optional

import numpy as np

from sanguopai.config import DEFAULT_CONFIG
from sanguopai.env.card import Card
from sanguopai.env.evaluator import evaluate_five_score
from sanguopai.env.game import (
    FACTION_WEI,
    FACTION_WU,
    N_ACTIONS,
    SanGuoPaiGame,
    decode_action,
    legal_action_ids,
)
from sanguopai.env.card_counter import CardCounter


# ----------------------------- 观测向量化（与 gym_env 一致） -----------------------------
def obs_to_vec(obs: dict) -> np.ndarray:
    own = obs["chips"][obs["player_id"]]
    bean_log = math.log10(own + 1) / 9.0
    bean_norm = min(own / 1.0e8, 2.0)
    vec = (
        obs["hand"]
        + obs["public_wei"]
        + obs["public_wu"]
        + [obs["round"]]
        + obs["public_seen"]
        + [bean_log, bean_norm]
    )
    return np.array(vec, dtype=np.float32)


# ----------------------------- numpy 策略网络（加载 torch 导出权重） -----------------------------
class NetNumpy:
    """与 train_reinforce.PolicyNet 结构一致的纯 numpy 前向（无 torch 依赖，供经济模拟/网页复用）。"""

    def __init__(self, weights: dict):
        # 权重 JSON 为嵌套 list，转 numpy 数组以便 fancy-index
        self.w = {k: np.array(v, dtype=np.float64) for k, v in weights.items()}

    def _relu(self, x):
        return np.maximum(x, 0.0)

    def forward(self, obs: np.ndarray) -> np.ndarray:
        # obs: (68,) float；cards = obs[:14] 取整数 code；seen=obs[14:66]；beans=obs[66:68]
        cards = obs[:14].astype(np.int64)
        seen = obs[14:66].astype(np.float64)
        beans = obs[66:68].astype(np.float64)
        # embedding: 53×8
        emb = self.w["card_embed.weight"][cards].reshape(-1)  # (14*8,)
        x = np.concatenate([emb, seen, beans])  # (166,)
        x = self._relu(self.w["fc.0.weight"] @ x + self.w["fc.0.bias"])
        x = self._relu(self.w["fc.2.weight"] @ x + self.w["fc.2.bias"])
        logits = self.w["policy_head.weight"] @ x + self.w["policy_head.bias"]
        return logits

    def act(self, obs: dict, rng: random.Random, risk_lambda: float = 0.0) -> int:
        vec = obs_to_vec(obs)
        logits = self.forward(vec)
        # 豆数条件风险预算层默认关闭(risk_lambda=0)：策略完全由 RL 学到的网络决定，
        # 豆子改变策略应是从训练奖励中自然涌现的，不手搓。
        if risk_lambda and risk_lambda > 0:
            own = obs["chips"][obs["player_id"]]
            bean_norm = min(own / 1.0e8, 2.0)
            hand = [Card.from_code(c) for c in obs["hand"] if c < 52]
            wei = [Card.from_code(c) for c in obs["public_wei"]]
            wu = [Card.from_code(c) for c in obs["public_wu"]]
            strengths = np.empty(N_ACTIONS, dtype=np.float64)
            for aid in range(N_ACTIONS):
                f, idx = decode_action(aid)
                sel = [hand[i] for i in idx]
                pub = wei if f == FACTION_WEI else (wu if f == FACTION_WU else [])
                strengths[aid] = evaluate_five_score(sel + pub)
            mx = strengths.max()
            risk = 1.0 - (strengths / mx if mx > 0 else 0.0)
            logits = logits - risk_lambda * bean_norm * risk + risk_lambda * 0.4 * (1 - bean_norm) * risk
        logits = logits - logits.max()
        p = np.exp(logits)
        p = p / p.sum()
        return int(rng.choices(range(len(p)), weights=p)[0])


# ----------------------------- 策略函数 -----------------------------
def random_policy(obs: dict, rng: random.Random) -> int:
    return rng.choice(legal_action_ids())


def greedy_policy(obs: dict, rng: random.Random) -> int:
    hand = [Card.from_code(c) for c in obs["hand"] if c < 52]
    public_wei = [Card.from_code(c) for c in obs["public_wei"]]
    public_wu = [Card.from_code(c) for c in obs["public_wu"]]
    best_a, best_s = 0, -1
    for aid in legal_action_ids():
        faction, hand_idx = decode_action(aid)
        sel = [hand[i] for i in hand_idx]
        pub = (
            public_wei
            if faction == FACTION_WEI
            else (public_wu if faction == FACTION_WU else [])
        )
        s = evaluate_five_score(sel + pub)
        if s > best_s:
            best_s, best_a = s, aid
    return best_a


def make_trained_policy(net: NetNumpy) -> Callable:
    def policy(obs: dict, rng: random.Random) -> int:
        return net.act(obs, rng)

    return policy


def make_cardcount_policy(n_sim: int = 25) -> Callable:
    """算牌/EV 推理策略（可解释，非端到端RL）。蒙特卡洛拟合对手牌型分布，选 EV 最大动作。"""
    counter = CardCounter(n_sim=n_sim, rng=random.Random(20260817))

    def policy(obs: dict, rng: random.Random) -> int:
        return counter.act(obs)

    return policy


def make_hybrid_policy(net: NetNumpy, n_sim: int = 25, cc_lambda: float = 2.0,
                       cc_eval_clip: float = 5.0e7) -> Callable:
    """杂交策略：网络 logits + λ·算牌EV（归一化），argmax 选动作。
    网络提供「豆数/手牌」基础判断，算牌提供「对面大概率多大」的读牌先验；
    二者叠加后选动作——既会用牌，又会读牌避险。需用 hybrid 训练出的权重。"""
    from sanguopai.env.card_counter import CardCounter
    counter = CardCounter(n_sim=n_sim, rng=random.Random(20260817))

    def policy(obs: dict, rng: random.Random) -> int:
        vec = obs_to_vec(obs)
        logits = net.forward(vec)
        ev, _win, _cands = counter.analyze(obs)
        ev_norm = np.clip(np.array(ev, dtype=np.float64) / cc_eval_clip, -2.0, 2.0)
        blended = logits + cc_lambda * ev_norm
        return int(np.argmax(blended))

    return policy


# ----------------------------- 经济模拟 -----------------------------
def run_economy(
    policy: Callable,
    n_agents: int = 1000,
    n_games: int = 100,
    seed: int = 12345,
    ticket: int = DEFAULT_CONFIG.ticket,
    rebuy: int = DEFAULT_CONFIG.rebuy,
    initial: int = 100_000_000,
) -> dict:
    rng = random.Random(seed)
    cfg = DEFAULT_CONFIG
    chips = [initial] * n_agents
    peak = [initial] * n_agents  # 追高豆：历史峰值
    bankruptcies = [0] * n_agents  # 破产次数（含局间补豆）
    ever_bankrupt = [False] * n_agents

    n_tables = n_agents // cfg.n_players
    for g in range(n_games):
        # 每局前：补豆/入口处理
        for a in range(n_agents):
            if chips[a] < ticket:
                # 豆不足门票 = 破产，补 16w 续打
                chips[a] = rebuy
                bankruptcies[a] += 1
                ever_bankrupt[a] = True
            peak[a] = max(peak[a], chips[a])

        # 开局：5 人一桌
        for t in range(n_tables):
            seats = [t * cfg.n_players + k for k in range(cfg.n_players)]
            start = [chips[s] for s in seats]
            game = SanGuoPaiGame(config=cfg, seed=rng.randint(0, 1 << 30), initial_chips=initial)
            game.reset(starting_chips=start)
            while not game.done:
                actions = {}
                for pid in range(cfg.n_players):
                    if not game.bankrupt[pid]:
                        obs = game.get_obs(pid)
                        actions[pid] = policy(obs, rng)
                game.step(actions)
                # 更新峰值（每轮后）
                for pid in range(cfg.n_players):
                    seat = seats[pid]
                    peak[seat] = max(peak[seat], game.chips[pid])
        # 进度可见（python -u 下实时刷新）
        print(f"  game {g + 1}/{n_games} 完成", flush=True)
        # 局末结算到各 agent
        for pid in range(cfg.n_players):
            seat = seats[pid]
            chips[seat] = game.chips[pid]
            peak[seat] = max(peak[seat], game.chips[pid])
            if game.chips[pid] <= 0:
                    ever_bankrupt[seat] = True

    chips_arr = np.array(chips, dtype=np.float64)
    peak_arr = np.array(peak, dtype=np.float64)
    bank_arr = np.array(bankruptcies, dtype=np.int64)

    alive = (chips_arr >= ticket).sum()
    return {
        "n_agents": n_agents,
        "n_games": n_games,
        "initial": initial,
        "ticket": ticket,
        "rebuy": rebuy,
        "total_bankruptcies": int(bank_arr.sum()),
        "avg_bankruptcies": float(bank_arr.mean()),
        "max_bankruptcies": int(bank_arr.max()),
        "pct_never_bankrupt": float((bank_arr == 0).mean() * 100),
        "alive_at_end": int(alive),
        "pct_alive_at_end": float(alive / n_agents * 100),
        "avg_peak": float(peak_arr.mean()),
        "median_peak": float(np.median(peak_arr)),
        "max_peak": float(peak_arr.max()),
        "avg_end_chips": float(chips_arr.mean()),
        "median_end_chips": float(np.median(chips_arr)),
        "max_end_chips": float(chips_arr.max()),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agents", type=int, default=1000)
    ap.add_argument("--games", type=int, default=100)
    ap.add_argument("--seed", type=int, default=12345)
    ap.add_argument(
        "--policies",
        nargs="+",
        default=["random", "greedy", "trained", "cardcount"],
        choices=["random", "greedy", "trained", "cardcount", "hybrid"],
    )
    ap.add_argument("--weights", default="sanguopai_weights.json")
    ap.add_argument("--weights_hybrid", default="sanguopai_hybrid_weights.json")
    args = ap.parse_args()

    results: Dict[str, dict] = {}
    for name in args.policies:
        if name == "random":
            pol = random_policy
        elif name == "greedy":
            pol = greedy_policy
        elif name == "cardcount":
            pol = make_cardcount_policy(n_sim=25)
        elif name == "hybrid":
            import os

            hw = args.weights_hybrid if getattr(args, "weights_hybrid", None) else "sanguopai_hybrid_weights.json"
            if not os.path.exists(hw):
                print(f"[skip] hybrid 需要权重 {hw} 不存在，跳过")
                continue
            with open(hw, "r", encoding="utf-8") as f:
                w = json.load(f)
            pol = make_hybrid_policy(NetNumpy(w), n_sim=25, cc_lambda=2.0)
        else:  # trained
            import os

            if not os.path.exists(args.weights):
                print(f"[skip] trained 权重 {args.weights} 不存在，跳过")
                continue
            with open(args.weights, "r", encoding="utf-8") as f:
                w = json.load(f)
            pol = make_trained_policy(NetNumpy(w))
        print(f"=== 运行策略: {name} ({args.agents} agents × {args.games} games) ===")
        r = run_economy(pol, n_agents=args.agents, n_games=args.games, seed=args.seed)
        results[name] = r
        print(
            f"  总破产次数={r['total_bankruptcies']}  人均破产={r['avg_bankruptcies']:.3f}  "
            f"从未破产={r['pct_never_bankrupt']:.1f}%  末局存活={r['pct_alive_at_end']:.1f}%"
        )
        print(
            f"  峰值豆: 均值={r['avg_peak']/1e8:.3f}亿  中位={r['median_peak']/1e8:.3f}亿  "
            f"最高={r['max_peak']/1e8:.3f}亿"
        )
        print(
            f"  末豆: 均值={r['avg_end_chips']/1e8:.3f}亿  中位={r['median_end_chips']/1e8:.3f}亿  "
            f"最高={r['max_end_chips']/1e8:.3f}亿"
        )

    with open("economy_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print("\n结果已写入 economy_results.json")

    # 对比小结
    if "trained" in results and "random" in results:
        tr, ra = results["trained"], results["random"]
        print(
            f"\n[trained vs random] 破产次数 {tr['total_bankruptcies']} vs {ra['total_bankruptcies']} "
            f"(减少 {(1-tr['total_bankruptcies']/max(1,ra['total_bankruptcies']))*100:.1f}%)"
        )
        print(
            f"[trained vs random] 最高峰豆 {tr['max_peak']/1e8:.2f}亿 vs {ra['max_peak']/1e8:.2f}亿"
        )


if __name__ == "__main__":
    main()
