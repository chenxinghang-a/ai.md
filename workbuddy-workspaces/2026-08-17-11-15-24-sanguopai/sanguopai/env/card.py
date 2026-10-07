"""牌的基础表示与工具函数。"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import IntEnum
from typing import List, Tuple


class Suit(IntEnum):
    SPADE = 0
    HEART = 1
    DIAMOND = 2
    CLUB = 3


class Rank(IntEnum):
    TWO = 0
    THREE = 1
    FOUR = 2
    FIVE = 3
    SIX = 4
    SEVEN = 5
    EIGHT = 6
    NINE = 7
    TEN = 8
    JACK = 9
    QUEEN = 10
    KING = 11
    ACE = 12


RANK_CHAR = "23456789TJQKA"
SUIT_CHAR = "♠♥♦♣"


@dataclass(frozen=True, order=True)
class Card:
    rank: Rank
    suit: Suit

    def __repr__(self) -> str:
        return f"{RANK_CHAR[self.rank]}{SUIT_CHAR[self.suit]}"

    @property
    def code(self) -> int:
        """唯一整数编码 0..51，方便位运算。"""
        return self.suit * 13 + self.rank

    @staticmethod
    def from_code(code: int) -> "Card":
        return Card(Rank(code % 13), Suit(code // 13))


def full_deck() -> List[Card]:
    return [Card(rank=r, suit=s) for s in Suit for r in Rank]


def shuffle_deck(rng: random.Random) -> List[Card]:
    deck = full_deck()
    rng.shuffle(deck)
    return deck


def cards_to_string(cards: List[Card]) -> str:
    return " ".join(str(c) for c in cards)
