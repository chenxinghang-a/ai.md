"""跑一局随机对局，验证核心逻辑与结算。"""

import random

from sanguopai.config import DEFAULT_CONFIG
from sanguopai.env.game import SanGuoPaiGame, legal_action_ids


def main():
    seed = 42
    game = SanGuoPaiGame(config=DEFAULT_CONFIG, seed=seed)
    game.reset()

    print("=== 三国牌仿真环境测试 ===\n")
    print(f"底分: {DEFAULT_CONFIG.base_score}, 封顶: {DEFAULT_CONFIG.cap:,}")
    print(f"动作空间大小: {len(legal_action_ids())}\n")

    total_rewards = [0] * DEFAULT_CONFIG.n_players

    while not game.done:
        print(f"--- 第 {game.round + 1} 轮 ---")
        obs = game.get_obs(0)
        print(f"玩家0手牌: {obs['hand']}")
        print(f"魏公共牌: {obs['public_wei']}, 吴公共牌: {obs['public_wu']}")

        actions = {pid: random.choice(legal_action_ids()) for pid in range(DEFAULT_CONFIG.n_players)}
        rewards, done, info = game.step(actions)

        for entry in info["log"]["submissions"]:
            print(
                f"  玩家{entry['player']} [{entry['faction']}] "
                f"{entry['cards']} -> {entry['grade']} 名次{entry['rank']} 收益{entry['reward']:+}"
            )
        print(f"  本轮收益: {rewards}")
        print(f"  当前豆数: {info['log']['chips']}\n")

        for pid, r in enumerate(rewards):
            total_rewards[pid] += r

    print("=== 4 轮结束 ===")
    print(f"总收益: {total_rewards}")
    print(f"最终豆数: {game.chips}")


if __name__ == "__main__":
    main()
