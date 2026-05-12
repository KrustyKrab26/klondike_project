"""DearPyGui user interface for Klondike Solitaire."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import dearpygui.dearpygui as dpg

from .game import KlondikeGame


Color = tuple[int, int, int, int]


class KlondikeApp:
    """Render and control a visual Klondike board with DearPyGui."""

    BASE_CARD_WIDTH = 108
    BASE_CARD_HEIGHT = 150
    MIN_CARD_WIDTH = 70
    MAX_CARD_WIDTH = 158
    CARD_WIDTH = BASE_CARD_WIDTH
    CARD_HEIGHT = BASE_CARD_HEIGHT
    TOP_Y = 24
    TABLEAU_Y = 198
    TOP_TO_TABLEAU_GAP = 50
    COL_GAP = 30
    DOWN_STEP = 18
    UP_STEP = 32
    DRAG_THRESHOLD = 4

    BOARD_BG: Color = (18, 103, 60, 255)
    BOARD_BG_ALT: Color = (13, 84, 50, 255)
    CARD_BORDER: Color = (18, 24, 28, 255)
    TEXT_LIGHT: Color = (235, 246, 241, 255)
    TEXT_MUTED: Color = (172, 205, 190, 255)
    ACCENT: Color = (244, 191, 80, 255)
    ERROR: Color = (238, 104, 89, 255)
    MIN_BOARD_WIDTH = 720
    MIN_BOARD_HEIGHT = 360

    def __init__(self) -> None:
        """Create game model, DearPyGui widgets, and initial board rendering."""
        self.game = KlondikeGame()
        self.fullscreen_enabled = False
        self.ranking_visible = True

        self.hotspots: list[dict[str, Any]] = []
        self.selected: dict[str, Any] | None = None
        self.drag_source: dict[str, Any] | None = None
        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.drag_current_x = 0
        self.drag_current_y = 0
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.drop_hotspot: dict[str, Any] | None = None
        self.mouse_pressed_on_board = False
        self.previous_left_mouse_down = False

        self.board_padding_x = 24
        self.board_width = 1060
        self.board_height = 600
        self.ranking_height = 230
        self.last_client_size = (0, 0)
        self.last_clock_second = -1

        self.texture_dir = self._resolve_texture_dir()
        self.card_textures: dict[str, str] = {}
        self.back_texture: str | None = None
        self.back_uv_min: tuple[float, float] = (0.0, 0.0)
        self.back_uv_max: tuple[float, float] = (1.0, 1.0)

        self.main_window_tag = "main_window"
        self.board_tag = "board_drawlist"
        self.player_tag = "player_input"
        self.status_tag = "status_text"
        self.score_tag = "score_text"
        self.moves_tag = "moves_text"
        self.time_tag = "time_text"
        self.selection_tag = "selection_text"
        self.ranking_holder_tag = "ranking_holder"
        self.ranking_table_tag = "ranking_table"
        self.ranking_toggle_tag = "ranking_toggle"
        self.modal_tag = "message_modal"

        self.default_font: int | str | None = None
        self.bold_font: int | str | None = None
        self.large_font: int | str | None = None

        self.column_left = [0 for _ in range(7)]
        self.stock_left = 0
        self.waste_left = 0
        self.foundation_left = [0 for _ in range(4)]
        self.top_row_y = self.TOP_Y
        self.tableau_row_y = self.TABLEAU_Y

        self._build_fonts()
        self._build_theme()
        self._load_card_textures()
        self._build_widgets()
        self._build_handlers()
        self.refresh_ranking_table(self.game.ranking_board.load_entries())
        self.refresh_board()
        self._tick_clock(force=True)

    def _build_fonts(self) -> None:
        """Load readable Windows fonts when available."""
        font_dir = Path("C:/Windows/Fonts")
        regular_path = font_dir / "segoeui.ttf"
        bold_path = font_dir / "segoeuib.ttf"

        with dpg.font_registry():
            if regular_path.exists():
                self.default_font = dpg.add_font(str(regular_path), 18)
                self.large_font = dpg.add_font(str(regular_path), 24)
            if bold_path.exists():
                self.bold_font = dpg.add_font(str(bold_path), 18)

        if self.default_font is not None:
            dpg.bind_font(self.default_font)

    def _build_theme(self) -> None:
        """Apply a quiet casino-table theme with strong contrast."""
        with dpg.theme() as theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (28, 31, 34, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (34, 38, 40, 255))
                dpg.add_theme_color(dpg.mvThemeCol_PopupBg, (34, 38, 40, 250))
                dpg.add_theme_color(dpg.mvThemeCol_Text, (238, 241, 238, 255))
                dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, (150, 159, 154, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Button, (49, 81, 78, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (64, 103, 98, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (82, 129, 120, 255))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (44, 50, 51, 255))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (55, 66, 66, 255))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, (73, 89, 86, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Header, (61, 90, 84, 255))
                dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, (75, 111, 103, 255))
                dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, (91, 132, 122, 255))
                dpg.add_theme_color(dpg.mvThemeCol_TableHeaderBg, (48, 61, 60, 255))
                dpg.add_theme_color(dpg.mvThemeCol_TableRowBg, (34, 38, 40, 255))
                dpg.add_theme_color(dpg.mvThemeCol_TableRowBgAlt, (39, 45, 46, 255))
                dpg.add_theme_color(dpg.mvThemeCol_CheckMark, self.ACCENT)
                dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, self.ACCENT)
                dpg.add_theme_color(dpg.mvThemeCol_Border, (74, 84, 83, 255))
                dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 14, 12)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 9, 6)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 9, 8)
                dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 6)
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 5)
                dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 6)
                dpg.add_theme_style(dpg.mvStyleVar_GrabRounding, 5)

        dpg.bind_theme(theme)

    def _build_widgets(self) -> None:
        """Create controls, board drawlist, and ranking table host."""
        with dpg.window(
            tag=self.main_window_tag,
            label="Klondike Solitaire",
            no_title_bar=True,
            no_move=True,
            no_collapse=True,
            no_close=True,
        ):
            with dpg.group(horizontal=True):
                title_tag = dpg.add_text("Klondike Solitaire")
                if self.large_font is not None:
                    dpg.bind_item_font(title_tag, self.large_font)

                dpg.add_spacer(width=18)
                dpg.add_text("Player")
                dpg.add_input_text(tag=self.player_tag, default_value="Player", width=190)
                dpg.add_button(label="New Game", callback=self.start_new_game)
                dpg.add_button(label="Undo", callback=self.undo_move)
                dpg.add_button(label="Redo", callback=self.redo_move)
                dpg.add_button(label="Save Result", callback=self.save_result)
                dpg.add_checkbox(
                    tag=self.ranking_toggle_tag,
                    label="Ranking",
                    default_value=True,
                    callback=self.toggle_ranking,
                )

            dpg.add_separator()
            with dpg.group(horizontal=True):
                dpg.add_text("Score: 0", tag=self.score_tag)
                dpg.add_text("Moves: 0", tag=self.moves_tag)
                dpg.add_text("Time: 0s", tag=self.time_tag)
                dpg.add_text("Selected: none", tag=self.selection_tag)

            dpg.add_text(
                "Click stock to draw. Drag cards or piles onto a target slot.",
                tag=self.status_tag,
                color=(179, 222, 207, 255),
            )
            dpg.add_drawlist(width=self.board_width, height=self.board_height, tag=self.board_tag)

            with dpg.child_window(tag=self.ranking_holder_tag, height=self.ranking_height, border=True):
                dpg.add_text("Ranking")

        dpg.set_primary_window(self.main_window_tag, True)

    def _build_handlers(self) -> None:
        """Register global mouse and keyboard handlers."""
        with dpg.handler_registry():
            dpg.add_key_press_handler(key=dpg.mvKey_F11, callback=self.toggle_fullscreen)

    def _resolve_texture_dir(self) -> Path:
        """Return absolute path of texture directory."""
        return Path(__file__).resolve().parent.parent / "png"

    def _load_card_textures(self) -> None:
        """Load all card PNG files into DearPyGui texture registry."""
        if not self.texture_dir.exists():
            return

        with dpg.texture_registry(show=False):
            for image_path in sorted(self.texture_dir.glob("*.png")):
                try:
                    width, height, _channels, data = dpg.load_image(str(image_path))
                except Exception:
                    continue

                texture_tag = f"texture_{image_path.stem.lower()}"
                if dpg.does_item_exist(texture_tag):
                    dpg.delete_item(texture_tag)
                dpg.add_static_texture(width, height, data, tag=texture_tag)

                key = image_path.stem.upper()
                if key == "CARD_BACK":
                    self.back_texture = texture_tag
                    self.back_uv_min, self.back_uv_max = self._opaque_texture_uv(width, height, data)
                else:
                    self.card_textures[key] = texture_tag

    def _opaque_texture_uv(self, width: int, height: int, data: Any) -> tuple[tuple[float, float], tuple[float, float]]:
        """Return UV coordinates that crop transparent padding from one RGBA texture."""
        min_x = width
        min_y = height
        max_x = -1
        max_y = -1

        for y_pos in range(height):
            row_offset = y_pos * width * 4
            for x_pos in range(width):
                alpha = data[row_offset + x_pos * 4 + 3]
                if alpha <= 0.01:
                    continue
                min_x = min(min_x, x_pos)
                min_y = min(min_y, y_pos)
                max_x = max(max_x, x_pos)
                max_y = max(max_y, y_pos)

        if max_x < min_x or max_y < min_y:
            return (0.0, 0.0), (1.0, 1.0)

        return (min_x / width, min_y / height), ((max_x + 1) / width, (max_y + 1) / height)

    def _rank_to_texture(self, rank: int) -> str:
        """Convert rank number to texture suffix token."""
        rank_map = {1: "A", 11: "J", 12: "Q", 13: "K"}
        return rank_map.get(rank, str(rank))

    def _card_texture_key(self, card: Any) -> str:
        """Return texture key for one card from suit and rank."""
        return f"{card.suit}{self._rank_to_texture(card.rank)}"

    def _set_status(self, text: str, *, error: bool = False) -> None:
        """Set one short message in the status bar."""
        dpg.set_value(self.status_tag, text)
        dpg.configure_item(self.status_tag, color=self.ERROR if error else (179, 222, 207, 255))

    def _set_selection_text(self, text: str) -> None:
        """Set current source selection text."""
        dpg.set_value(self.selection_tag, text)

    def _board_size(self) -> tuple[int, int]:
        """Return the currently configured board size."""
        return self.board_width, self.board_height

    def _resize_for_viewport(self) -> None:
        """Keep board height balanced with optional ranking space."""
        client_size = (dpg.get_viewport_client_width(), dpg.get_viewport_client_height())
        if client_size == self.last_client_size:
            return

        self.last_client_size = client_size
        resized = False
        dpg.configure_item(
            self.main_window_tag,
            width=max(self.MIN_BOARD_WIDTH, client_size[0]),
            height=max(self.MIN_BOARD_HEIGHT, client_size[1]),
        )

        new_width = max(self.MIN_BOARD_WIDTH, client_size[0] - 28)
        if abs(new_width - self.board_width) > 4:
            self.board_width = new_width
            dpg.configure_item(self.board_tag, width=self.board_width)
            resized = True

        if self.ranking_visible:
            new_ranking_height = max(96, min(230, int(client_size[1] * 0.22)))
            if abs(new_ranking_height - self.ranking_height) > 4:
                self.ranking_height = new_ranking_height
                dpg.configure_item(self.ranking_holder_tag, height=self.ranking_height)
                resized = True
        else:
            new_ranking_height = 0

        reserved = 120 + (new_ranking_height + 12 if self.ranking_visible else 0)
        new_height = max(self.MIN_BOARD_HEIGHT, client_size[1] - reserved)
        if abs(new_height - self.board_height) > 4:
            self.board_height = new_height
            dpg.configure_item(self.board_tag, height=self.board_height)
            resized = True

        if resized:
            self.refresh_board()

    def _recalculate_layout(self) -> None:
        """Recompute centered x/y positions based on current board size."""
        board_width, board_height = self._board_size()
        usable_width = max(board_width - 2 * self.board_padding_x, self.MIN_CARD_WIDTH * 7)

        width_target = int(usable_width / 8.9)
        height_target = int(max(118, board_height - 80) * 0.31)
        self.CARD_WIDTH = max(self.MIN_CARD_WIDTH, min(self.MAX_CARD_WIDTH, width_target, height_target))

        for _ in range(4):
            self.CARD_HEIGHT = int(self.CARD_WIDTH * self.BASE_CARD_HEIGHT / self.BASE_CARD_WIDTH)
            scale = self.CARD_WIDTH / self.BASE_CARD_WIDTH
            self.TOP_TO_TABLEAU_GAP = max(30, int(50 * scale))
            self.tableau_row_y = self.TOP_Y + self.CARD_HEIGHT + self.TOP_TO_TABLEAU_GAP
            remaining_height = max(80, board_height - self.tableau_row_y - self.CARD_HEIGHT - 10)
            max_up_step = max(int(20 * scale), remaining_height // 12)
            self.UP_STEP = max(int(20 * scale), min(int(self.CARD_HEIGHT * 0.34), max_up_step))
            self.DOWN_STEP = max(int(10 * scale), min(int(self.CARD_HEIGHT * 0.16), self.UP_STEP // 2))

            available_stack_height = max(60, board_height - self.tableau_row_y - 8)
            tallest_stack_height = self._tallest_tableau_stack_height()
            if tallest_stack_height <= available_stack_height or self.CARD_WIDTH <= self.MIN_CARD_WIDTH:
                break

            shrink_ratio = available_stack_height / tallest_stack_height
            self.CARD_WIDTH = max(self.MIN_CARD_WIDTH, int(self.CARD_WIDTH * shrink_ratio * 0.96))

        self.CARD_HEIGHT = int(self.CARD_WIDTH * self.BASE_CARD_HEIGHT / self.BASE_CARD_WIDTH)
        scale = self.CARD_WIDTH / self.BASE_CARD_WIDTH
        self.TOP_TO_TABLEAU_GAP = max(30, int(50 * scale))
        dynamic_gap = (usable_width - self.CARD_WIDTH * 7) // 6
        self.COL_GAP = max(4, min(int(52 * scale), dynamic_gap))

        if self.ranking_visible:
            self.top_row_y = self.TOP_Y
        else:
            estimated_tableau_height = self.CARD_HEIGHT
            for column in self.game.tableau:
                hidden_count = column.face_down.size()
                visible_count = len(column.visible_cards())
                stack_height = (
                    hidden_count * self.DOWN_STEP
                    + self.CARD_HEIGHT
                    + max(0, visible_count - 1) * self.UP_STEP
                )
                estimated_tableau_height = max(estimated_tableau_height, stack_height)

            content_height = self.CARD_HEIGHT + self.TOP_TO_TABLEAU_GAP + estimated_tableau_height
            self.top_row_y = max(18, (board_height - content_height) // 2)

        self.tableau_row_y = self.top_row_y + self.CARD_HEIGHT + self.TOP_TO_TABLEAU_GAP

        remaining_height = max(60, board_height - self.tableau_row_y - self.CARD_HEIGHT - 24)
        max_up_step = max(int(20 * scale), remaining_height // 12)
        self.UP_STEP = max(int(20 * scale), min(int(self.CARD_HEIGHT * 0.34), max_up_step))
        self.DOWN_STEP = max(int(10 * scale), min(int(self.CARD_HEIGHT * 0.16), self.UP_STEP // 2))

        total_board_width = self.CARD_WIDTH * 7 + self.COL_GAP * 6
        start_x = max((board_width - total_board_width) // 2, self.board_padding_x)

        self.column_left = [start_x + index * (self.CARD_WIDTH + self.COL_GAP) for index in range(7)]
        self.stock_left = self.column_left[0]
        self.waste_left = self.column_left[1]
        self.foundation_left = [self.column_left[3 + index] for index in range(4)]

    def _tallest_tableau_stack_height(self) -> int:
        """Return the rendered height of the tallest tableau column."""
        tallest = self.CARD_HEIGHT
        for column in self.game.tableau:
            hidden_count = column.face_down.size()
            visible_count = len(column.visible_cards())
            stack_height = (
                hidden_count * self.DOWN_STEP
                + self.CARD_HEIGHT
                + max(0, visible_count - 1) * self.UP_STEP
            )
            tallest = max(tallest, stack_height)
        return tallest

    def _hit_test(self, x: int, y: int) -> dict[str, Any] | None:
        """Return topmost hotspot containing pointer coordinates."""
        for hotspot in reversed(self.hotspots):
            left, top, right, bottom = hotspot["bbox"]
            if left <= x <= right and top <= y <= bottom:
                return hotspot
        return None

    def _mouse_board_pos(self) -> tuple[int, int] | None:
        """Return mouse coordinates relative to the board drawlist."""
        if not dpg.does_item_exist(self.board_tag):
            return None
        mouse_x, mouse_y = dpg.get_mouse_pos(local=False)
        board_x, board_y = dpg.get_item_rect_min(self.board_tag)
        board_width, board_height = self._board_size()
        local_x = int(mouse_x - board_x)
        local_y = int(mouse_y - board_y)
        if local_x < 0 or local_y < 0 or local_x > board_width or local_y > board_height:
            return None
        return local_x, local_y

    def _draw_centered_text(
        self,
        center_x: int,
        center_y: int,
        text: str,
        *,
        size: int = 15,
        color: Color | None = None,
    ) -> None:
        """Draw approximate centered text in the drawlist."""
        color = color or self.TEXT_LIGHT
        text_width = int(len(text) * size * 0.55)
        dpg.draw_text(
            (center_x - text_width // 2, center_y - size // 2),
            text,
            color=color,
            size=size,
            parent=self.board_tag,
        )

    def _draw_card(
        self,
        left: int,
        top: int,
        card: Any | None,
        *,
        is_back: bool,
        is_selected: bool,
        preview: bool = False,
    ) -> None:
        """Draw one card image with fallback style and selected border."""
        right = left + self.CARD_WIDTH
        bottom = top + self.CARD_HEIGHT
        if preview:
            dpg.draw_rectangle(
                (left + 7, top + 9),
                (right + 9, bottom + 11),
                color=(0, 0, 0, 95),
                fill=(0, 0, 0, 55),
                rounding=10,
                thickness=1,
                parent=self.board_tag,
            )

        texture = self.back_texture if is_back else None
        if not is_back and card is not None:
            texture = self.card_textures.get(self._card_texture_key(card))

        if texture is not None:
            if is_back:
                dpg.draw_rectangle(
                    (left, top),
                    (right, bottom),
                    color=(24, 28, 32, 255),
                    fill=(248, 248, 244, 255),
                    rounding=8,
                    thickness=1,
                    parent=self.board_tag,
                )
            dpg.draw_image(
                texture,
                (left, top),
                (right, bottom),
                parent=self.board_tag,
                uv_min=self.back_uv_min if is_back else (0.0, 0.0),
                uv_max=self.back_uv_max if is_back else (1.0, 1.0),
            )
        else:
            fill = (37, 78, 138, 255) if is_back else (248, 248, 244, 255)
            dpg.draw_rectangle(
                (left, top),
                (right, bottom),
                color=self.CARD_BORDER,
                fill=fill,
                rounding=7,
                thickness=2,
                parent=self.board_tag,
            )
            if card is not None:
                text_color = (196, 40, 40, 255) if card.is_red() else (26, 28, 31, 255)
                self._draw_centered_text(
                    left + self.CARD_WIDTH // 2,
                    top + self.CARD_HEIGHT // 2,
                    card.to_symbol(),
                    size=22,
                    color=text_color,
                )
            elif is_back:
                self._draw_centered_text(left + self.CARD_WIDTH // 2, top + self.CARD_HEIGHT // 2, "KL", size=20)

        if preview:
            dpg.draw_rectangle(
                (left - 2, top - 2),
                (right + 2, bottom + 2),
                color=(255, 225, 130, 240),
                rounding=9,
                thickness=2,
                parent=self.board_tag,
            )

        if is_selected:
            dpg.draw_rectangle(
                (left - 2, top - 2),
                (right + 2, bottom + 2),
                color=self.ACCENT,
                rounding=8,
                thickness=4,
                parent=self.board_tag,
            )

    def _draw_placeholder(self, left: int, top: int, label: str) -> None:
        """Draw one empty-slot placeholder."""
        right = left + self.CARD_WIDTH
        bottom = top + self.CARD_HEIGHT
        dpg.draw_rectangle(
            (left, top),
            (right, bottom),
            color=(138, 199, 170, 255),
            fill=self.BOARD_BG_ALT,
            rounding=7,
            thickness=2,
            parent=self.board_tag,
        )
        dpg.draw_rectangle(
            (left + 8, top + 8),
            (right - 8, bottom - 8),
            color=(112, 171, 143, 180),
            rounding=5,
            thickness=1,
            parent=self.board_tag,
        )
        self._draw_centered_text(left + self.CARD_WIDTH // 2, top + self.CARD_HEIGHT // 2, label, size=14)

    def _clear_selection(self) -> None:
        """Clear source selection marker."""
        self.selected = None
        self._set_selection_text("Selected: none")

    def _clear_drag_state(self) -> None:
        """Clear drag state."""
        self.drag_source = None
        self.dragging = False
        self.drop_hotspot = None

    def _select_waste(self) -> None:
        """Select waste as move source."""
        self.selected = {"type": "waste"}
        self._set_selection_text("Selected: waste")

    def _select_foundation(self, foundation_index: int) -> None:
        """Select foundation slot as move source."""
        self.selected = {"type": "foundation", "index": foundation_index}
        foundation = self.game.foundations[foundation_index]
        label = foundation.peek().suit if not foundation.is_empty() else str(foundation_index + 1)
        self._set_selection_text(f"Selected: foundation {label}")

    def _select_tableau(self, column: int, start_index: int) -> None:
        """Select one tableau sub-pile as source."""
        visible_count = len(self.game.tableau[column].visible_cards())
        count = visible_count - start_index
        self.selected = {"type": "tableau", "column": column, "start_index": start_index, "count": count}
        self._set_selection_text(f"Selected: tableau {column + 1}, cards {count}")

    def _is_selected(self, target: dict[str, Any]) -> bool:
        """Return True when target represents the currently selected source."""
        if self.selected is None:
            return False
        selected_type = self.selected["type"]
        target_type = target["type"]
        if selected_type == "waste" and target_type == "waste":
            return True
        if selected_type == "foundation" and target_type == "foundation":
            return self.selected["index"] == target["index"]
        if selected_type == "tableau" and target_type == "tableau_card":
            return self.selected["column"] == target["column"] and self.selected["start_index"] == target["start_index"]
        return False

    def _foundation_target_from_click(self, foundation_index: int) -> bool:
        """Attempt click-based move from selected source to a foundation slot."""
        if self.selected is None:
            self._set_status("Choose a source card first", error=True)
            return False
        if self.selected["type"] == "waste":
            return self.game.move_waste_to_foundation(foundation_index)
        if self.selected["type"] == "tableau":
            if self.selected["count"] != 1:
                return False
            return self.game.move_tableau_to_foundation(self.selected["column"], foundation_index)
        return False

    def _tableau_target_from_click(self, column: int) -> bool:
        """Attempt click-based move from selected source to tableau column."""
        if self.selected is None:
            self._set_status("Choose a source card first", error=True)
            return False
        if self.selected["type"] == "waste":
            return self.game.move_waste_to_tableau(column)
        if self.selected["type"] == "foundation":
            return self.game.move_foundation_to_tableau(self.selected["index"], column)
        if self.selected["type"] == "tableau":
            return self.game.move_tableau_to_tableau(self.selected["column"], column, self.selected["count"])
        return False

    def _source_from_hotspot(self, hotspot: dict[str, Any] | None) -> dict[str, Any] | None:
        """Convert hotspot under pointer into a move source descriptor."""
        if hotspot is None:
            return None
        kind = hotspot["type"]
        if kind == "waste":
            if self.game.waste.is_empty():
                return None
            return {"type": "waste"}
        if kind == "foundation":
            index = hotspot["index"]
            if self.game.foundations[index].is_empty():
                return None
            return {"type": "foundation", "index": index}
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
            return target_type == "foundation" and source["index"] == hotspot.get("index")
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
                return self.game.move_waste_to_foundation(hotspot["index"])
            if target_type in {"tableau_card", "tableau_column"}:
                return self.game.move_waste_to_tableau(hotspot["column"])
            return False

        if source_type == "foundation":
            if target_type in {"tableau_card", "tableau_column"}:
                return self.game.move_foundation_to_tableau(source["index"], hotspot["column"])
            return False

        if source_type == "tableau":
            if target_type == "foundation":
                if source["count"] != 1:
                    return False
                return self.game.move_tableau_to_foundation(source["column"], hotspot["index"])
            if target_type in {"tableau_card", "tableau_column"}:
                return self.game.move_tableau_to_tableau(source["column"], hotspot["column"], source["count"])
            return False

        return False

    def _can_drop_on_hotspot(self, source: dict[str, Any], hotspot: dict[str, Any] | None) -> bool:
        """Return True when source can legally move to the current drop hotspot."""
        if hotspot is None or self._same_source_target(source, hotspot):
            return False

        source_type = source["type"]
        target_type = hotspot["type"]
        if source_type == "waste":
            if self.game.waste.is_empty():
                return False
            card = self.game.waste.peek()
            if target_type == "foundation":
                return self.game.can_place_on_foundation(card, hotspot["index"])
            if target_type in {"tableau_card", "tableau_column"}:
                return self.game._can_place_on_tableau(card, hotspot["column"])
            return False

        if source_type == "foundation":
            foundation = self.game.foundations[source["index"]]
            if foundation.is_empty():
                return False
            if target_type in {"tableau_card", "tableau_column"}:
                return self.game._can_place_on_tableau(foundation.peek(), hotspot["column"])
            return False

        if source_type == "tableau":
            moving_cards = self.game.tableau[source["column"]].visible_cards()[source["start_index"] :]
            if not moving_cards:
                return False
            if target_type == "foundation":
                return len(moving_cards) == 1 and self.game.can_place_on_foundation(moving_cards[0], hotspot["index"])
            if target_type in {"tableau_card", "tableau_column"}:
                return (
                    self.game.is_valid_tableau_sequence(moving_cards)
                    and self.game._can_place_on_tableau(moving_cards[0], hotspot["column"])
                )
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
            self._select_foundation(source["index"])
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
            self._set_status("Draw success" if success else "No card available", error=not success)
            self._clear_selection()
            self.refresh_board()
            return

        if kind == "waste":
            if self.game.waste.is_empty():
                self._set_status("Waste is empty", error=True)
                return
            if self.selected is not None and self.selected.get("type") == "waste":
                self._clear_selection()
            else:
                self._select_waste()
            self.refresh_board()
            return

        if kind == "foundation":
            index = hotspot["index"]
            if self.selected is None:
                if self.game.foundations[index].is_empty():
                    self._set_status("Foundation is empty", error=True)
                    return
                self._select_foundation(index)
                self.refresh_board()
                return
            success = self._foundation_target_from_click(index)
            self._set_status("Move success" if success else "Invalid move", error=not success)
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
            self._set_status("Move success" if success else "Invalid move", error=not success)
            self._clear_selection()
            self.refresh_board()
            return

        if kind == "tableau_column":
            if self.selected is None:
                self._set_status("Choose a source card first", error=True)
                return
            success = self._tableau_target_from_click(hotspot["column"])
            self._set_status("Move success" if success else "Invalid move", error=not success)
            self._clear_selection()
            self.refresh_board()

    def on_mouse_press(self, *_args: Any) -> None:
        """Record drag start and source candidate on mouse press."""
        position = self._mouse_board_pos()
        if position is None:
            self.mouse_pressed_on_board = False
            self.drag_source = None
            return

        self.mouse_pressed_on_board = True
        x, y = position
        hotspot = self._hit_test(x, y)
        self.drag_start_x = x
        self.drag_start_y = y
        self.drag_current_x = x
        self.drag_current_y = y
        self.dragging = False
        self.drag_source = self._source_from_hotspot(hotspot)
        if hotspot is not None:
            left, top, _right, _bottom = hotspot["bbox"]
            self.drag_offset_x = x - left
            self.drag_offset_y = y - top

    def on_mouse_drag(self, *_args: Any) -> None:
        """Update drag visuals when pointer movement crosses drag threshold."""
        if self.drag_source is None:
            return
        position = self._mouse_board_pos()
        if position is None:
            return

        x, y = position
        if self.dragging and x == self.drag_current_x and y == self.drag_current_y:
            return

        moved_x = abs(x - self.drag_start_x)
        moved_y = abs(y - self.drag_start_y)
        if moved_x < self.DRAG_THRESHOLD and moved_y < self.DRAG_THRESHOLD and not self.dragging:
            return

        self.dragging = True
        self.drag_current_x = x
        self.drag_current_y = y
        hover_hotspot = self._hit_test(x, y)
        if hover_hotspot is not None and not self._same_source_target(self.drag_source, hover_hotspot):
            self.drop_hotspot = hover_hotspot
        else:
            self.drop_hotspot = None
        self._set_selection_from_source(self.drag_source)
        self.refresh_board()

    def on_mouse_release(self, *_args: Any) -> None:
        """Finalize drag-drop move or fallback to click behavior on release."""
        position = self._mouse_board_pos()
        release_hotspot = self._hit_test(*position) if position is not None else None

        if self.drag_source is not None and self.dragging:
            if release_hotspot is not None and not self._same_source_target(self.drag_source, release_hotspot):
                success = self._move_from_source_to_hotspot(self.drag_source, release_hotspot)
                self._set_status("Move success" if success else "Invalid move", error=not success)
                self._clear_selection()
                self.mouse_pressed_on_board = False
                self._clear_drag_state()
                self.refresh_board()
                return
            self._set_status("Invalid move", error=True)
            self._clear_selection()
            self.mouse_pressed_on_board = False
            self._clear_drag_state()
            self.refresh_board()
            return

        self.mouse_pressed_on_board = False
        self._clear_drag_state()
        self._handle_click_hotspot(release_hotspot)

    def _draw_top_piles(self) -> None:
        """Draw stock, waste, and foundation piles on top row."""
        self.hotspots.append(
            {
                "type": "stock",
                "bbox": (
                    self.stock_left,
                    self.top_row_y,
                    self.stock_left + self.CARD_WIDTH,
                    self.top_row_y + self.CARD_HEIGHT,
                ),
            }
        )
        if self.game.stock.is_empty():
            self._draw_placeholder(self.stock_left, self.top_row_y, "STOCK")
        else:
            self._draw_card(self.stock_left, self.top_row_y, None, is_back=True, is_selected=False)

        waste_selected = self.selected is not None and self.selected.get("type") == "waste"
        self.hotspots.append(
            {
                "type": "waste",
                "bbox": (
                    self.waste_left,
                    self.top_row_y,
                    self.waste_left + self.CARD_WIDTH,
                    self.top_row_y + self.CARD_HEIGHT,
                ),
            }
        )
        if self.game.waste.is_empty():
            self._draw_placeholder(self.waste_left, self.top_row_y, "WASTE")
        else:
            self._draw_card(
                self.waste_left,
                self.top_row_y,
                self.game.waste.peek(),
                is_back=False,
                is_selected=waste_selected,
            )

        for index in range(4):
            left = self.foundation_left[index]
            selected = (
                self.selected is not None
                and self.selected.get("type") == "foundation"
                and self.selected.get("index") == index
            )
            foundation = self.game.foundations[index]
            suit_label = foundation.peek().suit if not foundation.is_empty() else "?"
            self._draw_centered_text(
                left + self.CARD_WIDTH // 2,
                self.top_row_y - 11,
                f"F-{suit_label}",
                size=13,
                color=self.TEXT_MUTED,
            )
            self.hotspots.append(
                {
                    "type": "foundation",
                    "index": index,
                    "bbox": (left, self.top_row_y, left + self.CARD_WIDTH, self.top_row_y + self.CARD_HEIGHT),
                }
            )
            if foundation.is_empty():
                self._draw_placeholder(left, self.top_row_y, "F")
            else:
                self._draw_card(left, self.top_row_y, foundation.peek(), is_back=False, is_selected=selected)

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
                        self.tableau_row_y,
                        left + self.CARD_WIDTH,
                        self.tableau_row_y + self.CARD_HEIGHT + self.UP_STEP * max(len(visible_cards), 1),
                    ),
                }
            )

            dpg.draw_text(
                (left, self.tableau_row_y - 26),
                f"T{column_index + 1}",
                color=self.TEXT_MUTED,
                size=15,
                parent=self.board_tag,
            )

            down_count = len(hidden_cards)
            for down_index in range(down_count):
                top = self.tableau_row_y + down_index * self.DOWN_STEP
                self._draw_card(left, top, None, is_back=True, is_selected=False)

            up_start = self.tableau_row_y + down_count * self.DOWN_STEP
            if not visible_cards and down_count == 0:
                self._draw_placeholder(left, self.tableau_row_y, "TABLEAU")

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

    def _cards_for_source(self, source: dict[str, Any]) -> list[Any]:
        """Return card objects represented by a drag source."""
        if source["type"] == "waste":
            return [] if self.game.waste.is_empty() else [self.game.waste.peek()]
        if source["type"] == "foundation":
            foundation = self.game.foundations[source["index"]]
            return [] if foundation.is_empty() else [foundation.peek()]
        if source["type"] == "tableau":
            return self.game.tableau[source["column"]].visible_cards()[source["start_index"] :]
        return []

    def _draw_drag_preview(self) -> None:
        """Draw a floating preview of the cards being dragged."""
        if not self.dragging or self.drag_source is None:
            return
        cards = self._cards_for_source(self.drag_source)
        if not cards:
            return

        left = self.drag_current_x - self.drag_offset_x
        top = self.drag_current_y - self.drag_offset_y
        dpg.draw_rectangle(
            (left - 5, top - 5),
            (left + self.CARD_WIDTH + 5, top + self.CARD_HEIGHT + max(0, len(cards) - 1) * self.UP_STEP + 5),
            color=self.ACCENT,
            rounding=8,
            thickness=2,
            parent=self.board_tag,
        )
        for index, card in enumerate(cards):
            self._draw_card(left, top + index * self.UP_STEP, card, is_back=False, is_selected=False, preview=True)

        dpg.draw_circle(
            (self.drag_current_x, self.drag_current_y),
            max(9, int(self.CARD_WIDTH * 0.09)),
            color=(255, 231, 145, 230),
            fill=(255, 231, 145, 70),
            thickness=2,
            parent=self.board_tag,
        )

    def _draw_drop_feedback(self) -> None:
        """Draw hover feedback for the current drag target."""
        if not self.dragging or self.drag_source is None or self.drop_hotspot is None:
            return

        left, top, right, bottom = self.drop_hotspot["bbox"]
        is_valid = self._can_drop_on_hotspot(self.drag_source, self.drop_hotspot)
        color = (116, 230, 158, 255) if is_valid else (238, 104, 89, 255)
        fill = (116, 230, 158, 42) if is_valid else (238, 104, 89, 42)
        label = "DROP" if is_valid else "NO"

        dpg.draw_rectangle(
            (left - 8, top - 8),
            (right + 8, bottom + 8),
            color=color,
            fill=fill,
            rounding=12,
            thickness=4,
            parent=self.board_tag,
        )
        dpg.draw_rectangle(
            (left - 3, top - 3),
            (right + 3, bottom + 3),
            color=(255, 255, 255, 120),
            rounding=9,
            thickness=1,
            parent=self.board_tag,
        )
        self._draw_centered_text(
            (left + right) // 2,
            max(18, top - 22),
            label,
            size=max(13, int(self.CARD_WIDTH * 0.13)),
            color=color,
        )

    def _tick_clock(self, *, force: bool = False) -> None:
        """Update elapsed-time label once per second."""
        elapsed = self.game.elapsed_seconds()
        if force or elapsed != self.last_clock_second:
            self.last_clock_second = elapsed
            dpg.set_value(self.time_tag, f"Time: {elapsed}s")

    def refresh_board(self) -> None:
        """Redraw board and counters from current game state."""
        if not dpg.does_item_exist(self.board_tag):
            return

        dpg.set_value(self.score_tag, f"Score: {self.game.score}")
        dpg.set_value(self.moves_tag, f"Moves: {self.game.moves}")

        self._recalculate_layout()
        dpg.delete_item(self.board_tag, children_only=True)
        self.hotspots.clear()

        board_width, board_height = self._board_size()
        dpg.draw_rectangle((0, 0), (board_width, board_height), color=self.BOARD_BG, fill=self.BOARD_BG, parent=self.board_tag)
        dpg.draw_line((0, self.tableau_row_y - 44), (board_width, self.tableau_row_y - 44), color=(24, 122, 73, 255), thickness=2, parent=self.board_tag)

        self._draw_top_piles()
        self._draw_tableau()
        self._draw_drop_feedback()
        self._draw_drag_preview()

        if self.game.is_won():
            self._set_status("You won. Save result to ranking.")

    def refresh_ranking_table(self, entries: list[dict[str, Any]]) -> None:
        """Render sorted ranking entries into the leaderboard table."""
        if dpg.does_item_exist(self.ranking_table_tag):
            dpg.delete_item(self.ranking_table_tag)

        ordered = self.game.ranking_board.sorted_entries(entries)
        with dpg.table(
            tag=self.ranking_table_tag,
            parent=self.ranking_holder_tag,
            header_row=True,
            borders_innerH=True,
            borders_outerH=True,
            borders_innerV=True,
            borders_outerV=True,
            row_background=True,
            resizable=True,
            policy=dpg.mvTable_SizingStretchProp,
        ):
            dpg.add_table_column(label="Player", init_width_or_weight=3.0)
            dpg.add_table_column(label="Score", init_width_or_weight=1.0)
            dpg.add_table_column(label="Moves", init_width_or_weight=1.0)
            dpg.add_table_column(label="Won", init_width_or_weight=1.0)
            dpg.add_table_column(label="Seconds", init_width_or_weight=1.0)

            rows = ordered[:12]
            if not rows:
                with dpg.table_row():
                    dpg.add_text("No saved results yet")
                    dpg.add_text("-")
                    dpg.add_text("-")
                    dpg.add_text("-")
                    dpg.add_text("-")
                return

            for entry in rows:
                with dpg.table_row():
                    dpg.add_text(str(entry.get("player", "Unknown")))
                    dpg.add_text(str(entry.get("score", 0)))
                    dpg.add_text(str(entry.get("moves", 0)))
                    dpg.add_text("Yes" if entry.get("won") else "No")
                    dpg.add_text(str(entry.get("elapsed_seconds", 0)))

    def toggle_fullscreen(self, *_args: Any) -> None:
        """Toggle fullscreen mode while keeping layout responsive."""
        self.fullscreen_enabled = not self.fullscreen_enabled
        if hasattr(dpg, "toggle_viewport_fullscreen"):
            dpg.toggle_viewport_fullscreen()
        self.refresh_board()

    def toggle_ranking(self, *_args: Any) -> None:
        """Show or hide ranking panel to prioritize board space."""
        self.ranking_visible = bool(dpg.get_value(self.ranking_toggle_tag))
        dpg.configure_item(self.ranking_holder_tag, show=self.ranking_visible)
        self._set_status("Ranking shown" if self.ranking_visible else "Ranking hidden")
        self.last_client_size = (0, 0)
        self._resize_for_viewport()
        self.refresh_board()

    def start_new_game(self, *_args: Any) -> None:
        """Start a fresh game and apply current player name."""
        self.game.set_player_name(dpg.get_value(self.player_tag))
        self.game.new_game()
        self._clear_selection()
        self._clear_drag_state()
        self._set_status("Started a new game")
        self.refresh_board()
        self._tick_clock(force=True)

    def undo_move(self, *_args: Any) -> None:
        """Undo last move when history is available."""
        success = self.game.undo()
        self._clear_selection()
        self._clear_drag_state()
        self._set_status("Undo success" if success else "Nothing to undo", error=not success)
        self.refresh_board()

    def redo_move(self, *_args: Any) -> None:
        """Redo previously undone move when available."""
        success = self.game.redo()
        self._clear_selection()
        self._clear_drag_state()
        self._set_status("Redo success" if success else "Nothing to redo", error=not success)
        self.refresh_board()

    def _show_modal(self, title: str, message: str) -> None:
        """Show a small DearPyGui modal message."""
        if dpg.does_item_exist(self.modal_tag):
            dpg.delete_item(self.modal_tag)

        width, height = 340, 135
        pos = (
            max(80, dpg.get_viewport_client_width() // 2 - width // 2),
            max(80, dpg.get_viewport_client_height() // 2 - height // 2),
        )
        with dpg.window(
            tag=self.modal_tag,
            label=title,
            modal=True,
            no_resize=True,
            width=width,
            height=height,
            pos=pos,
        ):
            dpg.add_text(message, wrap=width - 32)
            dpg.add_spacer(height=8)
            dpg.add_button(label="OK", width=90, callback=lambda *_args: dpg.delete_item(self.modal_tag))

    def save_result(self, *_args: Any) -> None:
        """Save current run into ranking and refresh the table."""
        self.game.set_player_name(dpg.get_value(self.player_tag))
        entries = self.game.finalize_result()
        self.refresh_ranking_table(entries)
        won_text = "won" if self.game.is_won() else "not won"
        self._set_status(f"Saved result ({won_text})")
        self._show_modal("Ranking", "Result saved to ranking table")

    def frame_update(self) -> None:
        """Run lightweight per-frame updates."""
        self._resize_for_viewport()
        self._update_mouse_drag_state()
        self._tick_clock()

    def _update_mouse_drag_state(self) -> None:
        """Poll mouse state each frame so drag/drop stays reliable."""
        left_mouse_down = dpg.is_mouse_button_down(dpg.mvMouseButton_Left)

        if left_mouse_down and not self.previous_left_mouse_down:
            self.on_mouse_press()

        if left_mouse_down:
            self.on_mouse_drag()

        if not left_mouse_down and self.previous_left_mouse_down and self.mouse_pressed_on_board:
            self.on_mouse_release()

        self.previous_left_mouse_down = left_mouse_down


def run_app() -> None:
    """Create the DearPyGui viewport and run the application loop."""
    dpg.create_context()
    dpg.create_viewport(title="Klondike Solitaire - DearPyGui", width=1120, height=900, min_width=760, min_height=560)
    app = KlondikeApp()
    dpg.setup_dearpygui()
    dpg.show_viewport()

    while dpg.is_dearpygui_running():
        app.frame_update()
        dpg.render_dearpygui_frame()

    dpg.destroy_context()
