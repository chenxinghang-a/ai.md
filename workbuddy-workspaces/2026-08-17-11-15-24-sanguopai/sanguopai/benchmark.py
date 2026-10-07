"""简单基线对比：玩家 0 用最大牌型 heuristic，其余 4 人随机。"""

import random
from collections import Counter

from sanguopai.config import DEFAULT_CONFIG
from sanguopai.env.evaluator import evaluate_five_score
from sanguopai.env.game import SanGuoPaiGame, decode_action, legal_action_ids


def greedy_action(game: SanGuoPaiGame, player_id: int) -> int:
    """枚举所有合法动作，选组成 5 张牌最大的动作。"""
    best_action = None
    best_score = -1
    for aid in legal_action_ids():
        _, cards, _ = game._compose_cards(player_id, aid)
        score = evaluate_five_score(cards)
        if score > best_score:
            best_score = score
            best_action = aid
    return best_action


def run_match(seed: int):
    game = SanGuoPaiGame(config=DEFAULT_CONFIG, seed=seed)
    game.reset()
    while not game.done:
        actions = {}
        for pid in range(DEFAULT_CONFIG.n_players):
            if game.bankrupt[pid]:
                continue  # 破产者已停玩，不再出牌
            if pid == 0:
                actions[pid] = greedy_action(game, pid)
            else:
                actions[pid] = random.choice(legal_action_ids())
        game.step(actions)
    # 按最终豆数排名
    chips = game.chips
    sorted_pids = sorted(range(DEFAULT_CONFIG.n_players), key=lambda p: chips[p], reverse=True)
    rank_of = {pid: i + 1 for i, pid in enumerate(sorted_pids)}
    return rank_of[0], chips[0] - game.initial_chips


def main(n_games: int = 100):
    random.seed(0)
    ranks = Counter()
    total_profit = 0
    for i in range(n_games):
        rank, profit = run_match(seed=i)
        ranks[rank] += 1
        total_profit += profit
    print(f"=== {n_games} 局：Heuristic vs Random ===")
    print(f"名次分布: {dict(sorted(ranks.items()))}")
    print(f"平均每局收益: {total_profit / n_games:,.0f}")
    print(f"总收益: {total_profit:,.0f}")


if __name__ == "__main__":
    main()
