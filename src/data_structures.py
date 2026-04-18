"""Core data structures and utility algorithms for Klondike Solitaire."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from random import Random
from secrets import randbits
from time import time_ns
from typing import Any, Generic, TypeVar
import json


T = TypeVar("T")


@dataclass
class Card:
    """Represent a single playing card."""

    rank: int
    suit: str
    face_up: bool = False

    def is_red(self) -> bool:
        """Return True when the card is a red suit."""
        return self.suit in {"H", "D"}

    def to_symbol(self) -> str:
        """Return a short printable symbol for the card."""
        ranks = {1: "A", 11: "J", 12: "Q", 13: "K"}
        rank_text = ranks.get(self.rank, str(self.rank))
        return f"{rank_text}{self.suit}"


class Stack(Generic[T]):
    """Provide a classic LIFO stack with push and pop operations."""

    def __init__(self) -> None:
        """Initialize an empty stack."""
        self._items: list[T] = []

    def push(self, value: T) -> None:
        """Push one element on top of the stack."""
        self._items.append(value)

    def pop(self) -> T:
        """Pop and return the top element from the stack."""
        if self.is_empty():
            raise IndexError("Cannot pop from an empty stack")
        return self._items.pop()

    def peek(self) -> T:
        """Return the top element without removing it."""
        if self.is_empty():
            raise IndexError("Cannot peek an empty stack")
        return self._items[-1]

    def is_empty(self) -> bool:
        """Return True when the stack has no element."""
        return len(self._items) == 0

    def size(self) -> int:
        """Return the number of elements in the stack."""
        return len(self._items)

    def clear(self) -> None:
        """Remove all elements from the stack."""
        self._items.clear()

    def to_list(self) -> list[T]:
        """Return a shallow list copy ordered from bottom to top."""
        return list(self._items)

    def load_from_list(self, values: list[T]) -> None:
        """Replace current content with values ordered from bottom to top."""
        self._items = list(values)


class HistoryManager:
    """Store undo and redo history using two stacks."""

    def __init__(self) -> None:
        """Create empty undo and redo stacks."""
        self._undo_stack: Stack[dict[str, Any]] = Stack()
        self._redo_stack: Stack[dict[str, Any]] = Stack()

    def record(self, state: dict[str, Any]) -> None:
        """Push a new state into undo stack and clear redo stack."""
        self._undo_stack.push(deepcopy(state))
        self._redo_stack.clear()

    def can_undo(self) -> bool:
        """Return True when at least one undo state exists."""
        return not self._undo_stack.is_empty()

    def can_redo(self) -> bool:
        """Return True when at least one redo state exists."""
        return not self._redo_stack.is_empty()

    def undo(self, current_state: dict[str, Any]) -> dict[str, Any] | None:
        """Return the previous state and push current state into redo stack."""
        if not self.can_undo():
            return None
        self._redo_stack.push(deepcopy(current_state))
        return self._undo_stack.pop()

    def redo(self, current_state: dict[str, Any]) -> dict[str, Any] | None:
        """Return the next state and push current state into undo stack."""
        if not self.can_redo():
            return None
        self._undo_stack.push(deepcopy(current_state))
        return self._redo_stack.pop()

    def clear(self) -> None:
        """Reset both history stacks."""
        self._undo_stack.clear()
        self._redo_stack.clear()


def create_standard_deck() -> list[Card]:
    """Create a standard 52-card deck represented as an array."""
    suits = ["S", "H", "D", "C"]
    return [Card(rank=rank, suit=suit) for suit in suits for rank in range(1, 14)]


def fisher_yates_shuffle(cards: list[Card], seed: int | None = None) -> None:
    """Shuffle a deck in-place with Fisher-Yates for unbiased permutations."""
    random_seed = seed if seed is not None else (randbits(64) ^ time_ns())
    rng = Random(random_seed)
    for index in range(len(cards) - 1, 0, -1):
        swap_index = rng.randint(0, index)
        cards[index], cards[swap_index] = cards[swap_index], cards[index]


class TableauColumn:
    """Represent one tableau column using two stacks for hidden and visible cards."""

    def __init__(self) -> None:
        """Initialize empty hidden and visible stacks."""
        self.face_down: Stack[Card] = Stack()
        self.face_up: Stack[Card] = Stack()

    def setup(self, hidden_cards: list[Card], visible_card: Card) -> None:
        """Load initial cards with hidden cards and one visible card on top."""
        self.face_down.load_from_list(hidden_cards)
        visible_card.face_up = True
        self.face_up.load_from_list([visible_card])

    def visible_cards(self) -> list[Card]:
        """Return visible cards ordered from bottom to top."""
        return self.face_up.to_list()

    def top_visible(self) -> Card | None:
        """Return the top visible card or None when no visible card exists."""
        if self.face_up.is_empty():
            return None
        return self.face_up.peek()

    def can_accept_pile(self, moving_cards: list[Card]) -> bool:
        """Validate whether a pile can be stacked on this column."""
        if not moving_cards:
            return False
        moving_bottom = moving_cards[0]
        target_top = self.top_visible()
        if target_top is None:
            return moving_bottom.rank == 13
        return target_top.is_red() != moving_bottom.is_red() and target_top.rank == moving_bottom.rank + 1

    def remove_visible_count(self, count: int) -> list[Card]:
        """Cut and return count cards from top of visible stack, preserving order."""
        if count <= 0 or count > self.face_up.size():
            raise ValueError("Invalid number of cards to remove")
        popped_cards = [self.face_up.pop() for _ in range(count)]
        return list(reversed(popped_cards))

    def add_pile(self, cards: list[Card]) -> None:
        """Place cards on top of visible stack with bottom-to-top order."""
        for card in cards:
            card.face_up = True
            self.face_up.push(card)

    def auto_flip(self) -> bool:
        """Flip one hidden card when visible stack becomes empty."""
        if self.face_up.is_empty() and not self.face_down.is_empty():
            card = self.face_down.pop()
            card.face_up = True
            self.face_up.push(card)
            return True
        return False

    def snapshot(self) -> dict[str, list[dict[str, Any]]]:
        """Serialize this column to a dictionary snapshot."""
        return {
            "face_down": [card_to_dict(card) for card in self.face_down.to_list()],
            "face_up": [card_to_dict(card) for card in self.face_up.to_list()],
        }

    def restore(self, state: dict[str, list[dict[str, Any]]]) -> None:
        """Restore this column from a dictionary snapshot."""
        down_cards = [card_from_dict(raw) for raw in state["face_down"]]
        up_cards = [card_from_dict(raw) for raw in state["face_up"]]
        self.face_down.load_from_list(down_cards)
        self.face_up.load_from_list(up_cards)


def card_to_dict(card: Card) -> dict[str, Any]:
    """Serialize one card into dictionary format."""
    return {"rank": card.rank, "suit": card.suit, "face_up": card.face_up}


def card_from_dict(raw: dict[str, Any]) -> Card:
    """Deserialize one dictionary into a Card object."""
    return Card(rank=int(raw["rank"]), suit=str(raw["suit"]), face_up=bool(raw["face_up"]))


class RankingBoard:
    """Persist game results and provide sorted ranking entries."""

    def __init__(self, file_path: str) -> None:
        """Store where ranking data should be loaded and saved."""
        self.file_path = Path(file_path)

    def load_entries(self) -> list[dict[str, Any]]:
        """Load ranking entries from disk or return an empty list."""
        if not self.file_path.exists():
            return []
        with self.file_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, list):
            return []
        return [entry for entry in data if isinstance(entry, dict)]

    def save_entries(self, entries: list[dict[str, Any]]) -> None:
        """Save ranking entries to disk as JSON."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with self.file_path.open("w", encoding="utf-8") as file:
            json.dump(entries, file, indent=2, ensure_ascii=True)

    def sorted_entries(self, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return entries sorted by win status, score, moves, and elapsed time."""
        return sorted(
            entries,
            key=lambda item: (
                int(not bool(item.get("won", False))),
                -int(item.get("score", 0)),
                int(item.get("moves", 0)),
                int(item.get("elapsed_seconds", 0)),
            ),
        )

    def add_result(
        self,
        player_name: str,
        score: int,
        moves: int,
        won: bool,
        elapsed_seconds: int,
    ) -> list[dict[str, Any]]:
        """Append one result then return the sorted leaderboard."""
        entries = self.load_entries()
        entries.append(
            {
                "player": player_name,
                "score": score,
                "moves": moves,
                "won": won,
                "elapsed_seconds": elapsed_seconds,
            }
        )
        sorted_board = self.sorted_entries(entries)
        self.save_entries(sorted_board)
        return sorted_board
