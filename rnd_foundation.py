#!/usr/bin/env python3
"""A minimal foundation for a Rocks'n'Diamonds-like game.

Includes:
- ASCII demo mode (CI/Codex-friendly)
- Turn-based terminal mode
- Realtime terminal mode (curses)
- Realtime 2D graphics mode (pygame)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, List, Set, Tuple
import argparse
import curses
import importlib
import importlib.util
import os
import sys


class Tile(str, Enum):
    EMPTY = " "
    WALL = "#"
    SAND = "."
    ROCK = "O"
    DIAMOND = "*"
    PLAYER = "P"


class TimingMode(str, Enum):
    ASYNC = "async"
    SYNC = "sync"


DIRECTIONS = {
    "w": (0, -1),
    "a": (-1, 0),
    "s": (0, 1),
    "d": (1, 0),
}


Cell = Tuple[int, int]
Motion = tuple[Tile, Cell, Cell, int]
MotionState = dict[Cell, Motion]


_TILE_SURFACE_CACHE: dict[tuple[Tile, int], object | None] = {}


@dataclass
class GameState:
    grid: List[List[Tile]]
    player_x: int
    player_y: int
    diamonds_total: int
    diamonds_collected: int = 0
    alive: bool = True
    won: bool = False
    falling_positions: Set[Tuple[int, int]] = field(default_factory=set)
    pending_action: str | None = None

    @property
    def width(self) -> int:
        return len(self.grid[0])

    @property
    def height(self) -> int:
        return len(self.grid)

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def get(self, x: int, y: int) -> Tile:
        return self.grid[y][x]

    def set(self, x: int, y: int, tile: Tile) -> None:
        self.grid[y][x] = tile

    def render_lines(self) -> List[str]:
        return ["".join(cell.value for cell in row) for row in self.grid]

    def render(self) -> str:
        status = (
            f"Diamonds: {self.diamonds_collected}/{self.diamonds_total}  "
            f"Status: {'WON' if self.won else 'ALIVE' if self.alive else 'DEAD'}"
        )
        return "\n".join(self.render_lines() + [status])

    def try_move_player(self, dx: int, dy: int) -> None:
        if not self.alive or self.won:
            return

        tx, ty = self.player_x + dx, self.player_y + dy
        if not self.in_bounds(tx, ty):
            return

        target = self.get(tx, ty)

        if target in (Tile.EMPTY, Tile.SAND, Tile.DIAMOND):
            if target == Tile.DIAMOND:
                self.diamonds_collected += 1
                if self.diamonds_collected >= self.diamonds_total:
                    self.won = True
            self._move_player_to(tx, ty)
            return

        if target == Tile.ROCK and dy == 0:
            push_x, push_y = tx + dx, ty
            if self.in_bounds(push_x, push_y) and self.get(push_x, push_y) == Tile.EMPTY:
                self.set(push_x, push_y, Tile.ROCK)
                self._move_player_to(tx, ty)

    def _move_player_to(self, x: int, y: int) -> None:
        self.set(self.player_x, self.player_y, Tile.EMPTY)
        self.player_x, self.player_y = x, y
        self.set(self.player_x, self.player_y, Tile.PLAYER)

    def apply_gravity(self) -> None:
        if not self.alive or self.won:
            return

        new_falling_positions: Set[Tuple[int, int]] = set()
        for y in range(self.height - 2, -1, -1):
            for x in range(self.width):
                tile = self.get(x, y)
                if tile not in (Tile.ROCK, Tile.DIAMOND):
                    continue

                was_falling = (x, y) in self.falling_positions
                below = self.get(x, y + 1)

                if below == Tile.EMPTY:
                    self.set(x, y + 1, tile)
                    self.set(x, y, Tile.EMPTY)
                    new_falling_positions.add((x, y + 1))
                    continue

                if below == Tile.PLAYER and was_falling:
                    self.set(x, y + 1, tile)
                    self.set(x, y, Tile.EMPTY)
                    new_falling_positions.add((x, y + 1))
                    self.falling_positions = new_falling_positions
                    self.alive = False
                    return

        self.falling_positions = new_falling_positions


def parse_level(lines: Iterable[str]) -> GameState:
    raw = [line.rstrip("\n") for line in lines if line.strip("\n")]
    if not raw:
        raise ValueError("Level is empty")

    width = len(raw[0])
    if any(len(row) != width for row in raw):
        raise ValueError("All level rows must have equal width")

    grid: List[List[Tile]] = []
    player_pos: Tuple[int, int] | None = None
    diamonds_total = 0

    legend = {
        "#": Tile.WALL,
        " ": Tile.EMPTY,
        ".": Tile.SAND,
        "O": Tile.ROCK,
        "*": Tile.DIAMOND,
        "P": Tile.PLAYER,
    }

    for y, row in enumerate(raw):
        grid_row: List[Tile] = []
        for x, ch in enumerate(row):
            if ch not in legend:
                raise ValueError(f"Unsupported tile '{ch}' at ({x},{y})")
            tile = legend[ch]
            if tile == Tile.PLAYER:
                if player_pos is not None:
                    raise ValueError("Only one player is allowed")
                player_pos = (x, y)
            if tile == Tile.DIAMOND:
                diamonds_total += 1
            grid_row.append(tile)
        grid.append(grid_row)

    if player_pos is None:
        raise ValueError("Level must contain a player 'P'")

    return GameState(
        grid=grid,
        player_x=player_pos[0],
        player_y=player_pos[1],
        diamonds_total=diamonds_total,
    )


DEFAULT_LEVEL = [
    "########################################",
    "#...... ..*.O .....O.O....... ....O....#",
    "#.OPO...... .........O*..O.... ..... ..#",
    "#.......... ..O.....O.O..O........O....#",
    "#O.OO.........O......O..O....O...O.....#",
    "#O. O......... O..O........O......O.OO.#",
    "#... ..O........O.....O. O........O.OO.#",
    "###############################...O..O.#",
    "#. ...O..*. ..O.O..........*.O*...... .#",
    "#..*.....O..... ........OO O..O....O...#",
    "#...O..O.O..............O .O..O........#",
    "#.O.....O........OOO.......O.. .*....O.#",
    "#.*.. ..O.  .....O.O*..*....O...O..*. .#",
    "#. O..............O O..O........*.....O#",
    "#........###############################",
    "# O.........O...*....O.....O...O.......#",
    "# O......... O..O........O......O.OO.. #",
    "#. ..O........O.....O.  ....*...O.OO...#",
    "#....O*..O........O......O.O*......O...#",
    "#... ..O. ..O.OO.........O.O*...... ..O#",
    "#.*.... ..... ......... .O..O....O...O.#",
    "########################################",
]


def is_update_frame(
    frame_number: int,
    timing_mode: TimingMode = TimingMode.ASYNC,
    sync_interval: int = 1,
) -> bool:
    if frame_number < 0:
        raise ValueError("frame_number must be non-negative")
    if sync_interval <= 0:
        raise ValueError("sync_interval must be positive")
    if timing_mode == TimingMode.ASYNC:
        return True
    if timing_mode == TimingMode.SYNC:
        return frame_number % sync_interval == 0
    raise ValueError(f"Unsupported timing mode: {timing_mode}")


def step_game(state: GameState, action: str | None) -> None:
    if action in DIRECTIONS and state.alive and not state.won:
        dx, dy = DIRECTIONS[action]
        state.try_move_player(dx, dy)
    state.apply_gravity()


def buffer_action(state: GameState, action: str | None) -> None:
    if action in DIRECTIONS:
        state.pending_action = action


def consume_buffered_action(state: GameState) -> str | None:
    action = state.pending_action
    state.pending_action = None
    return action


def step_realtime_frame(
    state: GameState,
    frame_number: int,
    action: str | None,
    timing_mode: TimingMode = TimingMode.ASYNC,
    sync_interval: int = 1,
) -> None:
    if timing_mode == TimingMode.ASYNC:
        buffer_action(state, action)
        if not is_update_frame(frame_number, timing_mode, sync_interval):
            return
        step_game(state, consume_buffered_action(state))
        return

    if timing_mode == TimingMode.SYNC:
        buffer_action(state, action)
        if not is_update_frame(frame_number, timing_mode, sync_interval):
            return
        step_game(state, consume_buffered_action(state))
        return

    if not is_update_frame(frame_number, timing_mode, sync_interval):
        return
    step_game(state, action)


def action_from_turn_input(text: str) -> str | None:
    return text if text in DIRECTIONS else None


def action_from_curses_key(key: int) -> str | None:
    if key in (ord("w"), ord("W"), curses.KEY_UP):
        return "w"
    if key in (ord("a"), ord("A"), curses.KEY_LEFT):
        return "a"
    if key in (ord("s"), ord("S"), curses.KEY_DOWN):
        return "s"
    if key in (ord("d"), ord("D"), curses.KEY_RIGHT):
        return "d"
    return None


def action_from_pygame_key(key: int) -> str | None:
    pygame = importlib.import_module("pygame")
    if key in (pygame.K_w, pygame.K_UP):
        return "w"
    if key in (pygame.K_a, pygame.K_LEFT):
        return "a"
    if key in (pygame.K_s, pygame.K_DOWN):
        return "s"
    if key in (pygame.K_d, pygame.K_RIGHT):
        return "d"
    return None


def pygame_frame_requests_quit(events: Iterable[object]) -> bool:
    pygame = importlib.import_module("pygame")
    for event in events:
        if getattr(event, "type", None) == pygame.QUIT:
            return True
        if getattr(event, "type", None) == pygame.KEYDOWN and getattr(event, "key", None) == pygame.K_q:
            return True
    return False


def action_from_pygame_frame_events(events: Iterable[object]) -> str | None:
    pygame = importlib.import_module("pygame")
    for event in events:
        if getattr(event, "type", None) != pygame.KEYDOWN:
            continue
        action = action_from_pygame_key(getattr(event, "key", None))
        if action is not None:
            return action
    return None


def tile_color(tile: Tile) -> Tuple[int, int, int]:
    colors = {
        Tile.EMPTY: (16, 18, 22),
        Tile.WALL: (100, 110, 130),
        Tile.SAND: (180, 150, 90),
        Tile.ROCK: (140, 90, 60),
        Tile.DIAMOND: (70, 210, 255),
        Tile.PLAYER: (60, 220, 120),
    }
    return colors[tile]


def build_tile_surface(tile: Tile, tile_size: int) -> object | None:
    del tile, tile_size
    return None


def clear_tile_surface_cache() -> None:
    _TILE_SURFACE_CACHE.clear()


def tile_surface(tile: Tile, tile_size: int) -> object | None:
    cache_key = (tile, tile_size)
    if cache_key not in _TILE_SURFACE_CACHE:
        _TILE_SURFACE_CACHE[cache_key] = build_tile_surface(tile, tile_size)
    return _TILE_SURFACE_CACHE[cache_key]


def tile_appearance(tile: Tile, tile_size: int) -> Tuple[object | None, Tuple[int, int, int]]:
    return (tile_surface(tile, tile_size), tile_color(tile))


def tile_rect(pygame: object, x: int, y: int, tile_size: int) -> object:
    return pygame.Rect(x * tile_size, y * tile_size, tile_size, tile_size)


def make_motion(tile: Tile, start_cell: Cell, destination_cell: Cell, start_frame: int) -> Motion:
    if start_frame < 0:
        raise ValueError("start_frame must be non-negative")
    if start_cell == destination_cell:
        raise ValueError("motion must move between different cells")
    return (tile, start_cell, destination_cell, start_frame)


def motion_tile(motion: Motion) -> Tile:
    return motion[0]


def motion_start_cell(motion: Motion) -> Cell:
    return motion[1]


def motion_destination_cell(motion: Motion) -> Cell:
    return motion[2]


def motion_start_frame(motion: Motion) -> int:
    return motion[3]


def make_motion_state() -> MotionState:
    return {}


def set_motion(motion_state: MotionState, motion: Motion) -> None:
    motion_state[motion_destination_cell(motion)] = motion


def get_motion(motion_state: MotionState, cell: Cell) -> Motion | None:
    return motion_state.get(cell)


def remove_motion(motion_state: MotionState, cell: Cell) -> Motion | None:
    return motion_state.pop(cell, None)


def active_motions(motion_state: MotionState) -> list[Motion]:
    return list(motion_state.values())


def clamp_progress(progress: float) -> float:
    if progress < 0.0:
        return 0.0
    if progress > 1.0:
        return 1.0
    return progress


def motion_progress(
    motion: Motion,
    current_frame: int,
    duration_frames: int,
    timing_mode: TimingMode = TimingMode.ASYNC,
    sync_interval: int = 1,
) -> float:
    if current_frame < 0:
        raise ValueError("current_frame must be non-negative")
    if duration_frames <= 0:
        raise ValueError("duration_frames must be positive")
    if sync_interval <= 0:
        raise ValueError("sync_interval must be positive")

    if timing_mode == TimingMode.ASYNC:
        elapsed_frames = current_frame - motion_start_frame(motion)
        return clamp_progress(elapsed_frames / duration_frames)

    if timing_mode == TimingMode.SYNC:
        phase = current_frame % sync_interval
        return clamp_progress(phase / duration_frames)

    raise ValueError(f"Unsupported timing mode: {timing_mode}")


def motion_is_complete(
    motion: Motion,
    current_frame: int,
    duration_frames: int,
    timing_mode: TimingMode = TimingMode.ASYNC,
    sync_interval: int = 1,
) -> bool:
    return motion_progress(motion, current_frame, duration_frames, timing_mode, sync_interval) >= 1.0


def draw_board(pygame: object, screen: object, state: GameState, tile_size: int) -> None:
    for y in range(state.height):
        for x in range(state.width):
            tile = state.get(x, y)
            rect = tile_rect(pygame, x, y, tile_size)
            surface, fallback_color = tile_appearance(tile, tile_size)
            if surface is not None:
                screen.blit(surface, rect)
            else:
                pygame.draw.rect(screen, fallback_color, rect)
            pygame.draw.rect(screen, (30, 30, 30), rect, 1)


def draw_hud(
    screen: object,
    font: object,
    state: GameState,
    tile_size: int,
    hud_padding_x: int = 10,
    hud_top_padding: int | None = None,
    hud_line_gap: int | None = None,
) -> None:
    if hud_top_padding is None:
        hud_top_padding = hud_top_padding_px()
    if hud_line_gap is None:
        hud_line_gap = hud_line_gap_px()

    status = f"Diamonds: {state.diamonds_collected}/{state.diamonds_total}"
    if state.won:
        status += "   YOU WON"
    elif not state.alive:
        status += "   YOU DIED"

    help_text = "Move: WASD/Arrows   Quit: Q"
    hud_y = state.height * tile_size
    screen.blit(
        font.render(status, True, (245, 245, 245)),
        (hud_padding_x, hud_y + hud_top_padding),
    )
    screen.blit(
        font.render(help_text, True, (190, 190, 190)),
        (hud_padding_x, hud_y + hud_top_padding + hud_line_gap),
    )


def render_frame(
    pygame: object,
    screen: object,
    font: object,
    state: GameState,
    tile_size: int,
    hud_padding_x: int = 10,
    hud_top_padding: int | None = None,
    hud_line_gap: int | None = None,
) -> None:
    screen.fill((10, 10, 12))
    draw_board(pygame, screen, state, tile_size)
    draw_hud(screen, font, state, tile_size, hud_padding_x, hud_top_padding, hud_line_gap)


def hud_top_padding_px(font_size: int = 20) -> int:
    return max(10, font_size // 2)


def hud_line_gap_px(font_size: int = 20) -> int:
    return font_size + 8


def hud_height_px(hud_top_padding: int = 10, hud_line_gap: int = 28, font_size: int = 20) -> int:
    return hud_top_padding + hud_line_gap + font_size + 12


def board_size_px(state: GameState, tile_size: int) -> Tuple[int, int]:
    return (state.width * tile_size, state.height * tile_size)


def screen_size_px(
    state: GameState,
    tile_size: int,
    hud_top_padding: int | None = None,
    hud_line_gap: int | None = None,
    font_size: int = 20,
    hud_height: int | None = None,
) -> Tuple[int, int]:
    if hud_top_padding is None:
        hud_top_padding = hud_top_padding_px(font_size)
    if hud_line_gap is None:
        hud_line_gap = hud_line_gap_px(font_size)
    board_width, board_height = board_size_px(state, tile_size)
    if hud_height is None:
        hud_height = hud_height_px(hud_top_padding, hud_line_gap, font_size)
    return (board_width, board_height + hud_height)


def update_graphics_frame(
    state: GameState,
    frame_number: int,
    events: Iterable[object],
    timing_mode: TimingMode = TimingMode.ASYNC,
    sync_interval: int = 1,
) -> bool:
    event_list = list(events)
    should_quit = pygame_frame_requests_quit(event_list)
    if state.alive and not state.won:
        frame_action = action_from_pygame_frame_events(event_list)
        step_realtime_frame(state, frame_number, frame_action, timing_mode, sync_interval)
    return should_quit


def run_interactive_turn_based(state: GameState) -> None:
    print("Controls: w/a/s/d to move, q to quit")
    while state.alive and not state.won:
        print()
        print(state.render())
        move = input("Move> ").strip().lower()
        if move == "q":
            break
        action = action_from_turn_input(move)
        if action is None:
            print("Use w/a/s/d or q")
            continue
        step_game(state, action)

    print()
    print(state.render())


def run_interactive_realtime_terminal(
    state: GameState,
    tick_ms: int,
    timing_mode: TimingMode = TimingMode.ASYNC,
    sync_interval: int = 1,
) -> None:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise RuntimeError("Realtime terminal mode requires a TTY")

    def _loop(stdscr: curses.window) -> None:
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        stdscr.nodelay(True)
        stdscr.timeout(tick_ms)
        stdscr.keypad(True)
        frame_number = 0

        while True:
            stdscr.erase()
            for y, row in enumerate(state.render_lines()):
                stdscr.addstr(y, 0, row)

            status = (
                f"Diamonds: {state.diamonds_collected}/{state.diamonds_total}  "
                f"Status: {'WON' if state.won else 'ALIVE' if state.alive else 'DEAD'}"
            )
            stdscr.addstr(state.height + 1, 0, status)
            stdscr.addstr(state.height + 2, 0, "Controls: WASD/Arrows move, q quit")
            stdscr.refresh()

            key = stdscr.getch()
            if key in (ord("q"), ord("Q")):
                break
            action = action_from_curses_key(key)
            if state.alive and not state.won:
                step_realtime_frame(state, frame_number, action, timing_mode, sync_interval)
            frame_number += 1

    curses.wrapper(_loop)


def run_interactive_realtime_graphics(
    state: GameState,
    tick_ms: int,
    tile_size: int,
    max_frames: int = 0,
    headless: bool = False,
    timing_mode: TimingMode = TimingMode.ASYNC,
    sync_interval: int = 1,
    font_size: int = 20,
    hud_height: int | None = None,
) -> None:
    if importlib.util.find_spec("pygame") is None:
        raise RuntimeError("pygame is required for --graphics2d. Install with: python3 -m pip install pygame")

    sdl_driver = os.environ.get("SDL_VIDEODRIVER", "").lower()
    if sdl_driver == "dummy" and not headless:
        raise RuntimeError(
            "SDL_VIDEODRIVER is set to 'dummy', which disables real windows. "
            "Unset it to see the game window, or pass --headless for test runs."
        )

    pygame = importlib.import_module("pygame")
    pygame.init()
    pygame.display.set_caption("Rocks'n'Diamonds Prototype")

    hud_top_padding = hud_top_padding_px(font_size)
    hud_line_gap = hud_line_gap_px(font_size)
    computed_hud_height = hud_height_px(hud_top_padding, hud_line_gap, font_size)
    if hud_height is None:
        hud_height = computed_hud_height
    elif hud_height < computed_hud_height:
        raise ValueError(f"hud_height must be at least {computed_hud_height}")

    screen = pygame.display.set_mode(
        screen_size_px(state, tile_size, hud_top_padding, hud_line_gap, font_size, hud_height)
    )
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", font_size)

    running = True
    frames = 0
    while running:
        if update_graphics_frame(
            state,
            frames,
            pygame.event.get(),
            timing_mode,
            sync_interval,
        ):
            running = False

        render_frame(pygame, screen, font, state, tile_size, 10, hud_top_padding, hud_line_gap)

        pygame.display.flip()
        clock.tick(max(1, int(1000 / tick_ms)))

        frames += 1
        if max_frames > 0 and frames >= max_frames:
            running = False

    pygame.quit()


def run_scripted(state: GameState, moves: str) -> None:
    print("Initial state:")
    print(state.render())
    for move in moves:
        if move not in DIRECTIONS or not state.alive or state.won:
            continue
        step_game(state, move)
    print("\nAfter scripted moves:")
    print(state.render())


def main() -> None:
    parser = argparse.ArgumentParser(description="Rocks'n'Diamonds-style prototype")
    parser.add_argument("--demo", action="store_true", help="Run non-interactive scripted demo")
    parser.add_argument("--moves", default="dddddssaaawwwdd", help="Move sequence for --demo mode")
    parser.add_argument("--turn-based", action="store_true", help="Run turn-based terminal mode")
    parser.add_argument("--realtime", action="store_true", help="Run realtime terminal mode (curses)")
    parser.add_argument("--graphics2d", action="store_true", help="Run realtime 2D graphics mode (pygame)")
    parser.add_argument("--tick-ms", type=int, default=250, help="Milliseconds per game tick")
    parser.add_argument("--tile-size", type=int, default=48, help="Tile size for --graphics2d mode")
    parser.add_argument("--font-size", type=int, default=20, help="HUD font size for --graphics2d mode")
    parser.add_argument("--hud-height", type=int, default=0, help="HUD pixel height for --graphics2d mode (0 = auto)")
    parser.add_argument("--max-frames", type=int, default=0, help="Auto-exit after N frames (test helper)")
    parser.add_argument("--headless", action="store_true", help="Allow SDL dummy-driver runs for headless testing")
    args = parser.parse_args()

    state = parse_level(DEFAULT_LEVEL)

    if args.demo:
        run_scripted(state, args.moves)
    elif args.graphics2d:
        run_interactive_realtime_graphics(
            state,
            args.tick_ms,
            args.tile_size,
            args.max_frames,
            args.headless,
            font_size=args.font_size,
            hud_height=args.hud_height or None,
        )
    elif args.realtime:
        run_interactive_realtime_terminal(state, args.tick_ms)
    else:
        run_interactive_turn_based(state)


if __name__ == "__main__":
    main()
