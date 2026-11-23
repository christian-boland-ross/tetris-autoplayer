# Notes

Track the score of your submission in real time through the [web interface.](https://engf0002.cs.ucl.ac.uk/submissions/tetris)<br>
The deadline for submissions is Wednesday 25th November at 23:59 UK time.

- [Running instructions](#running-instructions)
- [Tetris variant](#tetris-variant)
- [Writing the player](#writing-the-player)
- [Tips](#tips)


## Running instructions

Run
```bash
python3 cmdline.py # command line interface
python3 visual.py # visual interface
python3 visual-pygame.py # Pygame version - fastest
```
Flags
```bash
-m # run code in manual mode
```

## Tetris variant

- Max 400 tetronimos
- Max 10 discards
- 5 bombs
- You can substitute a bomb for the next tetronimo
- Bombs destroy all surrounding blocks (3x3 grid)
- Blocks above and neighbouring squares fall to the ground

### Scoring
- Max 400 tetronimos, so just surviving doesn't give the highest score
- Scoring weights clearing multiple rows at once

| Rows | Points|
| -----| ----- |
| 1    | 2     |
| 2    | 100   |
| 3    | 400   |
| 4    | 160   |

- Blocks destroyed by bombs don't score anything

## Writing the player

- All code should be in player.py
- Player is a class with a function called choose_action(self, board)
- This function should decide what action to take based on the state of the board

### Board object

#### Board enums

```python
class Action(Enum):
    Bomb = 'BOMB'
    Discard = 'DISCARD'

class Direction(Enum): # Possible directions to move a block, plus dropping.

    Left = 'LEFT'
    Right = 'RIGHT'
    Down = 'DOWN'
    Drop = 'DROP'


class Rotation(Enum): # Possible rotations available to the player.

    Clockwise = 'CLOCKWISE'
    Anticlockwise = 'ANTICLOCKWISE'


class Shape(Enum): # Possible shapes of tetrominoes.

    I = 'I'  # noqa
    J = 'J'
    L = 'L'
    O = 'O'  # noqa
    S = 'S'
    T = 'T'
    Z = 'Z'
    B = 'B'
```

#### Board variables
```python
board.falling # The currently falling tetronimo
    board.falling.shape # Falling tetronimo shape
    board.falling.cells # Falling tetronimo cell coordinates

board.next # The next tetronimo to fall
    board.next.shape # Next tetronimo shape
    board.next.cells # Means nothing

board.cells Falling tetronimo cell coordinates # A set of tuples (x, y) that signify locations. Origin is top-left
```

Example to find occupied cells from top to bottom, left to right:
```python
for y in range(board.height):
    for x in range(board.width):
        if (x, y) in board.cells:
            # Do something here.
```

#### Board functions

- Calling any of the following (including skip) will also apply the implicit move down that occurs once every turn.
- If the block lands these functions will return True; otherwise, False.

```python
board.move() # Accepts an instance of the enum Direction, e.g.:
board.move(Direction.Left);

board.rotate() # Accepts an instance of the enum Rotation, e.g.:
board.rotate(Rotation.Anticlockwise)

skip() # Skips a move (essentialy moving down by one)

discard() # Discards the current tetronimo. If you have no discards remaining, it behaves the same as skip

bomb() # Switches tetronimo for a bomb. If you have no bombs remaining, it behaves the same as skip
```

## Tips

### Experimenting

To experiment with multiple options, it is useful to get a copy of the board and try the effects of your actions there; actions on the copy will not affect the original, so you can use that state later:
```python
sandbox = board.clone()
sandbox.rotate(Rotation.Anticlockwise)
sandbox.move(Direction.Drop)
sandbox.move(Action.Bomb)
# Check if the new board in sandbox is to your liking
```

Once sure about a move, you can tell the interface by returning that action, e.g.:
```python
return Rotation.Clockwise
return Action.Discard

# To return multiple moves
return [Rotation.Anticlockwise, Direction.Left, Direction.Drop, Action.Bomb]
# Or you can use the yield statement to return each individual move:
yield Rotation.Anticlockwise yield Direction.Left
yield None
yield Direction.Drop
yield Action.Discard
```
If your player returns multiple moves, they will only be executed until the currently falling block lands, then the rest of the list will be disregarded. <br>
If the moves supplied by the player run out *before* the block lands, the `choose()` function will be called again.

### Caveats

#### Changing files and state
You should not have to change anything but player.py, but modifying other files or adding files is not prohibited. In the best case, any changes to the game logic only have an effect locally — the test environment maintains its own copy of the game logic; in the worst case, your changes may crash the code as it is evaluated. Similarly, the test environment maintains its own copy of the board based on the actions that your player takes; the player will not be able to access this state. This means that, for instance, changing board.score to a value of your liking will not change the score maintained by the server.

#### Using python libraries

The grading server has a vanilla verion of python installed, with no additional libraries. If you include any external libraries in your code, you will find that your solution will crash when run on the grading server. You must write your solution code yourself without using any additional libraries.<br>
If you’re considering an advanced solution and want to use external code to train weights in your program, this is permitted, but that code must not be included in your player.py file.

### Suggested strategy overview

### Target-State Search
Because future blocks beyond board.next are unknown, search over candidate landing placements:
1. Test all rotations (0–3) and columns (0–9) — at most ≈40 placements.
2. Simulate each on board.clone() ending with Direction.Drop.
3. Score the resulting board and pick the maximum.
Lookahead: Extending to board.next tests ≈1,600 states (respecting O(bd) runtime bounds).

### Linear Heuristic Evaluation

Combine structural features with tuned weights,
```
E(s) = w1 ∆S− w2 H− w3 K− w4 B,
```
where:
- `∆S`: Score gain (rewards 3–4 row clears).
- `H`: Aggregate or maximum column height.
- `K`: Buried empty holes under blocks.
- `B`: Surface bumpiness `∑x |hx − hx+1 |`.