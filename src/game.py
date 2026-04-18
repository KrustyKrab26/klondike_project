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
    """Coordinate deck, piles, scoring, and move validation."""

    def __init__(self, ranking_file: str = "data/rankings.json") -> None:
        """Initialize game state and create a new game."""
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

    def new_game(self, seed: int | None = None) -> None:
        """Start a new shuffled game and deal cards into tableau and stock."""
        deck = create_standard_deck()
        fisher_yates_shuffle(deck, seed=seed)

        self.stock.clear()
        self.waste.clear()
        for suit_stack in self.foundations.values():
            suit_stack.clear()
        self.tableau = [TableauColumn() for _ in range(7)]

        cursor = 0
        for column_index in range(7):
            hidden = deck[cursor : cursor + column_index]
            cursor += column_index
            visible = deck[cursor]
            cursor += 1
            for card in hidden:
                card.face_up = False
            visible.face_up = True
            self.tableau[column_index].setup(hidden_cards=hidden, visible_card=visible)

        remaining = deck[cursor:]
        for card in remaining:
            card.face_up = False
            self.stock.push(card)

        self.score = 0
        self.moves = 0
        self.start_time = time()
        self.history.clear()

    def set_player_name(self, player_name: str) -> None:
        """Set player display name for ranking output."""
        cleaned = player_name.strip()
        self.player_name = cleaned if cleaned else "Player"

    def snapshot_state(self) -> dict[str, Any]:
        """Serialize the full board state for undo and redo."""
        return {
            "stock": [card_to_dict(card) for card in self.stock.to_list()],
            "waste": [card_to_dict(card) for card in self.waste.to_list()],
            "foundations": {
                suit: [card_to_dict(card) for card in stack.to_list()]
                for suit, stack in self.foundations.items()
            },
            "tableau": [column.snapshot() for column in self.tableau],
            "score": self.score,
            "moves": self.moves,
            "start_time": self.start_time,
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        """Restore the board from a previous serialized state."""
        self.stock.load_from_list([card_from_dict(raw) for raw in state["stock"]])
        self.waste.load_from_list([card_from_dict(raw) for raw in state["waste"]])

        for suit, values in state["foundations"].items():
            self.foundations[suit].load_from_list([card_from_dict(raw) for raw in values])

        for index, column_state in enumerate(state["tableau"]):
            self.tableau[index].restore(column_state)

        self.score = int(state["score"])
        self.moves = int(state["moves"])
        self.start_time = float(state["start_time"])

    def record_turn(self) -> None:
        """Save current state in undo history before applying a move."""
        self.history.record(self.snapshot_state())

    def can_place_on_foundation(self, card: Card, suit: str) -> bool:
        """Return True when a card can be placed on the target foundation."""
        foundation = self.foundations[suit]
        if foundation.is_empty():
            return card.suit == suit and card.rank == 1
        top = foundation.peek()
        return card.suit == suit and card.rank == top.rank + 1

    def draw_from_stock(self) -> bool:
        """Draw one card from stock to waste or recycle waste when stock is empty."""
        if self.stock.is_empty():
            if self.waste.is_empty():
                return False
            self.record_turn()
            while not self.waste.is_empty():
                card = self.waste.pop()
                card.face_up = False
                self.stock.push(card)
            self.moves += 1
            return True

        self.record_turn()
        card = self.stock.pop()
        card.face_up = True
        self.waste.push(card)
        self.score += 5
        self.moves += 1
        return True

    def move_waste_to_foundation(self, suit: str) -> bool:
        """Move top waste card to one foundation stack when valid."""
        if self.waste.is_empty() or suit not in self.foundations:
            return False
        card = self.waste.peek()
        if not self.can_place_on_foundation(card, suit):
            return False

        self.record_turn()
        self.waste.pop()
        self.foundations[suit].push(card)
        self.score += 10
        self.moves += 1
        return True

    def move_waste_to_tableau(self, target_column: int) -> bool:
        """Move top waste card to target tableau column when valid."""
        if self.waste.is_empty() or not (0 <= target_column < len(self.tableau)):
            return False
        card = self.waste.peek()
        if not self.tableau[target_column].can_accept_pile([card]):
            return False

        self.record_turn()
        moved = self.waste.pop()
        self.tableau[target_column].add_pile([moved])
        self.score += 5
        self.moves += 1
        return True

    def move_tableau_to_foundation(self, source_column: int) -> bool:
        """Move top visible tableau card to matching foundation when valid."""
        if not (0 <= source_column < len(self.tableau)):
            return False
        card = self.tableau[source_column].top_visible()
        if card is None or not self.can_place_on_foundation(card, card.suit):
            return False

        self.record_turn()
        moved_cards = self.tableau[source_column].remove_visible_count(1)
        self.foundations[card.suit].push(moved_cards[0])
        flipped = self.tableau[source_column].auto_flip()
        self.score += 10 if flipped else 8
        self.moves += 1
        return True

    def move_tableau_to_tableau(self, source_column: int, target_column: int, count: int) -> bool:
        """Move one card or a visible pile between tableau columns."""
        if not (0 <= source_column < len(self.tableau)):
            return False
        if not (0 <= target_column < len(self.tableau)):
            return False
        if source_column == target_column:
            return False

        visible = self.tableau[source_column].visible_cards()
        if count <= 0 or count > len(visible):
            return False

        moving_cards = visible[-count:]
        if not self.tableau[target_column].can_accept_pile(moving_cards):
            return False

        self.record_turn()
        moved = self.tableau[source_column].remove_visible_count(count)
        self.tableau[target_column].add_pile(moved)
        flipped = self.tableau[source_column].auto_flip()
        self.score += 6 if flipped else 3
        self.moves += 1
        return True

    def move_foundation_to_tableau(self, suit: str, target_column: int) -> bool:
        """Move top foundation card back to tableau when valid."""
        if suit not in self.foundations or not (0 <= target_column < len(self.tableau)):
            return False
        foundation = self.foundations[suit]
        if foundation.is_empty():
            return False

        card = foundation.peek()
        if not self.tableau[target_column].can_accept_pile([card]):
            return False

        self.record_turn()
        moved = foundation.pop()
        self.tableau[target_column].add_pile([moved])
        self.score -= 15
        self.moves += 1
        return True

    def undo(self) -> bool:
        """Undo one move using undo and redo stacks."""
        previous_state = self.history.undo(self.snapshot_state())
        if previous_state is None:
            return False
        self.restore_state(previous_state)
        return True

    def redo(self) -> bool:
        """Redo one move using undo and redo stacks."""
        next_state = self.history.redo(self.snapshot_state())
        if next_state is None:
            return False
        self.restore_state(next_state)
        return True

    def elapsed_seconds(self) -> int:
        """Return elapsed play time in seconds for current game."""
        return int(time() - self.start_time)

    def is_won(self) -> bool:
        """Return True when all four foundations have 13 cards."""
        return all(stack.size() == 13 for stack in self.foundations.values())

    def finalize_result(self) -> list[dict[str, Any]]:
        """Save current result to ranking and return sorted leaderboard."""
        return self.ranking_board.add_result(
            player_name=self.player_name,
            score=self.score,
            moves=self.moves,
            won=self.is_won(),
            elapsed_seconds=self.elapsed_seconds(),
        )

    def top_cards_view(self) -> dict[str, str]:
        """Return compact text symbols for stock, waste, and foundations."""
        stock_text = "XX" if not self.stock.is_empty() else "--"
        waste_text = self.waste.peek().to_symbol() if not self.waste.is_empty() else "--"
        foundations_text = {
            suit: (stack.peek().to_symbol() if not stack.is_empty() else "--")
            for suit, stack in self.foundations.items()
        }
        result = {"stock": stock_text, "waste": waste_text}
        result.update({f"foundation_{suit}": text for suit, text in foundations_text.items()})
        return result

    def tableau_view(self) -> list[str]:
        """Return one text line per tableau column for GUI display."""
        columns: list[str] = []
        for index, column in enumerate(self.tableau, start=1):
            hidden_count = column.face_down.size()
            visible = " ".join(card.to_symbol() for card in column.visible_cards())
            hidden_text = "[XX]" * hidden_count
            text = f"T{index}: {hidden_text} {visible}".strip()
            columns.append(text)
        return columns
