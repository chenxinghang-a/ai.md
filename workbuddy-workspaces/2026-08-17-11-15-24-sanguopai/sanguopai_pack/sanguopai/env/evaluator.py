"""德州扑克 5 张牌型评估器（直接用于三国牌 9 种牌型）。"""

from __future__ import annotations

from collections import Counter
from typing import List, Tuple

from .card import Card, Rank

# 牌型等级，与 config.type_multipliers 下标一致
GRADE_HIGH_CARD = 0
GRADE_ONE_PAIR = 1
GRADE_TWO_PAIR = 2
GRADE_THREE_KIND = 3
GRADE_STRAIGHT = 4
GRADE_FLUSH = 5
GRADE_FULL_HOUSE = 6
GRADE_FOUR_KIND = 7
GRADE_STRAIGHT_FLUSH = 8


def _is_straight(ranks: List[int]) -> int:
    """判断是否为顺子，返回顺子最大点数（A 高则 14，A 低则 5），否则 -1。"""
    unique = sorted(set(ranks))
    if len(unique) < 5:
        return -1
    # A 高顺
    for start in range(len(unique) - 5, -1, -1):
        if unique[start + 4] - unique[start] == 4:
            return unique[start + 4]
    # A 低顺：A,2,3,4,5
    if set(unique) >= {12, 0, 1, 2, 3}:
        return 3  # 5 的点数编码为 3
    return -1


def evaluate_five(cards: List[Card]) -> Tuple[int, Tuple[int, ...]]:
    """
    评估 5 张牌。
    返回 (grade, tiebreak_tuple)，可直接用 > / < 比较大小。
    """
    assert len(cards) == 5
    ranks = sorted([c.rank for c in cards], reverse=True)
    suits = [c.suit for c in cards]
    is_flush = len(set(suits)) == 1

    rank_counts = Counter(ranks)
    # 按 (出现次数, 点数) 降序排列
    count_rank = sorted(rank_counts.items(), key=lambda x: (x[1], x[0]), reverse=True)

    straight_high = _is_straight(ranks)

    if is_flush and straight_high >= 0:
        return GRADE_STRAIGHT_FLUSH, (straight_high,)

    if count_rank[0][1] == 4:
        # 四炸：四条点数 + 踢脚
        quad = count_rank[0][0]
        kicker = count_rank[1][0]
        return GRADE_FOUR_KIND, (quad, kicker)

    if count_rank[0][1] == 3 and count_rank[1][1] == 2:
        # 三带二
        trip = count_rank[0][0]
        pair = count_rank[1][0]
        return GRADE_FULL_HOUSE, (trip, pair)

    if is_flush:
        return GRADE_FLUSH, tuple(ranks)

    if straight_high >= 0:
        return GRADE_STRAIGHT, (straight_high,)

    if count_rank[0][1] == 3:
        trip = count_rank[0][0]
        kickers = sorted([r for r in ranks if r != trip], reverse=True)
        return GRADE_THREE_KIND, (trip,) + tuple(kickers)

    if count_rank[0][1] == 2 and count_rank[1][1] == 2:
        high_pair = count_rank[0][0]
        low_pair = count_rank[1][0]
        kicker = count_rank[2][0]
        return GRADE_TWO_PAIR, (high_pair, low_pair, kicker)

    if count_rank[0][1] == 2:
        pair = count_rank[0][0]
        kickers = sorted([r for r in ranks if r != pair], reverse=True)
        return GRADE_ONE_PAIR, (pair,) + tuple(kickers)

    return GRADE_HIGH_CARD, tuple(ranks)


def evaluate_five_score(cards: List[Card]) -> int:
    """打包成单一整数分数，越大越强（方便 numpy 存储）。
    grade 固定占据 13^5 位，可直接用 score // 13^5 取回 grade。"""
    grade, tie = evaluate_five(cards)
    score = grade
    # tiebreak 补齐到 5 位，确保 grade 总在相同高位
    padded = list(tie) + [0] * (5 - len(tie))
    for v in padded:
        score = score * 13 + v
    return score


def grade_name(grade: int) -> str:
    names = ["单张", "对子", "两对", "三张", "顺子", "同花", "三带二", "四炸", "同花顺"]
    return names[grade]
