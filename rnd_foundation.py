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


class EngineMode(str, Enum):
    RND = "rnd"
    EM = "em"


DEFAULT_ENGINE_MODE = EngineMode.RND
RND_BASELINE_TIMING_MODE = TimingMode.ASYNC
RND_BASELINE_SYNC_INTERVAL = 1
RND_BASELINE_ASYNC_MOTION_DURATION = 8
RND_BASELINE_HOLD_REPEAT_DELAY = 8
RND_BASELINE_HOLD_REPEAT_INTERVAL = 8
EM_BASELINE_TIMING_MODE = TimingMode.SYNC
EM_BASELINE_SYNC_INTERVAL = 8
EM_BASELINE_MOTION_DURATION = 8
EM_BASELINE_HOLD_REPEAT_DELAY = 8
EM_BASELINE_HOLD_REPEAT_INTERVAL = 8


DIRECTIONS = {
    "w": (0, -1),
    "a": (-1, 0),
    "s": (0, 1),
    "d": (1, 0),
}
SNAP_ACTIONS = {
    "W": (0, -1),
    "A": (-1, 0),
    "S": (0, 1),
    "D": (1, 0),
}


ElementCell = str | None
Cell = Tuple[int, int]
Motion = tuple[ElementCell, Cell, Cell, int]
MotionState = dict[Cell, Motion]
FallInProgress = tuple[ElementCell, Cell, Cell]
FallState = dict[Cell, FallInProgress]
EngineConfig = tuple[TimingMode, int]
HoldState = dict[str, object]


_TILE_SURFACE_CACHE: dict[tuple[Tile, int], object | None] = {}


@dataclass(frozen=True)
class CustomElement:
    name: str
    symbol: str
    diggable: bool = False
    collectible: bool = False
    pushable: bool = False
    can_fall: bool = False
    can_smash: bool = False


ElementLike = Tile | CustomElement


EMPTY_ELEMENT_ID = "empty"
WALL_ELEMENT_ID = "wall"
SAND_ELEMENT_ID = "sand"
SLIME_ELEMENT_ID = "slime"
BRICK_ELEMENT_ID = "brick"
ROCK_ELEMENT_ID = "rock"
DIAMOND_ELEMENT_ID = "diamond"
PLAYER_ELEMENT_ID = "player"


DEFAULT_CUSTOM_ELEMENTS: dict[str, CustomElement] = {
    SAND_ELEMENT_ID: CustomElement(name=SAND_ELEMENT_ID, symbol=".", diggable=True),
    SLIME_ELEMENT_ID: CustomElement(name=SLIME_ELEMENT_ID, symbol="s", diggable=True),
    BRICK_ELEMENT_ID: CustomElement(name=BRICK_ELEMENT_ID, symbol="B"),
    ROCK_ELEMENT_ID: CustomElement(
        name=ROCK_ELEMENT_ID,
        symbol="O",
        pushable=True,
        can_fall=True,
        can_smash=True,
    ),
    DIAMOND_ELEMENT_ID: CustomElement(
        name=DIAMOND_ELEMENT_ID,
        symbol="*",
        collectible=True,
        can_fall=True,
        can_smash=True,
    ),
    WALL_ELEMENT_ID: CustomElement(name=WALL_ELEMENT_ID, symbol="#"),
    PLAYER_ELEMENT_ID: CustomElement(name=PLAYER_ELEMENT_ID, symbol="P"),
}
CUSTOM_ELEMENTS: dict[str, CustomElement] = dict(DEFAULT_CUSTOM_ELEMENTS)


def register_custom_element(registry: dict[str, CustomElement], element: CustomElement) -> None:
    existing = registry.get(element.name)
    if existing is not None and existing != element:
        raise ValueError(f"Custom element name '{element.name}' is already registered")

    for name, registered in registry.items():
        if name != element.name and registered.symbol == element.symbol:
            raise ValueError(f"Custom element symbol '{element.symbol}' is already registered")

    registry[element.name] = element

BUILTIN_TILE_ELEMENTS: dict[Tile, CustomElement] = {
    Tile.EMPTY: CustomElement(name=EMPTY_ELEMENT_ID, symbol=" "),
    Tile.WALL: CUSTOM_ELEMENTS[WALL_ELEMENT_ID],
    Tile.SAND: CUSTOM_ELEMENTS[SAND_ELEMENT_ID],
    Tile.ROCK: CUSTOM_ELEMENTS[ROCK_ELEMENT_ID],
    Tile.DIAMOND: CUSTOM_ELEMENTS[DIAMOND_ELEMENT_ID],
    Tile.PLAYER: CUSTOM_ELEMENTS[PLAYER_ELEMENT_ID],
}
BUILTIN_TILE_SYMBOLS: dict[str, Tile] = {tile.value: tile for tile in Tile}
BUILTIN_TILE_ELEMENT_IDS: dict[Tile, str] = {
    tile: element.name for tile, element in BUILTIN_TILE_ELEMENTS.items()
}
BUILTIN_ELEMENTS: dict[str, CustomElement] = {
    element_id: BUILTIN_TILE_ELEMENTS[tile]
    for tile, element_id in BUILTIN_TILE_ELEMENT_IDS.items()
}
BUILTIN_ELEMENT_ID_TILES: dict[str, Tile] = {
    element_id: tile for tile, element_id in BUILTIN_TILE_ELEMENT_IDS.items()
}


def custom_element_symbols(registry: dict[str, CustomElement]) -> dict[str, CustomElement]:
    return {element.symbol: element for element in registry.values()}


CUSTOM_ELEMENT_SYMBOLS: dict[str, CustomElement] = custom_element_symbols(CUSTOM_ELEMENTS)


@dataclass(frozen=True)
class ParsedCell:
    tile: Tile | None = None
    custom_element_name: str | None = None

    def __post_init__(self) -> None:
        if (self.tile is None) == (self.custom_element_name is None):
            raise ValueError("ParsedCell must contain exactly one of tile or custom_element_name")


def custom_element_for_tile(tile: Tile) -> CustomElement:
    return BUILTIN_TILE_ELEMENTS[tile]


def element_id_for_tile(tile: Tile) -> str:
    return BUILTIN_TILE_ELEMENT_IDS[tile]


def builtin_element_for_id(element_id: str) -> CustomElement:
    try:
        return BUILTIN_ELEMENTS[element_id]
    except KeyError as exc:
        raise ValueError(f"Unknown built-in element id '{element_id}'") from exc


def builtin_tile_for_element_id(element_id: str) -> Tile:
    try:
        return BUILTIN_ELEMENT_ID_TILES[element_id]
    except KeyError as exc:
        raise ValueError(f"Unknown built-in element id '{element_id}'") from exc


def cell_for_tile(tile: Tile) -> ElementCell:
    if tile == Tile.EMPTY:
        return None
    return element_id_for_tile(tile)


def tile_for_cell(cell: ElementCell) -> Tile:
    if cell is None:
        return Tile.EMPTY
    return builtin_tile_for_element_id(cell)


def cell_is_empty(cell: ElementCell) -> bool:
    return cell is None


def tile_for_element_cell(cell: ElementCell, registry: dict[str, CustomElement]) -> Tile:
    return compatibility_tile_for_element_cell(cell, registry)


def surrogate_tile_for_element_cell(cell: ElementCell, registry: dict[str, CustomElement]) -> Tile | None:
    if cell is None:
        return Tile.EMPTY
    if cell in BUILTIN_ELEMENTS:
        return builtin_tile_for_element_id(cell)

    custom_element = registry.get(cell)
    if custom_element is None:
        raise ValueError(f"Unknown custom element '{cell}'")
    return surrogate_tile_for_custom_element(custom_element)


def compatibility_tile_for_element_cell(cell: ElementCell, registry: dict[str, CustomElement]) -> Tile:
    surrogate_tile = surrogate_tile_for_element_cell(cell, registry)
    if surrogate_tile is not None:
        return surrogate_tile
    raise ValueError(f"Custom element '{cell}' is not yet mapped to a built-in tile")


def compatibility_tile_for_level_symbol(symbol: str, registry: dict[str, CustomElement]) -> Tile:
    tile = tile_for_symbol(symbol)
    if tile is not None:
        return tile
    element = custom_element_symbols(registry).get(symbol)
    if element is not None:
        surrogate_tile = surrogate_tile_for_custom_element(element)
        if surrogate_tile is not None:
            return surrogate_tile
        raise ValueError(f"Custom element symbol '{symbol}' is not yet mapped to a built-in tile")
    raise ValueError(f"Unsupported tile '{symbol}'")


def parsed_cell_for_cell(cell: ElementCell) -> ParsedCell:
    if cell is None:
        return ParsedCell(tile=Tile.EMPTY)
    if cell in BUILTIN_ELEMENTS:
        return ParsedCell(tile=builtin_tile_for_element_id(cell))
    return ParsedCell(custom_element_name=cell)


def cell_for_parsed_cell(cell: ParsedCell) -> ElementCell:
    if cell.tile is not None:
        return cell_for_tile(cell.tile)
    return cell.custom_element_name


def element_cell_for_parsed_cell(cell: ParsedCell) -> ElementCell:
    return cell_for_parsed_cell(cell)


def parsed_cell_for_tile(tile: Tile) -> ParsedCell:
    return ParsedCell(tile=tile)


def parsed_cell_element(cell: ParsedCell, registry: dict[str, CustomElement]) -> ElementLike:
    element_cell = element_cell_for_parsed_cell(cell)
    if element_cell is None or element_cell in BUILTIN_ELEMENTS:
        return tile_for_element_cell(element_cell, registry)
    custom_element = registry.get(element_cell)
    if custom_element is None:
        raise ValueError(f"Unknown custom element '{element_cell}'")
    return custom_element


def tile_for_symbol(symbol: str) -> Tile | None:
    return BUILTIN_TILE_SYMBOLS.get(symbol)


def custom_element_for_symbol(symbol: str) -> CustomElement | None:
    return CUSTOM_ELEMENT_SYMBOLS.get(symbol)


def surrogate_tile_for_custom_element(element: CustomElement) -> Tile | None:
    if element.diggable and not element.collectible and not element.pushable and not element.can_fall:
        return Tile.SAND
    if element.collectible and element.can_fall and not element.diggable and not element.pushable:
        return Tile.DIAMOND
    if element.pushable and element.can_fall and not element.diggable and not element.collectible:
        return Tile.ROCK
    return None


def tile_for_level_symbol(symbol: str) -> Tile:
    return compatibility_tile_for_level_symbol(symbol, CUSTOM_ELEMENTS)


def parsed_cell_for_level_symbol(
    symbol: str,
    registry: dict[str, CustomElement],
) -> ParsedCell:
    tile = tile_for_symbol(symbol)
    if tile is not None:
        return parsed_cell_for_tile(tile)
    element = custom_element_symbols(registry).get(symbol)
    if element is not None:
        return ParsedCell(custom_element_name=element.name)
    raise ValueError(f"Unsupported tile '{symbol}'")


def parse_level_cells(
    lines: Iterable[str],
    registry: dict[str, CustomElement],
) -> list[list[ParsedCell]]:
    raw = [line.rstrip("\n") for line in lines if line.strip("\n")]
    if not raw:
        raise ValueError("Level is empty")

    width = len(raw[0])
    if any(len(row) != width for row in raw):
        raise ValueError("All level rows must have equal width")

    grid: list[list[ParsedCell]] = []
    for y, row in enumerate(raw):
        grid_row: list[ParsedCell] = []
        for x, ch in enumerate(row):
            try:
                grid_row.append(parsed_cell_for_level_symbol(ch, registry))
            except ValueError as exc:
                raise ValueError(f"{exc} at ({x},{y})") from None
        grid.append(grid_row)

    return grid


def parse_level_element_cells(
    lines: Iterable[str],
    registry: dict[str, CustomElement],
) -> list[list[ElementCell]]:
    parsed_grid = parse_level_cells(lines, registry)
    return [[cell_for_parsed_cell(cell) for cell in row] for row in parsed_grid]


def tile_grid_for_element_cells(
    grid: list[list[ElementCell]],
    registry: dict[str, CustomElement],
) -> list[list[Tile]]:
    return [[tile_for_element_cell(cell, registry) for cell in row] for row in grid]


def custom_element_for(element: ElementLike) -> CustomElement:
    if isinstance(element, CustomElement):
        return element
    return custom_element_for_tile(element)


def custom_element_for_cell(cell: ElementCell, registry: dict[str, CustomElement]) -> CustomElement | None:
    if cell is None:
        return None
    if cell in BUILTIN_ELEMENTS:
        return builtin_element_for_id(cell)
    custom_element = registry.get(cell)
    if custom_element is None:
        raise ValueError(f"Unknown custom element '{cell}'")
    return custom_element


def is_diggable(element: ElementLike) -> bool:
    return custom_element_for(element).diggable


def is_collectible(element: ElementLike) -> bool:
    return custom_element_for(element).collectible


def is_pushable(element: ElementLike) -> bool:
    return custom_element_for(element).pushable


def can_fall_element(element: ElementLike) -> bool:
    return custom_element_for(element).can_fall


def can_smash_element(element: ElementLike) -> bool:
    return custom_element_for(element).can_smash


def cell_is_diggable(cell: ElementCell, registry: dict[str, CustomElement]) -> bool:
    element = custom_element_for_cell(cell, registry)
    return element.diggable if element is not None else False


def cell_is_collectible(cell: ElementCell, registry: dict[str, CustomElement]) -> bool:
    element = custom_element_for_cell(cell, registry)
    return element.collectible if element is not None else False


def cell_is_pushable(cell: ElementCell, registry: dict[str, CustomElement]) -> bool:
    element = custom_element_for_cell(cell, registry)
    return element.pushable if element is not None else False


def cell_can_fall(cell: ElementCell, registry: dict[str, CustomElement]) -> bool:
    element = custom_element_for_cell(cell, registry)
    return element.can_fall if element is not None else False


def cell_can_smash(cell: ElementCell, registry: dict[str, CustomElement]) -> bool:
    element = custom_element_for_cell(cell, registry)
    return element.can_smash if element is not None else False


def cell_is_player(cell: ElementCell, registry: dict[str, CustomElement]) -> bool:
    element = custom_element_for_cell(cell, registry)
    return element is not None and element.name == PLAYER_ELEMENT_ID


def cell_is_motion_trackable(cell: ElementCell, registry: dict[str, CustomElement]) -> bool:
    return cell_can_fall(cell, registry)


def symbol_for_element_cell(cell: ElementCell, registry: dict[str, CustomElement]) -> str:
    element = custom_element_for_cell(cell, registry)
    if element is None:
        return " "
    return element.symbol


def text_render_symbol_for_position(state: "GameState", x: int, y: int) -> str:
    if state.is_blocked_fall_destination(x, y):
        return "v"
    return symbol_for_element_cell(state.get_cell(x, y), CUSTOM_ELEMENTS)


def parsed_cell_is_diggable(cell: ParsedCell, registry: dict[str, CustomElement]) -> bool:
    return cell_is_diggable(element_cell_for_parsed_cell(cell), registry)


def parsed_cell_is_collectible(cell: ParsedCell, registry: dict[str, CustomElement]) -> bool:
    return cell_is_collectible(element_cell_for_parsed_cell(cell), registry)


def parsed_cell_is_pushable(cell: ParsedCell, registry: dict[str, CustomElement]) -> bool:
    return cell_is_pushable(element_cell_for_parsed_cell(cell), registry)


def parsed_cell_can_fall(cell: ParsedCell, registry: dict[str, CustomElement]) -> bool:
    return cell_can_fall(element_cell_for_parsed_cell(cell), registry)


def parsed_cell_can_smash(cell: ParsedCell, registry: dict[str, CustomElement]) -> bool:
    return cell_can_smash(element_cell_for_parsed_cell(cell), registry)


def parsed_cell_is_empty(cell: ParsedCell) -> bool:
    return cell_is_empty(element_cell_for_parsed_cell(cell))


def parsed_cell_is_player(cell: ParsedCell) -> bool:
    return element_cell_for_parsed_cell(cell) == PLAYER_ELEMENT_ID


@dataclass
class GameState:
    grid: List[List[ElementCell]]
    player_x: int
    player_y: int
    diamonds_total: int
    diamonds_collected: int = 0
    alive: bool = True
    won: bool = False
    falling_positions: Set[Tuple[int, int]] = field(default_factory=set)
    just_pushed_positions: Set[Tuple[int, int]] = field(default_factory=set)
    recently_pushed_positions: Set[Tuple[int, int]] = field(default_factory=set)
    motion_locked_positions: Set[Tuple[int, int]] = field(default_factory=set)
    fall_state: FallState = field(default_factory=dict)
    pending_action: str | None = None

    @property
    def width(self) -> int:
        return len(self.grid[0])

    @property
    def height(self) -> int:
        return len(self.grid)

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def get_tile(self, x: int, y: int) -> Tile:
        return tile_for_element_cell(self.grid[y][x], CUSTOM_ELEMENTS)

    def set_tile(self, x: int, y: int, tile: Tile) -> None:
        self.grid[y][x] = cell_for_tile(tile)

    def get(self, x: int, y: int) -> Tile:
        return self.get_tile(x, y)

    def set(self, x: int, y: int, tile: Tile) -> None:
        self.set_tile(x, y, tile)

    def get_cell(self, x: int, y: int) -> ElementCell:
        return self.grid[y][x]

    def set_cell(self, x: int, y: int, cell: ElementCell) -> None:
        self.grid[y][x] = cell

    def blocked_fall_destinations(self) -> Set[Tuple[int, int]]:
        return blocked_fall_destinations(self.fall_state)

    def is_blocked_fall_destination(self, x: int, y: int) -> bool:
        return (x, y) in self.blocked_fall_destinations()

    def reserved_cells(self) -> Set[Tuple[int, int]]:
        return self.blocked_fall_destinations()

    def is_reserved_cell(self, x: int, y: int) -> bool:
        return (x, y) in self.reserved_cells()

    def is_open_for_entry(self, x: int, y: int) -> bool:
        return cell_is_empty(self.get_cell(x, y)) and not self.is_reserved_cell(x, y)

    def is_open_for_push_target(self, x: int, y: int) -> bool:
        return self.is_open_for_entry(x, y)

    def fall_origin_cells(self) -> Set[Tuple[int, int]]:
        return {fall_start_cell(fall) for fall in active_falls(self.fall_state)}

    def is_fall_origin_cell(self, x: int, y: int) -> bool:
        return (x, y) in self.fall_origin_cells()

    def render_lines(self) -> List[str]:
        return [
            "".join(text_render_symbol_for_position(self, x, y) for x in range(self.width))
            for y in range(self.height)
        ]

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

        target = self.get_cell(tx, ty)

        if self.is_fall_origin_cell(tx, ty):
            return

        if self.is_open_for_entry(tx, ty) or cell_is_diggable(target, CUSTOM_ELEMENTS) or cell_is_collectible(target, CUSTOM_ELEMENTS):
            if cell_is_collectible(target, CUSTOM_ELEMENTS):
                self.diamonds_collected += 1
                if self.diamonds_collected >= self.diamonds_total:
                    self.won = True
            self._move_player_to(tx, ty)
            return

        if cell_is_pushable(target, CUSTOM_ELEMENTS) and dy == 0:
            if (tx, ty) in self.motion_locked_positions:
                return
            if (tx, ty) in self.recently_pushed_positions:
                return
            push_x, push_y = tx + dx, ty
            if (
                self.in_bounds(push_x, push_y)
                and not self.is_blocked_fall_destination(push_x, push_y)
                and cell_is_empty(self.get_cell(push_x, push_y))
            ):
                self.set_cell(push_x, push_y, target)
                self.just_pushed_positions = {(push_x, push_y)}
                self.recently_pushed_positions = {(push_x, push_y)}
                self._move_player_to(tx, ty)

    def try_snap(self, dx: int, dy: int) -> None:
        if not self.alive or self.won:
            return

        tx, ty = self.player_x + dx, self.player_y + dy
        if not self.in_bounds(tx, ty):
            return

        target = self.get_cell(tx, ty)
        if self.is_fall_origin_cell(tx, ty):
            return

        if cell_is_diggable(target, CUSTOM_ELEMENTS):
            self.set_cell(tx, ty, None)
            return

        if cell_is_collectible(target, CUSTOM_ELEMENTS):
            self.set_cell(tx, ty, None)
            self.diamonds_collected += 1
            if self.diamonds_collected >= self.diamonds_total:
                self.won = True
            return

        if cell_is_pushable(target, CUSTOM_ELEMENTS) and dy == 0:
            if (tx, ty) in self.motion_locked_positions:
                return
            if (tx, ty) in self.recently_pushed_positions:
                return
            push_x, push_y = tx + dx, ty
            if (
                self.in_bounds(push_x, push_y)
                and not self.is_blocked_fall_destination(push_x, push_y)
                and cell_is_empty(self.get_cell(push_x, push_y))
            ):
                self.set_cell(push_x, push_y, target)
                self.set_cell(tx, ty, None)
                self.just_pushed_positions = {(push_x, push_y)}
                self.recently_pushed_positions = {(push_x, push_y)}

    def _move_player_to(self, x: int, y: int) -> None:
        self.set_cell(self.player_x, self.player_y, None)
        self.player_x, self.player_y = x, y
        self.set_cell(self.player_x, self.player_y, PLAYER_ELEMENT_ID)

    def apply_gravity(self, defer_falls: bool = False) -> None:
        if not self.alive or self.won:
            return

        blocked_destinations = self.blocked_fall_destinations()
        if not defer_falls:
            self.fall_state.clear()
        just_pushed_positions = set(self.just_pushed_positions)
        original_grid = [row.copy() for row in self.grid]
        new_falling_positions: Set[Tuple[int, int]] = set()
        for y in range(self.height - 2, -1, -1):
            for x in range(self.width):
                cell = original_grid[y][x]
                if not cell_can_fall(cell, CUSTOM_ELEMENTS):
                    continue
                if (x, y) in just_pushed_positions:
                    continue
                if (x, y) in self.motion_locked_positions:
                    continue

                was_falling = (x, y) in self.falling_positions
                below = original_grid[y + 1][x]

                if cell_is_empty(below) and (x, y + 1) not in blocked_destinations:
                    set_fall_in_progress(
                        self.fall_state,
                        make_fall_in_progress(cell, (x, y), (x, y + 1)),
                    )
                    if not defer_falls:
                        self.set_cell(x, y + 1, cell)
                        self.set_cell(x, y, None)
                        new_falling_positions.add((x, y + 1))
                    continue

                if cell_is_player(below, CUSTOM_ELEMENTS) and was_falling:
                    set_fall_in_progress(
                        self.fall_state,
                        make_fall_in_progress(cell, (x, y), (x, y + 1)),
                    )
                    if not defer_falls:
                        self.set_cell(x, y + 1, cell)
                        self.set_cell(x, y, None)
                        new_falling_positions.add((x, y + 1))
                        self.falling_positions = new_falling_positions
                    else:
                        self.falling_positions = set()
                    self.alive = False
                    return

        self.falling_positions = new_falling_positions
        self.just_pushed_positions.clear()
        self.recently_pushed_positions = just_pushed_positions


def parse_level(lines: Iterable[str]) -> GameState:
    element_cells = parse_level_element_cells(lines, CUSTOM_ELEMENTS)
    player_pos: Tuple[int, int] | None = None
    diamonds_total = 0

    for y, row in enumerate(element_cells):
        for x, cell in enumerate(row):
            if cell_is_player(cell, CUSTOM_ELEMENTS):
                if player_pos is not None:
                    raise ValueError("Only one player is allowed")
                player_pos = (x, y)
            if cell_is_collectible(cell, CUSTOM_ELEMENTS):
                diamonds_total += 1

    if player_pos is None:
        raise ValueError("Level must contain a player 'P'")

    return GameState(
        grid=element_cells,
        player_x=player_pos[0],
        player_y=player_pos[1],
        diamonds_total=diamonds_total,
    )


DEFAULT_LEVEL = [
    "########################################",
    "#ss.... ..*.O .....O.O....... ....O....#",
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
    timing_mode: TimingMode = RND_BASELINE_TIMING_MODE,
    sync_interval: int = RND_BASELINE_SYNC_INTERVAL,
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


def engine_config(engine_mode: EngineMode) -> EngineConfig:
    if engine_mode == EngineMode.RND:
        return (RND_BASELINE_TIMING_MODE, RND_BASELINE_SYNC_INTERVAL)
    if engine_mode == EngineMode.EM:
        return (EM_BASELINE_TIMING_MODE, EM_BASELINE_SYNC_INTERVAL)
    raise ValueError(f"Unsupported engine mode: {engine_mode}")


def engine_motion_duration_frames(engine_mode: EngineMode) -> int:
    if engine_mode == EngineMode.RND:
        return RND_BASELINE_ASYNC_MOTION_DURATION
    if engine_mode == EngineMode.EM:
        return EM_BASELINE_MOTION_DURATION
    raise ValueError(f"Unsupported engine mode: {engine_mode}")


def engine_hold_repeat_frames(engine_mode: EngineMode) -> tuple[int, int]:
    if engine_mode == EngineMode.RND:
        return (RND_BASELINE_HOLD_REPEAT_DELAY, RND_BASELINE_HOLD_REPEAT_INTERVAL)
    if engine_mode == EngineMode.EM:
        return (EM_BASELINE_HOLD_REPEAT_DELAY, EM_BASELINE_HOLD_REPEAT_INTERVAL)
    raise ValueError(f"Unsupported engine mode: {engine_mode}")


def step_game(state: GameState, action: str | None, defer_falls: bool = True) -> None:
    if defer_falls and not state.motion_locked_positions:
        complete_pending_falls(state)
    if action in DIRECTIONS and state.alive and not state.won:
        dx, dy = DIRECTIONS[action]
        state.try_move_player(dx, dy)
    elif action in SNAP_ACTIONS and state.alive and not state.won:
        dx, dy = SNAP_ACTIONS[action]
        state.try_snap(dx, dy)
    state.apply_gravity(defer_falls=defer_falls)


def buffer_action(state: GameState, action: str | None) -> None:
    if action in DIRECTIONS or action in SNAP_ACTIONS:
        state.pending_action = action


def consume_buffered_action(state: GameState) -> str | None:
    action = state.pending_action
    state.pending_action = None
    return action


def step_realtime_frame(
    state: GameState,
    frame_number: int,
    action: str | None,
    timing_mode: TimingMode = RND_BASELINE_TIMING_MODE,
    sync_interval: int = RND_BASELINE_SYNC_INTERVAL,
    defer_falls: bool = True,
) -> None:
    if timing_mode == TimingMode.ASYNC:
        buffer_action(state, action)
        if not is_update_frame(frame_number, timing_mode, sync_interval):
            return
        step_game(state, consume_buffered_action(state), defer_falls=defer_falls)
        return

    if timing_mode == TimingMode.SYNC:
        buffer_action(state, action)
        if not is_update_frame(frame_number, timing_mode, sync_interval):
            return
        step_game(state, consume_buffered_action(state), defer_falls=defer_falls)
        return

    if not is_update_frame(frame_number, timing_mode, sync_interval):
        return
    step_game(state, action, defer_falls=defer_falls)


def can_player_take_action(state: GameState, action: str | None) -> bool:
    if action not in DIRECTIONS:
        return False
    if not state.alive or state.won:
        return False

    dx, dy = DIRECTIONS[action]
    tx, ty = state.player_x + dx, state.player_y + dy
    if not state.in_bounds(tx, ty):
        return False

    target = state.get_cell(tx, ty)
    if state.is_blocked_fall_destination(tx, ty):
        return False
    if state.is_fall_origin_cell(tx, ty):
        return False
    if cell_is_empty(target) or cell_is_diggable(target, CUSTOM_ELEMENTS) or cell_is_collectible(target, CUSTOM_ELEMENTS):
        return True

    if cell_is_pushable(target, CUSTOM_ELEMENTS) and dy == 0:
        if (tx, ty) in state.motion_locked_positions:
            return False
        if (tx, ty) in state.recently_pushed_positions:
            return False
        push_x, push_y = tx + dx, ty
        return (
            state.in_bounds(push_x, push_y)
            and not state.is_blocked_fall_destination(push_x, push_y)
            and cell_is_empty(state.get_cell(push_x, push_y))
        )

    return False


def action_from_turn_input(text: str) -> str | None:
    if text in DIRECTIONS or text in SNAP_ACTIONS:
        return text
    return None


def action_from_curses_key(key: int) -> str | None:
    if key in (ord("w"), ord("W"), curses.KEY_UP):
        return "w"
    if key in (ord("a"), ord("A"), curses.KEY_LEFT):
        return "a"
    if key in (ord("s"), ord("S"), curses.KEY_DOWN):
        return "s"
    if key in (ord("d"), ord("D"), curses.KEY_RIGHT):
        return "d"
    if key == 23:
        return "W"
    if key == 1:
        return "A"
    if key == 19:
        return "S"
    if key == 4:
        return "D"
    return None


def action_from_pygame_key(key: int, ctrl_held: bool = False) -> str | None:
    pygame = importlib.import_module("pygame")
    if ctrl_held:
        if key in (pygame.K_w, pygame.K_UP):
            return "W"
        if key in (pygame.K_a, pygame.K_LEFT):
            return "A"
        if key in (pygame.K_s, pygame.K_DOWN):
            return "S"
        if key in (pygame.K_d, pygame.K_RIGHT):
            return "D"
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
        ctrl_held = bool(getattr(event, "mod", 0) & getattr(pygame, "KMOD_CTRL", 0))
        action = action_from_pygame_key(getattr(event, "key", None), ctrl_held)
        if action is not None:
            return action
    return None


def action_from_pygame_pressed_keys(pressed: object) -> str | None:
    pygame = importlib.import_module("pygame")
    if pressed[pygame.K_w] or pressed[pygame.K_UP]:
        return "w"
    if pressed[pygame.K_a] or pressed[pygame.K_LEFT]:
        return "a"
    if pressed[pygame.K_s] or pressed[pygame.K_DOWN]:
        return "s"
    if pressed[pygame.K_d] or pressed[pygame.K_RIGHT]:
        return "d"
    return None


def held_actions_from_pygame_pressed_keys(pressed: object) -> tuple[str, ...]:
    pygame = importlib.import_module("pygame")
    actions: list[str] = []
    if pressed[pygame.K_w] or pressed[pygame.K_UP]:
        actions.append("w")
    if pressed[pygame.K_s] or pressed[pygame.K_DOWN]:
        actions.append("s")
    if pressed[pygame.K_a] or pressed[pygame.K_LEFT]:
        actions.append("a")
    if pressed[pygame.K_d] or pressed[pygame.K_RIGHT]:
        actions.append("d")
    return tuple(actions)


def make_hold_state() -> HoldState:
    return {"action": None, "press_frame": None, "last_output_action": None}


def repeated_held_action(
    hold_state: HoldState,
    frame_number: int,
    held_action: str | tuple[str, ...] | None,
    initial_delay_frames: int,
    repeat_interval_frames: int,
) -> str | None:
    if initial_delay_frames <= 0:
        raise ValueError("initial_delay_frames must be positive")
    if repeat_interval_frames <= 0:
        raise ValueError("repeat_interval_frames must be positive")

    if held_action is None:
        held_actions: tuple[str, ...] = ()
    elif isinstance(held_action, str):
        held_actions = (held_action,)
    else:
        held_actions = held_action

    if not held_actions:
        hold_state["action"] = None
        hold_state["press_frame"] = None
        hold_state["last_output_action"] = None
        return None

    if hold_state["action"] != held_actions:
        previous_output_action = hold_state["last_output_action"]
        hold_state["action"] = held_actions
        if previous_output_action not in held_actions:
            hold_state["press_frame"] = frame_number
            hold_state["last_output_action"] = None
            return None

    press_frame = hold_state["press_frame"]
    if not isinstance(press_frame, int):
        hold_state["press_frame"] = frame_number
        return None

    elapsed_frames = frame_number - press_frame
    if elapsed_frames < initial_delay_frames:
        return None
    if (elapsed_frames - initial_delay_frames) % repeat_interval_frames == 0:
        if len(held_actions) == 1:
            action = held_actions[0]
        elif len(held_actions) == 2:
            last_output_action = hold_state["last_output_action"]
            if last_output_action == held_actions[0]:
                action = held_actions[1]
            else:
                action = held_actions[0]
        else:
            action = held_actions[0]
        hold_state["last_output_action"] = action
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


def background_color() -> Tuple[int, int, int]:
    return (8, 10, 14)


def board_background_color() -> Tuple[int, int, int]:
    return (18, 22, 28)


def hud_background_color() -> Tuple[int, int, int]:
    return (12, 14, 18)


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


def color_for_element_id(element_id: str | None) -> Tuple[int, int, int]:
    colors = {
        None: tile_color(Tile.EMPTY),
        EMPTY_ELEMENT_ID: tile_color(Tile.EMPTY),
        WALL_ELEMENT_ID: tile_color(Tile.WALL),
        SAND_ELEMENT_ID: tile_color(Tile.SAND),
        SLIME_ELEMENT_ID: (220, 90, 90),
        BRICK_ELEMENT_ID: (150, 80, 80),
        ROCK_ELEMENT_ID: tile_color(Tile.ROCK),
        DIAMOND_ELEMENT_ID: tile_color(Tile.DIAMOND),
        PLAYER_ELEMENT_ID: tile_color(Tile.PLAYER),
    }
    return colors.get(element_id, (220, 90, 90))


def element_color(element: ElementLike) -> Tuple[int, int, int]:
    if isinstance(element, Tile):
        return tile_color(element)
    if element.name in CUSTOM_ELEMENTS:
        return color_for_element_id(element.name)

    if element.symbol == ".":
        return tile_color(Tile.SAND)
    if element.symbol == "O":
        return tile_color(Tile.ROCK)
    if element.symbol == "*":
        return tile_color(Tile.DIAMOND)
    if element.symbol == "#":
        return tile_color(Tile.WALL)
    if element.symbol == "P":
        return tile_color(Tile.PLAYER)
    if element.symbol == " ":
        return tile_color(Tile.EMPTY)
    return (220, 90, 90)


def element_appearance(element: ElementLike, tile_size: int) -> Tuple[object | None, Tuple[int, int, int]]:
    if isinstance(element, Tile):
        return tile_appearance(element, tile_size)
    return (None, element_color(element))


def element_cell_color(cell: ElementCell, registry: dict[str, CustomElement]) -> Tuple[int, int, int]:
    _ = registry
    return color_for_element_id(cell)


def element_cell_appearance(
    cell: ElementCell,
    registry: dict[str, CustomElement],
    tile_size: int,
) -> Tuple[object | None, Tuple[int, int, int]]:
    if cell in BUILTIN_ELEMENT_ID_TILES:
        tile = builtin_tile_for_element_id(cell)
        return tile_appearance(tile, tile_size)
    return (None, element_cell_color(cell, registry))


def parsed_cell_appearance(
    cell: ParsedCell,
    registry: dict[str, CustomElement],
    tile_size: int,
) -> Tuple[object | None, Tuple[int, int, int]]:
    return element_cell_appearance(cell_for_parsed_cell(cell), registry, tile_size)


def tile_rect(pygame: object, x: int, y: int, tile_size: int) -> object:
    return pygame.Rect(x * tile_size, y * tile_size, tile_size, tile_size)


def make_motion(tile: ElementCell | Tile, start_cell: Cell, destination_cell: Cell, start_frame: int) -> Motion:
    if start_frame < 0:
        raise ValueError("start_frame must be non-negative")
    if start_cell == destination_cell:
        raise ValueError("motion must move between different cells")
    motion_cell = cell_for_tile(tile) if isinstance(tile, Tile) else tile
    return (motion_cell, start_cell, destination_cell, start_frame)


def motion_cell(motion: Motion) -> ElementCell:
    return motion[0]


def motion_tile(motion: Motion) -> Tile:
    return tile_for_element_cell(motion_cell(motion), CUSTOM_ELEMENTS)


def motion_start_cell(motion: Motion) -> Cell:
    return motion[1]


def motion_destination_cell(motion: Motion) -> Cell:
    return motion[2]


def motion_start_frame(motion: Motion) -> int:
    return motion[3]


def make_motion_state() -> MotionState:
    return {}


def make_fall_in_progress(cell: ElementCell | Tile, start_cell: Cell, destination_cell: Cell) -> FallInProgress:
    if start_cell == destination_cell:
        raise ValueError("fall must move between different cells")
    fall_cell = cell_for_tile(cell) if isinstance(cell, Tile) else cell
    return (fall_cell, start_cell, destination_cell)


def fall_cell(fall: FallInProgress) -> ElementCell:
    return fall[0]


def fall_start_cell(fall: FallInProgress) -> Cell:
    return fall[1]


def fall_destination_cell(fall: FallInProgress) -> Cell:
    return fall[2]


def make_fall_state() -> FallState:
    return {}


def set_fall_in_progress(fall_state: FallState, fall: FallInProgress) -> None:
    fall_state[fall_destination_cell(fall)] = fall


def get_fall_in_progress(fall_state: FallState, cell: Cell) -> FallInProgress | None:
    return fall_state.get(cell)


def remove_fall_in_progress(fall_state: FallState, cell: Cell) -> FallInProgress | None:
    return fall_state.pop(cell, None)


def active_falls(fall_state: FallState) -> list[FallInProgress]:
    return list(fall_state.values())


def blocked_fall_destinations(fall_state: FallState) -> set[Cell]:
    return set(fall_state)


def complete_fall(state: "GameState", cell: Cell) -> FallInProgress | None:
    fall = remove_fall_in_progress(state.fall_state, cell)
    if fall is None:
        return None

    start_x, start_y = fall_start_cell(fall)
    dest_x, dest_y = fall_destination_cell(fall)
    state.set_cell(start_x, start_y, None)
    state.set_cell(dest_x, dest_y, fall_cell(fall))
    state.falling_positions.add((dest_x, dest_y))
    return fall


def complete_pending_falls(state: "GameState") -> list[FallInProgress]:
    completed: list[FallInProgress] = []
    for cell in sorted(state.blocked_fall_destinations(), key=lambda position: (position[1], position[0]), reverse=True):
        fall = complete_fall(state, cell)
        if fall is not None:
            completed.append(fall)
    return completed


def set_motion(motion_state: MotionState, motion: Motion) -> None:
    motion_state[motion_destination_cell(motion)] = motion


def get_motion(motion_state: MotionState, cell: Cell) -> Motion | None:
    return motion_state.get(cell)


def remove_motion(motion_state: MotionState, cell: Cell) -> Motion | None:
    return motion_state.pop(cell, None)


def active_motions(motion_state: MotionState) -> list[Motion]:
    return list(motion_state.values())


def has_active_player_motion(motion_state: MotionState) -> bool:
    return any(motion_cell(motion) == PLAYER_ELEMENT_ID for motion in active_motions(motion_state))


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
    timing_mode: TimingMode = RND_BASELINE_TIMING_MODE,
    sync_interval: int = RND_BASELINE_SYNC_INTERVAL,
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
        elapsed_frames = current_frame - motion_start_frame(motion)
        return clamp_progress(elapsed_frames / duration_frames)

    raise ValueError(f"Unsupported timing mode: {timing_mode}")


def motion_is_complete(
    motion: Motion,
    current_frame: int,
    duration_frames: int,
    timing_mode: TimingMode = RND_BASELINE_TIMING_MODE,
    sync_interval: int = RND_BASELINE_SYNC_INTERVAL,
) -> bool:
    return motion_progress(motion, current_frame, duration_frames, timing_mode, sync_interval) >= 1.0


def start_motion(
    motion_state: MotionState,
    tile: ElementCell | Tile,
    start_cell: Cell,
    destination_cell: Cell,
    start_frame: int,
) -> Motion:
    motion = make_motion(tile, start_cell, destination_cell, start_frame)
    set_motion(motion_state, motion)
    return motion


def complete_motion(motion_state: MotionState, cell: Cell) -> Motion | None:
    return remove_motion(motion_state, cell)


def update_motion_state(
    motion_state: MotionState,
    current_frame: int,
    duration_frames: int,
    timing_mode: TimingMode = RND_BASELINE_TIMING_MODE,
    sync_interval: int = RND_BASELINE_SYNC_INTERVAL,
) -> list[Motion]:
    completed: list[Motion] = []
    for motion in list(active_motions(motion_state)):
        if motion_is_complete(motion, current_frame, duration_frames, timing_mode, sync_interval):
            removed = remove_motion(motion_state, motion_destination_cell(motion))
            if removed is not None:
                completed.append(removed)
    return completed


def default_motion_duration_frames(
    timing_mode: TimingMode = RND_BASELINE_TIMING_MODE,
    sync_interval: int = RND_BASELINE_SYNC_INTERVAL,
    async_duration_frames: int = RND_BASELINE_ASYNC_MOTION_DURATION,
) -> int:
    if async_duration_frames <= 0:
        raise ValueError("async_duration_frames must be positive")
    if sync_interval <= 0:
        raise ValueError("sync_interval must be positive")
    if timing_mode == TimingMode.ASYNC:
        return async_duration_frames
    if timing_mode == TimingMode.SYNC:
        return sync_interval
    raise ValueError(f"Unsupported timing mode: {timing_mode}")


def player_cell(state: GameState) -> Cell:
    return (state.player_x, state.player_y)


def track_player_motion(
    motion_state: MotionState,
    start_cell: Cell,
    state: GameState,
    frame_number: int,
) -> Motion | None:
    destination_cell = player_cell(state)
    if start_cell == destination_cell:
        return None
    return start_motion(motion_state, PLAYER_ELEMENT_ID, start_cell, destination_cell, frame_number)


def moving_object_cells(state: GameState) -> dict[ElementCell, set[Cell]]:
    cells: dict[ElementCell, set[Cell]] = {}
    for y in range(state.height):
        for x in range(state.width):
            tile = state.get_cell(x, y)
            if cell_is_motion_trackable(tile, CUSTOM_ELEMENTS):
                cells.setdefault(tile, set()).add((x, y))
    return cells


def find_moving_object_motions(
    before_cells: dict[ElementCell, set[Cell]],
    state: GameState,
    frame_number: int,
) -> list[Motion]:
    motions: list[Motion] = []
    after_cells = moving_object_cells(state)

    for tile in sorted(set(before_cells) | set(after_cells), key=lambda value: "" if value is None else value):
        moved_from = before_cells.get(tile, set()) - after_cells.get(tile, set())
        for start_cell in sorted(moved_from):
            candidate_destinations = (
                (start_cell[0], start_cell[1] + 1),
                (start_cell[0] - 1, start_cell[1]),
                (start_cell[0] + 1, start_cell[1]),
            )
            for destination_cell in candidate_destinations:
                if (
                    destination_cell in after_cells.get(tile, set())
                    and destination_cell not in before_cells.get(tile, set())
                ):
                    motions.append(make_motion(tile, start_cell, destination_cell, frame_number))
                    break

    return motions


def find_vertical_falling_motions(
    before_cells: dict[ElementCell, set[Cell]],
    state: GameState,
    frame_number: int,
) -> list[Motion]:
    falls = active_falls(state.fall_state)
    if falls:
        return [
            make_motion(fall_cell(fall), fall_start_cell(fall), fall_destination_cell(fall), frame_number)
            for fall in falls
        ]
    return [
        motion
        for motion in find_moving_object_motions(before_cells, state, frame_number)
        if motion_destination_cell(motion)[1] == motion_start_cell(motion)[1] + 1
    ]


def track_moving_object_motions(
    motion_state: MotionState,
    before_cells: dict[ElementCell, set[Cell]],
    state: GameState,
    frame_number: int,
) -> list[Motion]:
    motions = find_moving_object_motions(before_cells, state, frame_number)
    for motion in motions:
        set_motion(motion_state, motion)
    return motions


def track_falling_motions(
    motion_state: MotionState,
    before_cells: dict[ElementCell, set[Cell]],
    state: GameState,
    frame_number: int,
) -> list[Motion]:
    motions = find_vertical_falling_motions(before_cells, state, frame_number)
    new_motions: list[Motion] = []
    for motion in motions:
        if get_motion(motion_state, motion_destination_cell(motion)) is None:
            set_motion(motion_state, motion)
            new_motions.append(motion)
    return new_motions


def motion_position_px(
    motion: Motion,
    current_frame: int,
    tile_size: int,
    duration_frames: int,
    timing_mode: TimingMode = RND_BASELINE_TIMING_MODE,
    sync_interval: int = RND_BASELINE_SYNC_INTERVAL,
) -> Tuple[int, int]:
    progress = motion_progress(motion, current_frame, duration_frames, timing_mode, sync_interval)
    start_x, start_y = motion_start_cell(motion)
    dest_x, dest_y = motion_destination_cell(motion)
    px = int(round((start_x + (dest_x - start_x) * progress) * tile_size))
    py = int(round((start_y + (dest_y - start_y) * progress) * tile_size))
    return (px, py)


def motion_rect(
    pygame: object,
    motion: Motion,
    current_frame: int,
    tile_size: int,
    duration_frames: int,
    timing_mode: TimingMode = RND_BASELINE_TIMING_MODE,
    sync_interval: int = RND_BASELINE_SYNC_INTERVAL,
) -> object:
    px, py = motion_position_px(
        motion,
        current_frame,
        tile_size,
        duration_frames,
        timing_mode,
        sync_interval,
    )
    return pygame.Rect(px, py, tile_size, tile_size)


def draw_board(
    pygame: object,
    screen: object,
    state: GameState,
    tile_size: int,
    motion_state: MotionState | None = None,
    current_frame: int = 0,
    motion_duration_frames: int = RND_BASELINE_ASYNC_MOTION_DURATION,
    timing_mode: TimingMode = RND_BASELINE_TIMING_MODE,
    sync_interval: int = RND_BASELINE_SYNC_INTERVAL,
) -> None:
    moving_tiles: list[tuple[ElementCell, object]] = []
    blocked_destinations = state.blocked_fall_destinations()
    active_falls_by_destination = {
        fall_destination_cell(fall): fall
        for fall in active_falls(state.fall_state)
    }
    origin_fall_cells = {
        fall_start_cell(fall): fall_cell(fall)
        for fall in active_falls(state.fall_state)
    }
    moving_fall_origins: set[Cell] = set()
    if motion_state is not None:
        moving_fall_origins = {
            fall_start_cell(fall)
            for destination, fall in active_falls_by_destination.items()
            if get_motion(motion_state, destination) is not None
        }
    for y in range(state.height):
        for x in range(state.width):
            rect = tile_rect(pygame, x, y, tile_size)
            if motion_state is not None:
                motion = get_motion(motion_state, (x, y))
                if motion is not None:
                    moving_tiles.append(
                        (
                            motion_cell(motion),
                            motion_rect(
                                pygame,
                                motion,
                                current_frame,
                                tile_size,
                                motion_duration_frames,
                                timing_mode,
                                sync_interval,
                            ),
                        )
                    )
                    continue
            if (x, y) in moving_fall_origins:
                continue
            if (x, y) in blocked_destinations:
                continue
            cell = origin_fall_cells.get((x, y), state.get_cell(x, y))
            surface, fallback_color = element_cell_appearance(cell, CUSTOM_ELEMENTS, tile_size)
            if surface is not None:
                screen.blit(surface, rect)
            else:
                pygame.draw.rect(screen, fallback_color, rect)
            pygame.draw.rect(screen, (30, 30, 30), rect, 1)

    for cell, rect in moving_tiles:
        surface, fallback_color = element_cell_appearance(cell, CUSTOM_ELEMENTS, tile_size)
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


def draw_background(
    pygame: object,
    screen: object,
    state: GameState,
    tile_size: int,
    hud_top_padding: int | None = None,
    hud_line_gap: int | None = None,
    font_size: int = 20,
    hud_height: int | None = None,
) -> None:
    if hud_top_padding is None:
        hud_top_padding = hud_top_padding_px(font_size)
    if hud_line_gap is None:
        hud_line_gap = hud_line_gap_px(font_size)
    if hud_height is None:
        hud_height = hud_height_px(hud_top_padding, hud_line_gap, font_size)

    screen.fill(background_color())

    board_width, board_height = board_size_px(state, tile_size)
    board_rect = pygame.Rect(0, 0, board_width, board_height)
    hud_rect = pygame.Rect(0, board_height, board_width, hud_height)
    pygame.draw.rect(screen, board_background_color(), board_rect)
    pygame.draw.rect(screen, (28, 34, 42), board_rect, 2)
    pygame.draw.rect(screen, hud_background_color(), hud_rect)
    pygame.draw.rect(screen, (24, 28, 34), hud_rect, 1)


def render_frame(
    pygame: object,
    screen: object,
    font: object,
    state: GameState,
    tile_size: int,
    motion_state: MotionState | None = None,
    current_frame: int = 0,
    motion_duration_frames: int = RND_BASELINE_ASYNC_MOTION_DURATION,
    timing_mode: TimingMode = RND_BASELINE_TIMING_MODE,
    sync_interval: int = RND_BASELINE_SYNC_INTERVAL,
    hud_padding_x: int = 10,
    hud_top_padding: int | None = None,
    hud_line_gap: int | None = None,
    font_size: int = 20,
    hud_height: int | None = None,
) -> None:
    draw_background(
        pygame,
        screen,
        state,
        tile_size,
        hud_top_padding,
        hud_line_gap,
        font_size,
        hud_height,
    )
    draw_board(
        pygame,
        screen,
        state,
        tile_size,
        motion_state,
        current_frame,
        motion_duration_frames,
        timing_mode,
        sync_interval,
    )
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
    timing_mode: TimingMode = RND_BASELINE_TIMING_MODE,
    sync_interval: int = RND_BASELINE_SYNC_INTERVAL,
    motion_state: MotionState | None = None,
    motion_duration_frames: int = RND_BASELINE_ASYNC_MOTION_DURATION,
    pressed_keys: object | None = None,
    hold_state: HoldState | None = None,
    hold_repeat_delay_frames: int = RND_BASELINE_HOLD_REPEAT_DELAY,
    hold_repeat_interval_frames: int = RND_BASELINE_HOLD_REPEAT_INTERVAL,
) -> bool:
    event_list = list(events)
    should_quit = pygame_frame_requests_quit(event_list)
    if state.alive and not state.won:
        frame_action = action_from_pygame_frame_events(event_list)
        if frame_action is not None and hold_state is not None:
            hold_state["action"] = (frame_action,)
            hold_state["press_frame"] = frame_number
            hold_state["last_output_action"] = frame_action
        elif frame_action is None and pressed_keys is not None:
            held_actions = held_actions_from_pygame_pressed_keys(pressed_keys)
            if hold_state is not None:
                frame_action = repeated_held_action(
                    hold_state,
                    frame_number,
                    held_actions,
                    hold_repeat_delay_frames,
                    hold_repeat_interval_frames,
                )
                if (
                    frame_action is not None
                    and len(held_actions) > 1
                    and not can_player_take_action(state, frame_action)
                ):
                    for alternate_action in held_actions:
                        if alternate_action == frame_action:
                            continue
                        if can_player_take_action(state, alternate_action):
                            frame_action = alternate_action
                            hold_state["last_output_action"] = alternate_action
                            break
            else:
                frame_action = held_actions[0] if held_actions else None
        if motion_state is not None:
            completed_motions = update_motion_state(
                motion_state,
                frame_number,
                motion_duration_frames,
                timing_mode,
                sync_interval,
            )
            for motion in completed_motions:
                if get_fall_in_progress(state.fall_state, motion_destination_cell(motion)) is not None:
                    complete_fall(state, motion_destination_cell(motion))
            state.motion_locked_positions = {
                motion_destination_cell(motion)
                for motion in active_motions(motion_state)
                if cell_is_motion_trackable(motion_cell(motion), CUSTOM_ELEMENTS)
            }
            if has_active_player_motion(motion_state):
                buffer_action(state, frame_action)
                return should_quit
        else:
            state.motion_locked_positions = set()

        start_cell = player_cell(state)
        before_cells = moving_object_cells(state) if motion_state is not None else None
        step_realtime_frame(
            state,
            frame_number,
            frame_action,
            timing_mode,
            sync_interval,
            defer_falls=motion_state is not None,
        )
        if motion_state is not None:
            track_player_motion(motion_state, start_cell, state, frame_number)
            if before_cells is not None:
                track_falling_motions(motion_state, before_cells, state, frame_number)
            if before_cells is not None:
                track_moving_object_motions(motion_state, before_cells, state, frame_number)
    return should_quit


def run_interactive_turn_based(state: GameState) -> None:
    print("Controls: w/a/s/d move, W/A/S/D snap, q quit")
    while state.alive and not state.won:
        print()
        print(state.render())
        move = input("Move> ").strip()
        if move in ("q", "Q"):
            break
        action = action_from_turn_input(move)
        if action is None:
            print("Use w/a/s/d, W/A/S/D, or q")
            continue
        step_game(state, action)

    print()
    print(state.render())


def run_interactive_realtime_terminal(
    state: GameState,
    tick_ms: int,
    timing_mode: TimingMode = RND_BASELINE_TIMING_MODE,
    sync_interval: int = RND_BASELINE_SYNC_INTERVAL,
    engine_mode: EngineMode | None = None,
) -> None:
    if engine_mode is not None:
        timing_mode, sync_interval = engine_config(engine_mode)

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
                step_realtime_frame(state, frame_number, action, timing_mode, sync_interval, defer_falls=True)
            frame_number += 1

    curses.wrapper(_loop)


def run_interactive_realtime_graphics(
    state: GameState,
    tick_ms: int,
    tile_size: int,
    max_frames: int = 0,
    headless: bool = False,
    timing_mode: TimingMode = RND_BASELINE_TIMING_MODE,
    sync_interval: int = RND_BASELINE_SYNC_INTERVAL,
    font_size: int = 20,
    hud_height: int | None = None,
    engine_mode: EngineMode | None = None,
) -> None:
    if engine_mode is not None:
        timing_mode, sync_interval = engine_config(engine_mode)

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
    motion_state = make_motion_state()
    if engine_mode is not None:
        motion_duration_frames = engine_motion_duration_frames(engine_mode)
        hold_repeat_delay_frames, hold_repeat_interval_frames = engine_hold_repeat_frames(engine_mode)
    else:
        motion_duration_frames = default_motion_duration_frames(timing_mode, sync_interval)
        hold_repeat_delay_frames = motion_duration_frames
        hold_repeat_interval_frames = motion_duration_frames
    hold_state = make_hold_state()

    running = True
    frames = 0
    while running:
        if update_graphics_frame(
            state,
            frames,
            pygame.event.get(),
            timing_mode,
            sync_interval,
            motion_state,
            motion_duration_frames,
            pygame.key.get_pressed(),
            hold_state,
            hold_repeat_delay_frames,
            hold_repeat_interval_frames,
        ):
            running = False

        render_frame(
            pygame,
            screen,
            font,
            state,
            tile_size,
            motion_state,
            frames,
            motion_duration_frames,
            timing_mode,
            sync_interval,
            10,
            hud_top_padding,
            hud_line_gap,
            font_size,
            hud_height,
        )

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
        action = action_from_turn_input(move)
        if action is None or not state.alive or state.won:
            continue
        step_game(state, action)
    print("\nAfter scripted moves:")
    print(state.render())


def main() -> None:
    parser = argparse.ArgumentParser(description="Rocks'n'Diamonds-style prototype")
    parser.add_argument("--demo", action="store_true", help="Run non-interactive scripted demo")
    parser.add_argument("--moves", default="dddddssaaawwwdd", help="Move sequence for --demo mode")
    parser.add_argument("--turn-based", action="store_true", help="Run turn-based terminal mode")
    parser.add_argument("--realtime", action="store_true", help="Run realtime terminal mode (curses)")
    parser.add_argument("--graphics2d", action="store_true", help="Run realtime 2D graphics mode (pygame)")
    parser.add_argument(
        "--engine",
        choices=[engine.value for engine in EngineMode],
        default=DEFAULT_ENGINE_MODE.value,
        help="Engine timing mode to use for realtime play",
    )
    parser.add_argument("--tick-ms", type=int, default=250, help="Milliseconds per game tick")
    parser.add_argument("--tile-size", type=int, default=48, help="Tile size for --graphics2d mode")
    parser.add_argument("--font-size", type=int, default=20, help="HUD font size for --graphics2d mode")
    parser.add_argument("--hud-height", type=int, default=0, help="HUD pixel height for --graphics2d mode (0 = auto)")
    parser.add_argument("--max-frames", type=int, default=0, help="Auto-exit after N frames (test helper)")
    parser.add_argument("--headless", action="store_true", help="Allow SDL dummy-driver runs for headless testing")
    args = parser.parse_args()
    engine_mode = EngineMode(args.engine)

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
            engine_mode=engine_mode,
        )
    elif args.realtime:
        run_interactive_realtime_terminal(state, args.tick_ms, engine_mode=engine_mode)
    else:
        run_interactive_turn_based(state)


if __name__ == "__main__":
    main()
