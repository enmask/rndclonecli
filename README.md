# rndclonecli

`rndclonecli` is a small Python prototype of a Rocks'n'Diamonds-like CLI game. It includes a default turn-based terminal mode, plus optional demo, realtime terminal, and pygame-based graphics modes.

## Run the game

Start the default turn-based terminal game with:

```bash
python3 rnd_foundation.py
```

Optional modes:

```bash
python3 rnd_foundation.py --demo
python3 rnd_foundation.py --realtime
python3 rnd_foundation.py --graphics2d
```

## Run the tests

Run the test suite with `python3 -m pytest -q`:

```bash
python3 -m pytest -q
```
