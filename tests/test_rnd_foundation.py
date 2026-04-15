import pytest

from rnd_foundation import (
    BUILTIN_ELEMENTS,
    BUILTIN_TILE_ELEMENTS,
    BUILTIN_TILE_ELEMENT_IDS,
    BUILTIN_TILE_SYMBOLS,
    CUSTOM_ELEMENTS,
    CUSTOM_ELEMENT_SYMBOLS,
    CustomElement,
    BRICK_ELEMENT_ID,
    DIAMOND_ELEMENT_ID,
    DEFAULT_CUSTOM_ELEMENTS,
    DEFAULT_ENGINE_MODE,
    EngineMode,
    GameState,
    EMPTY_ELEMENT_ID,
    PLAYER_ELEMENT_ID,
    ROCK_ELEMENT_ID,
    SAND_ELEMENT_ID,
    SLIME_ELEMENT_ID,
    TimingMode,
    Tile,
    WALL_ELEMENT_ID,
    active_motions,
    action_from_pygame_frame_events,
    action_from_pygame_key,
    action_from_pygame_pressed_keys,
    action_from_turn_input,
    buffer_action,
    builtin_tile_for_element_id,
    cell_can_fall,
    cell_for_parsed_cell,
    cell_for_tile,
    cell_is_collectible,
    cell_is_diggable,
    cell_is_empty,
    cell_is_motion_trackable,
    cell_is_player,
    cell_is_pushable,
    consume_buffered_action,
    can_fall_element,
    can_player_take_action,
    clamp_progress,
    complete_motion,
    compatibility_tile_for_element_cell,
    compatibility_tile_for_level_symbol,
    color_for_element_id,
    custom_element_for,
    custom_element_for_cell,
    custom_element_for_symbol,
    custom_element_for_tile,
    element_cell_appearance,
    element_cell_color,
    element_appearance,
    element_color,
    default_motion_duration_frames,
    draw_background,
    draw_board,
    draw_hud,
    builtin_element_for_id,
    engine_config,
    engine_hold_repeat_frames,
    engine_motion_duration_frames,
    element_id_for_tile,
    find_moving_object_motions,
    find_vertical_falling_motions,
    get_motion,
    held_actions_from_pygame_pressed_keys,
    has_active_player_motion,
    hud_background_color,
    hud_height_px,
    hud_line_gap_px,
    hud_top_padding_px,
    is_collectible,
    is_diggable,
    is_pushable,
    is_update_frame,
    make_hold_state,
    make_motion_state,
    main,
    motion_destination_cell,
    motion_cell,
    motion_is_complete,
    motion_position_px,
    motion_progress,
    motion_rect,
    motion_start_cell,
    motion_start_frame,
    motion_tile,
    moving_object_cells,
    parse_level,
    parse_level_element_cells,
    player_cell,
    pygame_frame_requests_quit,
    ParsedCell,
    parse_level_cells,
    register_custom_element,
    background_color,
    board_background_color,
    board_size_px,
    clear_tile_surface_cache,
    remove_motion,
    render_frame,
    repeated_held_action,
    run_interactive_realtime_graphics,
    run_interactive_realtime_terminal,
    screen_size_px,
    set_motion,
    start_motion,
    step_game,
    step_realtime_frame,
    surrogate_tile_for_custom_element,
    surrogate_tile_for_element_cell,
    parsed_cell_appearance,
    element_cell_for_parsed_cell,
    parsed_cell_for_cell,
    parsed_cell_for_level_symbol,
    parsed_cell_element,
    parsed_cell_is_collectible,
    parsed_cell_is_diggable,
    parsed_cell_is_empty,
    parsed_cell_is_player,
    parsed_cell_is_pushable,
    parsed_cell_can_fall,
    parsed_cell_for_tile,
    custom_element_symbols,
    tile_for_symbol,
    tile_for_level_symbol,
    tile_appearance,
    tile_for_cell,
    tile_for_element_cell,
    tile_grid_for_element_cells,
    symbol_for_element_cell,
    tile_color,
    tile_rect,
    tile_surface,
    track_falling_motions,
    track_moving_object_motions,
    track_player_motion,
    update_graphics_frame,
    make_motion,
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


def test_parse_level_supports_true_custom_brick_cell() -> None:
    state = make_state(
        "#####",
        "#PB #",
        "#####",
    )

    assert state.get_cell(2, 1) == BRICK_ELEMENT_ID
    assert state.render_lines() == [
        "#####",
        "#PB #",
        "#####",
    ]


def test_game_state_cell_accessors_bridge_tile_backed_grid() -> None:
    state = make_state(
        "#####",
        "#P.O#",
        "#####",
    )

    assert state.get_cell(1, 1) == PLAYER_ELEMENT_ID
    assert state.get_cell(2, 1) == SAND_ELEMENT_ID
    assert state.get_cell(3, 1) == ROCK_ELEMENT_ID

    state.set_cell(2, 1, None)
    state.set_cell(3, 1, SAND_ELEMENT_ID)

    assert state.get(2, 1) == Tile.EMPTY
    assert state.get(3, 1) == Tile.SAND


def test_game_state_tile_bridge_reads_true_custom_cells_as_builtin_tiles() -> None:
    state = make_state(
        "#####",
        "#Ps #",
        "#####",
    )

    assert state.get_cell(2, 1) == SLIME_ELEMENT_ID
    assert state.get(2, 1) == Tile.SAND


def test_game_state_tile_bridge_set_preserves_tile_compatibility() -> None:
    state = make_state(
        "#####",
        "#P  #",
        "#####",
    )

    state.set(2, 1, Tile.DIAMOND)

    assert state.get_cell(2, 1) == DIAMOND_ELEMENT_ID
    assert state.get(2, 1) == Tile.DIAMOND


def test_game_state_explicit_tile_compatibility_helpers_match_get_and_set() -> None:
    state = make_state(
        "#####",
        "#P  #",
        "#####",
    )

    state.set_tile(2, 1, Tile.ROCK)

    assert state.get_tile(2, 1) == Tile.ROCK
    assert state.get(2, 1) == Tile.ROCK
    assert state.get_cell(2, 1) == ROCK_ELEMENT_ID


def test_make_motion_stores_element_cell_identity() -> None:
    player_motion = make_motion(Tile.PLAYER, (1, 2), (2, 2), 7)
    rock_motion = make_motion(ROCK_ELEMENT_ID, (2, 1), (2, 2), 8)

    assert motion_cell(player_motion) == PLAYER_ELEMENT_ID
    assert motion_cell(rock_motion) == ROCK_ELEMENT_ID
    assert motion_tile(player_motion) == Tile.PLAYER
    assert motion_tile(rock_motion) == Tile.ROCK


def test_custom_element_stores_declared_properties() -> None:
    element = CustomElement(
        name="custom-rock",
        symbol="r",
        diggable=False,
        collectible=False,
        pushable=True,
        can_fall=True,
    )

    assert element.name == "custom-rock"
    assert element.symbol == "r"
    assert element.diggable is False
    assert element.collectible is False
    assert element.pushable is True
    assert element.can_fall is True


def test_custom_element_defaults_boolean_properties_to_false() -> None:
    element = CustomElement(name="custom-wall", symbol="w")

    assert element == CustomElement(
        name="custom-wall",
        symbol="w",
        diggable=False,
        collectible=False,
        pushable=False,
        can_fall=False,
    )


def test_parsed_cell_can_wrap_builtin_tile() -> None:
    cell = parsed_cell_for_tile(Tile.ROCK)

    assert cell == ParsedCell(tile=Tile.ROCK)
    assert parsed_cell_element(cell, CUSTOM_ELEMENTS) == Tile.ROCK


def test_parsed_cell_can_reference_registered_custom_element() -> None:
    registry = dict(DEFAULT_CUSTOM_ELEMENTS)
    register_custom_element(registry, CustomElement(name="slime", symbol="s", diggable=True))
    cell = ParsedCell(custom_element_name="slime")

    assert parsed_cell_element(cell, registry) == registry["slime"]


def test_parsed_cell_rejects_invalid_state_shapes() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        ParsedCell()

    with pytest.raises(ValueError, match="exactly one"):
        ParsedCell(tile=Tile.ROCK, custom_element_name="slime")


def test_parsed_cell_element_rejects_unknown_custom_element_name() -> None:
    with pytest.raises(ValueError, match="Unknown custom element 'gel'"):
        parsed_cell_element(ParsedCell(custom_element_name="gel"), DEFAULT_CUSTOM_ELEMENTS)


def test_parsed_cell_for_level_symbol_returns_builtin_tile_cells() -> None:
    assert parsed_cell_for_level_symbol("O", DEFAULT_CUSTOM_ELEMENTS) == ParsedCell(tile=Tile.ROCK)
    assert parsed_cell_for_level_symbol("P", DEFAULT_CUSTOM_ELEMENTS) == ParsedCell(tile=Tile.PLAYER)


def test_parsed_cell_for_level_symbol_returns_custom_element_cells() -> None:
    registry = dict(DEFAULT_CUSTOM_ELEMENTS)
    register_custom_element(registry, CustomElement(name="slime", symbol="s", diggable=True))

    assert parsed_cell_for_level_symbol("s", registry) == ParsedCell(custom_element_name="slime")


def test_parse_level_cells_supports_builtin_and_custom_symbols() -> None:
    registry = dict(DEFAULT_CUSTOM_ELEMENTS)
    register_custom_element(registry, CustomElement(name="slime", symbol="s", diggable=True))

    cells = parse_level_cells(
        [
            "#####",
            "#Ps #",
            "#####",
        ],
        registry,
    )

    assert cells == [
        [ParsedCell(tile=Tile.WALL), ParsedCell(tile=Tile.WALL), ParsedCell(tile=Tile.WALL), ParsedCell(tile=Tile.WALL), ParsedCell(tile=Tile.WALL)],
        [ParsedCell(tile=Tile.WALL), ParsedCell(tile=Tile.PLAYER), ParsedCell(custom_element_name="slime"), ParsedCell(tile=Tile.EMPTY), ParsedCell(tile=Tile.WALL)],
        [ParsedCell(tile=Tile.WALL), ParsedCell(tile=Tile.WALL), ParsedCell(tile=Tile.WALL), ParsedCell(tile=Tile.WALL), ParsedCell(tile=Tile.WALL)],
    ]


def test_parse_level_element_cells_supports_builtin_and_custom_symbols() -> None:
    cells = parse_level_element_cells(
        [
            "#####",
            "#Ps #",
            "#####",
        ],
        DEFAULT_CUSTOM_ELEMENTS,
    )

    assert cells == [
        [WALL_ELEMENT_ID, WALL_ELEMENT_ID, WALL_ELEMENT_ID, WALL_ELEMENT_ID, WALL_ELEMENT_ID],
        [WALL_ELEMENT_ID, PLAYER_ELEMENT_ID, SLIME_ELEMENT_ID, None, WALL_ELEMENT_ID],
        [WALL_ELEMENT_ID, WALL_ELEMENT_ID, WALL_ELEMENT_ID, WALL_ELEMENT_ID, WALL_ELEMENT_ID],
    ]


def test_parse_level_element_cells_supports_builtin_only_levels() -> None:
    cells = parse_level_element_cells(
        [
            "#####",
            "#P.*#",
            "# O #",
            "#####",
        ],
        DEFAULT_CUSTOM_ELEMENTS,
    )

    assert cells == [
        [WALL_ELEMENT_ID, WALL_ELEMENT_ID, WALL_ELEMENT_ID, WALL_ELEMENT_ID, WALL_ELEMENT_ID],
        [WALL_ELEMENT_ID, PLAYER_ELEMENT_ID, SAND_ELEMENT_ID, DIAMOND_ELEMENT_ID, WALL_ELEMENT_ID],
        [WALL_ELEMENT_ID, None, ROCK_ELEMENT_ID, None, WALL_ELEMENT_ID],
        [WALL_ELEMENT_ID, WALL_ELEMENT_ID, WALL_ELEMENT_ID, WALL_ELEMENT_ID, WALL_ELEMENT_ID],
    ]


def test_parse_level_cells_rejects_empty_input() -> None:
    with pytest.raises(ValueError, match="Level is empty"):
        parse_level_cells([], DEFAULT_CUSTOM_ELEMENTS)


def test_parse_level_cells_rejects_uneven_rows() -> None:
    with pytest.raises(ValueError, match="equal width"):
        parse_level_cells(["#####", "#P #", "#####"], DEFAULT_CUSTOM_ELEMENTS)


def test_parse_level_cells_rejects_unsupported_symbol() -> None:
    with pytest.raises(ValueError, match="Unsupported tile 'x' at \\(1,1\\)"):
        parse_level_cells(
            [
                "###",
                "#x#",
                "###",
            ],
            DEFAULT_CUSTOM_ELEMENTS,
        )


def test_element_color_matches_builtin_tile_colors() -> None:
    assert element_color(Tile.ROCK) == tile_color(Tile.ROCK)
    assert element_color(Tile.DIAMOND) == tile_color(Tile.DIAMOND)


def test_element_color_uses_symbol_based_fallback_for_custom_elements() -> None:
    assert element_color(CustomElement(name="custom-rock", symbol="O")) == tile_color(Tile.ROCK)
    assert element_color(CustomElement(name="custom-slime", symbol="s")) == (220, 90, 90)


def test_symbol_for_element_cell_supports_empty_builtin_and_custom_cells() -> None:
    assert symbol_for_element_cell(None, DEFAULT_CUSTOM_ELEMENTS) == " "
    assert symbol_for_element_cell(ROCK_ELEMENT_ID, DEFAULT_CUSTOM_ELEMENTS) == "O"
    assert symbol_for_element_cell(SLIME_ELEMENT_ID, DEFAULT_CUSTOM_ELEMENTS) == "s"


def test_color_for_element_id_supports_builtin_and_custom_ids() -> None:
    assert color_for_element_id(None) == tile_color(Tile.EMPTY)
    assert color_for_element_id(ROCK_ELEMENT_ID) == tile_color(Tile.ROCK)
    assert color_for_element_id(DIAMOND_ELEMENT_ID) == tile_color(Tile.DIAMOND)
    assert color_for_element_id(SLIME_ELEMENT_ID) == (220, 90, 90)
    assert color_for_element_id(BRICK_ELEMENT_ID) == (150, 80, 80)
    assert color_for_element_id("mystery") == (220, 90, 90)


def test_element_appearance_supports_builtin_tiles_and_custom_elements() -> None:
    assert element_appearance(Tile.SAND, 24) == tile_appearance(Tile.SAND, 24)
    assert element_appearance(CustomElement(name="custom-gem", symbol="*"), 24) == (None, tile_color(Tile.DIAMOND))


def test_tile_bridge_keeps_builtin_and_custom_appearance_paths_consistent() -> None:
    state = make_state(
        "#####",
        "#Ps #",
        "#####",
    )

    assert tile_appearance(state.get(2, 1), 24) == tile_appearance(Tile.SAND, 24)
    assert element_cell_appearance(state.get_cell(2, 1), DEFAULT_CUSTOM_ELEMENTS, 24) == (None, (220, 90, 90))


def test_element_cell_color_supports_empty_builtin_and_custom_cells() -> None:
    assert element_cell_color(None, DEFAULT_CUSTOM_ELEMENTS) == tile_color(Tile.EMPTY)
    assert element_cell_color(ROCK_ELEMENT_ID, DEFAULT_CUSTOM_ELEMENTS) == tile_color(Tile.ROCK)
    assert element_cell_color(SLIME_ELEMENT_ID, DEFAULT_CUSTOM_ELEMENTS) == (220, 90, 90)


def test_element_cell_appearance_supports_builtin_and_custom_cells() -> None:
    assert element_cell_appearance(ROCK_ELEMENT_ID, DEFAULT_CUSTOM_ELEMENTS, 24) == tile_appearance(Tile.ROCK, 24)
    assert element_cell_appearance(SLIME_ELEMENT_ID, DEFAULT_CUSTOM_ELEMENTS, 24) == (None, (220, 90, 90))
    assert element_cell_appearance(None, DEFAULT_CUSTOM_ELEMENTS, 24) == tile_appearance(Tile.EMPTY, 24)


def test_parsed_cell_appearance_resolves_builtin_and_custom_cells() -> None:
    registry = dict(DEFAULT_CUSTOM_ELEMENTS)
    register_custom_element(registry, CustomElement(name="slime", symbol="s", diggable=True))

    assert parsed_cell_appearance(ParsedCell(tile=Tile.ROCK), registry, 24) == tile_appearance(Tile.ROCK, 24)
    assert parsed_cell_appearance(ParsedCell(custom_element_name="slime"), registry, 24) == (None, (220, 90, 90))


def test_parsed_cell_property_helpers_support_builtin_cells() -> None:
    registry = DEFAULT_CUSTOM_ELEMENTS

    assert parsed_cell_is_diggable(ParsedCell(tile=Tile.SAND), registry) is True
    assert parsed_cell_is_collectible(ParsedCell(tile=Tile.DIAMOND), registry) is True
    assert parsed_cell_is_pushable(ParsedCell(tile=Tile.ROCK), registry) is True
    assert parsed_cell_can_fall(ParsedCell(tile=Tile.ROCK), registry) is True
    assert parsed_cell_is_empty(ParsedCell(tile=Tile.EMPTY)) is True
    assert parsed_cell_is_player(ParsedCell(tile=Tile.PLAYER)) is True


def test_parsed_cell_property_helpers_support_custom_element_cells() -> None:
    registry = dict(DEFAULT_CUSTOM_ELEMENTS)
    register_custom_element(
        registry,
        CustomElement(
            name="crumbly",
            symbol="c",
            diggable=True,
            collectible=False,
            pushable=True,
            can_fall=False,
        ),
    )
    slime_cell = ParsedCell(custom_element_name="crumbly")

    assert parsed_cell_is_diggable(slime_cell, registry) is True
    assert parsed_cell_is_collectible(slime_cell, registry) is False
    assert parsed_cell_is_pushable(slime_cell, registry) is True
    assert parsed_cell_can_fall(slime_cell, registry) is False


def test_custom_element_registry_exposes_builtin_style_examples() -> None:
    assert CUSTOM_ELEMENTS["sand"] == CustomElement(
        name="sand",
        symbol=".",
        diggable=True,
        collectible=False,
        pushable=False,
        can_fall=False,
    )
    assert CUSTOM_ELEMENTS["slime"] == CustomElement(
        name="slime",
        symbol="s",
        diggable=True,
        collectible=False,
        pushable=False,
        can_fall=False,
    )
    assert CUSTOM_ELEMENTS["rock"] == CustomElement(
        name="rock",
        symbol="O",
        diggable=False,
        collectible=False,
        pushable=True,
        can_fall=True,
    )
    assert CUSTOM_ELEMENTS["diamond"] == CustomElement(
        name="diamond",
        symbol="*",
        diggable=False,
        collectible=True,
        pushable=False,
        can_fall=True,
    )


def test_default_custom_elements_seed_runtime_custom_element_registry() -> None:
    assert CUSTOM_ELEMENTS == DEFAULT_CUSTOM_ELEMENTS


def test_register_custom_element_adds_new_named_element() -> None:
    registry = dict(DEFAULT_CUSTOM_ELEMENTS)
    slime = CustomElement(name="slime", symbol="s", diggable=True)

    register_custom_element(registry, slime)

    assert registry["slime"] == slime


def test_register_custom_element_rejects_duplicate_name_with_different_definition() -> None:
    registry = dict(DEFAULT_CUSTOM_ELEMENTS)

    with pytest.raises(ValueError, match="name 'sand' is already registered"):
        register_custom_element(registry, CustomElement(name="sand", symbol="x"))


def test_register_custom_element_rejects_duplicate_symbol() -> None:
    registry = dict(DEFAULT_CUSTOM_ELEMENTS)

    with pytest.raises(ValueError, match="symbol '\\.' is already registered"):
        register_custom_element(registry, CustomElement(name="goo", symbol="."))


def test_custom_element_registry_uses_unique_symbols() -> None:
    symbols = [element.symbol for element in CUSTOM_ELEMENTS.values()]

    assert len(symbols) == len(set(symbols))


def test_builtin_tile_elements_mirror_current_builtin_tiles() -> None:
    assert BUILTIN_TILE_ELEMENTS[Tile.EMPTY] == CustomElement(name="empty", symbol=" ")
    assert BUILTIN_TILE_ELEMENTS[Tile.WALL] == CUSTOM_ELEMENTS["wall"]
    assert BUILTIN_TILE_ELEMENTS[Tile.SAND] == CUSTOM_ELEMENTS["sand"]
    assert BUILTIN_TILE_ELEMENTS[Tile.ROCK] == CUSTOM_ELEMENTS["rock"]
    assert BUILTIN_TILE_ELEMENTS[Tile.DIAMOND] == CUSTOM_ELEMENTS["diamond"]
    assert BUILTIN_TILE_ELEMENTS[Tile.PLAYER] == CUSTOM_ELEMENTS["player"]


def test_builtin_tile_element_ids_expose_stable_builtin_names() -> None:
    assert BUILTIN_TILE_ELEMENT_IDS == {
        Tile.EMPTY: EMPTY_ELEMENT_ID,
        Tile.WALL: WALL_ELEMENT_ID,
        Tile.SAND: SAND_ELEMENT_ID,
        Tile.ROCK: ROCK_ELEMENT_ID,
        Tile.DIAMOND: DIAMOND_ELEMENT_ID,
        Tile.PLAYER: PLAYER_ELEMENT_ID,
    }


def test_builtin_elements_are_addressable_by_builtin_element_id() -> None:
    assert BUILTIN_ELEMENTS[EMPTY_ELEMENT_ID] == CustomElement(name=EMPTY_ELEMENT_ID, symbol=" ")
    assert BUILTIN_ELEMENTS[WALL_ELEMENT_ID] == CUSTOM_ELEMENTS["wall"]
    assert BUILTIN_ELEMENTS[SAND_ELEMENT_ID] == CUSTOM_ELEMENTS["sand"]
    assert BUILTIN_ELEMENTS[ROCK_ELEMENT_ID] == CUSTOM_ELEMENTS["rock"]
    assert BUILTIN_ELEMENTS[DIAMOND_ELEMENT_ID] == CUSTOM_ELEMENTS["diamond"]
    assert BUILTIN_ELEMENTS[PLAYER_ELEMENT_ID] == CUSTOM_ELEMENTS["player"]


def test_element_id_for_tile_returns_stable_builtin_ids() -> None:
    assert element_id_for_tile(Tile.EMPTY) == EMPTY_ELEMENT_ID
    assert element_id_for_tile(Tile.WALL) == WALL_ELEMENT_ID
    assert element_id_for_tile(Tile.SAND) == SAND_ELEMENT_ID
    assert element_id_for_tile(Tile.ROCK) == ROCK_ELEMENT_ID
    assert element_id_for_tile(Tile.DIAMOND) == DIAMOND_ELEMENT_ID
    assert element_id_for_tile(Tile.PLAYER) == PLAYER_ELEMENT_ID


def test_builtin_element_for_id_returns_builtin_elements() -> None:
    assert builtin_element_for_id(EMPTY_ELEMENT_ID) == CustomElement(name=EMPTY_ELEMENT_ID, symbol=" ")
    assert builtin_element_for_id(WALL_ELEMENT_ID) == CUSTOM_ELEMENTS["wall"]
    assert builtin_element_for_id(SAND_ELEMENT_ID) == CUSTOM_ELEMENTS["sand"]
    assert builtin_element_for_id(ROCK_ELEMENT_ID) == CUSTOM_ELEMENTS["rock"]
    assert builtin_element_for_id(DIAMOND_ELEMENT_ID) == CUSTOM_ELEMENTS["diamond"]
    assert builtin_element_for_id(PLAYER_ELEMENT_ID) == CUSTOM_ELEMENTS["player"]


def test_builtin_element_for_id_rejects_unknown_id() -> None:
    with pytest.raises(ValueError, match="Unknown built-in element id 'unknown'"):
        builtin_element_for_id("unknown")


def test_builtin_tile_for_element_id_returns_builtin_tiles() -> None:
    assert builtin_tile_for_element_id(EMPTY_ELEMENT_ID) == Tile.EMPTY
    assert builtin_tile_for_element_id(WALL_ELEMENT_ID) == Tile.WALL
    assert builtin_tile_for_element_id(SAND_ELEMENT_ID) == Tile.SAND
    assert builtin_tile_for_element_id(ROCK_ELEMENT_ID) == Tile.ROCK
    assert builtin_tile_for_element_id(DIAMOND_ELEMENT_ID) == Tile.DIAMOND
    assert builtin_tile_for_element_id(PLAYER_ELEMENT_ID) == Tile.PLAYER


def test_builtin_tile_for_element_id_rejects_unknown_id() -> None:
    with pytest.raises(ValueError, match="Unknown built-in element id 'unknown'"):
        builtin_tile_for_element_id("unknown")


def test_cell_for_tile_uses_none_for_empty_and_element_ids_for_builtins() -> None:
    assert cell_for_tile(Tile.EMPTY) is None
    assert cell_for_tile(Tile.WALL) == WALL_ELEMENT_ID
    assert cell_for_tile(Tile.SAND) == SAND_ELEMENT_ID
    assert cell_for_tile(Tile.ROCK) == ROCK_ELEMENT_ID
    assert cell_for_tile(Tile.DIAMOND) == DIAMOND_ELEMENT_ID
    assert cell_for_tile(Tile.PLAYER) == PLAYER_ELEMENT_ID


def test_tile_for_cell_round_trips_builtin_cells() -> None:
    assert tile_for_cell(None) == Tile.EMPTY
    assert tile_for_cell(WALL_ELEMENT_ID) == Tile.WALL
    assert tile_for_cell(SAND_ELEMENT_ID) == Tile.SAND
    assert tile_for_cell(ROCK_ELEMENT_ID) == Tile.ROCK
    assert tile_for_cell(DIAMOND_ELEMENT_ID) == Tile.DIAMOND
    assert tile_for_cell(PLAYER_ELEMENT_ID) == Tile.PLAYER


def test_tile_for_element_cell_supports_builtin_and_custom_cells() -> None:
    assert tile_for_element_cell(None, DEFAULT_CUSTOM_ELEMENTS) == Tile.EMPTY
    assert tile_for_element_cell(ROCK_ELEMENT_ID, DEFAULT_CUSTOM_ELEMENTS) == Tile.ROCK
    assert tile_for_element_cell(SLIME_ELEMENT_ID, DEFAULT_CUSTOM_ELEMENTS) == Tile.SAND


def test_surrogate_tile_for_element_cell_exposes_isolated_fallback_behavior() -> None:
    assert surrogate_tile_for_element_cell(None, DEFAULT_CUSTOM_ELEMENTS) == Tile.EMPTY
    assert surrogate_tile_for_element_cell(ROCK_ELEMENT_ID, DEFAULT_CUSTOM_ELEMENTS) == Tile.ROCK
    assert surrogate_tile_for_element_cell(SLIME_ELEMENT_ID, DEFAULT_CUSTOM_ELEMENTS) == Tile.SAND


def test_compatibility_tile_for_element_cell_matches_existing_bridge() -> None:
    assert compatibility_tile_for_element_cell(None, DEFAULT_CUSTOM_ELEMENTS) == Tile.EMPTY
    assert compatibility_tile_for_element_cell(ROCK_ELEMENT_ID, DEFAULT_CUSTOM_ELEMENTS) == Tile.ROCK
    assert compatibility_tile_for_element_cell(SLIME_ELEMENT_ID, DEFAULT_CUSTOM_ELEMENTS) == Tile.SAND


def test_tile_grid_for_element_cells_converts_builtin_and_custom_cells() -> None:
    assert tile_grid_for_element_cells(
        [
            [WALL_ELEMENT_ID, PLAYER_ELEMENT_ID, SLIME_ELEMENT_ID, None, WALL_ELEMENT_ID],
            [WALL_ELEMENT_ID, ROCK_ELEMENT_ID, DIAMOND_ELEMENT_ID, SAND_ELEMENT_ID, WALL_ELEMENT_ID],
        ],
        DEFAULT_CUSTOM_ELEMENTS,
    ) == [
        [Tile.WALL, Tile.PLAYER, Tile.SAND, Tile.EMPTY, Tile.WALL],
        [Tile.WALL, Tile.ROCK, Tile.DIAMOND, Tile.SAND, Tile.WALL],
    ]


def test_tile_for_element_cell_rejects_unknown_or_unmapped_custom_cells() -> None:
    with pytest.raises(ValueError, match="Unknown custom element 'gel'"):
        tile_for_element_cell("gel", DEFAULT_CUSTOM_ELEMENTS)

    with pytest.raises(ValueError, match="Custom element 'brick' is not yet mapped"):
        tile_for_element_cell(BRICK_ELEMENT_ID, DEFAULT_CUSTOM_ELEMENTS)

    registry = dict(DEFAULT_CUSTOM_ELEMENTS)
    register_custom_element(registry, CustomElement(name="mystery", symbol="m"))
    with pytest.raises(ValueError, match="Custom element 'mystery' is not yet mapped"):
        tile_for_element_cell("mystery", registry)


def test_surrogate_tile_for_element_cell_rejects_unknown_custom_cell() -> None:
    with pytest.raises(ValueError, match="Unknown custom element 'gel'"):
        surrogate_tile_for_element_cell("gel", DEFAULT_CUSTOM_ELEMENTS)


def test_compatibility_tile_for_element_cell_rejects_unmapped_custom_cell() -> None:
    registry = dict(DEFAULT_CUSTOM_ELEMENTS)
    register_custom_element(registry, CustomElement(name="mystery", symbol="m"))

    with pytest.raises(ValueError, match="Custom element 'mystery' is not yet mapped"):
        compatibility_tile_for_element_cell("mystery", registry)


def test_cell_is_empty_matches_none_based_unified_cell_model() -> None:
    assert cell_is_empty(None) is True
    assert cell_is_empty(SAND_ELEMENT_ID) is False


def test_parsed_cell_for_cell_round_trips_builtin_and_custom_cells() -> None:
    assert parsed_cell_for_cell(None) == ParsedCell(tile=Tile.EMPTY)
    assert parsed_cell_for_cell(ROCK_ELEMENT_ID) == ParsedCell(tile=Tile.ROCK)
    assert parsed_cell_for_cell(SLIME_ELEMENT_ID) == ParsedCell(custom_element_name=SLIME_ELEMENT_ID)


def test_cell_for_parsed_cell_round_trips_builtin_and_custom_cells() -> None:
    assert cell_for_parsed_cell(ParsedCell(tile=Tile.EMPTY)) is None
    assert cell_for_parsed_cell(ParsedCell(tile=Tile.ROCK)) == ROCK_ELEMENT_ID
    assert cell_for_parsed_cell(ParsedCell(custom_element_name=SLIME_ELEMENT_ID)) == SLIME_ELEMENT_ID


def test_element_cell_for_parsed_cell_matches_cell_for_parsed_cell() -> None:
    assert element_cell_for_parsed_cell(ParsedCell(tile=Tile.EMPTY)) is None
    assert element_cell_for_parsed_cell(ParsedCell(tile=Tile.ROCK)) == ROCK_ELEMENT_ID
    assert element_cell_for_parsed_cell(ParsedCell(custom_element_name=SLIME_ELEMENT_ID)) == SLIME_ELEMENT_ID


def test_custom_element_for_cell_supports_empty_builtin_and_custom_cells() -> None:
    assert custom_element_for_cell(None, DEFAULT_CUSTOM_ELEMENTS) is None
    assert custom_element_for_cell(ROCK_ELEMENT_ID, DEFAULT_CUSTOM_ELEMENTS) == CUSTOM_ELEMENTS["rock"]
    assert custom_element_for_cell(SLIME_ELEMENT_ID, DEFAULT_CUSTOM_ELEMENTS) == CUSTOM_ELEMENTS["slime"]


def test_custom_element_for_cell_rejects_unknown_custom_element_id() -> None:
    with pytest.raises(ValueError, match="Unknown custom element 'gel'"):
        custom_element_for_cell("gel", DEFAULT_CUSTOM_ELEMENTS)


def test_cell_property_helpers_support_builtin_and_custom_cells() -> None:
    assert cell_is_diggable(SAND_ELEMENT_ID, DEFAULT_CUSTOM_ELEMENTS) is True
    assert cell_is_collectible(DIAMOND_ELEMENT_ID, DEFAULT_CUSTOM_ELEMENTS) is True
    assert cell_is_pushable(ROCK_ELEMENT_ID, DEFAULT_CUSTOM_ELEMENTS) is True
    assert cell_can_fall(ROCK_ELEMENT_ID, DEFAULT_CUSTOM_ELEMENTS) is True
    assert cell_is_player(PLAYER_ELEMENT_ID, DEFAULT_CUSTOM_ELEMENTS) is True
    assert cell_is_diggable(SLIME_ELEMENT_ID, DEFAULT_CUSTOM_ELEMENTS) is True
    assert cell_is_empty(None) is True


def test_cell_property_helpers_return_false_for_empty_cells() -> None:
    assert cell_is_diggable(None, DEFAULT_CUSTOM_ELEMENTS) is False
    assert cell_is_collectible(None, DEFAULT_CUSTOM_ELEMENTS) is False
    assert cell_is_pushable(None, DEFAULT_CUSTOM_ELEMENTS) is False
    assert cell_can_fall(None, DEFAULT_CUSTOM_ELEMENTS) is False
    assert cell_is_player(None, DEFAULT_CUSTOM_ELEMENTS) is False


def test_cell_is_motion_trackable_matches_current_falling_policy() -> None:
    assert cell_is_motion_trackable(None, DEFAULT_CUSTOM_ELEMENTS) is False
    assert cell_is_motion_trackable(ROCK_ELEMENT_ID, DEFAULT_CUSTOM_ELEMENTS) is True
    assert cell_is_motion_trackable(DIAMOND_ELEMENT_ID, DEFAULT_CUSTOM_ELEMENTS) is True
    assert cell_is_motion_trackable(SLIME_ELEMENT_ID, DEFAULT_CUSTOM_ELEMENTS) is False
    assert cell_is_motion_trackable(BRICK_ELEMENT_ID, DEFAULT_CUSTOM_ELEMENTS) is False


def test_custom_element_for_tile_returns_builtin_mirror() -> None:
    assert custom_element_for_tile(Tile.ROCK) == CUSTOM_ELEMENTS["rock"]
    assert custom_element_for_tile(Tile.DIAMOND) == CUSTOM_ELEMENTS["diamond"]
    assert custom_element_for_tile(Tile.EMPTY) == CustomElement(name="empty", symbol=" ")


def test_custom_element_for_accepts_tile_or_custom_element() -> None:
    custom = CustomElement(name="custom-sand", symbol="z", diggable=True)

    assert custom_element_for(Tile.SAND) == CUSTOM_ELEMENTS["sand"]
    assert custom_element_for(custom) == custom


def test_custom_element_property_helpers_match_builtin_mirrors() -> None:
    assert is_diggable(Tile.SAND) is True
    assert is_collectible(Tile.DIAMOND) is True
    assert is_pushable(Tile.ROCK) is True
    assert can_fall_element(Tile.ROCK) is True
    assert is_diggable(Tile.WALL) is False
    assert is_collectible(Tile.EMPTY) is False


def test_custom_element_property_helpers_support_custom_elements() -> None:
    element = CustomElement(
        name="custom-gem",
        symbol="g",
        diggable=True,
        collectible=True,
        pushable=False,
        can_fall=True,
    )

    assert is_diggable(element) is True
    assert is_collectible(element) is True
    assert is_pushable(element) is False
    assert can_fall_element(element) is True


@pytest.mark.parametrize(
    ("tile", "diggable", "collectible", "pushable", "can_fall"),
    [
        (Tile.EMPTY, False, False, False, False),
        (Tile.WALL, False, False, False, False),
        (Tile.SAND, True, False, False, False),
        (Tile.ROCK, False, False, True, True),
        (Tile.DIAMOND, False, True, False, True),
        (Tile.PLAYER, False, False, False, False),
    ],
)
def test_custom_element_helpers_match_current_builtin_tile_semantics(
    tile: Tile,
    diggable: bool,
    collectible: bool,
    pushable: bool,
    can_fall: bool,
) -> None:
    assert is_diggable(tile) is diggable
    assert is_collectible(tile) is collectible
    assert is_pushable(tile) is pushable
    assert can_fall_element(tile) is can_fall


def test_dual_logic_path_keeps_sand_diggable_for_player_movement() -> None:
    state = make_state(
        "#####",
        "#P. #",
        "#####",
    )

    state.try_move_player(1, 0)

    assert (state.player_x, state.player_y) == (2, 1)
    assert state.get(1, 1) == Tile.EMPTY
    assert state.get(2, 1) == Tile.PLAYER


def test_dual_logic_path_keeps_diamond_collectible_for_player_movement() -> None:
    state = make_state(
        "#####",
        "#P* #",
        "#####",
    )

    state.try_move_player(1, 0)

    assert (state.player_x, state.player_y) == (2, 1)
    assert state.diamonds_collected == 1
    assert state.won is True


def test_dual_logic_path_keeps_rock_pushable_for_snap_push() -> None:
    state = make_state(
        "######",
        "#PO  #",
        "######",
    )

    state.try_snap(1, 0)

    assert state.get(2, 1) == Tile.EMPTY
    assert state.get(3, 1) == Tile.ROCK


def test_dual_logic_path_keeps_falling_elements_subject_to_gravity() -> None:
    state = make_state(
        "#####",
        "# O #",
        "#P  #",
        "#####",
    )

    state.apply_gravity()

    assert state.get(2, 1) == Tile.EMPTY
    assert state.get(2, 2) == Tile.ROCK


@pytest.mark.parametrize("tile", list(Tile))
def test_builtin_tile_mirror_preserves_symbol(tile: Tile) -> None:
    assert custom_element_for_tile(tile).symbol == tile.value


def test_builtin_tile_symbol_mapping_exposes_current_tile_symbols() -> None:
    assert BUILTIN_TILE_SYMBOLS["#"] == Tile.WALL
    assert BUILTIN_TILE_SYMBOLS["."] == Tile.SAND
    assert BUILTIN_TILE_SYMBOLS["O"] == Tile.ROCK
    assert BUILTIN_TILE_SYMBOLS["*"] == Tile.DIAMOND
    assert BUILTIN_TILE_SYMBOLS["P"] == Tile.PLAYER


def test_custom_element_symbol_mapping_exposes_registered_symbols() -> None:
    assert CUSTOM_ELEMENT_SYMBOLS["."] == CUSTOM_ELEMENTS["sand"]
    assert CUSTOM_ELEMENT_SYMBOLS["O"] == CUSTOM_ELEMENTS["rock"]
    assert CUSTOM_ELEMENT_SYMBOLS["*"] == CUSTOM_ELEMENTS["diamond"]


def test_custom_element_symbols_builds_symbol_lookup_for_given_registry() -> None:
    registry = {
        "slime": CustomElement(name="slime", symbol="s", diggable=True),
        "gem": CustomElement(name="gem", symbol="g", collectible=True),
    }

    assert custom_element_symbols(registry) == {
        "s": registry["slime"],
        "g": registry["gem"],
    }


def test_symbol_lookup_helpers_return_builtin_or_custom_matches() -> None:
    assert tile_for_symbol("O") == Tile.ROCK
    assert tile_for_symbol("P") == Tile.PLAYER
    assert custom_element_for_symbol(".") == CUSTOM_ELEMENTS["sand"]
    assert custom_element_for_symbol("*") == CUSTOM_ELEMENTS["diamond"]


def test_symbol_lookup_helpers_return_none_for_unknown_symbols() -> None:
    assert tile_for_symbol("x") is None
    assert custom_element_for_symbol("x") is None


def test_tile_for_level_symbol_returns_builtin_tiles_from_mapping_layer() -> None:
    assert tile_for_level_symbol("#") == Tile.WALL
    assert tile_for_level_symbol(".") == Tile.SAND
    assert tile_for_level_symbol("s") == Tile.SAND
    assert tile_for_level_symbol("O") == Tile.ROCK
    assert tile_for_level_symbol("*") == Tile.DIAMOND
    assert tile_for_level_symbol("P") == Tile.PLAYER


def test_compatibility_tile_for_level_symbol_matches_existing_bridge() -> None:
    assert compatibility_tile_for_level_symbol("#", DEFAULT_CUSTOM_ELEMENTS) == Tile.WALL
    assert compatibility_tile_for_level_symbol(".", DEFAULT_CUSTOM_ELEMENTS) == Tile.SAND
    assert compatibility_tile_for_level_symbol("s", DEFAULT_CUSTOM_ELEMENTS) == Tile.SAND
    assert compatibility_tile_for_level_symbol("O", DEFAULT_CUSTOM_ELEMENTS) == Tile.ROCK
    assert compatibility_tile_for_level_symbol("*", DEFAULT_CUSTOM_ELEMENTS) == Tile.DIAMOND
    assert compatibility_tile_for_level_symbol("P", DEFAULT_CUSTOM_ELEMENTS) == Tile.PLAYER


def test_surrogate_tile_for_custom_element_maps_supported_builtin_like_shapes() -> None:
    assert surrogate_tile_for_custom_element(CUSTOM_ELEMENTS["slime"]) == Tile.SAND
    assert surrogate_tile_for_custom_element(CUSTOM_ELEMENTS["diamond"]) == Tile.DIAMOND
    assert surrogate_tile_for_custom_element(CUSTOM_ELEMENTS["rock"]) == Tile.ROCK
    assert surrogate_tile_for_custom_element(CUSTOM_ELEMENTS["wall"]) is None


def test_tile_for_level_symbol_rejects_unknown_symbol() -> None:
    with pytest.raises(ValueError, match="Unsupported tile 'x'"):
        tile_for_level_symbol("x")


def test_parse_level_accepts_default_custom_slime_symbol_via_surrogate_tile() -> None:
    state = parse_level(
        [
            "#####",
            "#Ps #",
            "#####",
        ]
    )

    assert state.get(2, 1) == Tile.SAND


def test_parse_level_keeps_default_custom_slime_as_true_custom_cell() -> None:
    state = parse_level(
        [
            "#####",
            "#Ps #",
            "#####",
        ]
    )

    assert state.get_cell(2, 1) == SLIME_ELEMENT_ID
    assert state.grid[1][2] == SLIME_ELEMENT_ID
    assert state.render_lines() == [
        "#####",
        "#Ps #",
        "#####",
    ]


def test_player_can_dig_default_custom_slime_symbol() -> None:
    state = parse_level(
        [
            "#####",
            "#Ps #",
            "#####",
        ]
    )

    step_game(state, "d")

    assert (state.player_x, state.player_y) == (2, 1)
    assert state.get(1, 1) == Tile.EMPTY
    assert state.get(2, 1) == Tile.PLAYER


def test_builtin_sand_and_custom_slime_parse_to_equivalent_states() -> None:
    sand_state = parse_level(
        [
            "#####",
            "#P. #",
            "# *O#",
            "#####",
        ]
    )
    slime_state = parse_level(
        [
            "#####",
            "#Ps #",
            "# *O#",
            "#####",
        ]
    )

    assert [[slime_state.get(x, y) for x in range(slime_state.width)] for y in range(slime_state.height)] == [
        [sand_state.get(x, y) for x in range(sand_state.width)] for y in range(sand_state.height)
    ]
    assert slime_state.player_x == sand_state.player_x
    assert slime_state.player_y == sand_state.player_y
    assert slime_state.diamonds_total == sand_state.diamonds_total
    assert sand_state.get_cell(2, 1) == SAND_ELEMENT_ID
    assert slime_state.get_cell(2, 1) == SLIME_ELEMENT_ID


def test_builtin_sand_and_custom_slime_have_equivalent_movement_behavior() -> None:
    sand_state = parse_level(
        [
            "#####",
            "#P. #",
            "#####",
        ]
    )
    slime_state = parse_level(
        [
            "#####",
            "#Ps #",
            "#####",
        ]
    )

    step_game(sand_state, "d")
    step_game(slime_state, "d")

    assert [[slime_state.get(x, y) for x in range(slime_state.width)] for y in range(slime_state.height)] == [
        [sand_state.get(x, y) for x in range(sand_state.width)] for y in range(sand_state.height)
    ]
    assert slime_state.player_x == sand_state.player_x
    assert slime_state.player_y == sand_state.player_y
    assert slime_state.alive == sand_state.alive
    assert slime_state.won == sand_state.won


def test_builtin_sand_and_custom_slime_have_equivalent_snap_behavior() -> None:
    sand_state = parse_level(
        [
            "#####",
            "#P. #",
            "#####",
        ]
    )
    slime_state = parse_level(
        [
            "#####",
            "#Ps #",
            "#####",
        ]
    )

    step_game(sand_state, "D")
    step_game(slime_state, "D")

    assert [[slime_state.get(x, y) for x in range(slime_state.width)] for y in range(slime_state.height)] == [
        [sand_state.get(x, y) for x in range(sand_state.width)] for y in range(sand_state.height)
    ]
    assert slime_state.player_x == sand_state.player_x
    assert slime_state.player_y == sand_state.player_y


def test_builtin_collectible_count_is_unchanged_in_presence_of_custom_slime() -> None:
    state = parse_level(
        [
            "######",
            "#Ps* #",
            "######",
        ]
    )

    assert state.diamonds_total == 1
    assert state.diamonds_collected == 0


def test_builtin_only_level_round_trips_through_unified_parse_bridge() -> None:
    lines = [
        "#####",
        "#P.*#",
        "# O #",
        "#####",
    ]

    element_cells = parse_level_element_cells(lines, DEFAULT_CUSTOM_ELEMENTS)
    state = parse_level(lines)

    assert element_cells == state.grid


def test_builtin_only_state_after_move_matches_unified_parse_bridge_baseline() -> None:
    lines = [
        "######",
        "#P O*#",
        "######",
    ]

    state = parse_level(lines)
    baseline_grid = parse_level_element_cells(lines, DEFAULT_CUSTOM_ELEMENTS)

    assert state.grid == baseline_grid

    step_game(state, "d")

    assert state.render_lines() == [
        "######",
        "# PO*#",
        "######",
    ]
    assert state.diamonds_total == 1
    assert state.diamonds_collected == 0


def test_parse_level_uses_symbol_mapping_layer_for_registered_builtin_symbols() -> None:
    state = parse_level(
        [
            "#####",
            "#P.*#",
            "# O #",
            "#####",
        ]
    )

    assert state.get(1, 1) == Tile.PLAYER
    assert state.get(2, 1) == Tile.SAND
    assert state.get(3, 1) == Tile.DIAMOND
    assert state.get(2, 2) == Tile.ROCK


def test_engine_mode_exposes_named_engine_choices() -> None:
    assert EngineMode.RND.value == "rnd"
    assert EngineMode.EM.value == "em"


def test_default_engine_mode_is_rnd_baseline() -> None:
    assert DEFAULT_ENGINE_MODE == EngineMode.RND
    assert engine_config(DEFAULT_ENGINE_MODE) == (TimingMode.ASYNC, 1)


def test_engine_config_maps_rnd_and_em_to_timing_defaults() -> None:
    assert engine_config(EngineMode.RND) == (TimingMode.ASYNC, 1)
    assert engine_config(EngineMode.EM) == (TimingMode.SYNC, 8)


def test_engine_config_rejects_invalid_engine_mode() -> None:
    with pytest.raises(ValueError, match="Unsupported engine mode"):
        engine_config("broken")  # type: ignore[arg-type]


def test_engine_config_maps_to_expected_default_motion_duration() -> None:
    rnd_timing_mode, rnd_sync_interval = engine_config(EngineMode.RND)
    em_timing_mode, em_sync_interval = engine_config(EngineMode.EM)

    assert default_motion_duration_frames(rnd_timing_mode, rnd_sync_interval) == 8
    assert default_motion_duration_frames(em_timing_mode, em_sync_interval) == 8


def test_engine_motion_duration_frames_maps_rnd_and_em_baselines() -> None:
    assert engine_motion_duration_frames(EngineMode.RND) == 8
    assert engine_motion_duration_frames(EngineMode.EM) == 8


def test_engine_motion_duration_frames_rejects_invalid_engine_mode() -> None:
    with pytest.raises(ValueError, match="Unsupported engine mode"):
        engine_motion_duration_frames("broken")  # type: ignore[arg-type]


def test_engine_hold_repeat_frames_maps_rnd_and_em_baselines() -> None:
    assert engine_hold_repeat_frames(EngineMode.RND) == (8, 8)
    assert engine_hold_repeat_frames(EngineMode.EM) == (8, 8)


def test_engine_hold_repeat_frames_rejects_invalid_engine_mode() -> None:
    with pytest.raises(ValueError, match="Unsupported engine mode"):
        engine_hold_repeat_frames("broken")  # type: ignore[arg-type]


def test_main_passes_selected_engine_to_graphics_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_run_interactive_realtime_graphics(
        state: GameState,
        tick_ms: int,
        tile_size: int,
        max_frames: int = 0,
        headless: bool = False,
        timing_mode: TimingMode = TimingMode.ASYNC,
        sync_interval: int = 1,
        font_size: int = 20,
        hud_height: int | None = None,
        engine_mode: EngineMode | None = None,
    ) -> None:
        captured["tick_ms"] = tick_ms
        captured["tile_size"] = tile_size
        captured["engine_mode"] = engine_mode
        captured["font_size"] = font_size
        captured["hud_height"] = hud_height

    monkeypatch.setattr("rnd_foundation.run_interactive_realtime_graphics", fake_run_interactive_realtime_graphics)
    monkeypatch.setattr("sys.argv", ["rnd_foundation.py", "--graphics2d", "--engine", "em"])

    main()

    assert captured == {
        "tick_ms": 250,
        "tile_size": 48,
        "engine_mode": EngineMode.EM,
        "font_size": 20,
        "hud_height": None,
    }


def test_main_passes_selected_engine_to_realtime_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_run_interactive_realtime_terminal(
        state: GameState,
        tick_ms: int,
        timing_mode: TimingMode = TimingMode.ASYNC,
        sync_interval: int = 1,
        engine_mode: EngineMode | None = None,
    ) -> None:
        captured["tick_ms"] = tick_ms
        captured["engine_mode"] = engine_mode

    monkeypatch.setattr("rnd_foundation.run_interactive_realtime_terminal", fake_run_interactive_realtime_terminal)
    monkeypatch.setattr("sys.argv", ["rnd_foundation.py", "--realtime", "--engine", "rnd"])

    main()

    assert captured == {
        "tick_ms": 250,
        "engine_mode": EngineMode.RND,
    }


def test_main_uses_rnd_engine_baseline_by_default_for_realtime_terminal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_run_interactive_realtime_terminal(
        state: GameState,
        tick_ms: int,
        timing_mode: TimingMode = TimingMode.ASYNC,
        sync_interval: int = 1,
        engine_mode: EngineMode | None = None,
    ) -> None:
        captured["tick_ms"] = tick_ms
        captured["engine_mode"] = engine_mode

    monkeypatch.setattr("rnd_foundation.run_interactive_realtime_terminal", fake_run_interactive_realtime_terminal)
    monkeypatch.setattr("sys.argv", ["rnd_foundation.py", "--realtime"])

    main()

    assert captured == {
        "tick_ms": 250,
        "engine_mode": EngineMode.RND,
    }


def test_realtime_terminal_engine_rnd_applies_async_timing_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeStdScr:
        keys = [-1, ord("d"), ord("q")]
        index = 0

        def erase(self) -> None:
            pass

        def addstr(self, y: int, x: int, text: str) -> None:
            pass

        def refresh(self) -> None:
            pass

        def nodelay(self, value: bool) -> None:
            pass

        def timeout(self, value: int) -> None:
            pass

        def keypad(self, value: bool) -> None:
            pass

        def getch(self) -> int:
            if self.index >= len(self.keys):
                return ord("q")
            key = self.keys[self.index]
            self.index += 1
            return key

    def fake_wrapper(func: object) -> None:
        func(FakeStdScr())

    monkeypatch.setattr("rnd_foundation.curses.wrapper", fake_wrapper)
    monkeypatch.setattr("rnd_foundation.curses.curs_set", lambda value: None)
    monkeypatch.setattr("rnd_foundation.sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("rnd_foundation.sys.stdout.isatty", lambda: True)

    state = make_state(
        "######",
        "#P   #",
        "######",
    )

    run_interactive_realtime_terminal(state, tick_ms=250, engine_mode=EngineMode.RND)

    assert (state.player_x, state.player_y) == (2, 1)
    assert state.pending_action is None


def test_realtime_terminal_engine_em_applies_sync_timing_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeStdScr:
        keys = [-1, ord("d"), ord("q")]
        index = 0

        def erase(self) -> None:
            pass

        def addstr(self, y: int, x: int, text: str) -> None:
            pass

        def refresh(self) -> None:
            pass

        def nodelay(self, value: bool) -> None:
            pass

        def timeout(self, value: int) -> None:
            pass

        def keypad(self, value: bool) -> None:
            pass

        def getch(self) -> int:
            if self.index >= len(self.keys):
                return ord("q")
            key = self.keys[self.index]
            self.index += 1
            return key

    def fake_wrapper(func: object) -> None:
        func(FakeStdScr())

    monkeypatch.setattr("rnd_foundation.curses.wrapper", fake_wrapper)
    monkeypatch.setattr("rnd_foundation.curses.curs_set", lambda value: None)
    monkeypatch.setattr("rnd_foundation.sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("rnd_foundation.sys.stdout.isatty", lambda: True)

    state = make_state(
        "######",
        "#P   #",
        "######",
    )

    run_interactive_realtime_terminal(state, tick_ms=250, engine_mode=EngineMode.EM)

    assert (state.player_x, state.player_y) == (1, 1)
    assert state.pending_action == "d"


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


def test_moving_object_cells_tracks_rocks_and_diamonds_only() -> None:
    state = make_state(
        "#####",
        "#PO*#",
        "# O #",
        "#####",
    )

    assert moving_object_cells(state) == {
        ROCK_ELEMENT_ID: {(2, 1), (2, 2)},
        DIAMOND_ELEMENT_ID: {(3, 1)},
    }


def test_moving_object_cells_includes_custom_falling_cells_when_eligible() -> None:
    registry = dict(DEFAULT_CUSTOM_ELEMENTS)
    registry[SLIME_ELEMENT_ID] = CustomElement(
        name=SLIME_ELEMENT_ID,
        symbol="s",
        diggable=False,
        pushable=True,
        can_fall=True,
    )

    original_registry = dict(CUSTOM_ELEMENTS)
    try:
        CUSTOM_ELEMENTS.clear()
        CUSTOM_ELEMENTS.update(registry)
        state = make_state(
            "#####",
            "#Ps #",
            "# s #",
            "#####",
        )

        assert moving_object_cells(state) == {
            SLIME_ELEMENT_ID: {(2, 1), (2, 2)},
        }
    finally:
        CUSTOM_ELEMENTS.clear()
        CUSTOM_ELEMENTS.update(original_registry)


def test_find_vertical_falling_motions_detects_falling_rock() -> None:
    state = make_state(
        "#####",
        "# O #",
        "#P  #",
        "#####",
    )
    before_cells = moving_object_cells(state)

    state.apply_gravity()

    assert find_vertical_falling_motions(before_cells, state, 7) == [
        make_motion(Tile.ROCK, (2, 1), (2, 2), 7)
    ]


def test_find_vertical_falling_motions_detects_falling_diamond() -> None:
    state = make_state(
        "#####",
        "# * #",
        "#P  #",
        "#####",
    )
    before_cells = moving_object_cells(state)

    state.apply_gravity()

    assert find_vertical_falling_motions(before_cells, state, 9) == [
        make_motion(Tile.DIAMOND, (2, 1), (2, 2), 9)
    ]


def test_find_vertical_falling_motions_ignores_horizontal_rock_push() -> None:
    state = make_state(
        "######",
        "#PO  #",
        "######",
    )
    before_cells = moving_object_cells(state)

    state.try_move_player(1, 0)

    assert find_vertical_falling_motions(before_cells, state, 5) == []


def test_find_vertical_falling_motions_ignores_stacked_rock_push_false_fall() -> None:
    state = make_state(
        "#######",
        "#PO   #",
        "# O   #",
        "#######",
    )
    before_cells = moving_object_cells(state)

    state.try_move_player(1, 0)

    assert find_vertical_falling_motions(before_cells, state, 6) == []


def test_find_moving_object_motions_detects_horizontal_rock_push() -> None:
    state = make_state(
        "#######",
        "#PO   #",
        "#######",
    )
    before_cells = moving_object_cells(state)

    state.try_move_player(1, 0)

    assert find_moving_object_motions(before_cells, state, 8) == [
        make_motion(Tile.ROCK, (2, 1), (3, 1), 8)
    ]


def test_pushed_rock_does_not_fall_over_edge_in_same_update() -> None:
    state = make_state(
        "#######",
        "#PO   #",
        "#     #",
        "#######",
    )

    step_game(state, "d")

    assert state.get(2, 1) == Tile.PLAYER
    assert state.get(3, 1) == Tile.ROCK
    assert state.get(3, 2) == Tile.EMPTY


def test_pushed_rock_falls_on_next_gravity_update_after_edge_push() -> None:
    state = make_state(
        "#######",
        "#PO   #",
        "#     #",
        "#######",
    )

    step_game(state, "d")
    step_game(state, None)

    assert state.get(3, 1) == Tile.EMPTY
    assert state.get(3, 2) == Tile.ROCK


def test_unsupported_rock_cannot_be_pushed_again_over_hole() -> None:
    state = make_state(
        "#######",
        "#PO   #",
        "#     #",
        "#######",
    )

    step_game(state, "d")
    step_game(state, "d")

    assert state.get(2, 1) == Tile.PLAYER
    assert state.get(3, 1) == Tile.EMPTY
    assert state.get(3, 2) == Tile.ROCK


def test_track_falling_motions_stores_detected_falling_motion() -> None:
    state = make_state(
        "#####",
        "# O #",
        "#P  #",
        "#####",
    )
    before_cells = moving_object_cells(state)
    motion_state = make_motion_state()

    state.apply_gravity()
    motions = track_falling_motions(motion_state, before_cells, state, 11)

    assert motions == [make_motion(Tile.ROCK, (2, 1), (2, 2), 11)]
    assert active_motions(motion_state) == motions


def test_track_moving_object_motions_stores_detected_horizontal_rock_push() -> None:
    state = make_state(
        "#######",
        "#PO   #",
        "#######",
    )
    before_cells = moving_object_cells(state)
    motion_state = make_motion_state()

    state.try_move_player(1, 0)
    motions = track_moving_object_motions(motion_state, before_cells, state, 13)

    assert motions == [make_motion(Tile.ROCK, (2, 1), (3, 1), 13)]
    assert active_motions(motion_state) == motions


def test_track_falling_motions_stores_multiple_detected_falling_motions() -> None:
    state = make_state(
        "#######",
        "# O * #",
        "#P    #",
        "#######",
    )
    before_cells = moving_object_cells(state)
    motion_state = make_motion_state()

    state.apply_gravity()
    motions = track_falling_motions(motion_state, before_cells, state, 12)

    assert set(motions) == {
        make_motion(Tile.ROCK, (2, 1), (2, 2), 12),
        make_motion(Tile.DIAMOND, (4, 1), (4, 2), 12),
    }
    assert active_motions(motion_state) == motions


def test_has_active_player_motion_detects_player_motion_only() -> None:
    motion_state = make_motion_state()
    set_motion(motion_state, make_motion(Tile.ROCK, (1, 1), (1, 2), 3))
    assert has_active_player_motion(motion_state) is False

    set_motion(motion_state, make_motion(Tile.PLAYER, (2, 1), (3, 1), 4))
    assert has_active_player_motion(motion_state) is True


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


def test_update_motion_state_removes_completed_falling_object_motion() -> None:
    motion_state = make_motion_state()
    rock_motion = start_motion(motion_state, Tile.ROCK, (2, 1), (2, 2), 10)
    diamond_motion = start_motion(motion_state, Tile.DIAMOND, (3, 1), (3, 2), 12)

    completed = update_motion_state(
        motion_state,
        current_frame=14,
        duration_frames=4,
        timing_mode=TimingMode.ASYNC,
    )

    assert completed == [rock_motion]
    assert active_motions(motion_state) == [diamond_motion]


def test_default_motion_duration_frames_matches_timing_mode() -> None:
    assert default_motion_duration_frames(TimingMode.ASYNC, sync_interval=8) == 8
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


def test_draw_board_renders_true_custom_slime_cell_from_game_state() -> None:
    state = make_state(
        "#####",
        "#Ps #",
        "#####",
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

    screen = FakeScreen()

    draw_board(FakePygame, screen, state, tile_size=8)

    assert state.get_cell(2, 1) == SLIME_ELEMENT_ID
    assert (screen, (220, 90, 90), (16, 8, 8, 8), 0) in calls
    assert (screen, (30, 30, 30), (16, 8, 8, 8), 1) in calls


def test_draw_board_renders_true_custom_brick_cell_from_game_state() -> None:
    state = make_state(
        "#####",
        "#PB #",
        "#####",
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

    screen = FakeScreen()

    draw_board(FakePygame, screen, state, tile_size=8)

    assert state.get_cell(2, 1) == BRICK_ELEMENT_ID
    assert (screen, (150, 80, 80), (16, 8, 8, 8), 0) in calls
    assert (screen, (30, 30, 30), (16, 8, 8, 8), 1) in calls


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


def test_draw_board_renders_multiple_moving_tiles_at_interpolated_positions() -> None:
    clear_tile_surface_cache()
    state = make_state(
        "#####",
        "# P #",
        "# O #",
        "#####",
    )
    motion_state = make_motion_state()
    set_motion(motion_state, make_motion(Tile.PLAYER, (1, 1), (2, 1), 10))
    set_motion(motion_state, make_motion(Tile.ROCK, (2, 1), (2, 2), 10))
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
    assert (screen, tile_color(Tile.ROCK), (48, 36, 24, 24), 0) in calls
    assert (screen, (30, 30, 30), (36, 24, 24, 24), 1) in calls
    assert (screen, (30, 30, 30), (48, 36, 24, 24), 1) in calls


def test_draw_board_renders_falling_rock_at_interpolated_rect() -> None:
    clear_tile_surface_cache()
    state = make_state(
        "#####",
        "#   #",
        "# O #",
        "#P  #",
        "#####",
    )
    motion_state = make_motion_state()
    set_motion(motion_state, make_motion(Tile.ROCK, (2, 1), (2, 2), 10))
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

    assert any(call[0] is screen and call[1] == tile_color(Tile.ROCK) and call[2] == (48, 36, 24, 24) and call[3] == 0 for call in calls)
    assert any(call[0] is screen and call[1] == (30, 30, 30) and call[2] == (48, 36, 24, 24) and call[3] == 1 for call in calls)


def test_draw_board_renders_falling_diamond_at_interpolated_rect() -> None:
    clear_tile_surface_cache()
    state = make_state(
        "#####",
        "#   #",
        "# * #",
        "#P  #",
        "#####",
    )
    motion_state = make_motion_state()
    set_motion(motion_state, make_motion(Tile.DIAMOND, (2, 1), (2, 2), 10))
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

    assert any(call[0] is screen and call[1] == tile_color(Tile.DIAMOND) and call[2] == (48, 36, 24, 24) and call[3] == 0 for call in calls)
    assert any(call[0] is screen and call[1] == (30, 30, 30) and call[2] == (48, 36, 24, 24) and call[3] == 1 for call in calls)


def test_draw_board_renders_pushed_rock_at_interpolated_rect() -> None:
    clear_tile_surface_cache()
    state = make_state(
        "#######",
        "#P O  #",
        "#######",
    )
    motion_state = make_motion_state()
    set_motion(motion_state, make_motion(Tile.ROCK, (2, 1), (3, 1), 10))
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

    assert any(call[0] is screen and call[1] == tile_color(Tile.ROCK) and call[2] == (60, 24, 24, 24) and call[3] == 0 for call in calls)
    assert any(call[0] is screen and call[1] == (30, 30, 30) and call[2] == (60, 24, 24, 24) and call[3] == 1 for call in calls)


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


def test_draw_background_renders_window_board_and_hud_underlays() -> None:
    state = make_state(
        "#####",
        "#P  #",
        "#####",
    )
    fill_calls: list[tuple[int, int, int]] = []
    draw_calls: list[tuple[object, tuple[int, int, int], object, int]] = []

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
        def fill(self, color: tuple[int, int, int]) -> None:
            fill_calls.append(color)

    screen = FakeScreen()

    draw_background(FakePygame, screen, state, tile_size=16)

    assert fill_calls == [background_color()]
    assert draw_calls == [
        (screen, board_background_color(), (0, 0, 80, 48), 0),
        (screen, (28, 34, 42), (0, 0, 80, 48), 2),
        (screen, hud_background_color(), (0, 48, 80, 70), 0),
        (screen, (24, 28, 34), (0, 48, 80, 70), 1),
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

    screen = FakeScreen()

    render_frame(FakePygame, screen, FakeFont(), state, tile_size=8)

    assert fill_calls == [background_color()]
    assert len(draw_calls) == 4 + state.width * state.height * 2
    assert draw_calls[:4] == [
        (screen, board_background_color(), (0, 0, 24, 24), 0),
        (screen, (28, 34, 42), (0, 0, 24, 24), 2),
        (screen, hud_background_color(), (0, 24, 24, 70), 0),
        (screen, (24, 28, 34), (0, 24, 24, 70), 1),
    ]
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


def test_update_graphics_frame_uses_held_key_when_no_keydown_event(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_pygame(monkeypatch)
    state = make_state(
        "######",
        "#P   #",
        "######",
    )
    pressed = [False] * 13
    pressed[FakePygame.K_d] = True
    hold_state = make_hold_state()

    should_quit = update_graphics_frame(
        state,
        frame_number=0,
        events=[],
        timing_mode=TimingMode.ASYNC,
        pressed_keys=pressed,
        hold_state=hold_state,
    )

    assert should_quit is False
    assert (state.player_x, state.player_y) == (1, 1)


def test_update_graphics_frame_uses_explicit_hold_repeat_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pygame(monkeypatch)
    state = make_state(
        "######",
        "#P   #",
        "######",
    )
    calls: list[tuple[int, int]] = []

    def fake_repeated_held_action(
        hold_state: dict[str, object],
        frame_number: int,
        held_action: str | None,
        initial_delay_frames: int,
        repeat_interval_frames: int,
    ) -> str | None:
        calls.append((initial_delay_frames, repeat_interval_frames))
        return "d"

    monkeypatch.setattr("rnd_foundation.repeated_held_action", fake_repeated_held_action)

    pressed = [False] * 13
    pressed[FakePygame.K_d] = True

    should_quit = update_graphics_frame(
        state,
        frame_number=3,
        events=[],
        timing_mode=TimingMode.ASYNC,
        motion_duration_frames=4,
        pressed_keys=pressed,
        hold_state=make_hold_state(),
        hold_repeat_delay_frames=8,
        hold_repeat_interval_frames=12,
    )

    assert should_quit is False
    assert calls == [(8, 12)]
    assert (state.player_x, state.player_y) == (2, 1)


def test_update_graphics_frame_alternates_two_held_directions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pygame(monkeypatch)
    state = make_state(
        "#####",
        "# P #",
        "#   #",
        "#####",
    )
    pressed = [False] * 13
    pressed[FakePygame.K_a] = True
    pressed[FakePygame.K_s] = True
    hold_state = make_hold_state()

    update_graphics_frame(
        state,
        frame_number=0,
        events=[],
        timing_mode=TimingMode.ASYNC,
        pressed_keys=pressed,
        hold_state=hold_state,
        hold_repeat_delay_frames=8,
        hold_repeat_interval_frames=8,
    )
    update_graphics_frame(
        state,
        frame_number=8,
        events=[],
        timing_mode=TimingMode.ASYNC,
        pressed_keys=pressed,
        hold_state=hold_state,
        hold_repeat_delay_frames=8,
        hold_repeat_interval_frames=8,
    )
    update_graphics_frame(
        state,
        frame_number=16,
        events=[],
        timing_mode=TimingMode.ASYNC,
        pressed_keys=pressed,
        hold_state=hold_state,
        hold_repeat_delay_frames=8,
        hold_repeat_interval_frames=8,
    )

    assert (state.player_x, state.player_y) == (1, 2)


def test_update_graphics_frame_preserves_alternation_when_second_held_direction_is_added(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pygame(monkeypatch)
    state = make_state(
        "######",
        "#P   #",
        "#    #",
        "######",
    )
    hold_state = make_hold_state()
    down_and_right = [False] * 13
    down_and_right[FakePygame.K_s] = True
    down_and_right[FakePygame.K_d] = True

    update_graphics_frame(
        state,
        frame_number=0,
        events=[FakeEvent(FakePygame.KEYDOWN, FakePygame.K_d)],
        timing_mode=TimingMode.ASYNC,
        hold_state=hold_state,
    )
    update_graphics_frame(
        state,
        frame_number=8,
        events=[FakeEvent(FakePygame.KEYDOWN, FakePygame.K_s)],
        timing_mode=TimingMode.ASYNC,
        pressed_keys=down_and_right,
        hold_state=hold_state,
    )
    update_graphics_frame(
        state,
        frame_number=16,
        events=[],
        timing_mode=TimingMode.ASYNC,
        pressed_keys=down_and_right,
        hold_state=hold_state,
        hold_repeat_delay_frames=8,
        hold_repeat_interval_frames=8,
    )

    assert (state.player_x, state.player_y) == (3, 2)


def test_update_graphics_frame_uses_other_held_direction_when_preferred_one_is_blocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pygame(monkeypatch)
    state = make_state(
        "#######",
        "#P    #",
        "####  #",
        "#######",
    )
    hold_state = make_hold_state()
    down_and_right = [False] * 13
    down_and_right[FakePygame.K_s] = True
    down_and_right[FakePygame.K_d] = True

    update_graphics_frame(
        state,
        frame_number=0,
        events=[],
        timing_mode=TimingMode.ASYNC,
        pressed_keys=down_and_right,
        hold_state=hold_state,
        hold_repeat_delay_frames=8,
        hold_repeat_interval_frames=8,
    )
    update_graphics_frame(
        state,
        frame_number=8,
        events=[],
        timing_mode=TimingMode.ASYNC,
        pressed_keys=down_and_right,
        hold_state=hold_state,
        hold_repeat_delay_frames=8,
        hold_repeat_interval_frames=8,
    )
    update_graphics_frame(
        state,
        frame_number=16,
        events=[],
        timing_mode=TimingMode.ASYNC,
        pressed_keys=down_and_right,
        hold_state=hold_state,
        hold_repeat_delay_frames=8,
        hold_repeat_interval_frames=8,
    )

    assert (state.player_x, state.player_y) == (3, 1)


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


def test_update_graphics_frame_tracks_falling_rock_motion_from_gravity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pygame(monkeypatch)
    state = make_state(
        "#####",
        "# O #",
        "#P  #",
        "#####",
    )
    motion_state = make_motion_state()

    should_quit = update_graphics_frame(
        state,
        frame_number=0,
        events=[],
        timing_mode=TimingMode.ASYNC,
        motion_state=motion_state,
    )

    assert should_quit is False
    assert state.get(2, 2) == Tile.ROCK
    assert get_motion(motion_state, (2, 2)) == make_motion(Tile.ROCK, (2, 1), (2, 2), 0)


def test_update_graphics_frame_tracks_multiple_falling_motions_from_gravity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pygame(monkeypatch)
    state = make_state(
        "#######",
        "# O * #",
        "#P    #",
        "#######",
    )
    motion_state = make_motion_state()

    should_quit = update_graphics_frame(
        state,
        frame_number=0,
        events=[],
        timing_mode=TimingMode.ASYNC,
        motion_state=motion_state,
    )

    assert should_quit is False
    assert get_motion(motion_state, (2, 2)) == make_motion(Tile.ROCK, (2, 1), (2, 2), 0)
    assert get_motion(motion_state, (4, 2)) == make_motion(Tile.DIAMOND, (4, 1), (4, 2), 0)


def test_update_graphics_frame_tracks_horizontal_rock_push_motion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pygame(monkeypatch)
    state = make_state(
        "#######",
        "#PO   #",
        "#######",
    )
    motion_state = make_motion_state()

    should_quit = update_graphics_frame(
        state,
        frame_number=0,
        events=[FakeEvent(FakePygame.KEYDOWN, FakePygame.K_d)],
        timing_mode=TimingMode.ASYNC,
        motion_state=motion_state,
    )

    assert should_quit is False
    assert get_motion(motion_state, (3, 1)) == make_motion(Tile.ROCK, (2, 1), (3, 1), 0)


def test_update_graphics_frame_keeps_pushed_rock_on_edge_for_one_update(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pygame(monkeypatch)
    state = make_state(
        "#######",
        "#PO   #",
        "#     #",
        "#######",
    )
    motion_state = make_motion_state()

    should_quit = update_graphics_frame(
        state,
        frame_number=0,
        events=[FakeEvent(FakePygame.KEYDOWN, FakePygame.K_d)],
        timing_mode=TimingMode.ASYNC,
        motion_state=motion_state,
    )

    assert should_quit is False
    assert state.get(3, 1) == Tile.ROCK
    assert state.get(3, 2) == Tile.EMPTY
    assert get_motion(motion_state, (3, 1)) == make_motion(Tile.ROCK, (2, 1), (3, 1), 0)


def test_update_graphics_frame_starts_fall_on_frame_after_edge_push(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pygame(monkeypatch)
    state = make_state(
        "#######",
        "#PO   #",
        "#     #",
        "#######",
    )
    motion_state = make_motion_state()

    update_graphics_frame(
        state,
        frame_number=0,
        events=[FakeEvent(FakePygame.KEYDOWN, FakePygame.K_d)],
        timing_mode=TimingMode.ASYNC,
        motion_state=motion_state,
    )
    update_graphics_frame(
        state,
        frame_number=8,
        events=[],
        timing_mode=TimingMode.ASYNC,
        motion_state=motion_state,
    )

    assert state.get(3, 1) == Tile.EMPTY
    assert state.get(3, 2) == Tile.ROCK
    assert get_motion(motion_state, (3, 2)) == make_motion(Tile.ROCK, (3, 1), (3, 2), 8)


def test_update_graphics_frame_keeps_falling_rock_in_place_while_fall_motion_is_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pygame(monkeypatch)
    state = make_state(
        "#####",
        "# O #",
        "#P  #",
        "#####",
    )
    motion_state = make_motion_state()

    update_graphics_frame(
        state,
        frame_number=0,
        events=[],
        timing_mode=TimingMode.ASYNC,
        motion_state=motion_state,
    )
    update_graphics_frame(
        state,
        frame_number=1,
        events=[],
        timing_mode=TimingMode.ASYNC,
        motion_state=motion_state,
    )

    assert state.get(2, 2) == Tile.ROCK
    assert state.get(2, 1) == Tile.EMPTY
    assert state.get(2, 3) == Tile.WALL
    assert get_motion(motion_state, (2, 2)) == make_motion(Tile.ROCK, (2, 1), (2, 2), 0)


def test_update_graphics_frame_keeps_snap_pushed_rock_on_edge_for_horizontal_glide(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pygame(monkeypatch)
    state = make_state(
        "#######",
        "#PO   #",
        "#     #",
        "#######",
    )
    motion_state = make_motion_state()

    update_graphics_frame(
        state,
        frame_number=0,
        events=[FakeEvent(FakePygame.KEYDOWN, FakePygame.K_d, mod=FakePygame.KMOD_CTRL)],
        timing_mode=TimingMode.ASYNC,
        motion_state=motion_state,
    )
    update_graphics_frame(
        state,
        frame_number=1,
        events=[],
        timing_mode=TimingMode.ASYNC,
        motion_state=motion_state,
    )

    assert state.get(3, 1) == Tile.ROCK
    assert state.get(3, 2) == Tile.EMPTY
    assert get_motion(motion_state, (3, 1)) == make_motion(Tile.ROCK, (2, 1), (3, 1), 0)


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


def test_update_graphics_frame_blocks_new_move_while_player_motion_is_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pygame(monkeypatch)
    state = make_state(
        "#######",
        "#P    #",
        "#######",
    )
    motion_state = make_motion_state()

    update_graphics_frame(
        state,
        frame_number=0,
        events=[FakeEvent(FakePygame.KEYDOWN, FakePygame.K_d)],
        timing_mode=TimingMode.ASYNC,
        motion_state=motion_state,
    )

    update_graphics_frame(
        state,
        frame_number=1,
        events=[FakeEvent(FakePygame.KEYDOWN, FakePygame.K_d)],
        timing_mode=TimingMode.ASYNC,
        motion_state=motion_state,
    )

    assert (state.player_x, state.player_y) == (2, 1)
    assert state.pending_action == "d"
    assert active_motions(motion_state) == [make_motion(Tile.PLAYER, (1, 1), (2, 1), 0)]


def test_update_graphics_frame_consumes_buffered_move_after_player_motion_finishes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pygame(monkeypatch)
    state = make_state(
        "#######",
        "#P    #",
        "#######",
    )
    motion_state = make_motion_state()

    update_graphics_frame(
        state,
        frame_number=0,
        events=[FakeEvent(FakePygame.KEYDOWN, FakePygame.K_d)],
        timing_mode=TimingMode.ASYNC,
        motion_state=motion_state,
    )
    update_graphics_frame(
        state,
        frame_number=1,
        events=[FakeEvent(FakePygame.KEYDOWN, FakePygame.K_d)],
        timing_mode=TimingMode.ASYNC,
        motion_state=motion_state,
    )
    update_graphics_frame(
        state,
        frame_number=8,
        events=[],
        timing_mode=TimingMode.ASYNC,
        motion_state=motion_state,
    )

    assert (state.player_x, state.player_y) == (3, 1)
    assert state.pending_action is None
    assert active_motions(motion_state) == [make_motion(Tile.PLAYER, (2, 1), (3, 1), 8)]


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


def test_player_cannot_move_into_true_custom_brick_cell() -> None:
    state = make_state(
        "#####",
        "#PB #",
        "#####",
    )

    state.try_move_player(1, 0)

    assert (state.player_x, state.player_y) == (1, 1)
    assert state.get_cell(2, 1) == BRICK_ELEMENT_ID
    assert state.render_lines() == [
        "#####",
        "#PB #",
        "#####",
    ]


def test_player_can_snap_sand_without_moving() -> None:
    state = make_state(
        "#####",
        "#P. #",
        "#####",
    )

    state.try_snap(1, 0)

    assert (state.player_x, state.player_y) == (1, 1)
    assert state.get(2, 1) == Tile.EMPTY


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


def test_player_can_snap_diamond_without_moving_and_win() -> None:
    state = make_state(
        "#####",
        "#P* #",
        "#####",
    )

    state.try_snap(1, 0)

    assert (state.player_x, state.player_y) == (1, 1)
    assert state.get(2, 1) == Tile.EMPTY
    assert state.diamonds_collected == 1
    assert state.won is True


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


def test_player_can_snap_push_rock_horizontally_without_moving() -> None:
    state = make_state(
        "######",
        "#PO  #",
        "######",
    )

    state.try_snap(1, 0)

    assert (state.player_x, state.player_y) == (1, 1)
    assert state.get(2, 1) == Tile.EMPTY
    assert state.get(3, 1) == Tile.ROCK


def test_player_cannot_snap_push_rock_vertically() -> None:
    state = make_state(
        "#####",
        "# O #",
        "# P #",
        "#####",
    )

    state.try_snap(0, -1)

    assert (state.player_x, state.player_y) == (2, 2)
    assert state.get(2, 1) == Tile.ROCK


def test_player_cannot_snap_push_rock_into_blocked_space() -> None:
    state = make_state(
        "#####",
        "#PO##",
        "#####",
    )

    state.try_snap(1, 0)

    assert (state.player_x, state.player_y) == (1, 1)
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


def test_step_game_supports_snap_actions() -> None:
    state = make_state(
        "#####",
        "#P. #",
        "#####",
    )

    step_game(state, "D")

    assert (state.player_x, state.player_y) == (1, 1)
    assert state.get(2, 1) == Tile.EMPTY


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
    def __init__(self, event_type: int, key: int | None = None, mod: int = 0) -> None:
        self.type = event_type
        self.key = key
        self.mod = mod


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
    KMOD_CTRL = 64

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

    class key:
        @staticmethod
        def get_pressed() -> list[bool]:
            return [False] * 13

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


def test_action_from_pygame_frame_events_supports_ctrl_snap_actions(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_pygame(monkeypatch)

    events = [
        FakeEvent(FakePygame.KEYDOWN, FakePygame.K_d, FakePygame.KMOD_CTRL),
    ]

    assert action_from_pygame_frame_events(events) == "D"


def test_action_from_pygame_pressed_keys_uses_held_direction(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_pygame(monkeypatch)
    pressed = [False] * 13
    pressed[FakePygame.K_d] = True

    assert action_from_pygame_pressed_keys(pressed) == "d"


def test_held_actions_from_pygame_pressed_keys_returns_orthogonal_pair(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_pygame(monkeypatch)
    pressed = [False] * 13
    pressed[FakePygame.K_a] = True
    pressed[FakePygame.K_s] = True

    assert held_actions_from_pygame_pressed_keys(pressed) == ("s", "a")


def test_action_from_pygame_pressed_keys_returns_none_without_held_direction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pygame(monkeypatch)

    assert action_from_pygame_pressed_keys([False] * 13) is None


def test_action_from_pygame_key_supports_ctrl_snap_actions(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_pygame(monkeypatch)

    assert action_from_pygame_key(FakePygame.K_d, ctrl_held=True) == "D"
    assert action_from_pygame_key(FakePygame.K_UP, ctrl_held=True) == "W"


def test_repeated_held_action_waits_for_repeat_delay() -> None:
    hold_state = make_hold_state()

    assert repeated_held_action(hold_state, 0, "d", 4, 4) is None
    assert repeated_held_action(hold_state, 1, "d", 4, 4) is None
    assert repeated_held_action(hold_state, 3, "d", 4, 4) is None
    assert repeated_held_action(hold_state, 4, "d", 4, 4) == "d"


def test_repeated_held_action_resets_when_key_is_released() -> None:
    hold_state = make_hold_state()

    assert repeated_held_action(hold_state, 0, "d", 4, 4) is None
    assert repeated_held_action(hold_state, 1, None, 4, 4) is None
    assert repeated_held_action(hold_state, 2, "d", 4, 4) is None
    assert hold_state == {"action": ("d",), "press_frame": 2, "last_output_action": None}


def test_repeated_held_action_alternates_two_orthogonal_directions() -> None:
    hold_state = make_hold_state()

    assert repeated_held_action(hold_state, 0, ("s", "a"), 4, 4) is None
    assert repeated_held_action(hold_state, 4, ("s", "a"), 4, 4) == "s"
    assert repeated_held_action(hold_state, 8, ("s", "a"), 4, 4) == "a"
    assert repeated_held_action(hold_state, 12, ("s", "a"), 4, 4) == "s"


def test_action_from_turn_input_supports_uppercase_snap_actions() -> None:
    assert action_from_turn_input("D") == "D"


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


def test_graphics_mode_engine_em_applies_sync_timing_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
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
        engine_mode=EngineMode.EM,
    )

    assert (state.player_x, state.player_y) == (1, 1)
    assert state.pending_action == "d"


def test_graphics_mode_engine_rnd_applies_async_timing_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
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
        engine_mode=EngineMode.RND,
    )

    assert (state.player_x, state.player_y) == (2, 1)
    assert state.pending_action is None


def test_graphics_mode_repeats_movement_when_direction_is_held(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_pygame(monkeypatch)

    class SequencedEventQueue:
        frames = [
            [FakeEvent(FakePygame.KEYDOWN, FakePygame.K_d)],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
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

    class HeldKeyState:
        frames = 0

        @classmethod
        def get_pressed(cls) -> list[bool]:
            cls.frames += 1
            pressed = [False] * 13
            if cls.frames <= 9:
                pressed[FakePygame.K_d] = True
            return pressed

    monkeypatch.setattr(FakePygame, "event", SequencedEventQueue)
    monkeypatch.setattr(FakePygame, "key", HeldKeyState)

    state = make_state(
        "########",
        "#P     #",
        "########",
    )

    run_interactive_realtime_graphics(state, tick_ms=250, tile_size=32, max_frames=9)

    assert (state.player_x, state.player_y) == (3, 1)


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


def test_render_frame_supports_sprite_tiles_with_background_and_hud(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_tile_surface_cache()
    state = make_state(
        "###",
        "#P#",
        "###",
    )
    fill_calls: list[tuple[int, int, int]] = []
    draw_calls: list[tuple[object, tuple[int, int, int], object, int]] = []
    blit_calls: list[tuple[object, object]] = []
    render_calls: list[tuple[str, bool, tuple[int, int, int]]] = []

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

    class FakeFont:
        def render(self, text: str, antialias: bool, color: tuple[int, int, int]) -> object:
            render_calls.append((text, antialias, color))
            return text

    class FakeScreen:
        def fill(self, color: tuple[int, int, int]) -> None:
            fill_calls.append(color)

        def blit(self, surface: object, position: tuple[int, int]) -> None:
            blit_calls.append((surface, position))

    screen = FakeScreen()

    render_frame(FakePygame, screen, FakeFont(), state, tile_size=8)

    assert fill_calls == [background_color()]
    assert blit_calls[0] == (("player-surface", 8), (8, 8, 8, 8))
    assert blit_calls[1:] == [
        ("Diamonds: 0/0", (10, 34)),
        ("Move: WASD/Arrows   Quit: Q", (10, 62)),
    ]
    assert render_calls == [
        ("Diamonds: 0/0", True, (245, 245, 245)),
        ("Move: WASD/Arrows   Quit: Q", True, (190, 190, 190)),
    ]
    assert (screen, tile_color(Tile.PLAYER), (8, 8, 8, 8), 0) not in draw_calls


def test_render_frame_supports_moving_sprite_tiles(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_tile_surface_cache()
    state = make_state(
        "###",
        "# P",
        "###",
    )
    motion_state = make_motion_state()
    set_motion(motion_state, make_motion(Tile.PLAYER, (1, 1), (2, 1), 10))
    blit_calls: list[tuple[object, object]] = []

    def fake_build(tile: Tile, tile_size: int) -> object | None:
        if tile == Tile.PLAYER:
            return ("player-surface", tile_size)
        return None

    monkeypatch.setattr("rnd_foundation.build_tile_surface", fake_build)

    class FakeDraw:
        @staticmethod
        def rect(screen: object, color: tuple[int, int, int], rect: object, width: int = 0) -> None:
            pass

    class FakePygame:
        draw = FakeDraw()

        @staticmethod
        def Rect(x: int, y: int, width: int, height: int) -> tuple[int, int, int, int]:
            return (x, y, width, height)

    class FakeFont:
        def render(self, text: str, antialias: bool, color: tuple[int, int, int]) -> object:
            return text

    class FakeScreen:
        def fill(self, color: tuple[int, int, int]) -> None:
            pass

        def blit(self, surface: object, position: tuple[int, int]) -> None:
            blit_calls.append((surface, position))

    render_frame(
        FakePygame,
        FakeScreen(),
        FakeFont(),
        state,
        tile_size=24,
        motion_state=motion_state,
        current_frame=12,
        motion_duration_frames=4,
    )

    assert blit_calls[0] == (("player-surface", 24), (36, 24, 24, 24))


def test_render_frame_scales_background_and_hud_with_visual_config() -> None:
    state = make_state(
        "#####",
        "#P  #",
        "#####",
    )
    fill_calls: list[tuple[int, int, int]] = []
    draw_calls: list[tuple[object, tuple[int, int, int], object, int]] = []
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
            return text

    class FakeScreen:
        def fill(self, color: tuple[int, int, int]) -> None:
            fill_calls.append(color)

        def blit(self, surface: object, position: tuple[int, int]) -> None:
            blit_calls.append((surface, position))

    screen = FakeScreen()

    render_frame(
        FakePygame,
        screen,
        FakeFont(),
        state,
        tile_size=16,
        hud_top_padding=hud_top_padding_px(30),
        hud_line_gap=hud_line_gap_px(30),
        font_size=30,
        hud_height=100,
    )

    assert fill_calls == [background_color()]
    assert draw_calls[:4] == [
        (screen, board_background_color(), (0, 0, 80, 48), 0),
        (screen, (28, 34, 42), (0, 0, 80, 48), 2),
        (screen, hud_background_color(), (0, 48, 80, 100), 0),
        (screen, (24, 28, 34), (0, 48, 80, 100), 1),
    ]
    assert blit_calls[-2:] == [
        ("Diamonds: 0/0", (10, 63)),
        ("Move: WASD/Arrows   Quit: Q", (10, 101)),
    ]
