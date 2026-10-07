"""探针：验证「纯 RL 学到的策略网络」是否随豆数改变出牌策略（无手搓风险层）。

方法：
- 固定一手牌，仅改变自己的豆数，比较网络输出的 top 动作/分布（纯 net_forward）。
- 在大量随机手牌上统计：① 平均 KL(低豆→高豆)；② top1 动作发生切换的手牌占比
  （切换即代表策略真的随豆改变）。
- 若切换占比或 KL 明显 > 0，说明豆子改变策略是 RL 自然涌现的。
"""

from __future__ import annotations

import json
import math

import numpy as np

from sanguopai.env.card import Card
from sanguopai.env.evaluator import evaluate_five_score
from sanguopai.env.game import ACTION_TABLE, FACTION_STARTS, decode_action, N_ACTIONS

WEIGHTS_PATH = "sanguopai_weights.json"


def obs_to_vec(hand, wei, wu, round_, seen, own):
    bean_log = math.log10(own + 1) / 9.0
    bean_norm = min(own / 1.0e8, 2.0)
    return np.array(hand + wei + wu + [round_] + seen + [bean_log, bean_norm], dtype=np.float32)


def relu(x):
    return np.maximum(x, 0.0)


def matvec(W, b, x):
    return W @ x + b


def net_forward(w, vec):
    cards = vec[:14].astype(np.int64)
    seen = vec[14:66].astype(np.float64)
    beans = vec[66:68].astype(np.float64)
    emb = w["card_embed.weight"][cards].reshape(-1)
    x = np.concatenate([emb, seen, beans])
    x = relu(matvec(w["fc.0.weight"], w["fc.0.bias"], x))
    x = relu(matvec(w["fc.2.weight"], w["fc.2.bias"], x))
    return matvec(w["policy_head.weight"], w["policy_head.bias"], x)


def softmax(logits):
    z = logits - logits.max()
    e = np.exp(z)
    return e / e.sum()


def action_desc(aid, hand):
    faction, idx = decode_action(aid)
    names = ["魏", "蜀", "吴"]
    return f"{names[faction]} 手牌{list(idx)}"


def kl(p, q):
    return float(np.sum(p * (np.log(p + 1e-12) - np.log(q + 1e-12))))


def main():
    w = {k: np.array(v) for k, v in json.load(open(WEIGHTS_PATH)).items()}

    # ---- 1) 固定一手牌演示（纯网络）----
    hand = [0, 13, 1, 14, 2, 15, 3, 16]
    wei = [26, 27, 28]
    wu = [39, 40]
    seen = [0] * 52
    for c in hand + wei + wu:
        seen[c] = 1
    print("=== 固定手牌，纯网络，改变豆数观察策略 ===")
    print("手牌:", hand, " 魏公共:", wei, " 吴公共:", wu)
    chips_levels = [160_000, 1_000_000, 10_000_000, 100_000_000]
    prev = None
    for own in chips_levels:
        logits = net_forward(w, obs_to_vec(hand, wei, wu, 0, seen, own))
        p = softmax(logits)
        top = np.argsort(-p)[:5]
        ta = [(int(a), float(p[a])) for a in top]
        ov = ""
        if prev is not None:
            ov = f"  (与前档重叠 {len(set(a for a,_ in ta)&set(a for a,_ in prev))}/5)"
        print(f"\n豆数={own:>12,} (norm={min(own/1e8,2):.3f}){ov}")
        for a, prob in ta:
            print(f"   {action_desc(a, hand):>20} p={prob*100:5.1f}%")
        prev = ta

    # ---- 2) 大量随机手牌统计 bean-awareness ----
    rng = np.random.default_rng(2026)
    N = 3000
    kls, flips = [], 0
    ex = []
    for _ in range(N):
        deck = rng.choice(52, size=8, replace=False).tolist()
        rem = [c for c in range(52) if c not in deck]
        ww = rng.choice(rem, size=3, replace=False).tolist()
        rem2 = [c for c in rem if c not in ww]
        uu = rng.choice(rem2, size=2, replace=False).tolist()
        seen = [0] * 52
        for c in deck + ww + uu:
            seen[c] = 1
        lo = net_forward(w, obs_to_vec(deck, ww, uu, 0, seen, 160_000))
        hi = net_forward(w, obs_to_vec(deck, ww, uu, 0, seen, 100_000_000))
        p0, p1 = softmax(lo), softmax(hi)
        kls.append(kl(p0, p1))
        if np.argmax(p0) != np.argmax(p1):
            flips += 1
            if min(p0.max(), p1.max()) > 0.30:
                ex.append((kl(p0, p1), int(np.argmax(p0)), float(p0.max()),
                           int(np.argmax(p1)), float(p1.max())))
    print("\n=== 纯网络 bean-awareness 统计（%d 随机手牌）===" % N)
    print(f"平均 KL(低→高豆): {np.mean(kls):.4f}   最大 KL: {np.max(kls):.3f}")
    print(f"top1 动作随豆切换占比: {flips/N*100:.1f}%")
    if ex:
        ex.sort(reverse=True)
        print("--- 切换明显示例(低豆→高豆) ---")
        fn = lambda a: action_desc(a, [0] * 8)
        for e in ex[:8]:
            print(f"KL={e[0]:.3f}  低豆:{fn(e[1])} p={e[2]*100:.0f}% → 高豆:{fn(e[3])} p={e[4]*100:.0f}%")
    else:
        print("（本次抽样未出现高置信切换样例）")
    print("结论:", "策略随豆数改变 ✅ (RL 涌现)" if (flips / N > 0.02 or np.mean(kls) > 0.01)
          else "策略随豆改变较弱 ⚠️（可加训或确认）")


if __name__ == "__main__":
    main()
