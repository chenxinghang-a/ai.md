"""测试 Gymnasium 环境接口。"""

import gymnasium as gym
import numpy as np

from sanguopai.env.gym_env import SanGuoPaiEnv


def main():
    env = SanGuoPaiEnv(seed=42)
    obs, info = env.reset(seed=42)
    print(f"obs shape: {obs.shape}, dtype: {obs.dtype}")
    print(f"action space: {env.action_space}")
    print(f"obs space: {env.observation_space}")

    total_reward = 0
    step = 0
    while True:
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        step += 1
        if terminated or truncated:
            break

    print(f"Total steps: {step}, total reward: {total_reward}")
    print(f"Final chips: {env.game.chips}")


if __name__ == "__main__":
    main()
