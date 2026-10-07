"""算牌 / 蒙特卡洛 EV 推理策略（可解释，非端到端 RL）。

老板的打牌智慧（原话）：
  - "人家大，你就得打小"  -> 估计对面大概率比我大，就出小牌型(散牌/对子)，少输 = 避险
  - "如果我觉得我大，我就直接上" -> 估计我大概率大，就上最大牌型(用满公共牌凑顺子/同花/葫芦) = 留牌成大牌
  - "通过公共牌，还有上一轮对面出的牌，能猜到对面大概率有什么牌"
  - "公共牌有个对子甚至3张，你这个顺子比较小，这你也敢上？" -> 对手能用公共对子凑葫芦，我小顺子该躲
  - "预测对面的牌有多大概率比我大。直接算期望值。通过几千次对局来拟合" -> 蒙特卡洛采样对手隐藏牌，估计胜率与 EV

实现：已知 我的手牌 + 公共牌 + public_seen(公共牌+历史出牌) -> 推断"对手可能持有的牌"
      -> 对未知对手手牌做 N 次蒙特卡洛采样 -> 对每个候选动作估计「我赢的概率」+「期望净收益 EV」 -> 选 argmax EV。

结算逻辑与 game.py 的 step 保持一致（**不对称**：输家恒 cap=1800万；赢家收款上限按财富档）。
"""

from __future__ import annotations

import random
from itertools import combinations
from typing import Dict, List, Optional, Tuple

from .card import Card
from .evaluator import evaluate_five_score
from .game import (
    ACTION_TABLE,
    FACTION_SHU,
    FACTION_WEI,
    FACTION_WU,
    N_ACTIONS,
    decode_action,
)
from ..config import DEFAULT_CONFIG

# 全局牌池，避免重复 from_code（性能）
_CARD_POOL = [Card.from_code(c) for c in range(52)]


def _cap_eff(E: int, C: int, cap: int, min_win: int) -> int:
    """单份封顶：clamp(max(入场豆, 当前豆), 最小输赢450万, 封顶1800万)。

    · 带 ≥1800万 → 恒定吃满 1800万（看入场豆）· 带 450万~1800万 → 入场/当前谁大用谁
    · 带 <450万 → 恒定 450万（最小输赢）
    """
    return min(max(max(E, C), min_win), cap)


def resolve_settle(
    submissions: List[Tuple[int, int, List[int], int, int]],
    n: int,
    entry_chips: List[int],
    chips: List[int],
    config,
) -> List[int]:
    """结算，与 game.py 的 step 内结算保持一致（**不对称**：输家恒 cap；赢家收款按财富档）。

    submissions: [(score, pid, cards_codes, faction, aid), ...]（已含全部活跃玩家）
    返回 rewards（长度 n，非活跃玩家为 0）。
    """
    rewards = [0] * n
    subs = sorted(submissions, key=lambda x: x[0], reverse=True)
    ranks = [0] * n
    cur = 1
    i = 0
    while i < len(subs):
        j = i
        while j < len(subs) and subs[j][0] == subs[i][0]:
            j += 1
        for k in range(i, j):
            ranks[subs[k][1]] = cur
        cur += j - i
        i = j

    first_pids = [pid for _, pid, _, _, _ in subs if ranks[pid] == 1]
    if not first_pids:
        return rewards

    first_grade = subs[0][0] // (13 ** 5)
    type_mult = config.type_multipliers[first_grade]
    cap = config.cap
    min_win = config.min_win

    # 赢家每份「收款」上限（只有"赢"这一侧按财富档分档）
    cap_eff_w = {w: _cap_eff(entry_chips[w], chips[w], cap, min_win) for w in first_pids}

    for i in range(n):
        if ranks[i] == 0 or ranks[i] == 1:
            continue
        faction_i = next(f for s, p, _, f, _ in subs if p == i)
        C = chips[i]
        E = entry_chips[i]
        total_pay = 0
        remaining = C  # 输家当前豆：实付不超过它（付不满即破产，缺口赢家吃亏）
        for w in first_pids:
            faction_w = next(f for s, p, _, f, _ in subs if p == w)
            if faction_i == faction_w:
                same_faction = sum(1 for _, p, _, f, _ in subs if f == faction_w)
            else:
                same_faction = 1
            grade_w = next(s for s, p, _, _, _ in subs if p == w) // (13 ** 5)
            kill_class_w = config.kill_classes[grade_w]
            same_type = sum(
                1 for s, _, _, _, _ in subs if config.kill_classes[s // (13 ** 5)] == kill_class_w
            )
            L = (
                type_mult
                * config.crit_multipliers[same_faction]
                * config.rank_multipliers[ranks[i]]
                * config.kill_multipliers[same_type]
                * config.base_score
            )
            if getattr(config, "scoring", "chips") == "score":
                # 积分制：±(牌型 × 暴击 × 名次 × 杀牌)，无封顶、无财富档、不受当前分限制
                pay = L // config.base_score
            else:
                # 豆制：输家侧封顶恒为 cap（1800万）；cap_eff_w = 赢家每份收款上限（财富档）
                pay = min(L, cap, cap_eff_w[w], remaining)
            if pay <= 0:
                break
            rewards[w] += pay
            if getattr(config, "scoring", "chips") != "score":
                remaining -= pay
            total_pay += pay
        rewards[i] = -total_pay
    return rewards


class CardCounter:
    """算牌 / 蒙特卡洛 EV 推理策略。"""

    def __init__(self, n_sim: int = 600, rng=None, config=None):
        self.n_sim = n_sim
        self.rng = rng or random.Random()
        self.config = config or DEFAULT_CONFIG

    def _opponent_best(self, hand_codes: List[int], pub_wei: List[int], pub_wu: List[int]):
        """对手手牌(8 codes) + 公共牌 -> 贪心选最优(阵营, 牌型分, 5张codes)。
        对手也会用公共牌凑最大牌型（魏配3公共/吴配2公共/蜀用5手牌），与真实玩法一致。"""
        best_score = -1
        best = None
        # 蜀：从 8 手牌选 5
        for combo in combinations(range(8), 5):
            cards = [hand_codes[i] for i in combo]
            s = evaluate_five_score([_CARD_POOL[c] for c in cards])
            if s > best_score:
                best_score = s
                best = (s, FACTION_SHU, cards)
        # 魏：选 2 手牌 + 3 公共
        for combo in combinations(range(8), 2):
            cards = [hand_codes[i] for i in combo] + list(pub_wei)
            s = evaluate_five_score([_CARD_POOL[c] for c in cards])
            if s > best_score:
                best_score = s
                best = (s, FACTION_WEI, cards)
        # 吴：选 3 手牌 + 2 公共
        for combo in combinations(range(8), 3):
            cards = [hand_codes[i] for i in combo] + list(pub_wu)
            s = evaluate_five_score([_CARD_POOL[c] for c in cards])
            if s > best_score:
                best_score = s
                best = (s, FACTION_WU, cards)
        return best  # (score, faction, cards_codes)

    def analyze(self, obs: dict, opp_alive=None, opp_entries=None, opp_chips=None):
        """分析每个候选动作：(win_prob, ev)。

        opp_alive: bool[4]，默认全活。
        opp_entries/opp_chips: 对手入口豆/当前豆；默认按高豆(cap_eff=cap)保守估计
                              （对手都富 -> 付最多 -> EV 偏保守，避险更明显）。
        返回 (ev[140], win[140], my_cands) 其中 my_cands[a]=(score,faction,cards_codes,aid)
        """
        my_hand = [c for c in obs["hand"] if c < 52]
        pub_wei = list(obs["public_wei"])
        pub_wu = list(obs["public_wu"])
        seen = set(c for c, v in enumerate(obs["public_seen"]) if v == 1)
        # obs["chips"] 在 game.get_obs 里是「全局五人豆数列表」，必须用 player_id 取下标，
        # 否则非 0 号座位会误用 0 号座位的财富来算 cap_eff（影响 EV 与风险判定）。
        chips_val = obs["chips"]
        pid_idx = int(obs.get("player_id", 0))
        if isinstance(chips_val, (list, tuple)):
            my_chips = chips_val[pid_idx] if 0 <= pid_idx < len(chips_val) else chips_val[0]
        else:
            my_chips = chips_val
        # 入口豆（决定 cap_eff 财富档）；无则退化为当前豆
        entry_val = obs.get("entry_chips")
        if entry_val is None:
            my_entry = my_chips
        elif isinstance(entry_val, (list, tuple)):
            my_entry = entry_val[pid_idx] if 0 <= pid_idx < len(entry_val) else entry_val[0]
        else:
            my_entry = entry_val

        # 预计算我的 140 候选（手牌固定，只算一次）
        my_cands = []
        for aid in range(N_ACTIONS):
            faction, hand_idx = decode_action(aid)
            sel = [my_hand[i] for i in hand_idx]
            pub = (
                pub_wei
                if faction == FACTION_WEI
                else (pub_wu if faction == FACTION_WU else [])
            )
            cards = sel + list(pub)
            score = evaluate_five_score([_CARD_POOL[c] for c in cards])
            my_cands.append((score, faction, cards, aid))

        # 剩余牌池（对手隐藏手牌 + 牌库）：52 - 我的手牌 - 当前公共牌。
        # 关键：本局"历史出过的牌"会回库重补（牌循环机制），下一轮仍可能出现在对手手牌里，
        # 因此**不能用 seen 去减**——否则多轮后牌池会小于 4×8=32 而采样失败，且也不符合真实概率空间。
        # 真正可用于"读牌"的信号是「当前公共牌」（对手也拿它凑牌型），已在 my_cands / 对手最优里体现。
        pub_all = set(pub_wei) | set(pub_wu)
        pool = [c for c in range(52) if c not in my_hand and c not in pub_all]
        n_opp = 4 if opp_alive is None else sum(1 for a in opp_alive if a)

        ev = [0.0] * N_ACTIONS
        win = [0] * N_ACTIONS

        for _ in range(self.n_sim):
            self.rng.shuffle(pool)
            opp_hands = [pool[k * 8 : (k + 1) * 8] for k in range(n_opp)]
            opp_subs = []
            for k, hc in enumerate(opp_hands):
                s, fac, cards = self._opponent_best(hc, pub_wei, pub_wu)
                opp_subs.append((s, k + 1, cards, fac, -1))
            # 对手财富（保守：cap_eff=cap，对手都富）
            oentry = [self.config.cap] * 5
            ochips = [self.config.cap] * 5
            oentry[0] = my_entry
            ochips[0] = my_chips
            for a_idx, (score, faction, cards, aid) in enumerate(my_cands):
                subs = [(score, 0, cards, faction, aid)] + opp_subs
                rewards = resolve_settle(subs, 5, oentry, ochips, self.config)
                net = rewards[0]
                ev[a_idx] += net
                if net > 0:  # 我净赚 = 赢（平局 net=0 不计）
                    win[a_idx] += 1

        ev = [e / self.n_sim for e in ev]
        win = [w / self.n_sim for w in win]
        return ev, win, my_cands

    def act(self, obs: dict, opp_alive=None) -> int:
        ev, win, cands = self.analyze(obs, opp_alive)
        return int(max(range(N_ACTIONS), key=lambda a: ev[a]))


def cardcount_policy(n_sim: int = 200):
    """工厂：返回供 economy / gym 使用的策略 callable(obs)->action。

    注意：必须从 obs 里推出**活跃对手**再传下去，否则 act() 会按"4 个对手全活 + 全富"估 EV，
    残局的暴击/杀牌人数与名次都会被算错（EV 系统性偏保守）。
    """
    counter = CardCounter(n_sim=n_sim)

    def _policy(obs):
        chips = obs.get("chips")
        opp_alive = None
        if isinstance(chips, (list, tuple)):
            me = int(obs.get("player_id", 0))
            opp_alive = [i for i in range(len(chips)) if i != me and chips[i] > 0]
        return counter.act(obs, opp_alive=opp_alive)

    return _policy
