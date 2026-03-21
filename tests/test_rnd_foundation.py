import pytest

from rnd_foundation import GameState, Tile, parse_level, run_interactive_realtime_graphics


def make_state(*rows: str) -> GameState:
    return parse_level(rows)


def test_parse_level_rejects_empty_input() -> None:
    with pytest.raises(ValueError, match="Level is empty"):
        parse_level([])


def test_parse_level_rejects_uneven_rows() -> None:
    with pytest.raises(ValueError, match="equal width"):
        parse_level(
            [
                "#####",
                "#P #",
                "#####",
            ]
        )


def test_parse_level_rejects_unsupported_tile() -> None:
    with pytest.raises(ValueError, match="Unsupported tile"):
        parse_level(
            [
                "###",
                "#X#",
                "#P#",
            ]
        )


def test_parse_level_requires_exactly_one_player() -> None:
    with pytest.raises(ValueError, match="contain a player"):
        parse_level(
            [
                "###",
                "# #",
                "###",
            ]
        )

    with pytest.raises(ValueError, match="Only one player"):
        parse_level(
            [
                "#####",
                "#P P#",
                "#####",
            ]
        )


def test_parse_level_tracks_dimensions_and_diamonds() -> None:
    state = make_state(
        "#####",
        "#P *#",
        "# O #",
        "#####",
    )

    assert state.width == 5
    assert state.height == 4
    assert state.player_x == 1
    assert state.player_y == 1
    assert state.diamonds_total == 1
    assert state.get(2, 2) == Tile.ROCK


def test_player_can_move_into_empty_space() -> None:
    state = make_state(
        "#####",
        "#P  #",
        "#####",
    )

    state.try_move_player(1, 0)

    assert (state.player_x, state.player_y) == (2, 1)
    assert state.get(1, 1) == Tile.EMPTY
    assert state.get(2, 1) == Tile.PLAYER


def test_player_collects_diamond_and_wins_when_last_diamond_taken() -> None:
    state = make_state(
        "#####",
        "#P* #",
        "#####",
    )

    state.try_move_player(1, 0)

    assert state.diamonds_collected == 1
    assert state.won is True
    assert state.alive is True
    assert state.get(2, 1) == Tile.PLAYER


def test_player_can_push_rock_horizontally_if_space_is_free() -> None:
    state = make_state(
        "######",
        "#PO  #",
        "######",
    )

    state.try_move_player(1, 0)

    assert (state.player_x, state.player_y) == (2, 1)
    assert state.get(3, 1) == Tile.ROCK


def test_player_cannot_push_rock_vertically() -> None:
    state = make_state(
        "#####",
        "# O #",
        "# P #",
        "#####",
    )

    state.try_move_player(0, -1)

    assert (state.player_x, state.player_y) == (2, 2)
    assert state.get(2, 1) == Tile.ROCK


def test_player_cannot_push_rock_into_blocked_space() -> None:
    state = make_state(
        "#####",
        "#PO##",
        "#####",
    )

    state.try_move_player(1, 0)

    assert (state.player_x, state.player_y) == (1, 1)
    assert state.get(2, 1) == Tile.ROCK


def test_gravity_drops_rock_into_empty_space() -> None:
    state = make_state(
        "#####",
        "# O #",
        "#   #",
        "# P #",
        "#   #",
        "#####",
    )

    state.apply_gravity()

    assert state.get(2, 2) == Tile.ROCK
    assert state.get(2, 1) == Tile.EMPTY
    assert state.alive is True


def test_gravity_can_kill_player() -> None:
    state = make_state(
        "#####",
        "# O #",
        "# P #",
        "#####",
    )

    state.apply_gravity()

    assert state.alive is False
    assert state.won is False
    assert state.get(2, 2) == Tile.ROCK


def test_gravity_ignores_updates_after_game_is_over() -> None:
    state = make_state(
        "#####",
        "#P* #",
        "# O #",
        "#   #",
        "#####",
    )
    state.try_move_player(1, 0)

    state.apply_gravity()

    assert state.won is True
    assert state.get(2, 2) == Tile.ROCK
    assert state.get(2, 3) == Tile.EMPTY


def test_graphics_mode_processes_at_most_one_move_per_frame(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeEvent:
        def __init__(self, event_type: int, key: int | None = None) -> None:
            self.type = event_type
            self.key = key

    class FakeFont:
        def render(self, text: str, antialias: bool, color: tuple[int, int, int]) -> object:
            return object()

    class FakeScreen:
        def fill(self, color: tuple[int, int, int]) -> None:
            pass

        def blit(self, surface: object, position: tuple[int, int]) -> None:
            pass

    class FakeClock:
        def tick(self, fps: int) -> None:
            pass

    class FakePygame:
        QUIT = 1
        KEYDOWN = 2
        K_q = 3
        K_w = 4
        K_UP = 5
        K_a = 6
        K_LEFT = 7
        K_s = 8
        K_DOWN = 9
        K_d = 10
        K_RIGHT = 11

        class display:
            @staticmethod
            def set_caption(text: str) -> None:
                pass

            @staticmethod
            def set_mode(size: tuple[int, int]) -> FakeScreen:
                return FakeScreen()

            @staticmethod
            def flip() -> None:
                pass

        class font:
            @staticmethod
            def SysFont(name: str, size: int) -> FakeFont:
                return FakeFont()

        class time:
            @staticmethod
            def Clock() -> FakeClock:
                return FakeClock()

        class event:
            @staticmethod
            def get() -> list[FakeEvent]:
                return [
                    FakeEvent(FakePygame.KEYDOWN, FakePygame.K_d),
                    FakeEvent(FakePygame.KEYDOWN, FakePygame.K_d),
                ]

        class draw:
            @staticmethod
            def rect(screen: FakeScreen, color: tuple[int, int, int], rect: object, width: int = 0) -> None:
                pass

        @staticmethod
        def Rect(x: int, y: int, width: int, height: int) -> tuple[int, int, int, int]:
            return (x, y, width, height)

        @staticmethod
        def init() -> None:
            pass

        @staticmethod
        def quit() -> None:
            pass

    monkeypatch.setattr("rnd_foundation.importlib.util.find_spec", lambda name: object())
    monkeypatch.setattr("rnd_foundation.importlib.import_module", lambda name: FakePygame)

    state = make_state(
        "######",
        "#P   #",
        "######",
    )

    run_interactive_realtime_graphics(state, tick_ms=250, tile_size=32, max_frames=1)

    assert (state.player_x, state.player_y) == (2, 1)
