"""统一对战评估：0 号座位用被评测策略，其余 4 家固定贪心。输出 0 号平均净豆。

对比基准：
  greedy   —— 无脑选最大牌型（老板说的「自动选最大」）
  rl_reinforce —— 老 REINFORCE 纯网络(sanguopai_weights.json)
  dmc      —— 新 Deep Monte-Carlo 权重(sanguopai_dmc_weights.json)

用法：
  python sanguopai/eval_headtohead.py --policy greedy --n 120
  python sanguopai/eval_headtohead.py --policy dmc --weights sanguopai_dmc_weights.json --n 120
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sanguopai.config import DEFAULT_CONFIG as CFG  # noqa: E402
from sanguopai.env.game import SanGuoPaiGame, N_ACTIONS  # noqa: E402
from sanguopai.env.gym_env import GreedyHeuristic  # noqa: E402

START = 100_000_000
GREEDY = GreedyHeuristic()


def make_policy(kind, weights_path):
    if kind == "greedy":
        return lambda obs, game, pid: GREEDY.act(obs)
    if kind == "rl_reinforce":
        from sanguopai.train_reinforce import PolicyNet, obs_to_tensor
        net = PolicyNet()
        with open(weights_path, "r", encoding="utf-8") as f:
            sd = json.load(f)
        net.load_state_dict({k: torch.tensor(np.array(v), dtype=torch.float32) for k, v in sd.items()})
        net.eval()

        def pol(obs, game, pid):
            # train_reinforce.env 的 68 维观测
            own = obs["chips"][pid]
            vec = (list(obs["hand"]) + list(obs["public_wei"]) + list(obs["public_wu"])
                   + [obs["round"]] + list(obs["public_seen"])
                   + [math.log10(own + 1) / 9.0, min(own / 1e8, 2.0)])
            with torch.no_grad():
                logits, _ = net(obs_to_tensor(np.array(vec, dtype=np.float32)))
            return int(torch.argmax(logits, dim=-1).item())
        return pol
    if kind == "dmc":
        from sanguopai.train_dmc import QNet, build_action_feats, build_state_feats, lists_to_model
        with open(weights_path, "r", encoding="utf-8") as f:
            wd = json.load(f)
        net = lists_to_model(wd)
        net.eval()

        def pol(obs, game, pid):
            af, grades, scores, _ = build_action_feats(
                [c.code for c in game.hands[pid]], [c.code for c in game.public[0]],
                [c.code for c in game.public[2]])
            sv = build_state_feats(game, pid, af, grades, scores)
            x = np.concatenate([np.repeat(sv[None, :], N_ACTIONS, axis=0), af], axis=1)
            with torch.no_grad():
                q = net(torch.from_numpy(x).to(torch.device("cpu"))).numpy()
            return int(np.argmax(q))
        return pol
    raise ValueError(kind)


def run(policy, n, seed0=1000):
    tot = 0
    ranks = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    bust = 0
    for k in range(n):
        g = SanGuoPaiGame(config=CFG, seed=seed0 + k, initial_chips=START)
        g.reset([START] * CFG.n_players)
        last = None
        while not g.done:
            acts = {}
            for pid in range(CFG.n_players):
                if g.bankrupt[pid]:
                    continue
                obs = g.get_obs(pid)
                acts[pid] = policy(obs, g, pid) if pid == 0 else GREEDY.act(obs)
            _r, _d, info = g.step(acts)
            if info.get("log"):
                last = info["log"]
        tot += g.chips[0] - START
        if g.bankrupt[0]:
            bust += 1
        # 用整局总豆排名（终局名次）
        order = sorted(range(CFG.n_players), key=lambda p: g.chips[p], reverse=True)
        ranks[order.index(0) + 1] += 1
    return tot / n, ranks, bust


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", default="greedy", choices=["greedy", "rl_reinforce", "dmc"])
    ap.add_argument("--weights", default=None)
    ap.add_argument("--n", type=int, default=120)
    ap.add_argument("--seed0", type=int, default=1000)
    a = ap.parse_args()
    w = a.weights
    if w is None:
        w = {"rl_reinforce": "sanguopai/sanguopai_weights.json",
             "dmc": "sanguopai_dmc_weights.json"}.get(a.policy)
    pol = make_policy(a.policy, w)
    avg, ranks, bust = run(pol, a.n, a.seed0)
    print(f"[{a.policy:12s}] n={a.n}  0号平均净豆 = {avg:,.0f}  ({avg/1e4:.0f}万)  "
          f"破产={bust}  终局名次分布={ranks}")


if __name__ == "__main__":
    main()
