import pytest

from rnd_foundation import (
    GameState,
    TimingMode,
    Tile,
    active_motions,
    action_from_pygame_frame_events,
    buffer_action,
    consume_buffered_action,
    default_motion_duration_frames,
    get_motion,
    is_update_frame,
    complete_motion,
    motion_is_complete,
    motion_progress,
    make_motion_state,
    parse_level,
    pygame_frame_requests_quit,
    board_size_px,
    clear_tile_surface_cache,
    draw_board,
    draw_hud,
    hud_height_px,
    hud_line_gap_px,
    hud_top_padding_px,
    render_frame,
    run_interactive_realtime_graphics,
    screen_size_px,
    step_realtime_frame,
    tile_appearance,
    tile_color,
    tile_rect,
    tile_surface,
    update_graphics_frame,
    make_motion,
    motion_destination_cell,
    motion_position_px,
    motion_rect,
    motion_start_cell,
    motion_start_frame,
    motion_tile,
    player_cell,
    remove_motion,
    set_motion,
    start_motion,
    track_player_motion,
    clamp_progress,
    update_motion_state,
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


def test_parse_level_supports_sand() -> None:
    state = make_state(
        "#####",
        "#P. #",
        "#####",
    )

    assert state.get(2, 1) == Tile.SAND


def test_make_motion_builds_a_transition_model() -> None:
    motion = make_motion(Tile.PLAYER, (1, 2), (2, 2), 7)

    assert motion_tile(motion) == Tile.PLAYER
    assert motion_start_cell(motion) == (1, 2)
    assert motion_destination_cell(motion) == (2, 2)
    assert motion_start_frame(motion) == 7


def test_make_motion_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        make_motion(Tile.PLAYER, (1, 2), (2, 2), -1)

    with pytest.raises(ValueError, match="different cells"):
        make_motion(Tile.PLAYER, (1, 2), (1, 2), 0)


def test_motion_state_stores_and_reads_motion_by_destination_cell() -> None:
    motion_state = make_motion_state()
    motion = make_motion(Tile.PLAYER, (1, 2), (2, 2), 7)

    set_motion(motion_state, motion)

    assert get_motion(motion_state, (2, 2)) == motion
    assert active_motions(motion_state) == [motion]


def test_motion_state_replaces_existing_motion_for_same_destination() -> None:
    motion_state = make_motion_state()
    first = make_motion(Tile.PLAYER, (1, 2), (2, 2), 7)
    second = make_motion(Tile.ROCK, (2, 1), (2, 2), 8)

    set_motion(motion_state, first)
    set_motion(motion_state, second)

    assert get_motion(motion_state, (2, 2)) == second
    assert active_motions(motion_state) == [second]


def test_motion_state_removes_motion_by_destination_cell() -> None:
    motion_state = make_motion_state()
    motion = make_motion(Tile.PLAYER, (1, 2), (2, 2), 7)
    set_motion(motion_state, motion)

    removed = remove_motion(motion_state, (2, 2))

    assert removed == motion
    assert get_motion(motion_state, (2, 2)) is None
    assert active_motions(motion_state) == []


def test_clamp_progress_bounds_values() -> None:
    assert clamp_progress(-0.5) == 0.0
    assert clamp_progress(0.25) == 0.25
    assert clamp_progress(1.5) == 1.0


def test_motion_progress_async_uses_motion_start_frame() -> None:
    motion = make_motion(Tile.PLAYER, (1, 2), (2, 2), 10)

    assert motion_progress(motion, current_frame=10, duration_frames=4, timing_mode=TimingMode.ASYNC) == 0.0
    assert motion_progress(motion, current_frame=12, duration_frames=4, timing_mode=TimingMode.ASYNC) == 0.5
    assert motion_progress(motion, current_frame=14, duration_frames=4, timing_mode=TimingMode.ASYNC) == 1.0


def test_motion_progress_sync_uses_motion_start_frame() -> None:
    motion = make_motion(Tile.PLAYER, (1, 2), (2, 2), 8)

    assert motion_progress(motion, current_frame=8, duration_frames=4, timing_mode=TimingMode.SYNC, sync_interval=8) == 0.0
    assert motion_progress(motion, current_frame=10, duration_frames=4, timing_mode=TimingMode.SYNC, sync_interval=8) == 0.5
    assert motion_progress(motion, current_frame=12, duration_frames=4, timing_mode=TimingMode.SYNC, sync_interval=8) == 1.0


def test_motion_progress_rejects_invalid_values() -> None:
    motion = make_motion(Tile.PLAYER, (1, 2), (2, 2), 3)

    with pytest.raises(ValueError, match="non-negative"):
        motion_progress(motion, current_frame=-1, duration_frames=4)

    with pytest.raises(ValueError, match="positive"):
        motion_progress(motion, current_frame=3, duration_frames=0)

    with pytest.raises(ValueError, match="positive"):
        motion_progress(motion, current_frame=3, duration_frames=4, sync_interval=0)


def test_motion_is_complete_uses_progress_rules() -> None:
    motion = make_motion(Tile.PLAYER, (1, 2), (2, 2), 10)

    assert motion_is_complete(motion, current_frame=13, duration_frames=4, timing_mode=TimingMode.ASYNC) is False
    assert motion_is_complete(motion, current_frame=14, duration_frames=4, timing_mode=TimingMode.ASYNC) is True


def test_start_motion_adds_motion_to_motion_state() -> None:
    motion_state = make_motion_state()

    motion = start_motion(motion_state, Tile.PLAYER, (1, 2), (2, 2), 7)

    assert get_motion(motion_state, (2, 2)) == motion
    assert active_motions(motion_state) == [motion]


def test_complete_motion_removes_motion_from_motion_state() -> None:
    motion_state = make_motion_state()
    motion = start_motion(motion_state, Tile.PLAYER, (1, 2), (2, 2), 7)

    removed = complete_motion(motion_state, (2, 2))

    assert removed == motion
    assert active_motions(motion_state) == []


def test_update_motion_state_removes_completed_async_motions() -> None:
    motion_state = make_motion_state()
    first = start_motion(motion_state, Tile.PLAYER, (1, 2), (2, 2), 10)
    second = start_motion(motion_state, Tile.ROCK, (3, 3), (3, 4), 12)

    completed = update_motion_state(
        motion_state,
        current_frame=14,
        duration_frames=4,
        timing_mode=TimingMode.ASYNC,
    )

    assert completed == [first]
    assert active_motions(motion_state) == [second]


def test_update_motion_state_removes_completed_sync_motions_by_global_phase() -> None:
    motion_state = make_motion_state()
    motion = start_motion(motion_state, Tile.PLAYER, (1, 2), (2, 2), 3)

    completed = update_motion_state(
        motion_state,
        current_frame=12,
        duration_frames=4,
        timing_mode=TimingMode.SYNC,
        sync_interval=8,
    )

    assert completed == [motion]
    assert active_motions(motion_state) == []


def test_default_motion_duration_frames_matches_timing_mode() -> None:
    assert default_motion_duration_frames(TimingMode.ASYNC, sync_interval=8) == 4
    assert default_motion_duration_frames(TimingMode.SYNC, sync_interval=8) == 8


def test_default_motion_duration_frames_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="positive"):
        default_motion_duration_frames(TimingMode.ASYNC, async_duration_frames=0)

    with pytest.raises(ValueError, match="positive"):
        default_motion_duration_frames(TimingMode.SYNC, sync_interval=0)


def test_player_cell_returns_current_player_position() -> None:
    state = make_state(
        "#####",
        "# P #",
        "#####",
    )

    assert player_cell(state) == (2, 1)


def test_track_player_motion_starts_motion_when_player_cell_changes() -> None:
    motion_state = make_motion_state()
    state = make_state(
        "#####",
        "#P  #",
        "#####",
    )
    state.try_move_player(1, 0)

    motion = track_player_motion(motion_state, (1, 1), state, frame_number=5)

    assert motion is not None
    assert motion_tile(motion) == Tile.PLAYER
    assert motion_start_cell(motion) == (1, 1)
    assert motion_destination_cell(motion) == (2, 1)
    assert motion_start_frame(motion) == 5
    assert active_motions(motion_state) == [motion]


def test_track_player_motion_does_nothing_without_player_movement() -> None:
    motion_state = make_motion_state()
    state = make_state(
        "#####",
        "#P###",
        "#####",
    )

    motion = track_player_motion(motion_state, (1, 1), state, frame_number=5)

    assert motion is None
    assert active_motions(motion_state) == []


def test_motion_contract_async_transition_progresses_then_completes() -> None:
    motion_state = make_motion_state()
    motion = start_motion(motion_state, Tile.PLAYER, (1, 1), (2, 1), 10)

    assert motion_progress(motion, current_frame=10, duration_frames=4, timing_mode=TimingMode.ASYNC) == 0.0
    assert motion_progress(motion, current_frame=12, duration_frames=4, timing_mode=TimingMode.ASYNC) == 0.5
    assert update_motion_state(
        motion_state,
        current_frame=12,
        duration_frames=4,
        timing_mode=TimingMode.ASYNC,
    ) == []
    assert active_motions(motion_state) == [motion]

    completed = update_motion_state(
        motion_state,
        current_frame=14,
        duration_frames=4,
        timing_mode=TimingMode.ASYNC,
    )

    assert completed == [motion]
    assert active_motions(motion_state) == []


def test_motion_contract_sync_transition_uses_shared_phase_then_completes() -> None:
    motion_state = make_motion_state()
    motion = start_motion(motion_state, Tile.PLAYER, (1, 1), (2, 1), 8)

    assert motion_progress(
        motion,
        current_frame=8,
        duration_frames=4,
        timing_mode=TimingMode.SYNC,
        sync_interval=8,
    ) == 0.0
    assert motion_progress(
        motion,
        current_frame=10,
        duration_frames=4,
        timing_mode=TimingMode.SYNC,
        sync_interval=8,
    ) == 0.5
    assert update_motion_state(
        motion_state,
        current_frame=10,
        duration_frames=4,
        timing_mode=TimingMode.SYNC,
        sync_interval=8,
    ) == []
    assert active_motions(motion_state) == [motion]

    completed = update_motion_state(
        motion_state,
        current_frame=12,
        duration_frames=4,
        timing_mode=TimingMode.SYNC,
        sync_interval=8,
    )

    assert completed == [motion]
    assert active_motions(motion_state) == []


def test_motion_contract_sync_transition_can_span_full_sync_interval() -> None:
    motion_state = make_motion_state()
    motion = start_motion(motion_state, Tile.PLAYER, (1, 1), (2, 1), 8)
    duration = default_motion_duration_frames(TimingMode.SYNC, sync_interval=8)

    assert motion_progress(
        motion,
        current_frame=10,
        duration_frames=duration,
        timing_mode=TimingMode.SYNC,
        sync_interval=8,
    ) == 0.25
    assert update_motion_state(
        motion_state,
        current_frame=14,
        duration_frames=duration,
        timing_mode=TimingMode.SYNC,
        sync_interval=8,
    ) == []
    assert active_motions(motion_state) == [motion]

    completed = update_motion_state(
        motion_state,
        current_frame=16,
        duration_frames=duration,
        timing_mode=TimingMode.SYNC,
        sync_interval=8,
    )

    assert completed == [motion]
    assert active_motions(motion_state) == []


def test_motion_position_px_interpolates_between_cells() -> None:
    motion = make_motion(Tile.PLAYER, (1, 1), (2, 1), 10)

    assert motion_position_px(motion, current_frame=10, tile_size=24, duration_frames=4) == (24, 24)
    assert motion_position_px(motion, current_frame=12, tile_size=24, duration_frames=4) == (36, 24)
    assert motion_position_px(motion, current_frame=14, tile_size=24, duration_frames=4) == (48, 24)


def test_motion_rect_uses_interpolated_pixel_position() -> None:
    motion = make_motion(Tile.PLAYER, (1, 1), (2, 1), 10)

    class FakePygame:
        @staticmethod
        def Rect(x: int, y: int, width: int, height: int) -> tuple[int, int, int, int]:
            return (x, y, width, height)

    assert motion_rect(FakePygame, motion, current_frame=12, tile_size=24, duration_frames=4) == (36, 24, 24, 24)


def test_tile_color_maps_each_tile_type() -> None:
    assert tile_color(Tile.EMPTY) == (16, 18, 22)
    assert tile_color(Tile.WALL) == (100, 110, 130)
    assert tile_color(Tile.SAND) == (180, 150, 90)
    assert tile_color(Tile.ROCK) == (140, 90, 60)
    assert tile_color(Tile.DIAMOND) == (70, 210, 255)
    assert tile_color(Tile.PLAYER) == (60, 220, 120)


def test_tile_surface_defaults_to_none() -> None:
    clear_tile_surface_cache()
    assert tile_surface(Tile.PLAYER, 32) is None


def test_tile_surface_uses_cache_for_repeated_lookups(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_tile_surface_cache()
    built: list[tuple[Tile, int]] = []

    def fake_build(tile: Tile, tile_size: int) -> object:
        built.append((tile, tile_size))
        return {"tile": tile, "tile_size": tile_size}

    monkeypatch.setattr("rnd_foundation.build_tile_surface", fake_build)

    first = tile_surface(Tile.ROCK, 32)
    second = tile_surface(Tile.ROCK, 32)

    assert first == {"tile": Tile.ROCK, "tile_size": 32}
    assert second is first
    assert built == [(Tile.ROCK, 32)]


def test_clear_tile_surface_cache_forces_rebuild(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_tile_surface_cache()
    built: list[tuple[Tile, int]] = []

    def fake_build(tile: Tile, tile_size: int) -> object:
        built.append((tile, tile_size))
        return {"call": len(built)}

    monkeypatch.setattr("rnd_foundation.build_tile_surface", fake_build)

    first = tile_surface(Tile.DIAMOND, 48)
    clear_tile_surface_cache()
    second = tile_surface(Tile.DIAMOND, 48)

    assert first == {"call": 1}
    assert second == {"call": 2}
    assert built == [(Tile.DIAMOND, 48), (Tile.DIAMOND, 48)]


def test_tile_appearance_returns_surface_or_fallback_color() -> None:
    clear_tile_surface_cache()
    surface, fallback_color = tile_appearance(Tile.DIAMOND, 48)

    assert surface is None
    assert fallback_color == tile_color(Tile.DIAMOND)


def test_tile_rect_scales_with_tile_size() -> None:
    class FakePygame:
        @staticmethod
        def Rect(x: int, y: int, width: int, height: int) -> tuple[int, int, int, int]:
            return (x, y, width, height)

    assert tile_rect(FakePygame, 2, 3, 16) == (32, 48, 16, 16)
    assert tile_rect(FakePygame, 2, 3, 48) == (96, 144, 48, 48)


def test_draw_board_renders_each_tile_with_fill_and_outline() -> None:
    state = make_state(
        "###",
        "#P#",
        "###",
    )
    calls: list[tuple[object, tuple[int, int, int], object, int]] = []
    blit_calls: list[tuple[object, object]] = []

    class FakeDraw:
        @staticmethod
        def rect(screen: object, color: tuple[int, int, int], rect: object, width: int = 0) -> None:
            calls.append((screen, color, rect, width))

    class FakePygame:
        draw = FakeDraw()

        @staticmethod
        def Rect(x: int, y: int, width: int, height: int) -> tuple[int, int, int, int]:
            return (x, y, width, height)

    class FakeScreen:
        def blit(self, surface: object, rect: object) -> None:
            blit_calls.append((surface, rect))

    screen = FakeScreen()

    draw_board(FakePygame, screen, state, tile_size=8)

    assert len(calls) == state.width * state.height * 2
    assert blit_calls == []
    assert calls[0] == (screen, tile_color(Tile.WALL), (0, 0, 8, 8), 0)
    assert calls[1] == (screen, (30, 30, 30), (0, 0, 8, 8), 1)
    assert calls[8] == (screen, tile_color(Tile.PLAYER), (8, 8, 8, 8), 0)
    assert calls[9] == (screen, (30, 30, 30), (8, 8, 8, 8), 1)


def test_draw_board_uses_tile_size_for_rect_geometry() -> None:
    state = make_state(
        "##",
        "#P",
    )
    calls: list[tuple[object, tuple[int, int, int], object, int]] = []

    class FakeDraw:
        @staticmethod
        def rect(screen: object, color: tuple[int, int, int], rect: object, width: int = 0) -> None:
            calls.append((screen, color, rect, width))

    class FakePygame:
        draw = FakeDraw()

        @staticmethod
        def Rect(x: int, y: int, width: int, height: int) -> tuple[int, int, int, int]:
            return (x, y, width, height)

    class FakeScreen:
        def blit(self, surface: object, rect: object) -> None:
            raise AssertionError("unexpected sprite blit")

    draw_board(FakePygame, FakeScreen(), state, tile_size=24)

    assert calls[0][2] == (0, 0, 24, 24)
    assert calls[2][2] == (24, 0, 24, 24)
    assert calls[4][2] == (0, 24, 24, 24)
    assert calls[6][2] == (24, 24, 24, 24)


def test_draw_board_blits_surface_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_tile_surface_cache()
    state = make_state(
        "##",
        "#P",
    )
    draw_calls: list[tuple[object, tuple[int, int, int], object, int]] = []
    blit_calls: list[tuple[object, object]] = []

    def fake_build(tile: Tile, tile_size: int) -> object | None:
        if tile == Tile.PLAYER:
            return ("player-surface", tile_size)
        return None

    monkeypatch.setattr("rnd_foundation.build_tile_surface", fake_build)

    class FakeDraw:
        @staticmethod
        def rect(screen: object, color: tuple[int, int, int], rect: object, width: int = 0) -> None:
            draw_calls.append((screen, color, rect, width))

    class FakePygame:
        draw = FakeDraw()

        @staticmethod
        def Rect(x: int, y: int, width: int, height: int) -> tuple[int, int, int, int]:
            return (x, y, width, height)

    class FakeScreen:
        def blit(self, surface: object, rect: object) -> None:
            blit_calls.append((surface, rect))

    screen = FakeScreen()

    draw_board(FakePygame, screen, state, tile_size=24)

    assert blit_calls == [(("player-surface", 24), (24, 24, 24, 24))]
    assert len(draw_calls) == (state.width * state.height - 1) * 2 + 1
    assert (screen, tile_color(Tile.PLAYER), (24, 24, 24, 24), 0) not in draw_calls
    assert (screen, (30, 30, 30), (24, 24, 24, 24), 1) in draw_calls


def test_draw_board_renders_moving_player_at_interpolated_rect() -> None:
    clear_tile_surface_cache()
    state = make_state(
        "###",
        "# P",
        "###",
    )
    motion_state = make_motion_state()
    set_motion(motion_state, make_motion(Tile.PLAYER, (1, 1), (2, 1), 10))
    calls: list[tuple[object, tuple[int, int, int], object, int]] = []

    class FakeDraw:
        @staticmethod
        def rect(screen: object, color: tuple[int, int, int], rect: object, width: int = 0) -> None:
            calls.append((screen, color, rect, width))

    class FakePygame:
        draw = FakeDraw()

        @staticmethod
        def Rect(x: int, y: int, width: int, height: int) -> tuple[int, int, int, int]:
            return (x, y, width, height)

    class FakeScreen:
        def blit(self, surface: object, rect: object) -> None:
            raise AssertionError("unexpected sprite blit")

    screen = FakeScreen()

    draw_board(
        FakePygame,
        screen,
        state,
        tile_size=24,
        motion_state=motion_state,
        current_frame=12,
        motion_duration_frames=4,
    )

    assert (screen, tile_color(Tile.PLAYER), (36, 24, 24, 24), 0) in calls
    assert (screen, (30, 30, 30), (36, 24, 24, 24), 1) in calls


def test_draw_board_draws_leftward_motion_after_static_tiles() -> None:
    clear_tile_surface_cache()
    state = make_state(
        "####",
        "#P #",
        "####",
    )
    motion_state = make_motion_state()
    set_motion(motion_state, make_motion(Tile.PLAYER, (2, 1), (1, 1), 10))
    calls: list[tuple[object, tuple[int, int, int], object, int]] = []

    class FakeDraw:
        @staticmethod
        def rect(screen: object, color: tuple[int, int, int], rect: object, width: int = 0) -> None:
            calls.append((screen, color, rect, width))

    class FakePygame:
        draw = FakeDraw()

        @staticmethod
        def Rect(x: int, y: int, width: int, height: int) -> tuple[int, int, int, int]:
            return (x, y, width, height)

    class FakeScreen:
        def blit(self, surface: object, rect: object) -> None:
            raise AssertionError("unexpected sprite blit")

    screen = FakeScreen()

    draw_board(
        FakePygame,
        screen,
        state,
        tile_size=24,
        motion_state=motion_state,
        current_frame=12,
        motion_duration_frames=4,
    )

    player_fill = (screen, tile_color(Tile.PLAYER), (36, 24, 24, 24), 0)
    player_outline = (screen, (30, 30, 30), (36, 24, 24, 24), 1)

    assert calls[-2] == player_fill
    assert calls[-1] == player_outline


def test_draw_hud_renders_status_and_help_text() -> None:
    state = make_state(
        "#####",
        "#P* #",
        "#####",
    )
    state.diamonds_collected = 1
    state.won = True
    render_calls: list[tuple[str, bool, tuple[int, int, int]]] = []
    blit_calls: list[tuple[object, tuple[int, int]]] = []

    class FakeFont:
        def render(self, text: str, antialias: bool, color: tuple[int, int, int]) -> object:
            render_calls.append((text, antialias, color))
            return text

    class FakeScreen:
        def blit(self, surface: object, position: tuple[int, int]) -> None:
            blit_calls.append((surface, position))

    draw_hud(FakeScreen(), FakeFont(), state, tile_size=8)

    assert render_calls == [
        ("Diamonds: 1/1   YOU WON", True, (245, 245, 245)),
        ("Move: WASD/Arrows   Quit: Q", True, (190, 190, 190)),
    ]
    assert blit_calls == [
        ("Diamonds: 1/1   YOU WON", (10, 34)),
        ("Move: WASD/Arrows   Quit: Q", (10, 62)),
    ]


def test_draw_hud_scales_spacing_with_font_size() -> None:
    state = make_state(
        "#####",
        "#P  #",
        "#####",
    )
    render_calls: list[tuple[str, bool, tuple[int, int, int]]] = []
    blit_calls: list[tuple[object, tuple[int, int]]] = []

    class FakeFont:
        def render(self, text: str, antialias: bool, color: tuple[int, int, int]) -> object:
            render_calls.append((text, antialias, color))
            return text

    class FakeScreen:
        def blit(self, surface: object, position: tuple[int, int]) -> None:
            blit_calls.append((surface, position))

    draw_hud(
        FakeScreen(),
        FakeFont(),
        state,
        tile_size=8,
        hud_top_padding=hud_top_padding_px(30),
        hud_line_gap=hud_line_gap_px(30),
    )

    assert render_calls == [
        ("Diamonds: 0/0", True, (245, 245, 245)),
        ("Move: WASD/Arrows   Quit: Q", True, (190, 190, 190)),
    ]
    assert blit_calls == [
        ("Diamonds: 0/0", (10, 39)),
        ("Move: WASD/Arrows   Quit: Q", (10, 77)),
    ]


def test_draw_hud_renders_dead_status_text() -> None:
    state = make_state(
        "#####",
        "#P  #",
        "#####",
    )
    state.alive = False
    render_calls: list[tuple[str, bool, tuple[int, int, int]]] = []
    blit_calls: list[tuple[object, tuple[int, int]]] = []

    class FakeFont:
        def render(self, text: str, antialias: bool, color: tuple[int, int, int]) -> object:
            render_calls.append((text, antialias, color))
            return text

    class FakeScreen:
        def blit(self, surface: object, position: tuple[int, int]) -> None:
            blit_calls.append((surface, position))

    draw_hud(FakeScreen(), FakeFont(), state, tile_size=8)

    assert render_calls == [
        ("Diamonds: 0/0   YOU DIED", True, (245, 245, 245)),
        ("Move: WASD/Arrows   Quit: Q", True, (190, 190, 190)),
    ]
    assert blit_calls == [
        ("Diamonds: 0/0   YOU DIED", (10, 34)),
        ("Move: WASD/Arrows   Quit: Q", (10, 62)),
    ]


def test_render_frame_clears_screen_and_draws_board_and_hud() -> None:
    state = make_state(
        "###",
        "#P#",
        "###",
    )
    fill_calls: list[tuple[int, int, int]] = []
    draw_calls: list[tuple[object, tuple[int, int, int], object, int]] = []
    render_calls: list[tuple[str, bool, tuple[int, int, int]]] = []
    blit_calls: list[tuple[object, tuple[int, int]]] = []

    class FakeDraw:
        @staticmethod
        def rect(screen: object, color: tuple[int, int, int], rect: object, width: int = 0) -> None:
            draw_calls.append((screen, color, rect, width))

    class FakePygame:
        draw = FakeDraw()

        @staticmethod
        def Rect(x: int, y: int, width: int, height: int) -> tuple[int, int, int, int]:
            return (x, y, width, height)

    class FakeFont:
        def render(self, text: str, antialias: bool, color: tuple[int, int, int]) -> object:
            render_calls.append((text, antialias, color))
            return text

    class FakeScreen:
        def fill(self, color: tuple[int, int, int]) -> None:
            fill_calls.append(color)

        def blit(self, surface: object, position: tuple[int, int]) -> None:
            blit_calls.append((surface, position))

    render_frame(FakePygame, FakeScreen(), FakeFont(), state, tile_size=8)

    assert fill_calls == [(10, 10, 12)]
    assert len(draw_calls) == state.width * state.height * 2
    assert render_calls == [
        ("Diamonds: 0/0", True, (245, 245, 245)),
        ("Move: WASD/Arrows   Quit: Q", True, (190, 190, 190)),
    ]
    assert blit_calls == [
        ("Diamonds: 0/0", (10, 34)),
        ("Move: WASD/Arrows   Quit: Q", (10, 62)),
    ]


def test_layout_helpers_return_expected_pixel_sizes() -> None:
    state = make_state(
        "#####",
        "#P  #",
        "#####",
    )

    assert hud_height_px() == 70
    assert board_size_px(state, tile_size=16) == (80, 48)
    assert screen_size_px(state, tile_size=16) == (80, 118)


def test_layout_helpers_support_custom_visual_config() -> None:
    state = make_state(
        "#####",
        "#P  #",
        "#####",
    )

    assert hud_top_padding_px() == 10
    assert hud_line_gap_px() == 28
    assert hud_top_padding_px(30) == 15
    assert hud_line_gap_px(30) == 38
    assert hud_height_px(font_size=30) == 80
    assert screen_size_px(state, tile_size=16, font_size=30, hud_height=100) == (80, 148)


def test_update_graphics_frame_updates_state_and_reports_quit(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_pygame(monkeypatch)
    state = make_state(
        "######",
        "#P   #",
        "######",
    )
    events = [
        FakeEvent(FakePygame.KEYDOWN, FakePygame.K_d),
        FakeEvent(FakePygame.KEYDOWN, FakePygame.K_q),
    ]

    should_quit = update_graphics_frame(
        state,
        frame_number=0,
        events=events,
        timing_mode=TimingMode.ASYNC,
    )

    assert should_quit is True
    assert (state.player_x, state.player_y) == (2, 1)


def test_update_graphics_frame_starts_player_motion_when_player_moves(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_pygame(monkeypatch)
    state = make_state(
        "######",
        "#P   #",
        "######",
    )
    motion_state = make_motion_state()
    events = [FakeEvent(FakePygame.KEYDOWN, FakePygame.K_d)]

    should_quit = update_graphics_frame(
        state,
        frame_number=0,
        events=events,
        timing_mode=TimingMode.ASYNC,
        motion_state=motion_state,
    )

    assert should_quit is False
    assert active_motions(motion_state) == [make_motion(Tile.PLAYER, (1, 1), (2, 1), 0)]


def test_update_graphics_frame_does_not_start_player_motion_without_movement(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_pygame(monkeypatch)
    state = make_state(
        "#####",
        "#P###",
        "#####",
    )
    motion_state = make_motion_state()
    events = [FakeEvent(FakePygame.KEYDOWN, FakePygame.K_d)]

    update_graphics_frame(
        state,
        frame_number=0,
        events=events,
        timing_mode=TimingMode.ASYNC,
        motion_state=motion_state,
    )

    assert active_motions(motion_state) == []


def test_consume_buffered_action_returns_none_when_buffer_is_empty() -> None:
    state = make_state(
        "#####",
        "#P  #",
        "#####",
    )

    assert state.pending_action is None
    assert consume_buffered_action(state) is None
    assert state.pending_action is None


def test_buffer_action_stores_latest_valid_action() -> None:
    state = make_state(
        "#####",
        "#P  #",
        "#####",
    )

    buffer_action(state, "a")
    assert state.pending_action == "a"

    buffer_action(state, "d")
    assert state.pending_action == "d"
    assert consume_buffered_action(state) == "d"
    assert state.pending_action is None


def test_buffer_action_ignores_invalid_input() -> None:
    state = make_state(
        "#####",
        "#P  #",
        "#####",
    )

    buffer_action(state, "w")
    buffer_action(state, "x")
    buffer_action(state, None)

    assert state.pending_action == "w"


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


def test_player_can_move_into_sand() -> None:
    state = make_state(
        "#####",
        "#P. #",
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


def test_gravity_does_not_drop_rock_into_sand() -> None:
    state = make_state(
        "#####",
        "# O #",
        "# . #",
        "# P #",
        "#####",
    )

    state.apply_gravity()

    assert state.get(2, 1) == Tile.ROCK
    assert state.get(2, 2) == Tile.SAND
    assert state.alive is True


def test_player_can_stand_under_resting_rock() -> None:
    state = make_state(
        "#####",
        "# O #",
        "# P #",
        "#####",
    )

    state.apply_gravity()

    assert state.alive is True
    assert state.won is False
    assert state.get(2, 1) == Tile.ROCK
    assert state.get(2, 2) == Tile.PLAYER


def test_gravity_can_kill_player_if_rock_was_already_falling() -> None:
    state = make_state(
        "#####",
        "# O #",
        "#   #",
        "# P #",
        "#####",
    )

    state.apply_gravity()

    assert state.alive is True
    assert state.get(2, 2) == Tile.ROCK

    state.apply_gravity()

    assert state.alive is False
    assert state.won is False
    assert state.get(2, 3) == Tile.ROCK


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


def test_is_update_frame_async_mode_ignores_sync_interval() -> None:
    assert is_update_frame(0, TimingMode.ASYNC, sync_interval=8) is True
    assert is_update_frame(7, TimingMode.ASYNC, sync_interval=8) is True
    assert is_update_frame(8, TimingMode.ASYNC, sync_interval=8) is True


def test_is_update_frame_sync_mode_uses_interval() -> None:
    assert is_update_frame(0, TimingMode.SYNC, sync_interval=8) is True
    assert is_update_frame(7, TimingMode.SYNC, sync_interval=8) is False
    assert is_update_frame(8, TimingMode.SYNC, sync_interval=8) is True


def test_is_update_frame_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        is_update_frame(-1)

    with pytest.raises(ValueError, match="positive"):
        is_update_frame(0, sync_interval=0)

    with pytest.raises(ValueError, match="Unsupported timing mode"):
        is_update_frame(0, "broken")  # type: ignore[arg-type]


def test_step_realtime_frame_async_mode_updates_every_frame() -> None:
    state = make_state(
        "#####",
        "#P  #",
        "# O #",
        "#   #",
        "#####",
    )

    step_realtime_frame(state, frame_number=1, action="d", timing_mode=TimingMode.ASYNC, sync_interval=8)

    assert (state.player_x, state.player_y) == (2, 1)
    assert state.get(2, 3) == Tile.ROCK


def test_step_realtime_frame_async_mode_consumes_prebuffered_action() -> None:
    state = make_state(
        "#####",
        "#P  #",
        "#   #",
        "#####",
    )
    buffer_action(state, "d")

    step_realtime_frame(state, frame_number=3, action=None, timing_mode=TimingMode.ASYNC)

    assert (state.player_x, state.player_y) == (2, 1)
    assert state.pending_action is None


def test_step_realtime_frame_async_mode_clears_buffer_after_consuming_action() -> None:
    state = make_state(
        "#####",
        "#P  #",
        "#   #",
        "#####",
    )

    step_realtime_frame(state, frame_number=0, action="d", timing_mode=TimingMode.ASYNC)

    assert (state.player_x, state.player_y) == (2, 1)
    assert state.pending_action is None


def test_step_realtime_frame_async_mode_current_input_replaces_older_buffered_input() -> None:
    state = make_state(
        "######",
        "# P  #",
        "#    #",
        "######",
    )
    buffer_action(state, "a")

    step_realtime_frame(state, frame_number=0, action="d", timing_mode=TimingMode.ASYNC)

    assert (state.player_x, state.player_y) == (3, 1)
    assert state.pending_action is None


def test_step_realtime_frame_async_mode_consumed_action_is_not_replayed() -> None:
    state = make_state(
        "#######",
        "# P   #",
        "#     #",
        "#######",
    )

    step_realtime_frame(state, frame_number=0, action="d", timing_mode=TimingMode.ASYNC)
    step_realtime_frame(state, frame_number=1, action=None, timing_mode=TimingMode.ASYNC)

    assert (state.player_x, state.player_y) == (3, 1)
    assert state.pending_action is None


def test_step_realtime_frame_async_mode_runs_gravity_without_buffered_action() -> None:
    state = make_state(
        "#####",
        "# O #",
        "#   #",
        "# P #",
        "#   #",
        "#####",
    )

    step_realtime_frame(state, frame_number=4, action=None, timing_mode=TimingMode.ASYNC)

    assert state.get(2, 2) == Tile.ROCK
    assert state.pending_action is None


def test_step_realtime_frame_async_mode_advances_falling_state_each_frame() -> None:
    state = make_state(
        "#####",
        "# O #",
        "#   #",
        "#   #",
        "# P #",
        "#####",
    )

    step_realtime_frame(state, frame_number=0, action=None, timing_mode=TimingMode.ASYNC)

    assert state.get(2, 2) == Tile.ROCK
    assert state.alive is True

    step_realtime_frame(state, frame_number=1, action=None, timing_mode=TimingMode.ASYNC)

    assert state.get(2, 3) == Tile.ROCK
    assert state.alive is True


def test_step_realtime_frame_sync_mode_skips_non_update_frames() -> None:
    state = make_state(
        "#####",
        "#P  #",
        "# O #",
        "#   #",
        "#####",
    )

    step_realtime_frame(state, frame_number=1, action="d", timing_mode=TimingMode.SYNC, sync_interval=2)

    assert (state.player_x, state.player_y) == (1, 1)
    assert state.get(2, 2) == Tile.ROCK
    assert state.get(2, 3) == Tile.EMPTY


def test_step_realtime_frame_sync_mode_skipped_frames_do_not_advance_gravity() -> None:
    state = make_state(
        "#####",
        "# O #",
        "#   #",
        "#   #",
        "# P #",
        "#####",
    )

    step_realtime_frame(state, frame_number=1, action=None, timing_mode=TimingMode.SYNC, sync_interval=2)

    assert state.get(2, 1) == Tile.ROCK
    assert state.get(2, 2) == Tile.EMPTY
    assert state.alive is True

    step_realtime_frame(state, frame_number=2, action=None, timing_mode=TimingMode.SYNC, sync_interval=2)

    assert state.get(2, 2) == Tile.ROCK
    assert state.alive is True


def test_step_realtime_frame_sync_mode_retains_input_until_update_frame() -> None:
    state = make_state(
        "#####",
        "#P  #",
        "#   #",
        "#####",
    )

    step_realtime_frame(state, frame_number=1, action="d", timing_mode=TimingMode.SYNC, sync_interval=4)

    assert (state.player_x, state.player_y) == (1, 1)
    assert state.pending_action == "d"

    step_realtime_frame(state, frame_number=4, action=None, timing_mode=TimingMode.SYNC, sync_interval=4)

    assert (state.player_x, state.player_y) == (2, 1)
    assert state.pending_action is None


def test_step_realtime_frame_sync_mode_latest_input_wins_before_update_frame() -> None:
    state = make_state(
        "######",
        "# P  #",
        "######",
    )

    step_realtime_frame(state, frame_number=1, action="a", timing_mode=TimingMode.SYNC, sync_interval=4)
    step_realtime_frame(state, frame_number=3, action="d", timing_mode=TimingMode.SYNC, sync_interval=4)

    assert state.pending_action == "d"
    assert (state.player_x, state.player_y) == (2, 1)

    step_realtime_frame(state, frame_number=4, action=None, timing_mode=TimingMode.SYNC, sync_interval=4)

    assert (state.player_x, state.player_y) == (3, 1)
    assert state.pending_action is None


def test_step_realtime_frame_sync_mode_update_frame_input_replaces_older_buffered_input() -> None:
    state = make_state(
        "######",
        "# P  #",
        "######",
    )
    buffer_action(state, "a")

    step_realtime_frame(state, frame_number=4, action="d", timing_mode=TimingMode.SYNC, sync_interval=4)

    assert (state.player_x, state.player_y) == (3, 1)
    assert state.pending_action is None


def test_step_realtime_frame_sync_mode_consumed_action_is_not_replayed() -> None:
    state = make_state(
        "#######",
        "# P   #",
        "#     #",
        "#######",
    )

    step_realtime_frame(state, frame_number=1, action="d", timing_mode=TimingMode.SYNC, sync_interval=2)
    step_realtime_frame(state, frame_number=2, action=None, timing_mode=TimingMode.SYNC, sync_interval=2)
    step_realtime_frame(state, frame_number=4, action=None, timing_mode=TimingMode.SYNC, sync_interval=2)

    assert (state.player_x, state.player_y) == (3, 1)
    assert state.pending_action is None


def test_step_realtime_frame_sync_mode_preserves_falling_state_across_skipped_frames() -> None:
    state = make_state(
        "#####",
        "# O #",
        "#   #",
        "# P #",
        "#####",
    )

    step_realtime_frame(state, frame_number=2, action=None, timing_mode=TimingMode.SYNC, sync_interval=2)

    assert state.get(2, 2) == Tile.ROCK
    assert state.alive is True

    step_realtime_frame(state, frame_number=3, action=None, timing_mode=TimingMode.SYNC, sync_interval=2)

    assert state.get(2, 2) == Tile.ROCK
    assert state.alive is True

    step_realtime_frame(state, frame_number=4, action=None, timing_mode=TimingMode.SYNC, sync_interval=2)

    assert state.get(2, 3) == Tile.ROCK
    assert state.alive is False


def test_step_realtime_frame_sync_mode_runs_game_update_on_update_frames() -> None:
    state = make_state(
        "#####",
        "#P  #",
        "# O #",
        "#   #",
        "#####",
    )

    step_realtime_frame(state, frame_number=2, action="d", timing_mode=TimingMode.SYNC, sync_interval=2)

    assert (state.player_x, state.player_y) == (2, 1)
    assert state.get(2, 3) == Tile.ROCK


def test_step_realtime_frame_sync_mode_can_consume_buffered_input_on_frame_zero() -> None:
    state = make_state(
        "#####",
        "#P  #",
        "#####",
    )

    step_realtime_frame(state, frame_number=0, action="d", timing_mode=TimingMode.SYNC, sync_interval=8)

    assert (state.player_x, state.player_y) == (2, 1)
    assert state.pending_action is None


def test_step_realtime_frame_sync_mode_retains_input_across_boundary_until_next_sync_tick() -> None:
    state = make_state(
        "######",
        "#P   #",
        "######",
    )

    step_realtime_frame(state, frame_number=7, action="d", timing_mode=TimingMode.SYNC, sync_interval=8)

    assert (state.player_x, state.player_y) == (1, 1)
    assert state.pending_action == "d"

    step_realtime_frame(state, frame_number=8, action=None, timing_mode=TimingMode.SYNC, sync_interval=8)

    assert (state.player_x, state.player_y) == (2, 1)
    assert state.pending_action is None


def test_step_realtime_frame_does_not_store_buffered_input_after_win() -> None:
    state = make_state(
        "#####",
        "#P* #",
        "#####",
    )
    state.try_move_player(1, 0)

    step_realtime_frame(state, frame_number=0, action="d", timing_mode=TimingMode.ASYNC)

    assert state.won is True
    assert state.pending_action is None


def test_step_realtime_frame_does_not_store_buffered_input_after_death() -> None:
    state = make_state(
        "#####",
        "#P  #",
        "#####",
    )
    state.alive = False

    step_realtime_frame(state, frame_number=0, action="d", timing_mode=TimingMode.ASYNC)

    assert state.pending_action is None


def test_step_realtime_frame_clears_buffer_when_consumed_action_cannot_move() -> None:
    state = make_state(
        "#####",
        "#P###",
        "#####",
    )

    step_realtime_frame(state, frame_number=0, action="d", timing_mode=TimingMode.ASYNC)

    assert (state.player_x, state.player_y) == (1, 1)
    assert state.pending_action is None


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


def test_graphics_mode_sync_timing_consumes_buffered_input_on_sync_frame(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pygame(monkeypatch)

    class SequencedEventQueue:
        frames = [
            [],
            [FakeEvent(FakePygame.KEYDOWN, FakePygame.K_d)],
            [],
        ]
        index = 0

        @classmethod
        def get(cls) -> list[FakeEvent]:
            if cls.index >= len(cls.frames):
                return []
            events = cls.frames[cls.index]
            cls.index += 1
            return events

    monkeypatch.setattr(FakePygame, "event", SequencedEventQueue)

    state = make_state(
        "######",
        "#P   #",
        "######",
    )

    run_interactive_realtime_graphics(
        state,
        tick_ms=250,
        tile_size=32,
        max_frames=3,
        timing_mode=TimingMode.SYNC,
        sync_interval=2,
    )

    assert (state.player_x, state.player_y) == (2, 1)
    assert state.pending_action is None


def test_graphics_mode_uses_screen_size_layout_helper(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_pygame(monkeypatch)
    set_mode_calls: list[tuple[int, int]] = []

    class FakeDisplay:
        @staticmethod
        def set_caption(text: str) -> None:
            pass

        @staticmethod
        def set_mode(size: tuple[int, int]) -> FakeScreen:
            set_mode_calls.append(size)
            return FakeScreen()

        @staticmethod
        def flip() -> None:
            pass

    monkeypatch.setattr(FakePygame, "display", FakeDisplay)

    state = make_state(
        "#####",
        "#P  #",
        "#####",
    )

    run_interactive_realtime_graphics(state, tick_ms=250, tile_size=16, max_frames=1)

    assert set_mode_calls == [screen_size_px(state, 16)]


def test_graphics_mode_uses_configured_font_size_and_hud_height(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_pygame(monkeypatch)
    set_mode_calls: list[tuple[int, int]] = []
    font_calls: list[tuple[str, int]] = []

    class FakeDisplay:
        @staticmethod
        def set_caption(text: str) -> None:
            pass

        @staticmethod
        def set_mode(size: tuple[int, int]) -> FakeScreen:
            set_mode_calls.append(size)
            return FakeScreen()

        @staticmethod
        def flip() -> None:
            pass

    class FakeFontModule:
        @staticmethod
        def SysFont(name: str, size: int) -> FakeFont:
            font_calls.append((name, size))
            return FakeFont()

    monkeypatch.setattr(FakePygame, "display", FakeDisplay)
    monkeypatch.setattr(FakePygame, "font", FakeFontModule)

    state = make_state(
        "#####",
        "#P  #",
        "#####",
    )

    run_interactive_realtime_graphics(
        state,
        tick_ms=250,
        tile_size=16,
        max_frames=1,
        font_size=30,
        hud_height=100,
    )

    assert set_mode_calls == [screen_size_px(state, 16, font_size=30, hud_height=100)]
    assert font_calls == [("arial", 30)]
