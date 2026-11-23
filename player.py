from collections import deque

from board import Action, Block, Direction, Rotation, Shape


class Player:
    def choose_action(self, board):
        raise NotImplementedError


class SearchPlayer(Player):
    def _landing_options(self, board, block, start_y=None, prefix=()):
        if start_y is None:
            start_y = block.center[1]

        queue = deque([(block.clone(), list(prefix))])
        visited = set()
        landings = {}
        actions = (
            Direction.Left,
            Direction.Right,
            Rotation.Clockwise,
            Rotation.Anticlockwise,
            None,
        )

        def add_landing(landed, path):
            key = tuple(sorted(landed.cells))
            drop_score = landed.center[1] - start_y
            previous = landings.get(key)
            if (previous is None or drop_score > previous[2]
                    or (drop_score == previous[2]
                        and len(path) < len(previous[1]))):
                landings[key] = (landed, path, drop_score)

        while queue:
            current, path = queue.popleft()
            state = (tuple(sorted(current.cells)), current.center)
            if state in visited:
                continue
            visited.add(state)

            dropped = current.clone()
            while not dropped.supported(board):
                dropped.cells = {(x, y + 1) for x, y in dropped.cells}
                dropped.center = (dropped.center[0], dropped.center[1] + 1)
            add_landing(dropped, path + [Direction.Drop])

            for action in actions:
                moved = current.clone()
                if isinstance(action, Direction):
                    moved.move(action, board)
                elif isinstance(action, Rotation):
                    score = board.score
                    moved.rotate(action, board)
                    board.score = score

                if moved.supported(board):
                    add_landing(moved, path + [action])
                    continue
                moved.cells = {(x, y + 1) for x, y in moved.cells}
                moved.center = (moved.center[0], moved.center[1] + 1)
                queue.append((moved, path + [action]))

        return list(landings.values())

    def _land(self, board, option, next_shape=None):
        landed, _, drop_score = option
        result = board.clone()
        result.score = board.score + drop_score
        result.falling = landed.clone()
        result.next = Block(next_shape) if next_shape is not None else None
        result.land_block()
        return result

    def _potential(self, board):
        heights = []
        holes = 0
        for x in range(board.width):
            occupied_y = [y for cell_x, y in board.cells if cell_x == x]
            if not occupied_y:
                heights.append(0)
                continue
            top = min(occupied_y)
            height = board.height - top
            heights.append(height)
            holes += sum(
                (x, y) not in board.cells
                for y in range(top + 1, board.height)
            )

        aggregate_height = sum(heights)
        bumpiness = sum(
            abs(heights[x] - heights[x + 1])
            for x in range(board.width - 1)
        )
        max_height = max(heights, default=0)
        danger = max(0, max_height - 14)
        return (
            -2.0 * aggregate_height
            - 14.0 * holes
            - 1.5 * bumpiness
            - 4.0 * max_height
            - 12.0 * danger * danger
        )

    def _best_next_value(self, board):
        if board.falling is None:
            return self._potential(board)
        if not board.alive:
            return -100000.0

        best = None
        for option in self._landing_options(board, board.falling):
            result = self._land(board, option)
            reward = result.score - board.score + self._potential(result)
            if best is None or reward > best:
                best = reward
        return best if best is not None else -100000.0

    def _rank_options(self, board, options, next_shape, limit):
        ranked = []
        for option in options:
            result = self._land(board, option, next_shape)
            immediate_reward = result.score - board.score
            value = immediate_reward + self._potential(result)
            if next_shape is not None and not result.alive:
                value -= 100000.0
            ranked.append((value, option, result, immediate_reward))

        ranked.sort(key=lambda item: item[0], reverse=True)
        return ranked[:limit]

    def _lookahead_value(self, item, next_shape):
        value, _, result, immediate_reward = item
        if next_shape is None:
            return value
        future_value = self._best_next_value(result)
        if future_value <= -100000.0:
            return value - 100000.0
        return immediate_reward + 0.75 * future_value

    def choose_action(self, board):
        if board.falling is None:
            return None

        best_value = -float("inf")
        best_path = [Direction.Drop]

        next_shape = board.next.shape if board.next is not None else None
        normal_options = self._landing_options(board, board.falling)
        normal_ranked = self._rank_options(
            board, normal_options, next_shape, 2
        )
        for item in normal_ranked:
            value = self._lookahead_value(item, next_shape)
            if value > best_value:
                best_value = value
                best_path = item[1][1]

        max_height = max(
            (
                board.height - min(y for cell_x, y in board.cells
                                   if cell_x == x)
                for x in range(board.width)
                if any(cell_x == x for cell_x, _ in board.cells)
            ),
            default=0,
        )
        if board.bombs_remaining > 0 and board.next is not None \
                and board.next.shape is not Shape.B and max_height >= 8:
            bomb_board = board.clone()
            bomb_board.bomb()
            if bomb_board.falling is not None \
                    and bomb_board.falling.shape == board.falling.shape:
                bomb_options = self._landing_options(
                    bomb_board,
                    bomb_board.falling,
                    start_y=board.falling.center[1],
                    prefix=[Action.Bomb],
                )
                for item in self._rank_options(
                    board, bomb_options, Shape.B, 1
                ):
                    value = self._lookahead_value(item, Shape.B) - 45
                    if value > best_value:
                        best_value = value
                        best_path = item[1][1]

        if board.discards_remaining > 0 and board.next is not None \
                and normal_ranked and not normal_ranked[0][2].alive:
            discard_board = board.clone()
            discard_board.discard()
            if discard_board.falling is not None:
                for option in self._landing_options(
                    discard_board, discard_board.falling
                ):
                    result = self._land(discard_board, option)
                    value = (
                        result.score - discard_board.score
                        + self._potential(result) - 40
                    )
                    if value > best_value:
                        best_value = value
                        best_path = [Action.Discard] + option[1]

        return best_path


SelectedPlayer = SearchPlayer
