"""Gymnasium 风格单 agent 环境：玩家 0 由外部 RL 控制，其余 4 人用对手策略。"""

from __future__ import annotations

import math
import random
from typing import Dict, Optional

import gymnasium as gym
import numpy as np

from ..config import DEFAULT_CONFIG, SanGuoPaiConfig
from .card import Card
from .evaluator import evaluate_five_score
from .game import (
    FACTION_STARTS,
    FACTION_WEI,
    FACTION_WU,
    N_ACTIONS,
    SanGuoPaiGame,
    decode_action,
    legal_action_ids,
)


class RandomOpponent:
    """随机对手：每轮从合法动作中均匀随机选择。"""

    def __init__(self, rng=None):
        self.rng = rng

    def act(self, observation: dict) -> int:
        return np.random.choice(legal_action_ids())


class GreedyHeuristic:
    """贪心对手：选使自己 5 张组合牌型分最高的动作（epsilon 注入随机性增加多样性）。"""

    def __init__(self, epsilon: float = 0.0, rng=None):
        self.epsilon = epsilon
        self.rng = rng or random.Random()

    def act(self, observation: dict) -> int:
        if self.epsilon > 0 and self.rng.random() < self.epsilon:
            return self.rng.choice(legal_action_ids())
        hand = [Card.from_code(c) for c in observation["hand"] if c < 52]
        public_wei = [Card.from_code(c) for c in observation["public_wei"]]
        public_wu = [Card.from_code(c) for c in observation["public_wu"]]
        best_a, best_s = 0, -1
        for aid in legal_action_ids():
            faction, hand_idx = decode_action(aid)
            sel = [hand[i] for i in hand_idx]
            pub = (
                public_wei
                if faction == FACTION_WEI
                else (public_wu if faction == FACTION_WU else [])
            )
            cards = sel + pub
            s = evaluate_five_score(cards)
            if s > best_s:
                best_s, best_a = s, aid
        return best_a


class SanGuoPaiEnv(gym.Env):
    """
    单 agent 环境。
    观察（68 维）：
      自己手牌(8) + 魏公共牌(3) + 吴公共牌(2) + 轮次(1) [牌槽 code 0..52] +
      历史公开牌 one-hot(52) + 自己豆数(2)：[log10(own+1)/9, own/1e8]
    豆数进观测是「豆子改变出牌策略」的关键——低豆保守、高豆激进。
    动作：整数 0..139，对应 (阵营, 手牌组合)。
    """

    metadata = {"render_modes": ["human"]}

    def __init__(
        self,
        config: Optional[SanGuoPaiConfig] = None,
        opponent: Optional[RandomOpponent] = None,
        seed: Optional[int] = None,
        initial_chips: int = 100_000_000,
    ):
        super().__init__()
        self.config = config or DEFAULT_CONFIG
        self.opponent = opponent or RandomOpponent()
        self.initial_chips = initial_chips

        self.game = SanGuoPaiGame(config=self.config, seed=seed, initial_chips=initial_chips)
        self.agent_id = 0

        # 动作空间：140 个离散动作
        self.action_space = gym.spaces.Discrete(N_ACTIONS)

        # 观察空间：68 维（14 牌槽 code 0..52 + 52 seen 0/1 + 2 豆数特征 ~0..2）
        self.observation_space = gym.spaces.Box(
            low=0.0, high=53.0, shape=(68,), dtype=np.float32
        )

    def _obs_to_vector(self, obs: dict) -> np.ndarray:
        own = obs["chips"][self.agent_id]
        # 豆数特征：对数尺度 + 线性归一，使策略能感知财富水平（低豆/高豆）
        bean_log = math.log10(own + 1) / 9.0  # 1e9 -> 1.0
        bean_norm = min(own / 1.0e8, 2.0)  # 1亿 -> 1.0，封顶 2.0
        vec = (
            obs["hand"]
            + obs["public_wei"]
            + obs["public_wu"]
            + [obs["round"]]
            + obs["public_seen"]
            + [bean_log, bean_norm]
        )
        return np.array(vec, dtype=np.float32)

    def reset(self, seed: Optional[int] = None, options: Optional[dict] = None, starting_chips: Optional[int] = None):
        super().reset(seed=seed)
        if seed is not None:
            self.game.rng.seed(seed)
        if starting_chips is not None:
            # 训练时随机财富水平：本局所有玩家同一起始豆，让策略学会按豆数调整
            self.game.reset(starting_chips=[starting_chips] * self.config.n_players)
        else:
            self.game.reset()
        obs = self.game.get_obs(self.agent_id)
        return self._obs_to_vector(obs), {"raw_obs": obs}

    def step(self, action: int):
        assert self.action_space.contains(action)

        # 自己已破产则本局直接终止（豆归0即停玩）
        if self.game.bankrupt[self.agent_id]:
            obs = self.game.get_obs(self.agent_id)
            return self._obs_to_vector(obs), 0, True, False, {"raw_obs": obs}

        actions: Dict[int, int] = {self.agent_id: action}
        for pid in range(1, self.config.n_players):
            if not self.game.bankrupt[pid]:
                actions[pid] = self.opponent.act(self.game.get_obs(pid))

        rewards, done, info = self.game.step(actions)
        obs = self.game.get_obs(self.agent_id)
        reward = rewards[self.agent_id]

        terminated = done or self.game.bankrupt[self.agent_id]
        truncated = False
        return self._obs_to_vector(obs), reward, terminated, truncated, {**info, "raw_obs": obs}

    def render(self):
        if len(self.game.history_log) == 0:
            return
        last = self.game.history_log[-1]
        print(f"Round {last['round'] + 1} chips: {last['chips']}")


class SanGuoPaiParallelEnv:
    """
    同时管理 5 个 agent 的 self-play 接口（非标准 Gym，但便于 centralized self-play）。
    step 接收 actions dict，返回 observations dict / rewards dict。
    """

    def __init__(
        self,
        config: Optional[SanGuoPaiConfig] = None,
        seed: Optional[int] = None,
        initial_chips: int = 100_000_000,
    ):
        self.config = config or DEFAULT_CONFIG
        self.game = SanGuoPaiGame(config=self.config, seed=seed, initial_chips=initial_chips)

    def reset(self):
        self.game.reset()
        return {pid: self.game.get_obs(pid) for pid in range(self.config.n_players)}

    def step(self, actions: Dict[int, int]):
        rewards, done, info = self.game.step(actions)
        obs = {pid: self.game.get_obs(pid) for pid in range(self.config.n_players)}
        return obs, rewards, done, info
