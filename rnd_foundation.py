#!/usr/bin/env python3
"""A minimal foundation for a Rocks'n'Diamonds-like game.

Includes:
- ASCII demo mode (CI/Codex-friendly)
- Turn-based terminal mode
- Realtime terminal mode (curses)
- Realtime 2D graphics mode (pygame)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, List, Tuple
import argparse
import curses
import importlib
import importlib.util
import os
import sys


class Tile(str, Enum):
    EMPTY = " "
    WALL = "#"
    ROCK = "O"
    DIAMOND = "*"
    PLAYER = "P"


DIRECTIONS = {
    "w": (0, -1),
    "a": (-1, 0),
    "s": (0, 1),
    "d": (1, 0),
}


@dataclass
class GameState:
    grid: List[List[Tile]]
    player_x: int
    player_y: int
    diamonds_total: int
    diamonds_collected: int = 0
    alive: bool = True
    won: bool = False

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

        if target in (Tile.EMPTY, Tile.DIAMOND):
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

        for y in range(self.height - 2, -1, -1):
            for x in range(self.width):
                tile = self.get(x, y)
                if tile not in (Tile.ROCK, Tile.DIAMOND):
                    continue

                below = self.get(x, y + 1)

                if below == Tile.EMPTY:
                    self.set(x, y + 1, tile)
                    self.set(x, y, Tile.EMPTY)
                    continue

                if below == Tile.PLAYER:
                    self.set(x, y + 1, tile)
                    self.set(x, y, Tile.EMPTY)
                    self.alive = False
                    return


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
    "###############",
    "#      O     *#",
    "#   #######   #",
    "# P      O    #",
    "#   *         #",
    "#       O     #",
    "###############",
]


def step_game(state: GameState, action: str | None) -> None:
    if action in DIRECTIONS and state.alive and not state.won:
        dx, dy = DIRECTIONS[action]
        state.try_move_player(dx, dy)
    state.apply_gravity()


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


def run_interactive_realtime_terminal(state: GameState, tick_ms: int) -> None:
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
                step_game(state, action)

    curses.wrapper(_loop)


def run_interactive_realtime_graphics(
    state: GameState,
    tick_ms: int,
    tile_size: int,
    max_frames: int = 0,
    headless: bool = False,
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

    width_px = state.width * tile_size
    hud_height = 70
    height_px = state.height * tile_size + hud_height
    screen = pygame.display.set_mode((width_px, height_px))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 20)

    colors = {
        Tile.EMPTY: (16, 18, 22),
        Tile.WALL: (100, 110, 130),
        Tile.ROCK: (140, 90, 60),
        Tile.DIAMOND: (70, 210, 255),
        Tile.PLAYER: (60, 220, 120),
    }

    running = True
    frames = 0
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    running = False
                elif state.alive and not state.won:
                    action = action_from_pygame_key(event.key)
                    if action is not None:
                        step_game(state, action)

        if state.alive and not state.won:
            step_game(state, None)

        screen.fill((10, 10, 12))

        for y in range(state.height):
            for x in range(state.width):
                tile = state.get(x, y)
                rect = pygame.Rect(x * tile_size, y * tile_size, tile_size, tile_size)
                pygame.draw.rect(screen, colors[tile], rect)
                pygame.draw.rect(screen, (30, 30, 30), rect, 1)

        status = f"Diamonds: {state.diamonds_collected}/{state.diamonds_total}"
        if state.won:
            status += "   YOU WON"
        elif not state.alive:
            status += "   YOU DIED"

        help_text = "Move: WASD/Arrows   Quit: Q"
        screen.blit(font.render(status, True, (245, 245, 245)), (10, state.height * tile_size + 10))
        screen.blit(font.render(help_text, True, (190, 190, 190)), (10, state.height * tile_size + 38))

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
        )
    elif args.realtime:
        run_interactive_realtime_terminal(state, args.tick_ms)
    else:
        run_interactive_turn_based(state)


if __name__ == "__main__":
    main()
