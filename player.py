from board import Action, Block, Direction, Rotation, Shape


class Player:
    def choose_action(self, board):
        raise NotImplementedError


class SearchPlayer(Player):
    MAX_REACHABLE_STATES = 80
    TUCK_THRESHOLD = 100

    PIECE_SHAPES = (
        Shape.I,
        Shape.J,
        Shape.L,
        Shape.O,
        Shape.S,
        Shape.T,
        Shape.Z,
    )

    CLEAR_ADJUSTMENTS = {
        25: -50,
        100: -25,
        400: 250,
        1600: 700,
    }
    AGGREGATE_HEIGHT_WEIGHT = 2.0
    HOLE_WEIGHT = 14.0
    COVERED_HOLE_WEIGHT = 0.05
    BUMPINESS_WEIGHT = 1.5
    MAX_HEIGHT_WEIGHT = 4.0
    DANGER_WEIGHT = 40.0
    ROW_COMPLETION_WEIGHT = 12.0
    WELL_WEIGHT = 2.5
    I_WELL_WEIGHT = 1.0

    def __init__(self):
        self.pieces_played = 0

    def _endgame_progress(self):
        return max(0.0, min(1.0, (self.pieces_played - 340) / 60.0))

    def _stack_pressure(self, max_height):
        return max(0.0, min(1.0, (max_height - 16) / 6.0))

    def _target_landing_options(self, board, block, start_y=None, prefix=()):
        if start_y is None:
            start_y = block.center[1]

        landings = {}
        for rotations in range(4):
            rotated_board = board.clone()
            rotated = block.clone()
            rotation_path = list(prefix)
            landed_early = False

            for _ in range(rotations):
                rotated.rotate(Rotation.Clockwise, rotated_board)
                rotation_path.append(Rotation.Clockwise)
                if rotated.move(Direction.Down, rotated_board):
                    key = tuple(sorted(rotated.cells))
                    landings[key] = (
                        rotated.clone(),
                        list(rotation_path),
                        rotated.center[1] - start_y,
                    )
                    landed_early = True
                    break

            if landed_early:
                continue

            width = rotated.right - rotated.left + 1
            for target_left in range(board.width - width + 1):
                simulation = rotated_board.clone()
                current = rotated.clone()
                path = list(rotation_path)
                landed_early = False

                while current.left != target_left:
                    direction = (
                        Direction.Left
                        if current.left > target_left
                        else Direction.Right
                    )
                    current.move(direction, simulation)
                    path.append(direction)
                    if current.move(Direction.Down, simulation):
                        key = tuple(sorted(current.cells))
                        option = (
                            current.clone(),
                            path,
                            current.center[1] - start_y,
                        )
                        previous = landings.get(key)
                        if previous is None or len(option[1]) < len(previous[1]):
                            landings[key] = option
                        landed_early = True
                        break

                if landed_early:
                    continue

                current.move(Direction.Drop, simulation)
                key = tuple(sorted(current.cells))
                option = (
                    current.clone(),
                    path + [Direction.Drop],
                    current.center[1] - start_y,
                )
                previous = landings.get(key)
                if previous is None or len(option[1]) < len(previous[1]):
                    landings[key] = option

        return list(landings.values())

    def _advance_state(self, block, action, board):
        moved = block.clone()
        score_before = board.score

        if isinstance(action, Direction):
            moved.move(action, board)
        elif isinstance(action, Rotation):
            moved.rotate(action, board)

        landed = moved.move(Direction.Down, board)
        drop_score = board.score - score_before
        board.score = score_before
        return moved, drop_score, landed

    def _reachable_landing_options(self, board, block, start_y, prefix):
        landings = {}
        initial = block.clone()
        queue = [(initial, list(prefix), 0)]
        visited = {
            (tuple(sorted(initial.cells)), initial.center)
        }
        actions = (
            None,
            Direction.Left,
            Direction.Right,
            Direction.Down,
            Rotation.Clockwise,
            Rotation.Anticlockwise,
        )
        expanded = 0

        def add_landing(landed, path, drop_score):
            key = tuple(sorted(landed.cells))
            previous = landings.get(key)
            if previous is None or drop_score > previous[2] \
                    or (drop_score == previous[2]
                        and len(path) < len(previous[1])):
                landings[key] = (landed.clone(), path, drop_score)

        while queue and expanded < self.MAX_REACHABLE_STATES:
            current, path, drop_score = queue.pop()
            expanded += 1

            dropped = current.clone()
            score_before = board.score
            dropped.move(Direction.Drop, board)
            hard_drop_score = board.score - score_before
            board.score = score_before
            add_landing(
                dropped,
                path + [Direction.Drop],
                drop_score + hard_drop_score,
            )

            for action in reversed(actions):
                moved, gained, landed = self._advance_state(
                    current, action, board
                )
                next_path = path + [action]
                next_score = drop_score + gained
                if landed:
                    add_landing(moved, next_path, next_score)
                    continue

                state = (tuple(sorted(moved.cells)), moved.center)
                if state not in visited:
                    visited.add(state)
                    queue.append((moved, next_path, next_score))

        return list(landings.values())

    def _landing_options(self, board, block, start_y=None, prefix=()):
        if start_y is None:
            start_y = block.center[1]
        options = self._target_landing_options(
            board, block, start_y, prefix
        )
        if not self._has_covered_holes(board):
            return options

        reachable = self._reachable_landing_options(
            board, block, start_y, prefix
        )

        landings = {tuple(sorted(option[0].cells)): option for option in options}
        for option in reachable:
            key = tuple(sorted(option[0].cells))
            if key in landings or not self._is_tuck(option[1]):
                continue
            landings[key] = option
        return list(landings.values())

    def _has_covered_holes(self, board):
        tops = [board.height] * board.width
        for x, y in board.cells:
            tops[x] = min(tops[x], y)
        return any(
            (x, y) not in board.cells
            for x, top in enumerate(tops)
            for y in range(top + 1, board.height)
        )

    def _is_tuck(self, path):
        descended = False
        moved_horizontally = False
        for action in path:
            if action is None or action == Direction.Down:
                descended = True
            elif action in (Direction.Left, Direction.Right):
                if descended:
                    return True
                moved_horizontally = True
            elif isinstance(action, Rotation) and moved_horizontally:
                return True
        return False

    def _land(self, board, option, next_shape=None):
        landed, _, drop_score = option
        result = board.clone()
        result.score = board.score + drop_score
        result.falling = landed.clone()
        result.next = Block(next_shape) if next_shape is not None else None
        result.land_block()
        return result

    def _potential(self, board):
        column_tops = [board.height] * board.width
        row_counts = [0] * board.height
        for x, y in board.cells:
            column_tops[x] = min(column_tops[x], y)
            row_counts[y] += 1

        heights = [board.height - top for top in column_tops]
        holes = 0
        covered_holes = 0
        for x, top in enumerate(column_tops):
            blocks_above = 0
            for y in range(top, board.height):
                if (x, y) in board.cells:
                    blocks_above += 1
                else:
                    holes += 1
                    covered_holes += blocks_above

        aggregate_height = sum(heights)
        bumpiness = sum(
            abs(heights[x] - heights[x + 1])
            for x in range(board.width - 1)
        )
        max_height = max(heights, default=0)
        stack_pressure = self._stack_pressure(max_height)
        danger = max(0, max_height - 14)
        endgame = self._endgame_progress()
        blocked_spawns = 0
        if stack_pressure > 0:
            for shape in self.PIECE_SHAPES:
                spawn = Block(shape)
                spawn.initialize(board)
                if spawn.collides(board):
                    blocked_spawns += 1

        row_completion = sum(
            (count / board.width) ** 3 for count in row_counts
        )
        wells = sum(
            min(4, max(0, min(heights[x - 1], heights[x + 1]) - heights[x]))
            for x in range(1, board.width - 1)
        )
        i_well_potential = 0.0
        for x, first_block in enumerate(column_tops):
            top = first_block - 4
            if top < 0:
                continue
            row_fill = [
                (row_counts[y] - ((x, y) in board.cells))
                / (board.width - 1)
                for y in range(top, top + 4)
            ]
            all_rows_fill = 1.0
            for fill in row_fill:
                all_rows_fill *= fill ** 2
            i_well_potential = max(
                i_well_potential,
                1.5 * (
                    30 * sum(fill ** 6 for fill in row_fill)
                    + 80 * all_rows_fill
                ),
            )

        aggregate_height_weight = (
            self.AGGREGATE_HEIGHT_WEIGHT + 2.0 * stack_pressure
        )
        hole_weight = self.HOLE_WEIGHT + stack_pressure
        covered_hole_weight = self.COVERED_HOLE_WEIGHT + 0.025 * stack_pressure
        occupied_cell_weight = 0.1 + 1.5 * endgame
        danger_weight = (
            self.DANGER_WEIGHT + 100.0 * stack_pressure + 12.0 * endgame
        )
        well_weight = self.WELL_WEIGHT * (1.0 - 0.75 * stack_pressure)
        i_well_weight = (
            self.I_WELL_WEIGHT
            * (1.0 - 0.8 * endgame)
            * (1.0 - 0.75 * stack_pressure)
        )

        return (
            -aggregate_height_weight * aggregate_height
            -hole_weight * holes
            -covered_hole_weight * covered_holes
            -self.BUMPINESS_WEIGHT * bumpiness
            -self.MAX_HEIGHT_WEIGHT * max_height
            -occupied_cell_weight * len(board.cells)
            -danger_weight * danger * danger
            -2500.0 * blocked_spawns
            + self.ROW_COMPLETION_WEIGHT * row_completion
            + well_weight * wells
            + i_well_weight * i_well_potential
        )

    def _clear_adjustment(self, result, score_before, drop_score):
        clear_score = result.score - score_before - drop_score
        adjustment = self.CLEAR_ADJUSTMENTS.get(clear_score, 0)
        endgame = self._endgame_progress()
        if clear_score <= 100:
            return adjustment * (1.0 - endgame)
        max_height = max(
            (
                result.height - min(y for cell_x, y in result.cells
                                    if cell_x == x)
                for x in range(result.width)
                if any(cell_x == x for cell_x, _ in result.cells)
            ),
            default=0,
        )
        stack_pressure = self._stack_pressure(max_height)
        low_stack_bonus = (
            1.05 if self.pieces_played < 340 and max_height <= 8 else 1.0
        )
        return adjustment * (
            low_stack_bonus + 0.5 * endgame + 0.5 * stack_pressure
        )

    def _best_next_value(self, board):
        if board.falling is None:
            return self._potential(board)
        if not board.alive:
            return -100000.0

        best = None
        options = self._target_landing_options(board, board.falling)
        ranked = self._rank_options(board, options, None, len(options))
        for _, option, result, immediate_reward in ranked:
            reward = (
                immediate_reward + self._potential(result)
            )
            if best is None or reward > best:
                best = reward
        return best if best is not None else -100000.0

    def _expected_next_value(self, board):
        total = 0.0
        for shape in self.PIECE_SHAPES:
            future = board.clone()
            future.falling = Block(shape)
            future.falling.initialize(future)
            total += self._best_next_value(future)
        return total / len(self.PIECE_SHAPES)

    def _expected_unknown_value(self, board):
        total = 0.0
        for shape in self.PIECE_SHAPES:
            future = board.clone()
            future.falling = Block(shape)
            future.falling.initialize(future)

            best = None
            options = self._target_landing_options(
                future, future.falling
            )
            ranked = self._rank_options(
                future,
                options,
                None,
                min(2, len(options)),
            )
            if ranked:
                best = ranked[0][0]
            total += best if best is not None else -100000.0
        return total / len(self.PIECE_SHAPES)

    def _rank_options(self, board, options, next_shape, limit):
        ranked = []
        for option in options:
            result = self._land(board, option, next_shape)
            immediate_reward = result.score - board.score
            immediate_reward += self._clear_adjustment(
                result, board.score, option[2]
            )
            if self._is_tuck(option[1]):
                immediate_reward -= self.TUCK_THRESHOLD
            value = immediate_reward + self._potential(result)
            if next_shape is not None and not result.alive:
                value -= 100000.0
            ranked.append((value, option, result, immediate_reward))

        ranked.sort(key=lambda item: item[0], reverse=True)
        return ranked[:limit]

    def _lookahead_value(self, item, next_shape):
        value, _, result, adjusted_immediate_reward = item
        if next_shape is None:
            return value
        future_value = self._best_next_value(result)
        if future_value <= -100000.0:
            return value - 100000.0
        return adjusted_immediate_reward + 0.75 * future_value

    def choose_action(self, board):
        if board.falling is None:
            return None
        self.pieces_played += 1

        best_value = -float("inf")
        best_path = [Direction.Drop]

        next_shape = board.next.shape if board.next is not None else None
        normal_options = self._landing_options(board, board.falling)
        normal_ranked = self._rank_options(
            board, normal_options, next_shape, len(normal_options)
        )
        for item in normal_ranked:
            value = self._lookahead_value(item, next_shape)
            if value > best_value:
                best_value = value
                best_path = item[1][1]

        if board.bombs_remaining > 0 and board.next is not None \
                and board.next.shape is not Shape.B:
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

        if board.discards_remaining > 0 and board.next is not None:
            discard_board = board.clone()
            discard_board.discard()
            if discard_board.falling is not None:
                discard_options = self._landing_options(
                    discard_board, discard_board.falling
                )
                discard_ranked = self._rank_options(
                    discard_board,
                    discard_options,
                    None,
                    min(3, len(discard_options)),
                )
                discard_value = -float("inf")
                for item in discard_ranked:
                    _, _, landed_board, adjusted_immediate_reward = item
                    future_value = self._expected_unknown_value(landed_board)
                    candidate_value = (
                        adjusted_immediate_reward + 0.75 * future_value
                    )
                    discard_value = max(discard_value, candidate_value)

                if discard_ranked:
                    current_value = best_value
                    resource_cost = 500 + 50 * (
                        10 - board.discards_remaining
                    )
                    if discard_value > current_value + resource_cost:
                        best_path = [Action.Discard]

        return best_path


SelectedPlayer = SearchPlayer
