"""冒烟测试：新奖励塑形（每轮名次，非 4 轮总豆）。"""
import sys
sys.path.insert(0, ".")
import sanguopai.train_reinforce as T

SH = T.DEFAULT_SHAPING

# 构造一回合 log_entry：5 人，agent=0 当第2名（被电，净豆为负）
def make_log(agent_rank, agent_net, bankrupt=False, score=2 * (13 ** 5)):
    subs = []
    # 给 5 个人分配名次与净豆：第1名赢(+)、其余输(-)
    nets = {1: 8000000, 2: -6000000, 3: -8000000, 4: -9000000, 5: -10000000}
    ranks = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5}
    for p in range(5):
        subs.append({
            "player": p,
            "score": score if p == 0 else 0,
            "rank": agent_rank if p == 0 else ranks[p],
            "reward": agent_net if p == 0 else nets[p],
            "bankrupt": bankrupt if p == 0 else False,
        })
    return {"submissions": subs, "chips": [0] * 5}


# 1) 第1名应得 chain_others 奖励
r1 = T.apply_shaping(8_000_000, make_log(1, 8_000_000), 0, 0, None, SH)
assert r1 == SH["chain_others"] + 1.0 * 8_000_000, f"第1名奖励错: {r1}"
print(f"[ok] 第1名: {r1} = chain_others({SH['chain_others']}) + 净豆(8M)")

# 2) 第2名(被电,净豆负) 应得：被链− + 第2额外惩罚 + 豆子减−(放大×1)
r2 = T.apply_shaping(-6_000_000, make_log(2, -6_000_000), 0, 0, None, SH)
expected = -SH["chained"] - SH["match_rank2"] + 1.0 * (-6_000_000)
assert r2 == expected, f"第2名奖励错: {r2} != {expected}"
print(f"[ok] 第2名(被电): {r2} = -chained({SH['chained']}) -match_rank2({SH['match_rank2']}) + 净豆(-6M)")

# 3) 第4名落败且出小牌型 → 划水+（paddle4）
r4 = T.apply_shaping(-9_000_000, make_log(4, -9_000_000, score=0), 0, 0, None, SH)
assert r4 > -20_000_000, f"第4名划水项没生效: {r4}"
print(f"[ok] 第4名(落败小牌): {r4} 含划水+{SH['paddle4']}")

# 4) 确认已无整局总豆终局函数（之前错的 ±15M）
assert not hasattr(T, "apply_match_terminal"), "apply_match_terminal 应已删除"
assert not hasattr(T, "_final_match_rank"), "_final_match_rank 应已删除"
print("[ok] 整局总豆终局函数已删除（不再有 ±15M 总豆排名）")

# 5) _collect 端到端能跑通不崩（小局）
from sanguopai.env.gym_env import SanGuoPaiEnv
env = SanGuoPaiEnv()
import torch
net = T.PolicyNet()
lp, rw, va, en, tot = T._collect(net, env, shaping=SH)
assert len(rw) == len(lp) > 0
# 末轮奖励不应再含 match-terminal bonus
print(f"[ok] _collect 端到端: {len(rw)} 步, total={tot:.2f}, 末轮奖励={rw[-1]:.2f}")

print("\n=== 全部冒烟通过 ===")
