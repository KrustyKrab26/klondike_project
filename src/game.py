"""Game mechanics for Klondike Solitaire."""

from __future__ import annotations

from time import time
from typing import Any

from .data_structures import (
    Card,
    HistoryManager,
    RankingBoard,
    Stack,
    TableauColumn,
    card_from_dict,
    card_to_dict,
    create_standard_deck,
    fisher_yates_shuffle,
)


class KlondikeGame:
    """Coordinate deck, piles, scoring, and strict move validation."""

    def __init__(self, ranking_file: str = "data/rankings.json") -> None:
        """Initialize game state containers and immediately start a new deal."""
        self.stock: Stack[Card] = Stack()
        self.waste: Stack[Card] = Stack()
        self.foundations: dict[str, Stack[Card]] = {suit: Stack() for suit in ["S", "H", "D", "C"]}
        self.tableau: list[TableauColumn] = [TableauColumn() for _ in range(7)]
        self.history = HistoryManager()
        self.ranking_board = RankingBoard(ranking_file)
        self.score = 0
        self.moves = 0
        self.player_name = "Player"
        self.start_time = time()
        self.new_game()

    def _clear_board(self) -> None:
        """Reset all piles and tableau columns to an empty board."""
        self.stock.clear()
        self.waste.clear()
        for foundation in self.foundations.values():
            foundation.clear()
        self.tableau = [TableauColumn() for _ in range(7)]

    def _push_many(self, stack: Stack[Card], cards: list[Card], face_up: bool) -> None:
        """Push cards to a stack while enforcing card orientation."""
        for card in cards:
            card.face_up = face_up
            stack.push(card)

    def _record_turn(self) -> None:
        """Store pre-move state for undo and clear redo history."""
        self.history.record(self.snapshot_state())

    def _card_key(self, card: Card) -> str:
        """Return a unique key for one rank/suit card identity."""
        return f"{card.rank}:{card.suit}"

    def _all_cards(self) -> list[Card]:
        """Return a flat list of all cards currently on board."""
        cards: list[Card] = []
        cards.extend(self.stock.to_list())
        cards.extend(self.waste.to_list())
        for stack in self.foundations.values():
            cards.extend(stack.to_list())
        for column in self.tableau:
            cards.extend(column.face_down.to_list())
            cards.extend(column.face_up.to_list())
        return cards

    def _auto_flip_if_needed(self, column_index: int) -> bool:
        """Flip one hidden card when source tableau has no visible cards left."""
        return self.tableau[column_index].auto_flip()

    def _is_valid_tableau_link(self, lower_card: Card, upper_card: Card) -> bool:
        """Return True when upper_card can be stacked above lower_card in tableau."""
        return lower_card.is_red() != upper_card.is_red() and lower_card.rank == upper_card.rank + 1

    def is_valid_tableau_sequence(self, cards: list[Card]) -> bool:
        """Return True when cards form one descending alternating-color tableau pile."""
        if not cards:
            return False
        for index in range(len(cards) - 1):
            if not self._is_valid_tableau_link(cards[index], cards[index + 1]):
                return False
        return True

    def can_place_on_foundation(self, card: Card, suit: str) -> bool:
        """Return True when card can be legally pushed to target foundation."""
        foundation = self.foundations[suit]
        if foundation.is_empty():
            return card.suit == suit and card.rank == 1
        top = foundation.peek()
        return card.suit == suit and card.rank == top.rank + 1

    def _can_place_on_tableau(self, moving_bottom: Card, target_column: int) -> bool:
        """Return True when moving_bottom can be placed on target tableau column."""
        target_top = self.tableau[target_column].top_visible()
        if target_top is None:
            return moving_bottom.rank == 13
        return self._is_valid_tableau_link(target_top, moving_bottom)

    def _commit_move(self, score_delta: int = 0, count_move: bool = True) -> None:
        """Apply score and move counters after a successful mutation."""
        self.score += score_delta
        if count_move:
            self.moves += 1

    def new_game(self, seed: int | None = None) -> None:
        """Deal a brand new shuffled game to stock and tableau piles."""
        deck = create_standard_deck()
        fisher_yates_shuffle(deck, seed=seed)

        self._clear_board()
        cursor = 0
        for column_index in range(7):
            hidden_cards = deck[cursor : cursor + column_index]
            cursor += column_index
            visible_card = deck[cursor]
            cursor += 1

            for card in hidden_cards:
                card.face_up = False
            visible_card.face_up = True
            self.tableau[column_index].setup(hidden_cards=hidden_cards, visible_card=visible_card)

        self._push_many(self.stock, deck[cursor:], face_up=False)
        self.score = 0
        self.moves = 0
        self.start_time = time()
        self.history.clear()

    def set_player_name(self, player_name: str) -> None:
        """Set player display name that will be used in ranking records."""
        cleaned = player_name.strip()
        self.player_name = cleaned if cleaned else "Player"

    def snapshot_state(self) -> dict[str, Any]:
        """Serialize full game state for undo, redo, and validations."""
        return {
            "stock": [card_to_dict(card) for card in self.stock.to_list()],
            "waste": [card_to_dict(card) for card in self.waste.to_list()],
            "foundations": {
                suit: [card_to_dict(card) for card in foundation.to_list()]
                for suit, foundation in self.foundations.items()
            },
            "tableau": [column.snapshot() for column in self.tableau],
            "score": self.score,
            "moves": self.moves,
            "start_time": self.start_time,
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        """Restore state payload produced by snapshot_state."""
        self.stock.load_from_list([card_from_dict(raw) for raw in state["stock"]])
        self.waste.load_from_list([card_from_dict(raw) for raw in state["waste"]])

        for suit, cards in state["foundations"].items():
            self.foundations[suit].load_from_list([card_from_dict(raw) for raw in cards])

        for index, column_state in enumerate(state["tableau"]):
            self.tableau[index].restore(column_state)

        self.score = int(state["score"])
        self.moves = int(state["moves"])
        self.start_time = float(state["start_time"])

    def draw_from_stock(self) -> bool:
        """Draw one card to waste or recycle waste back to stock when stock is empty."""
        if self.stock.is_empty() and self.waste.is_empty():
            return False

        self._record_turn()
        if self.stock.is_empty():
            while not self.waste.is_empty():
                card = self.waste.pop()
                card.face_up = False
                self.stock.push(card)
            self._commit_move(score_delta=0)
            return True

        card = self.stock.pop()
        card.face_up = True
        self.waste.push(card)
        self._commit_move(score_delta=5)
        return True

    def move_waste_to_foundation(self, suit: str) -> bool:
        """Move top waste card to one foundation if legal."""
        if suit not in self.foundations or self.waste.is_empty():
            return False
        card = self.waste.peek()
        if not self.can_place_on_foundation(card, suit):
            return False

        self._record_turn()
        moved = self.waste.pop()
        moved.face_up = True
        self.foundations[suit].push(moved)
        self._commit_move(score_delta=10)
        return True

    def move_waste_to_tableau(self, target_column: int) -> bool:
        """Move top waste card to target tableau column if legal."""
        if self.waste.is_empty() or not (0 <= target_column < 7):
            return False
        card = self.waste.peek()
        if not self._can_place_on_tableau(card, target_column):
            return False

        self._record_turn()
        moved = self.waste.pop()
        moved.face_up = True
        self.tableau[target_column].add_pile([moved])
        self._commit_move(score_delta=5)
        return True

    def move_tableau_to_foundation(self, source_column: int) -> bool:
        """Move top visible card from tableau column to matching foundation if legal."""
        if not (0 <= source_column < 7):
            return False
        card = self.tableau[source_column].top_visible()
        if card is None or not self.can_place_on_foundation(card, card.suit):
            return False

        self._record_turn()
        moved = self.tableau[source_column].remove_visible_count(1)[0]
        moved.face_up = True
        self.foundations[moved.suit].push(moved)
        flipped = self._auto_flip_if_needed(source_column)
        self._commit_move(score_delta=10 if flipped else 8)
        return True

    def move_tableau_to_tableau(self, source_column: int, target_column: int, count: int) -> bool:
        """Move one visible card or visible pile between tableau columns if legal."""
        if not (0 <= source_column < 7) or not (0 <= target_column < 7):
            return False
        if source_column == target_column:
            return False

        visible_cards = self.tableau[source_column].visible_cards()
        if count <= 0 or count > len(visible_cards):
            return False

        moving_cards = visible_cards[-count:]
        if not self.is_valid_tableau_sequence(moving_cards):
            return False
        if not self._can_place_on_tableau(moving_cards[0], target_column):
            return False

        self._record_turn()
        moved_cards = self.tableau[source_column].remove_visible_count(count)
        self.tableau[target_column].add_pile(moved_cards)
        flipped = self._auto_flip_if_needed(source_column)
        self._commit_move(score_delta=6 if flipped else 3)
        return True

    def move_foundation_to_tableau(self, suit: str, target_column: int) -> bool:
        """Move top foundation card back to tableau if legal."""
        if suit not in self.foundations or not (0 <= target_column < 7):
            return False
        foundation = self.foundations[suit]
        if foundation.is_empty():
            return False

        card = foundation.peek()
        if not self._can_place_on_tableau(card, target_column):
            return False

        self._record_turn()
        moved = foundation.pop()
        moved.face_up = True
        self.tableau[target_column].add_pile([moved])
        self._commit_move(score_delta=-15)
        return True

    def validate_tableau_state(self) -> bool:
        """Return True when tableau columns satisfy card orientation and stack ordering."""
        for column in self.tableau:
            down_cards = column.face_down.to_list()
            up_cards = column.face_up.to_list()
            if any(card.face_up for card in down_cards):
                return False
            if any(not card.face_up for card in up_cards):
                return False
            if up_cards and not self.is_valid_tableau_sequence(up_cards):
                return False
        return True

    def validate_foundation_state(self) -> bool:
        """Return True when each foundation stack is same-suit and strictly ascending."""
        for suit, stack in self.foundations.items():
            expected = 1
            for card in stack.to_list():
                if card.suit != suit or card.rank != expected or not card.face_up:
                    return False
                expected += 1
        return True

    def validate_card_inventory(self) -> bool:
        """Return True when board contains exactly one copy of each of 52 cards."""
        cards = self._all_cards()
        if len(cards) != 52:
            return False
        unique_keys = {self._card_key(card) for card in cards}
        return len(unique_keys) == 52

    def validate_state(self) -> bool:
        """Return True when tableau, foundation, and inventory invariants all hold."""
        return (
            self.validate_tableau_state()
            and self.validate_foundation_state()
            and self.validate_card_inventory()
        )

    def undo(self) -> bool:
        """Undo one move using history stacks."""
        previous = self.history.undo(self.snapshot_state())
        if previous is None:
            return False
        self.restore_state(previous)
        return True

    def redo(self) -> bool:
        """Redo one move using history stacks."""
        next_state = self.history.redo(self.snapshot_state())
        if next_state is None:
            return False
        self.restore_state(next_state)
        return True

    def elapsed_seconds(self) -> int:
        """Return elapsed game time in seconds."""
        return int(time() - self.start_time)

    def is_won(self) -> bool:
        """Return True when all foundations are complete from Ace to King."""
        return all(stack.size() == 13 for stack in self.foundations.values())

    def finalize_result(self) -> list[dict[str, Any]]:
        """Persist current game result into ranking storage and return leaderboard."""
        return self.ranking_board.add_result(
            player_name=self.player_name,
            score=self.score,
            moves=self.moves,
            won=self.is_won(),
            elapsed_seconds=self.elapsed_seconds(),
        )

    def top_cards_view(self) -> dict[str, str]:
        """Return compact symbols for stock, waste, and foundation top cards."""
        stock_text = "XX" if not self.stock.is_empty() else "--"
        waste_text = self.waste.peek().to_symbol() if not self.waste.is_empty() else "--"
        foundation_text = {
            suit: (stack.peek().to_symbol() if not stack.is_empty() else "--")
            for suit, stack in self.foundations.items()
        }
        result = {"stock": stock_text, "waste": waste_text}
        result.update({f"foundation_{suit}": text for suit, text in foundation_text.items()})
        return result

    def tableau_view(self) -> list[str]:
        """Return one text summary line for each tableau column."""
        lines: list[str] = []
        for index, column in enumerate(self.tableau, start=1):
            hidden = "[XX]" * column.face_down.size()
            visible = " ".join(card.to_symbol() for card in column.visible_cards())
            lines.append(f"T{index}: {hidden} {visible}".strip())
        return lines
