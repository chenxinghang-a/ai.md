"""三国牌核心游戏逻辑：发牌、牌循环、动作解析、结算、状态管理。

关键机制（来自官方规则修正）：
- 4 轮共用一副 52 张牌，**不每轮重置**。
- 每轮玩家出 k 张手牌（魏2/吴3/蜀5）+ 用到的公共牌，结算后这些牌返回公共库并洗混，
  再从库里补到满（手牌补到 8，公共牌补到固定张数）。
- 封顶 = 单人单轮最多输（config.cap）；第一名单轮可赢至多 4×cap。
- 结算后所有人可见彼此提交的牌组（信息进入 observation）。
"""

from __future__ import annotations

import random
from itertools import combinations
from typing import Dict, List, Optional, Tuple

from ..config import SanGuoPaiConfig
from .card import Card, cards_to_string, full_deck, shuffle_deck
from .evaluator import evaluate_five_score, grade_name

# 阵营顺序：魏=0, 蜀=1, 吴=2
FACTION_WEI = 0
FACTION_SHU = 1
FACTION_WU = 2
FACTION_NAMES = ["魏", "蜀", "吴"]


def _build_action_table() -> Tuple[List[Tuple[int, Tuple[int, ...]]], List[int]]:
    """返回 (action_id -> (faction, hand_indices)) 表，以及每个 faction 的起始 id。"""
    table: List[Tuple[int, Tuple[int, ...]]] = []
    faction_starts = [0, 0, 0]

    faction_starts[FACTION_WEI] = 0
    for combo in combinations(range(8), 2):
        table.append((FACTION_WEI, combo))

    faction_starts[FACTION_SHU] = len(table)
    for combo in combinations(range(8), 5):
        table.append((FACTION_SHU, combo))

    faction_starts[FACTION_WU] = len(table)
    for combo in combinations(range(8), 3):
        table.append((FACTION_WU, combo))

    return table, faction_starts


ACTION_TABLE, FACTION_STARTS = _build_action_table()
N_ACTIONS = len(ACTION_TABLE)


def decode_action(action_id: int) -> Tuple[int, Tuple[int, ...]]:
    return ACTION_TABLE[action_id]


def legal_action_ids() -> List[int]:
    return list(range(N_ACTIONS))


class SanGuoPaiGame:
    def __init__(
        self,
        config: Optional[SanGuoPaiConfig] = None,
        seed: Optional[int] = None,
        initial_chips: int = 100_000_000,  # 默认 1 亿豆
    ):
        self.config = config or SanGuoPaiConfig()
        self.config.validate()
        self.rng = random.Random(seed)
        self.default_entry = initial_chips  # 默认入口豆（首局）
        self.entry_chips: List[int] = [initial_chips] * self.config.n_players  # 每局各玩家入口豆（决定 cap_eff）

        self.round: int = 0
        self.done: bool = False
        self.hands: List[List[Card]] = []
        self.public: List[List[Card]] = [[], [], []]  # 魏蜀吴
        self.deck_pool: List[Card] = []  # 公共库
        self.chips: List[int] = [initial_chips] * self.config.n_players
        self.last_rewards: List[int] = [0] * self.config.n_players
        self.history_log: List[dict] = []
        self.bankrupt: List[bool] = [False] * self.config.n_players
        self.public_seen: set = set()  # 历史公开出现过的牌 code

    def reset(self, starting_chips: Optional[List[int]] = None) -> None:
        """开始新一局（4 轮，牌循环）。

        starting_chips: 每玩家本局入口豆；为 None 时用默认入口豆。
        入口即扣门票(ticket)入系统池（不进玩家）；入口豆决定 cap_eff（最小输赢/封顶）。
        当前局内破产者不参与本局剩余回合（elimination），补豆续打在局间经济模拟处理。
        """
        self.round = 0
        self.done = False
        if starting_chips is None:
            starting_chips = [self.default_entry] * self.config.n_players
        self.entry_chips = list(starting_chips)
        # 扣门票（系统池，不进玩家）
        self.chips = [max(0, c - self.config.ticket) for c in self.entry_chips]
        self.last_rewards = [0] * self.config.n_players
        self.history_log.clear()
        self.bankrupt = [False] * self.config.n_players
        self.public_seen = set()

        deck = shuffle_deck(self.rng)
        n = self.config.n_players
        self.hands = [deck[i * 8 : (i + 1) * 8] for i in range(n)]
        offset = n * 8
        self.public[FACTION_WEI] = deck[offset : offset + self.config.public_cards[FACTION_WEI]]
        self.public[FACTION_WU] = deck[
            offset
            + self.config.public_cards[FACTION_WEI] : offset
            + self.config.public_cards[FACTION_WEI]
            + self.config.public_cards[FACTION_WU]
        ]
        self.public[FACTION_SHU] = []
        self.deck_pool = deck[offset + 5 :]  # 剩余 7 张进库

        for c in self.public[FACTION_WEI] + self.public[FACTION_WU]:
            self.public_seen.add(c.code)

    def get_legal_actions(self, player_id: int) -> List[int]:
        return legal_action_ids()

    def _compose_cards(self, player_id: int, action_id: int) -> Tuple[int, List[Card], Tuple[int, ...]]:
        """返回 (faction, 5 张提交牌组, 用掉的手牌索引)。"""
        faction, hand_idx = decode_action(action_id)
        hand = self.hands[player_id]
        selected = [hand[i] for i in hand_idx]
        cards = selected + self.public[faction]
        assert len(cards) == 5
        return faction, cards, hand_idx

    def step(self, actions: Dict[int, int]) -> Tuple[List[int], bool, dict]:
        """
        执行一轮。
        actions: {player_id: action_id}（破产玩家不出现也行，出现则忽略）
        返回: rewards(5人), done, info
        """
        assert not self.done
        n = self.config.n_players

        # 0. 活跃玩家 = 未破产者。破产者已「停玩」，其提交忽略。
        active = [pid for pid in range(n) if not self.bankrupt[pid]]
        if len(active) <= 1:
            # 只剩 1 人（或更少）时本局实质已分胜负
            self.done = True
            return [0] * n, self.done, {"log": None}

        # 1. 解析所有活跃玩家提交（基于当前公共牌）
        submissions: List[Tuple[int, int, List[Card], int, int]] = []
        hand_used: Dict[int, List[int]] = {}   # pid -> 本轮从「手牌」里花掉的那几张(code)
        for pid in active:
            aid = actions.get(pid)
            if aid is None:
                aid = 0  # 兜底：缺动作时取默认合法动作
            faction, cards, hand_idx = self._compose_cards(pid, aid)
            score = evaluate_five_score(cards)
            submissions.append((score, pid, cards, faction, aid))
            # 手牌花销要在这里抓（step 5 会把手牌 pop 掉），且**不含公共牌**：
            # 公共牌是公用的、不体现他的信息；只有"他花掉哪几张手牌"才能推出他的留牌。
            hand_used[pid] = [self.hands[pid][i].code for i in hand_idx]

        submissions.sort(key=lambda x: x[0], reverse=True)

        # 2. 名次（仅活跃玩家参与；同分并列，多第一顺延）
        ranks = [0] * n
        cur = 1
        i = 0
        while i < len(submissions):
            j = i
            while j < len(submissions) and submissions[j][0] == submissions[i][0]:
                j += 1
            for k in range(i, j):
                ranks[submissions[k][1]] = cur
            cur += j - i
            i = j

        first_pids = [pid for _, pid, _, _, _ in submissions if ranks[pid] == 1]
        first_grade = submissions[0][0] // (13 ** 5)
        type_mult = self.config.type_multipliers[first_grade]
        ref_faction = submissions[0][3]

        # 赢家侧 cap_eff：与输家对称——赢家每收到一份，也按自己财富档封顶。
        # 否则低豆赢家会与高豆赢家从同样输家手里收到一模一样的钱（"当前豆没刷新到赢家侧"的 bug）。
        def _win_cap(E: int, C: int) -> int:
            """**赢家每份收款上限**（只有"赢"这一侧才按财富档分档）：
               clamp( max(入场豆, 当前豆), 450万, 1800万 )
               · 带 ≥1800万 → 每份收满 1800万（看**入场**豆：中途掉到900万也照收1800万）
               · 带 450万~1800万 → 入场/当前谁大用谁（带900万后涨到1800万 → 按1800万收）
               · 带 <450万 → 每份只收 450万
            """
            return min(max(max(E, C), min_win), cap)

        # 3 & 4. 结算：输家对每个第一名各付一份；单份上限按「入口豆 vs 当前豆」判定
        rewards = [0] * n
        cap = self.config.cap
        min_win = self.config.min_win

        # 赢家侧每份收款上限（财富档）。注意：**输家侧没有财富档封顶**，恒为 cap=1800万（"管你有多少"）。
        cap_eff_w = {w: _win_cap(self.entry_chips[w], self.chips[w]) for w in first_pids}

        for i in active:
            if ranks[i] == 1:
                continue
            faction_i = next(f for s, p, _, f, _ in submissions if p == i)
            C = self.chips[i]
            E = self.entry_chips[i]  # 该玩家本局入场豆（只用于对自己"收款"侧的分档）
            total_pay = 0
            remaining = C  # 输家当前豆：实付不超过它（付不出即破产，缺口赢家吃亏）
            for w in first_pids:
                faction_w = next(f for s, p, _, f, _ in submissions if p == w)
                if faction_i == faction_w:
                    same_faction = sum(1 for _, p, _, f, _ in submissions if f == faction_w)
                else:
                    same_faction = 1
                # 杀牌倍率 = 赢家(第1名)牌型类的拥挤度（含赢家自身）：
                # 小牌类(单张/对子/两对/三张=class 0)众人易撞型→连锁高。
                # 例：赢家打三条且4名对手全打小牌(2对/1对/散牌)→同型5人→γ=16。
                grade_w = next(s for s, p, _, _, _ in submissions if p == w) // (13 ** 5)
                kill_class_w = self.config.kill_classes[grade_w]
                same_type = sum(
                    1 for s, _, _, _, _ in submissions if self.config.kill_classes[s // (13 ** 5)] == kill_class_w
                )
                crit_mult = self.config.crit_multipliers[same_faction]
                kill_mult = self.config.kill_multipliers[same_type]
                rank_mult = self.config.rank_multipliers[ranks[i]]
                # 所有第一名同 grade，type_mult 相同
                L = type_mult * crit_mult * rank_mult * kill_mult * self.config.base_score
                # 输家单份支付 = min(L, 1800万, 赢家每份收款上限, 输家当前豆)
                #  · 输家侧封顶恒为 cap=1800万（"管你有多少"，不按财富档打折）
                #  · 实付受当前豆限制：付不满即破产，缺口由赢家自担（"赢家吃亏"）
                #  · L 小时按 L 实付（低倍率不会被拉高）
                if self.config.scoring == "score":
                    # ★ 积分制：直接 ±(牌型 × 暴击 × 名次 × 杀牌)。
                    #   无封顶、无财富档、不受当前分限制 —— 打得好/坏直接体现在分数上。
                    pay = L // self.config.base_score
                else:
                    pay = min(L, cap, cap_eff_w[w], remaining)
                if pay <= 0:
                    break  # 豆已归 0（或积分为 0），停止对其他第一名支付
                rewards[w] += pay
                if self.config.scoring != "score":
                    remaining -= pay
                total_pay += pay
            rewards[i] = -total_pay
            # 豆归 0 即破产停；**积分制不破产**（分数可以为负，继续打）
            if self.config.scoring != "score" and self.chips[i] + rewards[i] <= 0:
                self.bankrupt[i] = True

        # 5. 牌循环：活跃玩家用掉的牌回库，再补齐
        used: List[Card] = []
        used_factions = set()
        for score, pid, cards, faction, action_id in submissions:
            _, hand_idx = decode_action(action_id)
            for k in sorted(hand_idx, reverse=True):
                used.append(self.hands[pid].pop(k))
            if faction not in used_factions:
                used.extend(self.public[faction])
                used_factions.add(faction)
                self.public[faction] = []

        self.deck_pool.extend(used)
        self.rng.shuffle(self.deck_pool)

        # 补齐未破产活跃玩家手牌到 8（本轮回首破产者不再补牌）
        for pid in active:
            if self.bankrupt[pid]:
                continue
            while len(self.hands[pid]) < self.config.hand_size and self.deck_pool:
                self.hands[pid].append(self.deck_pool.pop())
        # 补齐被使用阵营公共牌到固定张数
        for faction in used_factions:
            while len(self.public[faction]) < self.config.public_cards[faction] and self.deck_pool:
                self.public[faction].append(self.deck_pool.pop())

        # 破产玩家：未打出的手牌回归公共牌库（已停玩，不再持牌）
        for pid in range(n):
            if self.bankrupt[pid] and len(self.hands[pid]) > 0:
                self.deck_pool.extend(self.hands[pid])
                self.hands[pid] = []
        self.rng.shuffle(self.deck_pool)

        # 更新公开可见牌集（本轮活跃玩家出的牌）
        for _, _, cards, _, _ in submissions:
            for c in cards:
                self.public_seen.add(c.code)

        # 6. 更新筹码与日志（仅活跃玩家）
        for pid in active:
            self.chips[pid] += rewards[pid]
            self.last_rewards[pid] = rewards[pid]

        log_entry = {
            "round": self.round,
            "submissions": [
                {
                    "player": pid,
                    "faction": FACTION_NAMES[faction],
                    "faction_id": faction,               # 0魏/1蜀/2吴（AI 读牌用）
                    "cards": cards_to_string(cards),
                    "cards_codes": [c.code for c in cards],
                    "hand_codes": hand_used.get(pid, []),   # 本轮花掉的手牌（不含公共牌）→ 读"留牌"用
                    "score": score,
                    "rank": ranks[pid],
                    "reward": rewards[pid],
                    "grade": grade_name(score // (13 ** 5)),
                    "grade_id": score // (13 ** 5),      # 0..8（AI 读牌用）
                    "bankrupt": self.bankrupt[pid],
                }
                for score, pid, cards, faction, _ in submissions
            ],
            "chips": self.chips.copy(),
            "bankrupt": self.bankrupt.copy(),
        }
        self.history_log.append(log_entry)

        self.round += 1
        if self.round >= self.config.n_rounds:
            self.done = True

        return rewards, self.done, {"log": log_entry}

    def _seen_vector(self) -> List[int]:
        v = [0] * 52
        for code in self.public_seen:
            v[code] = 1
        return v

    def get_obs(self, player_id: int) -> dict:
        hand = [c.code for c in self.hands[player_id]]
        # 破产/空槽用哨兵 52 补齐到固定手牌数（合法牌 code 仅 0..51）
        hand = hand + [52] * (self.config.hand_size - len(hand))
        return {
            "player_id": player_id,
            "round": self.round,
            "hand": hand,
            "public_wei": [c.code for c in self.public[FACTION_WEI]],
            "public_wu": [c.code for c in self.public[FACTION_WU]],
            "public_seen": self._seen_vector(),
            "chips": self.chips.copy(),
            "entry_chips": self.entry_chips.copy(),   # 入场豆：结算"赢家收款上限"的财富档要用
            "bankrupt": self.bankrupt[player_id],
        }

    def get_state(self) -> dict:
        return {
            "round": self.round,
            "hands": [[c.code for c in h] for h in self.hands],
            "public": [[c.code for c in p] for p in self.public],
            "deck_pool": [c.code for c in self.deck_pool],
            "public_seen": self._seen_vector(),
            "chips": self.chips.copy(),
        }
