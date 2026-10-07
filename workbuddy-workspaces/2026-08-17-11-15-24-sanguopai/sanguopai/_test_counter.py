"""验证 CardCounter 的避险/留牌能力。"""
from sanguopai.env.card_counter import CardCounter, decode_action, FACTION_WEI, FACTION_WU, FACTION_SHU, ACTION_TABLE
from sanguopai.env.evaluator import evaluate_five_score

def code(rank, suit): return suit * 13 + rank

my_hand1 = [code(1,0), code(2,1), code(3,2), code(4,3), code(5,0),  # 3♠4♥5♦6♣7♠ = 混合花色小顺子
            code(12,1), code(12,2), code(12,3)]                      # 三张A当 filler
pub_wei1 = [code(7,0), code(7,1), code(4,2)]
pub_wu1 = [code(0,2), code(1,3)]
seen1 = set(pub_wei1 + pub_wu1)
obs1 = {
    "hand": my_hand1 + [52]*(8-len(my_hand1)),
    "public_wei": pub_wei1, "public_wu": pub_wu1,
    "public_seen": [1 if c in seen1 else 0 for c in range(52)],
    "chips": [100_000_000]*5,
}

my_hand2 = [code(11,0), code(11,1), code(0,0), code(2,1), code(3,2),
            code(5,3), code(7,2), code(9,3)]
pub_wei2 = [code(0,2), code(1,3), code(4,0)]
pub_wu2 = [code(11,2), code(11,3)]
seen2 = set(pub_wei2 + pub_wu2)
obs2 = {
    "hand": my_hand2 + [52]*(8-len(my_hand2)),
    "public_wei": pub_wei2, "public_wu": pub_wu2,
    "public_seen": [1 if c in seen2 else 0 for c in range(52)],
    "chips": [100_000_000]*5,
}

cc = CardCounter(n_sim=2500, rng=__import__('random').Random(0))

def grade_name(g):
    return ['高牌','对子','两对','三条','顺子','同花','葫芦','四炸','同花顺'][g]

print("="*60)
print("场景1：我小顺子(34567) + 公共魏有对9（对面能凑葫芦/四炸）")
print("="*60)
ev1, win1, cands1 = cc.analyze(obs1)
straight_aid = None
for aid in range(len(ACTION_TABLE)):
    fac, idx = decode_action(aid)
    if fac == FACTION_SHU and list(idx) == [0,1,2,3,4]:
        straight_aid = aid; break
top1 = max(range(len(ev1)), key=lambda a: ev1[a])
print(f"顺子动作 aid={straight_aid}: win_prob={win1[straight_aid]:.3f}  EV={ev1[straight_aid]:+.0f}")
print(f"全场最优 aid={top1}: fac={decode_action(top1)[0]} idx={decode_action(top1)[1]} "
      f"grade={grade_name(cands1[top1][0]//(13**5))} win={win1[top1]:.3f} EV={ev1[top1]:+.0f}")
order = sorted(range(len(ev1)), key=lambda a: ev1[a], reverse=True)[:5]
print("Top5(按EV):")
for a in order:
    fac, idx = decode_action(a)
    print(f"  aid={a:3d} fac={fac} grade={grade_name(cands1[a][0]//(13**5)):>4} win={win1[a]:.3f} EV={ev1[a]:+10.0f}")
print("=> 避险验证：顺子 win_prob 应<0.5 且 EV 偏低，最优应为更小/更安全牌型\n")

print("="*60)
print("场景2：我手有对K + 公共吴有对K -> 应上四炸(我大就上)")
print("="*60)
ev2, win2, cands2 = cc.analyze(obs2)
fourk_aid = None
for aid in range(len(ACTION_TABLE)):
    fac, idx = decode_action(aid)
    if fac == FACTION_WU and 0 in idx and 1 in idx:  # 吴选 K♠K♥ + 公共K♦K♣ = 四炸
        fourk_aid = aid; break
top2 = max(range(len(ev2)), key=lambda a: ev2[a])
print(f"四炸动作 aid={fourk_aid}: win_prob={win2[fourk_aid]:.3f}  EV={ev2[fourk_aid]:+.0f}")
print(f"全场最优 aid={top2}: fac={decode_action(top2)[0]} idx={decode_action(top2)[1]} "
      f"grade={grade_name(cands2[top2][0]//(13**5))} win={win2[top2]:.3f} EV={ev2[top2]:+.0f}")
order2 = sorted(range(len(ev2)), key=lambda a: ev2[a], reverse=True)[:5]
print("Top5(按EV):")
for a in order2:
    fac, idx = decode_action(a)
    print(f"  aid={a:3d} fac={fac} grade={grade_name(cands2[a][0]//(13**5)):>4} win={win2[a]:.3f} EV={ev2[a]:+10.0f}")
print("=> 留牌验证：四炸 win_prob 应>0.8 且是最优动作\n")
