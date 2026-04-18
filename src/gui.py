"""Tkinter user interface for Klondike Solitaire."""

from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from .game import KlondikeGame


class KlondikeApp:
    """Render and control a visual Klondike board."""

    CARD_WIDTH = 88
    CARD_HEIGHT = 124
    TOP_Y = 18
    TABLEAU_Y = 190
    COL_GAP = 28
    DOWN_STEP = 18
    UP_STEP = 30
    DRAG_THRESHOLD = 4

    def __init__(self, root: tk.Tk) -> None:
        """Create game model, widgets, and initial board rendering."""
        self.root = root
        self.root.title("Klondike Solitaire - Python")
        self.root.geometry("1060x860")
        self.root.minsize(1000, 780)
        self.game = KlondikeGame()

        self.player_var = tk.StringVar(value="Player")
        self.status_var = tk.StringVar(value="Click stock to draw, then drag source to target")
        self.score_var = tk.StringVar(value="Score: 0")
        self.moves_var = tk.StringVar(value="Moves: 0")
        self.time_var = tk.StringVar(value="Time: 0s")
        self.selection_var = tk.StringVar(value="Selected: none")

        self.hotspots: list[dict[str, Any]] = []
        self.selected: dict[str, Any] | None = None
        self.drag_source: dict[str, Any] | None = None
        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.drag_preview_id: int | None = None

        self.suit_order = ["S", "H", "D", "C"]
        self.board_padding_x = 20
        self.texture_dir = self._resolve_texture_dir()
        self.card_textures: dict[str, tk.PhotoImage] = {}
        self._load_card_textures()
        self.back_texture = self._create_back_texture()

        self.column_left = [0 for _ in range(7)]
        self.stock_left = 0
        self.waste_left = 0
        self.foundation_left = [0 for _ in range(4)]

        self._build_widgets()
        self.refresh_board()
        self._tick_clock()

    def _build_widgets(self) -> None:
        """Create toolbar, canvas board, and ranking table."""
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

        self.canvas = tk.Canvas(container, bg="#0f6d3b", highlightthickness=0, height=540)
        self.canvas.pack(fill=tk.BOTH, expand=False)
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<Configure>", self.on_canvas_resize)

        ttk.Label(
            container,
            text="How to play: Click Stock to draw. Drag a card/pile and drop exactly on a target slot.",
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
        """Set one short message in the status bar."""
        self.status_var.set(text)

    def _recalculate_layout(self) -> None:
        """Recompute centered x positions based on current canvas width."""
        canvas_width = max(int(self.canvas.winfo_width()), 960)
        usable_width = max(canvas_width - 2 * self.board_padding_x, self.CARD_WIDTH * 7)
        dynamic_gap = (usable_width - self.CARD_WIDTH * 7) // 6
        self.COL_GAP = max(14, min(40, dynamic_gap))
        total_board_width = self.CARD_WIDTH * 7 + self.COL_GAP * 6
        start_x = max((canvas_width - total_board_width) // 2, self.board_padding_x)

        self.column_left = [start_x + index * (self.CARD_WIDTH + self.COL_GAP) for index in range(7)]
        self.stock_left = self.column_left[0]
        self.waste_left = self.column_left[1]
        self.foundation_left = [self.column_left[3 + index] for index in range(4)]

    def on_canvas_resize(self, _event: tk.Event[Any]) -> None:
        """Refresh board when canvas geometry changes."""
        self.refresh_board()

    def _resolve_texture_dir(self) -> Path:
        """Return absolute path of texture directory."""
        return Path(__file__).resolve().parent.parent / "png"

    def _load_card_textures(self) -> None:
        """Load card textures from png directory when files are available."""
        if not self.texture_dir.exists():
            return

        loaded_keys: list[str] = []
        for image_path in sorted(self.texture_dir.glob("*.png")):
            key = image_path.stem.upper()
            try:
                original = tk.PhotoImage(file=str(image_path))
            except tk.TclError:
                continue

            scale_x = max(1, (original.width() + self.CARD_WIDTH - 1) // self.CARD_WIDTH)
            scale_y = max(1, (original.height() + self.CARD_HEIGHT - 1) // self.CARD_HEIGHT)
            scale = max(scale_x, scale_y)
            self.card_textures[key] = original.subsample(scale, scale)
            loaded_keys.append(key)

        if loaded_keys:
            first = self.card_textures[loaded_keys[0]]
            self.CARD_WIDTH = first.width()
            self.CARD_HEIGHT = first.height()
            self.DOWN_STEP = max(14, self.CARD_HEIGHT // 6)
            self.UP_STEP = max(24, self.CARD_HEIGHT // 3)

    def _create_back_texture(self) -> tk.PhotoImage:
        """Create a generated back texture for hidden cards."""
        image = tk.PhotoImage(width=self.CARD_WIDTH, height=self.CARD_HEIGHT)
        image.put("#1b4f91", to=(0, 0, self.CARD_WIDTH, self.CARD_HEIGHT))
        border = 4
        image.put("#f0f6ff", to=(border, border, self.CARD_WIDTH - border, self.CARD_HEIGHT - border))
        image.put(
            "#2a67b6",
            to=(border + 3, border + 3, self.CARD_WIDTH - border - 3, self.CARD_HEIGHT - border - 3),
        )
        for x_pos in range(border + 5, self.CARD_WIDTH - border - 3, 8):
            image.put("#99c4ff", to=(x_pos, border + 5, x_pos + 2, self.CARD_HEIGHT - border - 3))
        return image

    def _rank_to_texture(self, rank: int) -> str:
        """Convert rank number to texture suffix token."""
        rank_map = {1: "A", 11: "J", 12: "Q", 13: "K"}
        return rank_map.get(rank, str(rank))

    def _card_texture_key(self, card: Any) -> str:
        """Return texture key for one card from suit and rank."""
        return f"{card.suit}{self._rank_to_texture(card.rank)}"

    def _hit_test(self, x: int, y: int) -> dict[str, Any] | None:
        """Return topmost hotspot containing pointer coordinates."""
        for hotspot in reversed(self.hotspots):
            left, top, right, bottom = hotspot["bbox"]
            if left <= x <= right and top <= y <= bottom:
                return hotspot
        return None

    def _is_selected(self, target: dict[str, Any]) -> bool:
        """Return True when target represents the currently selected source."""
        if self.selected is None:
            return False
        selected_type = self.selected["type"]
        target_type = target["type"]
        if selected_type == "waste" and target_type == "waste":
            return True
        if selected_type == "foundation" and target_type == "foundation":
            return self.selected["suit"] == target["suit"]
        if selected_type == "tableau" and target_type == "tableau_card":
            return self.selected["column"] == target["column"] and self.selected["start_index"] == target["start_index"]
        return False

    def _draw_card(self, left: int, top: int, card: Any | None, is_back: bool, is_selected: bool) -> None:
        """Draw one card image with fallback style and selected border."""
        right = left + self.CARD_WIDTH
        bottom = top + self.CARD_HEIGHT

        texture = self.back_texture if is_back else None
        if not is_back and card is not None:
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

        if is_selected:
            self.canvas.create_rectangle(left, top, right, bottom, outline="#ffd84d", width=3)

    def _draw_placeholder(self, left: int, top: int, label: str) -> None:
        """Draw one dashed empty-slot placeholder."""
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
        """Clear source selection marker."""
        self.selected = None
        self.selection_var.set("Selected: none")

    def _clear_drag_state(self) -> None:
        """Clear drag state and remove preview marker if present."""
        self.drag_source = None
        self.dragging = False
        if self.drag_preview_id is not None:
            self.canvas.delete(self.drag_preview_id)
            self.drag_preview_id = None

    def _select_waste(self) -> None:
        """Select waste as move source."""
        self.selected = {"type": "waste"}
        self.selection_var.set("Selected: waste")

    def _select_foundation(self, suit: str) -> None:
        """Select foundation suit as move source."""
        self.selected = {"type": "foundation", "suit": suit}
        self.selection_var.set(f"Selected: foundation {suit}")

    def _select_tableau(self, column: int, start_index: int) -> None:
        """Select one tableau sub-pile as source."""
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
        """Attempt click-based move from selected source to foundation suit."""
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
        """Attempt click-based move from selected source to tableau column."""
        if self.selected is None:
            self._set_status("Choose a source card first")
            return False
        if self.selected["type"] == "waste":
            return self.game.move_waste_to_tableau(column)
        if self.selected["type"] == "foundation":
            return self.game.move_foundation_to_tableau(self.selected["suit"], column)
        if self.selected["type"] == "tableau":
            source_column = self.selected["column"]
            count = self.selected["count"]
            return self.game.move_tableau_to_tableau(source_column, column, count)
        return False

    def _source_from_hotspot(self, hotspot: dict[str, Any]) -> dict[str, Any] | None:
        """Convert hotspot under pointer into a move source descriptor."""
        kind = hotspot["type"]
        if kind == "waste":
            if self.game.waste.is_empty():
                return None
            return {"type": "waste"}
        if kind == "foundation":
            suit = hotspot["suit"]
            if self.game.foundations[suit].is_empty():
                return None
            return {"type": "foundation", "suit": suit}
        if kind == "tableau_card":
            column = hotspot["column"]
            start_index = hotspot["start_index"]
            visible_count = len(self.game.tableau[column].visible_cards())
            return {
                "type": "tableau",
                "column": column,
                "start_index": start_index,
                "count": visible_count - start_index,
            }
        return None

    def _same_source_target(self, source: dict[str, Any], hotspot: dict[str, Any]) -> bool:
        """Return True when drop target is the same pile as source."""
        source_type = source["type"]
        target_type = hotspot["type"]
        if source_type == "waste":
            return target_type == "waste"
        if source_type == "foundation":
            return target_type == "foundation" and source["suit"] == hotspot.get("suit")
        if source_type == "tableau":
            return target_type in {"tableau_card", "tableau_column"} and source["column"] == hotspot.get("column")
        return False

    def _move_from_source_to_hotspot(self, source: dict[str, Any], hotspot: dict[str, Any] | None) -> bool:
        """Attempt one drag-drop move from source descriptor to hotspot."""
        if hotspot is None:
            return False

        source_type = source["type"]
        target_type = hotspot["type"]

        if source_type == "waste":
            if target_type == "foundation":
                return self.game.move_waste_to_foundation(hotspot["suit"])
            if target_type in {"tableau_card", "tableau_column"}:
                return self.game.move_waste_to_tableau(hotspot["column"])
            return False

        if source_type == "foundation":
            if target_type in {"tableau_card", "tableau_column"}:
                return self.game.move_foundation_to_tableau(source["suit"], hotspot["column"])
            return False

        if source_type == "tableau":
            if target_type == "foundation":
                if source["count"] != 1:
                    return False
                source_column = source["column"]
                top_card = self.game.tableau[source_column].top_visible()
                if top_card is None or top_card.suit != hotspot["suit"]:
                    return False
                return self.game.move_tableau_to_foundation(source_column)
            if target_type in {"tableau_card", "tableau_column"}:
                return self.game.move_tableau_to_tableau(source["column"], hotspot["column"], source["count"])
            return False

        return False

    def _set_selection_from_source(self, source: dict[str, Any] | None) -> None:
        """Update UI selection state from a source descriptor."""
        if source is None:
            self._clear_selection()
            return
        if source["type"] == "waste":
            self._select_waste()
            return
        if source["type"] == "foundation":
            self._select_foundation(source["suit"])
            return
        self._select_tableau(source["column"], source["start_index"])

    def _handle_click_hotspot(self, hotspot: dict[str, Any] | None) -> None:
        """Handle non-drag click interactions for source selection and moves."""
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
            if self.selected is None:
                self._set_status("Choose a source card first")
                return
            success = self._tableau_target_from_click(hotspot["column"])
            self._set_status("Move success" if success else "Invalid move")
            self._clear_selection()
            self.refresh_board()

    def on_canvas_press(self, event: tk.Event[Any]) -> None:
        """Record drag start and source candidate on mouse press."""
        hotspot = self._hit_test(event.x, event.y)
        self.drag_start_x = int(event.x)
        self.drag_start_y = int(event.y)
        self.dragging = False
        self.drag_source = self._source_from_hotspot(hotspot) if hotspot is not None else None

    def on_canvas_drag(self, event: tk.Event[Any]) -> None:
        """Update drag visuals when pointer movement crosses drag threshold."""
        if self.drag_source is None:
            return

        moved_x = abs(int(event.x) - self.drag_start_x)
        moved_y = abs(int(event.y) - self.drag_start_y)
        if moved_x < self.DRAG_THRESHOLD and moved_y < self.DRAG_THRESHOLD and not self.dragging:
            return

        self.dragging = True
        self._set_selection_from_source(self.drag_source)
        self.refresh_board()

        if self.drag_preview_id is not None:
            self.canvas.delete(self.drag_preview_id)
        self.drag_preview_id = self.canvas.create_oval(
            int(event.x) - 8,
            int(event.y) - 8,
            int(event.x) + 8,
            int(event.y) + 8,
            outline="#ffd84d",
            width=2,
        )

    def on_canvas_release(self, event: tk.Event[Any]) -> None:
        """Finalize drag-drop move or fallback to click behavior on release."""
        release_hotspot = self._hit_test(event.x, event.y)

        if self.drag_source is not None:
            if release_hotspot is not None and not self._same_source_target(self.drag_source, release_hotspot):
                success = self._move_from_source_to_hotspot(self.drag_source, release_hotspot)
                self._set_status("Move success" if success else "Invalid move")
                self._clear_selection()
                self._clear_drag_state()
                self.refresh_board()
                return

        self._clear_drag_state()
        self._handle_click_hotspot(release_hotspot)

    def _draw_top_piles(self) -> None:
        """Draw stock, waste, and foundation piles on top row."""
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
            self._draw_card(self.stock_left, self.TOP_Y, None, is_back=True, is_selected=False)

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
            self._draw_card(self.waste_left, self.TOP_Y, self.game.waste.peek(), is_back=False, is_selected=waste_selected)

        for index, suit in enumerate(self.suit_order):
            left = self.foundation_left[index]
            selected = self.selected is not None and self.selected.get("type") == "foundation" and self.selected.get("suit") == suit
            self.canvas.create_text(
                left + self.CARD_WIDTH // 2,
                self.TOP_Y - 8,
                text=f"F-{suit}",
                fill="#e8fff3",
                font=("Consolas", 10, "bold"),
            )
            self.hotspots.append(
                {
                    "type": "foundation",
                    "suit": suit,
                    "bbox": (left, self.TOP_Y, left + self.CARD_WIDTH, self.TOP_Y + self.CARD_HEIGHT),
                }
            )
            foundation = self.game.foundations[suit]
            if foundation.is_empty():
                self._draw_placeholder(left, self.TOP_Y, f"F-{suit}")
            else:
                self._draw_card(left, self.TOP_Y, foundation.peek(), is_back=False, is_selected=selected)

    def _draw_tableau(self) -> None:
        """Draw all tableau columns with hidden and visible card stacks."""
        for column_index in range(7):
            left = self.column_left[column_index]
            column = self.game.tableau[column_index]
            hidden_cards = column.face_down.to_list()
            visible_cards = column.visible_cards()

            self.hotspots.append(
                {
                    "type": "tableau_column",
                    "column": column_index,
                    "bbox": (
                        left,
                        self.TABLEAU_Y,
                        left + self.CARD_WIDTH,
                        self.TABLEAU_Y + self.CARD_HEIGHT + self.UP_STEP * max(len(visible_cards), 1),
                    ),
                }
            )

            self.canvas.create_text(
                left,
                self.TABLEAU_Y - 20,
                anchor=tk.NW,
                text=f"T{column_index + 1}",
                fill="#e8fff3",
                font=("Consolas", 11, "bold"),
            )

            down_count = len(hidden_cards)
            for down_index in range(down_count):
                top = self.TABLEAU_Y + down_index * self.DOWN_STEP
                self._draw_card(left, top, None, is_back=True, is_selected=False)

            up_start = self.TABLEAU_Y + down_count * self.DOWN_STEP
            if not visible_cards and down_count == 0:
                self._draw_placeholder(left, self.TABLEAU_Y, "TABLEAU")

            for visible_index, card in enumerate(visible_cards):
                top = up_start + visible_index * self.UP_STEP
                is_selected = self._is_selected(
                    {"type": "tableau_card", "column": column_index, "start_index": visible_index}
                )
                self._draw_card(left, top, card, is_back=False, is_selected=is_selected)
                self.hotspots.append(
                    {
                        "type": "tableau_card",
                        "column": column_index,
                        "start_index": visible_index,
                        "bbox": (left, top, left + self.CARD_WIDTH, top + self.CARD_HEIGHT),
                    }
                )

    def _tick_clock(self) -> None:
        """Update elapsed-time label every second."""
        self.time_var.set(f"Time: {self.game.elapsed_seconds()}s")
        self.root.after(1000, self._tick_clock)

    def refresh_board(self) -> None:
        """Redraw board and counters from current game state."""
        self.score_var.set(f"Score: {self.game.score}")
        self.moves_var.set(f"Moves: {self.game.moves}")

        self._recalculate_layout()
        self.canvas.delete("all")
        self.hotspots.clear()
        self._draw_top_piles()
        self._draw_tableau()

        if self.game.is_won():
            self._set_status("You won. Save result to ranking.")

    def refresh_ranking_table(self, entries: list[dict[str, Any]]) -> None:
        """Render sorted ranking entries into the leaderboard table."""
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
        """Start a fresh game and apply current player name."""
        self.game.set_player_name(self.player_var.get())
        self.game.new_game()
        self._clear_selection()
        self._set_status("Started a new game")
        self.refresh_board()

    def undo_move(self) -> None:
        """Undo last move when history is available."""
        success = self.game.undo()
        self._clear_selection()
        self._set_status("Undo success" if success else "Nothing to undo")
        self.refresh_board()

    def redo_move(self) -> None:
        """Redo previously undone move when available."""
        success = self.game.redo()
        self._clear_selection()
        self._set_status("Redo success" if success else "Nothing to redo")
        self.refresh_board()

    def save_result(self) -> None:
        """Save current run into ranking and refresh the table."""
        self.game.set_player_name(self.player_var.get())
        entries = self.game.finalize_result()
        self.refresh_ranking_table(entries)
        won_text = "won" if self.game.is_won() else "not won"
        self._set_status(f"Saved result ({won_text})")
        messagebox.showinfo("Ranking", "Result saved to ranking table")


def run_app() -> None:
    """Create root window and run the Tkinter main loop."""
    root = tk.Tk()
    KlondikeApp(root)
    root.mainloop()
