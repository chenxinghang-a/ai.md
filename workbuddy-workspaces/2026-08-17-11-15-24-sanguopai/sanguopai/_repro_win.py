"""复现：低豆玩家(16万)作为『赢家』时，赢的金额是否与高豆(1亿)玩家相同。"""
import random
from sanguopai.env.card import Card
from sanguopai.env.game import SanGuoPaiGame, ACTION_TABLE, FACTION_STARTS
from sanguopai.config import DEFAULT_CONFIG

def C(code):
    return Card.from_code(code)

# 蜀(idx 0,1,2,3,4) 动作 id
A_SHA5 = next(aid for aid, (f, idx) in enumerate(ACTION_TABLE) if f == 1 and list(idx) == [0, 1, 2, 3, 4])

# 玩家0 同花顺 10sJsQsKsAs = suit0 ranks 8,9,10,11,12
WIN_CARDS = [8, 9, 10, 11, 12, 13, 14, 15]  # 前5张=同花顺, 后3张填充

def build(entry0, seed=7):
    g = SanGuoPaiGame(config=DEFAULT_CONFIG, seed=seed, initial_chips=100_000_000)
    g.round = 0; g.done = False
    g.bankrupt = [False] * 5
    g.history_log.clear(); g.public_seen = set()
    g.hands = [[] for _ in range(5)]
    g.public = [[], [], []]
    g.hands[0] = [C(c) for c in WIN_CARDS]
    # 对手: 随机散牌(排除玩家0的牌)，保证玩家0同花顺必胜
    used = set(WIN_CARDS)
    rng = random.Random(seed)
    for i in range(1, 5):
        h = []
        while len(h) < 8:
            c = rng.randint(0, 51)
            if c in used: continue
            used.add(c); h.append(c)
        g.hands[i] = [C(c) for c in h]
    g.public[0] = [C(40), C(41), C(42)]
    g.public[2] = [C(43), C(44)]
    g.public_seen.update([40, 41, 42, 43, 44])
    chips = [entry0] + [100_000_000] * 4
    g.chips = chips[:]; g.entry_chips = chips[:]
    return g

for label, entry0 in [("16万", 160_000), ("1亿", 100_000_000)]:
    g = build(entry0)
    acts = {i: A_SHA5 for i in range(5)}
    rewards, done, info = g.step(acts)
    sub = info["log"]["submissions"]
    ranks = {s["player"]: s["rank"] for s in sub}
    grades = {s["player"]: s["grade"] for s in sub}
    assert ranks[0] == 1, f"玩家0不是第一名! ranks={ranks}"
    print(f"[{label}] 玩家0=第1名(同花顺) | 玩家0赢额 reward[0]={rewards[0]:,} | 各人奖励={rewards}")
