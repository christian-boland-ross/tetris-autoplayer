# tetris-autoplayer

Python coursework for UCL's *ENGF0034: Design and Professional Skills I (Computer Science)* course.<br>
Coursework specification can be found at [specification.pdf](docs/provided/specification.pdf), with notes thereof [here](docs/specification-notes.md).

# Tetris Autoplayer

An implementation of a Tetris autoplayer for a slightly modified version of tetris. The game uses
the standard 10-by-24 board with a 400-block limit and provides ten discards
and five bombs.

- [Overview](#overview)
- [Requirements](#requirements)
- [Running the game](#running-the-game)
- [Manual controls](#manual-controls)
- [Player design](#player-design)
- [Scoring](#scoring)
- [Project layout](#project-layout)



## Overview

The selected player is `SearchPlayer`, aliased as `SelectedPlayer` in
`player.py`. It evaluates potential placements by cloning the board, simulates
normal, discarded, and bomb-assisted moves, and uses a heuristic to rank the
resulting states.

The player considers:

- Aggregate column height and maximum height
- Holes and covered cells
- Surface bumpiness and wells
- Completed-row potential and line-clear rewards
- Stack pressure and danger near the top of the board
- The known next tetromino
- Bomb and discard resource use

## Requirements

- Python 3
- Pygame is optional and only required for `visual-pygame.py`

No third-party Python packages are required for the autoplayer or the
command-line and curses interfaces.

## Running the game

Run the automatic player with either interface:

```bash
python3 visual.py
python3 cmdline.py
python3 visual-pygame.py
```

The Pygame interface is the fastest visual option. If Pygame is not already
installed, install it with:

```bash
python3 -m pip install pygame
```

Windows users may need the curses package for the command-line interface:

```bash
python3 -m pip install windows-curses
```

To play manually, add `-m`:

```bash
python3 visual.py -m
python3 cmdline.py -m
python3 visual-pygame.py -m
```

## Manual controls

| Key | Action |
| --- | --- |
| Left / Right | Move the falling block |
| Down | Move down one row |
| Space | Drop the block |
| Up or X | Rotate clockwise |
| Z | Rotate anticlockwise |
| B | Replace the next piece with a bomb |
| D | Discard the current piece |
| Escape or Q | Quit |

## Player design

The player entry point is `SearchPlayer.choose_action()` in
[`player.py`](player.py). The game calls this method with a copy of the board
and expects an action, a list of actions, or `None`.

### Placement search

The player:

1. Enumerates rotations and landing positions for the falling piece.
2. Clones the board for each candidate and applies the landing drop.
3. Evaluates the resulting board using a weighted heuristic.
4. Repeats the search for the known next piece.
5. Compares normal placements against bomb and discard options.

Board cloning ensures that exploration does not mutate the live game state.

### Bombs

A bomb replaces the next piece and is available five times. Bomb placements are
limited and reserve-aware: the player considers candidate landings, adjusts
for stack pressure and remaining bombs, and avoids spending the last bomb when
it may be more useful in a more dangerous position.

### Discards

The player may discard the current piece at a cost of one of ten discards.
Discard candidates are evaluated against unknown future pieces so that
discarding is not based only on the immediately visible piece.

## Scoring

The player has a maximum of 400 pieces. Clearing multiple rows is much more
valuable than clearing a single row:

| Rows cleared | Score |
| --- | --- |
| 1 | 25 |
| 2 | 100 |
| 3 | 400 |
| 4 | 1600 |

Bomb-destroyed cells do not add to the score.

## Project layout

- `player.py` - autoplayer implementation
- `board.py` - board, pieces, movement, cloning, and bomb logic
- `adversary.py` - block sequence generation
- `constants.py` - board dimensions and game limits
- `arguments.py` - command-line arguments
- `cmdline.py` - curses command-line interface
- `visual.py` - curses visual interface
- `visual-pygame.py` - Pygame visual interface
- `server.py` - network submission protocol
- `docs/` - specification, notes, and assignment documentation