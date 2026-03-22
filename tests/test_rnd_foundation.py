import pytest

from rnd_foundation import (
    GameState,
    Tile,
    action_from_pygame_frame_events,
    is_update_frame,
    parse_level,
    pygame_frame_requests_quit,
    run_interactive_realtime_graphics,
    step_realtime_frame,
)


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


def test_is_update_frame_defaults_to_every_frame() -> None:
    assert is_update_frame(0) is True
    assert is_update_frame(1) is True
    assert is_update_frame(7) is True


def test_is_update_frame_supports_synchronized_intervals() -> None:
    assert is_update_frame(0, sync_interval=8) is True
    assert is_update_frame(7, sync_interval=8) is False
    assert is_update_frame(8, sync_interval=8) is True


def test_is_update_frame_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        is_update_frame(-1)

    with pytest.raises(ValueError, match="positive"):
        is_update_frame(0, sync_interval=0)


def test_step_realtime_frame_skips_non_update_frames() -> None:
    state = make_state(
        "#####",
        "#P  #",
        "# O #",
        "#   #",
        "#####",
    )

    step_realtime_frame(state, frame_number=1, action="d", sync_interval=2)

    assert (state.player_x, state.player_y) == (1, 1)
    assert state.get(2, 2) == Tile.ROCK
    assert state.get(2, 3) == Tile.EMPTY


def test_step_realtime_frame_runs_game_update_on_update_frames() -> None:
    state = make_state(
        "#####",
        "#P  #",
        "# O #",
        "#   #",
        "#####",
    )

    step_realtime_frame(state, frame_number=2, action="d", sync_interval=2)

    assert (state.player_x, state.player_y) == (2, 1)
    assert state.get(2, 3) == Tile.ROCK


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
    K_x = 12

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
            return []

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


def install_fake_pygame(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("rnd_foundation.importlib.util.find_spec", lambda name: object())
    monkeypatch.setattr("rnd_foundation.importlib.import_module", lambda name: FakePygame)


def test_action_from_pygame_frame_events_uses_only_first_move(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_pygame(monkeypatch)

    events = [
        FakeEvent(FakePygame.KEYDOWN, FakePygame.K_d),
        FakeEvent(FakePygame.KEYDOWN, FakePygame.K_a),
    ]

    assert action_from_pygame_frame_events(events) == "d"


def test_action_from_pygame_frame_events_ignores_non_movement_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_pygame(monkeypatch)

    events = [
        FakeEvent(FakePygame.KEYDOWN, FakePygame.K_x),
        FakeEvent(FakePygame.KEYDOWN, FakePygame.K_LEFT),
    ]

    assert action_from_pygame_frame_events(events) == "a"


def test_pygame_frame_requests_quit_is_separate_from_movement(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_pygame(monkeypatch)

    move_events = [FakeEvent(FakePygame.KEYDOWN, FakePygame.K_d)]
    quit_events = [FakeEvent(FakePygame.KEYDOWN, FakePygame.K_q)]
    window_close_events = [FakeEvent(FakePygame.QUIT)]

    assert pygame_frame_requests_quit(move_events) is False
    assert pygame_frame_requests_quit(quit_events) is True
    assert pygame_frame_requests_quit(window_close_events) is True


def test_graphics_mode_processes_at_most_one_move_per_frame(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_pygame(monkeypatch)

    class FakeEventQueue:
        @staticmethod
        def get() -> list[FakeEvent]:
            return [
                FakeEvent(FakePygame.KEYDOWN, FakePygame.K_d),
                FakeEvent(FakePygame.KEYDOWN, FakePygame.K_d),
            ]

    monkeypatch.setattr(FakePygame, "event", FakeEventQueue)

    state = make_state(
        "######",
        "#P   #",
        "######",
    )

    run_interactive_realtime_graphics(state, tick_ms=250, tile_size=32, max_frames=1)

    assert (state.player_x, state.player_y) == (2, 1)
