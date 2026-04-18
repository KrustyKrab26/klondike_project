"""Tkinter user interface for Klondike Solitaire."""

from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from .game import KlondikeGame


class KlondikeApp:
    """Render and control a visual Klondike board."""

    CARD_WIDTH = 72
    CARD_HEIGHT = 100
    TOP_Y = 18
    TABLEAU_Y = 190
    COL_GAP = 24
    DOWN_STEP = 18
    UP_STEP = 30

    def __init__(self, root: tk.Tk) -> None:
        """Create game model, widgets, and initial board rendering."""
        self.root = root
        self.root.title("Klondike Solitaire - Python")
        self.root.geometry("1060x860")
        self.root.minsize(1000, 780)
        self.game = KlondikeGame()

        self.player_var = tk.StringVar(value="Player")
        self.status_var = tk.StringVar(value="Click stock to draw, then click source -> target to move")
        self.score_var = tk.StringVar(value="Score: 0")
        self.moves_var = tk.StringVar(value="Moves: 0")
        self.time_var = tk.StringVar(value="Time: 0s")
        self.selection_var = tk.StringVar(value="Selected: none")

        self.hotspots: list[dict[str, Any]] = []
        self.selected: dict[str, Any] | None = None
        self.suit_order = ["S", "H", "D", "C"]
        self.texture_dir = self._resolve_texture_dir()
        self.card_textures: dict[str, tk.PhotoImage] = {}
        self._load_card_textures()
        self.back_texture = self._create_back_texture()
        self.column_left = [
            20 + index * (self.CARD_WIDTH + self.COL_GAP)
            for index in range(7)
        ]
        self.stock_left = 20
        self.waste_left = self.stock_left + self.CARD_WIDTH + self.COL_GAP
        self.foundation_left = [
            20 + (index + 3) * (self.CARD_WIDTH + self.COL_GAP)
            for index in range(4)
        ]

        self._build_widgets()
        self.refresh_board()
        self._tick_clock()

    def _build_widgets(self) -> None:
        """Create toolbar, visual board, and ranking table."""
        container = ttk.Frame(self.root, padding=10)
        container.pack(fill=tk.BOTH, expand=True)

        top_bar = ttk.Frame(container)
        top_bar.pack(fill=tk.X)

        ttk.Label(top_bar, text="Player").pack(side=tk.LEFT, padx=(0, 6))
        ttk.Entry(top_bar, textvariable=self.player_var, width=20).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(top_bar, text="New Game", command=self.start_new_game).pack(side=tk.LEFT, padx=3)
        ttk.Button(top_bar, text="Undo", command=self.undo_move).pack(side=tk.LEFT, padx=3)
        ttk.Button(top_bar, text="Redo", command=self.redo_move).pack(side=tk.LEFT, padx=3)
        ttk.Button(top_bar, text="Save Result", command=self.save_result).pack(side=tk.LEFT, padx=3)

        status_bar = ttk.Frame(container)
        status_bar.pack(fill=tk.X, pady=(8, 8))
        ttk.Label(status_bar, textvariable=self.score_var).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(status_bar, textvariable=self.moves_var).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(status_bar, textvariable=self.time_var).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(status_bar, textvariable=self.selection_var).pack(side=tk.LEFT, padx=(0, 10))

        message_bar = ttk.Frame(container)
        message_bar.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(message_bar, textvariable=self.status_var, foreground="#004f7a").pack(side=tk.LEFT)

        self.canvas = tk.Canvas(
            container,
            bg="#0f6d3b",
            highlightthickness=0,
            height=540,
        )
        self.canvas.pack(fill=tk.BOTH, expand=False)
        self.canvas.bind("<Button-1>", self.on_canvas_click)

        ttk.Label(
            container,
            text="How to play: Click Stock to draw. Then click a source pile/card and click a target pile.",
        ).pack(fill=tk.X, pady=(8, 4))

        rank_frame = ttk.LabelFrame(container, text="Ranking", padding=8)
        rank_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        columns_def = ("player", "score", "moves", "won", "elapsed")
        self.ranking_table = ttk.Treeview(rank_frame, columns=columns_def, show="headings", height=8)
        self.ranking_table.heading("player", text="Player")
        self.ranking_table.heading("score", text="Score")
        self.ranking_table.heading("moves", text="Moves")
        self.ranking_table.heading("won", text="Won")
        self.ranking_table.heading("elapsed", text="Seconds")
        self.ranking_table.column("player", width=220)
        self.ranking_table.column("score", width=100)
        self.ranking_table.column("moves", width=100)
        self.ranking_table.column("won", width=80)
        self.ranking_table.column("elapsed", width=120)
        self.ranking_table.pack(fill=tk.BOTH, expand=True)

        self.refresh_ranking_table(self.game.ranking_board.load_entries())

    def _set_status(self, text: str) -> None:
        """Show one status message under toolbar."""
        self.status_var.set(text)

    def _resolve_texture_dir(self) -> Path:
        """Return the texture directory path relative to project root."""
        return Path(__file__).resolve().parent.parent / "png"

    def _load_card_textures(self) -> None:
        """Load card face textures from the png directory when available."""
        if not self.texture_dir.exists():
            return

        loaded_keys: list[str] = []
        for image_path in sorted(self.texture_dir.glob("*.png")):
            key = image_path.stem.upper()
            try:
                original_texture = tk.PhotoImage(file=str(image_path))
            except tk.TclError:
                continue

            scale_x = max(1, (original_texture.width() + self.CARD_WIDTH - 1) // self.CARD_WIDTH)
            scale_y = max(1, (original_texture.height() + self.CARD_HEIGHT - 1) // self.CARD_HEIGHT)
            scale = max(scale_x, scale_y)
            texture = original_texture.subsample(scale, scale)

            self.card_textures[key] = texture
            loaded_keys.append(key)

        if loaded_keys:
            first_texture = self.card_textures[loaded_keys[0]]
            self.CARD_WIDTH = first_texture.width()
            self.CARD_HEIGHT = first_texture.height()

    def _create_back_texture(self) -> tk.PhotoImage:
        """Create a generated card-back texture for hidden cards."""
        image = tk.PhotoImage(width=self.CARD_WIDTH, height=self.CARD_HEIGHT)
        image.put("#1b4f91", to=(0, 0, self.CARD_WIDTH, self.CARD_HEIGHT))

        border = 4
        image.put(
            "#f0f6ff",
            to=(border, border, self.CARD_WIDTH - border, self.CARD_HEIGHT - border),
        )
        image.put(
            "#2a67b6",
            to=(border + 3, border + 3, self.CARD_WIDTH - border - 3, self.CARD_HEIGHT - border - 3),
        )

        stripe_step = 8
        for x_pos in range(border + 5, self.CARD_WIDTH - border - 3, stripe_step):
            image.put("#99c4ff", to=(x_pos, border + 5, x_pos + 2, self.CARD_HEIGHT - border - 3))
        return image

    def _rank_to_texture(self, rank: int) -> str:
        """Convert numeric rank to file naming token."""
        rank_map = {1: "A", 11: "J", 12: "Q", 13: "K"}
        return rank_map.get(rank, str(rank))

    def _card_texture_key(self, card: Any) -> str:
        """Build one texture key like SA or D10 for a card object."""
        return f"{card.suit}{self._rank_to_texture(card.rank)}"

    def _suit_color(self, suit: str) -> str:
        """Return text color for one suit."""
        return "#b10000" if suit in {"H", "D"} else "#111111"

    def _card_text(self, card: Any) -> str:
        """Return printable short text for a card."""
        return card.to_symbol()

    def _hit_test(self, x: int, y: int) -> dict[str, Any] | None:
        """Return the topmost hotspot at cursor position."""
        for hotspot in reversed(self.hotspots):
            left, top, right, bottom = hotspot["bbox"]
            if left <= x <= right and top <= y <= bottom:
                return hotspot
        return None

    def _is_selected(self, target: dict[str, Any]) -> bool:
        """Return True when a hotspot corresponds to current selected source."""
        if self.selected is None:
            return False
        selected_type = self.selected["type"]
        target_type = target["type"]
        if selected_type == "waste" and target_type == "waste":
            return True
        if selected_type == "foundation" and target_type == "foundation":
            return self.selected["suit"] == target["suit"]
        if selected_type == "tableau" and target_type == "tableau_card":
            return (
                self.selected["column"] == target["column"]
                and self.selected["start_index"] == target["start_index"]
            )
        return False

    def _draw_card(
        self,
        left: int,
        top: int,
        card: Any | None,
        is_back: bool,
        is_selected: bool,
    ) -> None:
        """Draw one card using texture when available with fallback style."""
        right = left + self.CARD_WIDTH
        bottom = top + self.CARD_HEIGHT

        texture = None
        if is_back:
            texture = self.back_texture
        elif card is not None:
            texture = self.card_textures.get(self._card_texture_key(card))

        if texture is not None:
            self.canvas.create_image(left, top, image=texture, anchor=tk.NW)
        else:
            fill = "#2b579a" if is_back else "#fefefe"
            self.canvas.create_rectangle(left, top, right, bottom, fill=fill, outline="#1d1d1d", width=2)
            if is_back:
                self.canvas.create_text(
                    left + self.CARD_WIDTH // 2,
                    top + self.CARD_HEIGHT // 2,
                    text="KL",
                    fill="#ffffff",
                    font=("Consolas", 16, "bold"),
                )
            elif card is not None:
                text = self._card_text(card)
                text_color = self._suit_color(card.suit)
                self.canvas.create_text(
                    left + 12,
                    top + 12,
                    anchor=tk.NW,
                    text=text,
                    fill=text_color,
                    font=("Consolas", 12, "bold"),
                )
                self.canvas.create_text(
                    left + self.CARD_WIDTH - 12,
                    top + self.CARD_HEIGHT - 12,
                    anchor=tk.SE,
                    text=text,
                    fill=text_color,
                    font=("Consolas", 12, "bold"),
                )

        if is_selected:
            self.canvas.create_rectangle(left, top, right, bottom, outline="#ffd84d", width=3)

    def _draw_placeholder(self, left: int, top: int, label: str) -> None:
        """Draw an empty pile placeholder with label."""
        right = left + self.CARD_WIDTH
        bottom = top + self.CARD_HEIGHT
        self.canvas.create_rectangle(
            left,
            top,
            right,
            bottom,
            fill="#0d5d34",
            outline="#98d4b4",
            width=2,
            dash=(6, 4),
        )
        self.canvas.create_text(
            left + self.CARD_WIDTH // 2,
            top + self.CARD_HEIGHT // 2,
            text=label,
            fill="#d8f8e7",
            font=("Consolas", 12, "bold"),
        )

    def _clear_selection(self) -> None:
        """Clear current source selection."""
        self.selected = None
        self.selection_var.set("Selected: none")

    def _select_waste(self) -> None:
        """Select waste top card as move source."""
        self.selected = {"type": "waste"}
        self.selection_var.set("Selected: waste")

    def _select_foundation(self, suit: str) -> None:
        """Select one foundation top card as move source."""
        self.selected = {"type": "foundation", "suit": suit}
        self.selection_var.set(f"Selected: foundation {suit}")

    def _select_tableau(self, column: int, start_index: int) -> None:
        """Select a tableau sub-pile as move source."""
        visible_count = len(self.game.tableau[column].visible_cards())
        count = visible_count - start_index
        self.selected = {
            "type": "tableau",
            "column": column,
            "start_index": start_index,
            "count": count,
        }
        self.selection_var.set(f"Selected: tableau {column + 1}, cards {count}")

    def _foundation_target_from_click(self, suit: str) -> bool:
        """Attempt moving selected source to one foundation."""
        if self.selected is None:
            self._set_status("Choose a source card first")
            return False
        if self.selected["type"] == "waste":
            return self.game.move_waste_to_foundation(suit)
        if self.selected["type"] == "tableau":
            if self.selected["count"] != 1:
                return False
            source_column = self.selected["column"]
            top_card = self.game.tableau[source_column].top_visible()
            if top_card is None or top_card.suit != suit:
                return False
            return self.game.move_tableau_to_foundation(source_column)
        return False

    def _tableau_target_from_click(self, column: int) -> bool:
        """Attempt moving selected source to one tableau column."""
        if self.selected is None:
            self._set_status("Choose a source card first")
            return False
        if self.selected["type"] == "waste":
            return self.game.move_waste_to_tableau(column)
        if self.selected["type"] == "foundation":
            suit = self.selected["suit"]
            return self.game.move_foundation_to_tableau(suit, column)
        if self.selected["type"] == "tableau":
            source_column = self.selected["column"]
            count = self.selected["count"]
            return self.game.move_tableau_to_tableau(source_column, column, count)
        return False

    def on_canvas_click(self, event: tk.Event[Any]) -> None:
        """Handle click interactions on the visual board."""
        hotspot = self._hit_test(event.x, event.y)
        if hotspot is None:
            self._clear_selection()
            self.refresh_board()
            return

        kind = hotspot["type"]
        if kind == "stock":
            success = self.game.draw_from_stock()
            self._set_status("Draw success" if success else "No card available")
            self._clear_selection()
            self.refresh_board()
            return

        if kind == "waste":
            if self.game.waste.is_empty():
                self._set_status("Waste is empty")
                return
            if self.selected is not None and self.selected.get("type") == "waste":
                self._clear_selection()
            else:
                self._select_waste()
            self.refresh_board()
            return

        if kind == "foundation":
            suit = hotspot["suit"]
            if self.selected is None:
                if self.game.foundations[suit].is_empty():
                    self._set_status("Foundation is empty")
                    return
                self._select_foundation(suit)
                self.refresh_board()
                return
            success = self._foundation_target_from_click(suit)
            self._set_status("Move success" if success else "Invalid move")
            self._clear_selection()
            self.refresh_board()
            return

        if kind == "tableau_card":
            column = hotspot["column"]
            start_index = hotspot["start_index"]
            if self.selected is None:
                self._select_tableau(column, start_index)
                self.refresh_board()
                return
            if (
                self.selected["type"] == "tableau"
                and self.selected["column"] == column
                and self.selected["start_index"] == start_index
            ):
                self._clear_selection()
                self.refresh_board()
                return
            success = self._tableau_target_from_click(column)
            self._set_status("Move success" if success else "Invalid move")
            self._clear_selection()
            self.refresh_board()
            return

        if kind == "tableau_column":
            column = hotspot["column"]
            if self.selected is None:
                self._set_status("Choose a source card first")
                return
            success = self._tableau_target_from_click(column)
            self._set_status("Move success" if success else "Invalid move")
            self._clear_selection()
            self.refresh_board()

    def _draw_top_piles(self) -> None:
        """Draw stock, waste, and foundation piles."""
        self.hotspots.append(
            {
                "type": "stock",
                "bbox": (
                    self.stock_left,
                    self.TOP_Y,
                    self.stock_left + self.CARD_WIDTH,
                    self.TOP_Y + self.CARD_HEIGHT,
                ),
            }
        )
        if self.game.stock.is_empty():
            self._draw_placeholder(self.stock_left, self.TOP_Y, "STOCK")
        else:
            self._draw_card(
                left=self.stock_left,
                top=self.TOP_Y,
                card=None,
                is_back=True,
                is_selected=False,
            )

        waste_selected = self.selected is not None and self.selected.get("type") == "waste"
        self.hotspots.append(
            {
                "type": "waste",
                "bbox": (
                    self.waste_left,
                    self.TOP_Y,
                    self.waste_left + self.CARD_WIDTH,
                    self.TOP_Y + self.CARD_HEIGHT,
                ),
            }
        )
        if self.game.waste.is_empty():
            self._draw_placeholder(self.waste_left, self.TOP_Y, "WASTE")
        else:
            card = self.game.waste.peek()
            self._draw_card(
                left=self.waste_left,
                top=self.TOP_Y,
                card=card,
                is_back=False,
                is_selected=waste_selected,
            )

        for index, suit in enumerate(self.suit_order):
            left = self.foundation_left[index]
            foundation = self.game.foundations[suit]
            selected = self.selected is not None and self.selected.get("type") == "foundation" and self.selected.get("suit") == suit
            self.hotspots.append(
                {
                    "type": "foundation",
                    "suit": suit,
                    "bbox": (
                        left,
                        self.TOP_Y,
                        left + self.CARD_WIDTH,
                        self.TOP_Y + self.CARD_HEIGHT,
                    ),
                }
            )
            if foundation.is_empty():
                self._draw_placeholder(left, self.TOP_Y, f"F-{suit}")
            else:
                card = foundation.peek()
                self._draw_card(
                    left=left,
                    top=self.TOP_Y,
                    card=card,
                    is_back=False,
                    is_selected=selected,
                )

    def _draw_tableau(self) -> None:
        """Draw seven tableau columns with hidden and visible cards."""
        for column_index in range(7):
            left = self.column_left[column_index]
            column = self.game.tableau[column_index]
            hidden_cards = column.face_down.to_list()
            visible_cards = column.visible_cards()

            self.canvas.create_text(
                left,
                self.TABLEAU_Y - 20,
                anchor=tk.NW,
                text=f"T{column_index + 1}",
                fill="#e8fff3",
                font=("Consolas", 11, "bold"),
            )

            column_bottom = self.TABLEAU_Y + self.CARD_HEIGHT
            down_count = len(hidden_cards)
            for down_index in range(down_count):
                top = self.TABLEAU_Y + down_index * self.DOWN_STEP
                self._draw_card(
                    left=left,
                    top=top,
                    card=None,
                    is_back=True,
                    is_selected=False,
                )
                column_bottom = max(column_bottom, top + self.CARD_HEIGHT)

            up_start = self.TABLEAU_Y + down_count * self.DOWN_STEP
            if not visible_cards and down_count == 0:
                self._draw_placeholder(left, self.TABLEAU_Y, "TABLEAU")

            for visible_index, card in enumerate(visible_cards):
                top = up_start + visible_index * self.UP_STEP
                is_selected = self._is_selected(
                    {
                        "type": "tableau_card",
                        "column": column_index,
                        "start_index": visible_index,
                    }
                )
                self._draw_card(
                    left=left,
                    top=top,
                    card=card,
                    is_back=False,
                    is_selected=is_selected,
                )
                self.hotspots.append(
                    {
                        "type": "tableau_card",
                        "column": column_index,
                        "start_index": visible_index,
                        "bbox": (left, top, left + self.CARD_WIDTH, top + self.CARD_HEIGHT),
                    }
                )
                column_bottom = max(column_bottom, top + self.CARD_HEIGHT)

            self.hotspots.append(
                {
                    "type": "tableau_column",
                    "column": column_index,
                    "bbox": (left, self.TABLEAU_Y, left + self.CARD_WIDTH, column_bottom),
                }
            )

    def _tick_clock(self) -> None:
        """Refresh elapsed timer periodically."""
        self.time_var.set(f"Time: {self.game.elapsed_seconds()}s")
        self.root.after(1000, self._tick_clock)

    def refresh_board(self) -> None:
        """Redraw entire visual board based on current state."""
        self.score_var.set(f"Score: {self.game.score}")
        self.moves_var.set(f"Moves: {self.game.moves}")

        self.canvas.delete("all")
        self.hotspots.clear()
        self._draw_top_piles()
        self._draw_tableau()

        if self.game.is_won():
            self._set_status("You won. Save result to ranking.")

    def refresh_ranking_table(self, entries: list[dict[str, Any]]) -> None:
        """Render ranking rows into the table."""
        for row in self.ranking_table.get_children():
            self.ranking_table.delete(row)

        ordered = self.game.ranking_board.sorted_entries(entries)
        for entry in ordered:
            self.ranking_table.insert(
                "",
                tk.END,
                values=(
                    entry.get("player", "Unknown"),
                    entry.get("score", 0),
                    entry.get("moves", 0),
                    "Yes" if entry.get("won") else "No",
                    entry.get("elapsed_seconds", 0),
                ),
            )

    def start_new_game(self) -> None:
        """Start a fresh game and apply player name from input."""
        self.game.set_player_name(self.player_var.get())
        self.game.new_game()
        self._clear_selection()
        self._set_status("Started a new game")
        self.refresh_board()

    def undo_move(self) -> None:
        """Undo one previous move if history exists."""
        success = self.game.undo()
        self._clear_selection()
        self._set_status("Undo success" if success else "Nothing to undo")
        self.refresh_board()

    def redo_move(self) -> None:
        """Redo one previously undone move if history exists."""
        success = self.game.redo()
        self._clear_selection()
        self._set_status("Redo success" if success else "Nothing to redo")
        self.refresh_board()

    def save_result(self) -> None:
        """Save current score into ranking and refresh ranking table."""
        self.game.set_player_name(self.player_var.get())
        entries = self.game.finalize_result()
        self.refresh_ranking_table(entries)
        won_text = "won" if self.game.is_won() else "not won"
        self._set_status(f"Saved result ({won_text})")
        messagebox.showinfo("Ranking", "Result saved to ranking table")


def run_app() -> None:
    """Create Tk root and run the Klondike GUI main loop."""
    root = tk.Tk()
    KlondikeApp(root)
    root.mainloop()
