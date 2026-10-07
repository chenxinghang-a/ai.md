"""忠实复现 game.py 结算，构造老板给的场景，算第5名实际扣多少。
直接用真实 evaluate_five_score 取 grade/faction，调用 card_counter.resolve_settle（与 game.step 一致）。
"""
import sys
sys.path.insert(0, '.')
from sanguopai.config import DEFAULT_CONFIG as C
from sanguopai.env.card import Card
from sanguopai.env.evaluator import evaluate_five_score, grade_name
from sanguopai.env.card_counter import resolve_settle

FAC = {0: '魏', 1: '蜀', 2: '吴'}

def hand(cards):
    """cards: list of (rank, suit)，rank 0=A..12=K, suit 0..3"""
    cs = [Card(r, s) for r, s in cards]
    return evaluate_five_score(cs), [c.code for c in cs]

def build(players):
    """players: list of (pid, faction, cards)"""
    subs = []
    for pid, fac, cards in players:
        sc, codes = hand(cards)
        subs.append((sc, pid, codes, fac, -1))
    return subs

def show(title, subs):
    print('\n=== ' + title + ' ===')
    n = 5
    entry = [100_000_000] * n   # 入口 1 亿（默认），>= cap → cap_eff = cap = 1800万
    chips = [100_000_000] * n
    rewards = resolve_settle(subs, n, entry, chips, C)
    # 名次
    order = sorted(subs, key=lambda x: x[0], reverse=True)
    ranks = [0]*n; cur=1; i=0
    while i < len(order):
        j=i
        while j<len(order) and order[j][0]==order[i][0]: j+=1
        for k in range(i,j): ranks[order[k][1]]=cur
        cur+=j-i; i=j
    for sc, pid, codes, fac, _ in sorted(subs, key=lambda x: -ranks[x[1]]):
        r = rewards[pid]
        capped = '  ← 顶到上限1800万' if (r < 0 and -r >= C.cap) else ''
        print(f'  P{pid} {FAC[fac]} {grade_name(sc//(13**5)):>3} 名次{rank_rank(ranks[pid])}  净{("+" if r>=0 else "")}{r:,} ({r/1e4:.1f}万){capped}')
    return rewards

def rank_rank(r): return ['-','①','②','③','④','⑤'][r]

# 场景 A：葫芦赢，同阵营(魏)4人，其余小牌，第5名=同阵营单张（同型只有赢家1人）
A = build([
    (0, 0, [(5,0),(5,1),(5,2),(9,0),(9,1)]),   # 魏 葫芦 555+99 → 赢
    (1, 0, [(0,0),(0,1),(1,0),(1,1),(3,2)]),   # 魏 两对 AA22+3
    (2, 0, [(11,0),(11,1),(4,2),(6,3),(8,0)]), # 魏 对子 KK
    (3, 0, [(2,0),(4,1),(7,2),(9,3),(10,0)]),  # 魏 单张（第5名，同阵营）
    (4, 2, [(8,0),(8,1),(8,2),(3,3),(5,0)]),   # 吴 三张 888
])

# 场景 B：同花赢（同花 class 2，同型只有赢家1人），其余同上 → 看同花差值
B = build([
    (0, 0, [(1,0),(3,0),(5,0),(7,0),(9,0)]),   # 魏 同花（同suit0，非顺）
    (1, 0, [(0,0),(0,1),(1,0),(1,1),(3,2)]),
    (2, 0, [(11,0),(11,1),(4,2),(6,3),(8,0)]),
    (3, 0, [(2,0),(4,1),(7,2),(9,3),(10,0)]),  # 第5名单张
    (4, 2, [(8,0),(8,1),(8,2),(3,3),(5,0)]),
])

# 场景 C：葫芦赢，但同阵营里还有另一个葫芦（同型2人）→ 第5名同型拥挤，杀牌倍率触发
Cc = build([
    (0, 0, [(5,0),(5,1),(5,2),(9,0),(9,1)]),   # 魏 葫芦 555+99 赢
    (1, 0, [(4,0),(4,1),(4,2),(2,0),(2,1)]),   # 魏 葫芦 444+22（同型，名次②）
    (2, 0, [(11,0),(11,1),(4,3),(6,3),(8,0)]),
    (3, 0, [(2,2),(4,1),(7,2),(9,3),(10,0)]),  # 第5名单张（同阵营）
    (4, 2, [(8,0),(8,1),(8,2),(3,3),(5,1)]),
])

show('A 葫芦赢 / 同阵营4人 / 第5名=同阵营单张（同型仅赢家1人）', A)
show('B 同花赢 / 同阵营4人 / 第5名=同阵营单张（同型仅赢家1人）', B)
show('C 葫芦赢 / 同阵营4人 / 第5名=同阵营单张（同型拥挤=2人→杀牌倍率触发）', Cc)

print('\n--- 当前倍率（已按老板修正）---')
print('type_multipliers :', C.type_multipliers)
print('rank_multipliers :', C.rank_multipliers, '(索引2..5 = 名次②③④⑤)')
print('crit 同阵营      :', C.crit_multipliers[1:6], ' ← 同阵营 1 2 4 8 12')
print('kill 同牌型      :', C.kill_multipliers[1:6], ' ← 同牌型 1 2 4 8 16')
print('base_score=%d  cap=%d(%.0f万)' % (C.base_score, C.cap, C.cap/1e4))
