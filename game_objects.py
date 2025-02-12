from enum import IntEnum
from dataclasses import dataclass
from collections import Counter, defaultdict
from typing import List, Optional

class Rank(IntEnum):
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 1  # Ace can be 1 or 14, but defaulting to 1 for sequences

    @property
    def symbol(self) -> str:
        rank_symbols = {1: 'A', 2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7',
                        8: '8', 9: '9', 10: 'T', 11: 'J', 12: 'Q', 13: 'K'}
        return rank_symbols[self.value]

    def __str__(self) -> str:
        return self.symbol

class Suit(IntEnum):
    CLUBS = 1
    DIAMONDS = 2
    HEARTS = 3
    SPADES = 4

    @property
    def symbol(self) -> str:
        return {1: 'C', 2: 'D', 3: 'H', 4: 'S'}[self.value]

    def __str__(self) -> str:
        return self.symbol

@dataclass(frozen=True)
class Card:
    rank: Rank
    suit: Suit

    def __str__(self) -> str:
        return f"{self.rank.symbol}{self.suit.symbol}"

    def __lt__(self, other: 'Card') -> bool:
        return (self.rank.value, self.suit.value) < (other.rank.value, other.suit.value)

    @classmethod
    def from_string(cls, card_str: str) -> 'Card':
        if len(card_str) < 2:
            raise ValueError("Invalid card format")

        rank_char = card_str[:-1].upper()
        suit_char = card_str[-1].upper()

        rank = next(r for r in Rank if r.symbol == rank_char)
        suit = next(s for s in Suit if s.symbol == suit_char)
        return cls(rank=rank, suit=suit)

class Hand:
    def __init__(self):
        self.cards: List[Card] = []

    def add_card(self, card: Card) -> None:
        self.cards.append(card)
        self.cards.sort()

    def remove_card(self, card: Card) -> None:
        if card in self.cards:
            self.cards.remove(card)
        else:
            raise ValueError(f"Card {card} not found in hand")

    def find_sets(self) -> List[List[Card]]:
        sets = []
        rank_counts = Counter(card.rank for card in self.cards)

        for rank, count in rank_counts.items():
            if count >= 3:
                sets.append(sorted(self.get_cards_by_rank(rank)))

        return sets

    def find_runs(self) -> List[List[Card]]:
        runs = []
        suit_cards = defaultdict(list)
        for card in self.cards:
            suit_cards[card.suit].append(card)

        for cards in suit_cards.values():
            sorted_cards = sorted(cards, key=lambda c: c.rank.value)
            temp_run = []

            for card in sorted_cards:
                if temp_run and card.rank.value == temp_run[-1].rank.value + 1:
                    temp_run.append(card)
                else:
                    if len(temp_run) >= 3:
                        runs.append(temp_run[:])
                    temp_run = [card]

            if len(temp_run) >= 3:
                runs.append(temp_run)

        return runs

    def get_cards_by_rank(self, rank: Rank) -> List[Card]:
        return [card for card in self.cards if card.rank == rank]

    def __str__(self) -> str:
        return f"Hand: {', '.join(map(str, self.cards))}"

class GameState:
    def __init__(self):
        self.hand = Hand()
        self.discard_pile: List[Card] = []
        self.cannot_discard: Optional[Card] = None

    def update_discard_pile(self, card: Card) -> None:
        self.discard_pile.insert(0, card)

    def draw_from_discard_pile(self) -> Optional[Card]:
        return self.discard_pile.pop(0) if self.discard_pile else None

    def evaluate_card_value(self, card: Card) -> float:
        value = 0.0
        rank_matches = len(self.hand.get_cards_by_rank(card.rank))
        value += rank_matches * 3  # Higher weight for potential sets

        suit_cards = [c for c in self.hand.cards if c.suit == card.suit]
        for c in suit_cards:
            if abs(c.rank.value - card.rank.value) <= 1:
                value += 2  # Higher weight for potential runs

        return value

    def choose_discard(self) -> Optional[Card]:
        if not self.hand.cards:
            return None

        candidates = [card for card in self.hand.cards if card != self.cannot_discard]
        if not candidates:
            return None

        return min(candidates, key=self.evaluate_card_value)

    def __str__(self) -> str:
        return f"GameState(hand={self.hand}, discard_pile=[{', '.join(map(str, self.discard_pile))}])"
