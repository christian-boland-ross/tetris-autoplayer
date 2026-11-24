Build and preserve a deliberate I-piece well. Four cleared rows score 1,600 in the engine, far more than one or two rows. Reward placements that keep a deep, clean channel available for an I-piece, while penalizing holes that would make the well unusable. A generic “wells are good” bonus proved risky; make it specific to a usable four-row setup.

Make discard decisions comparable to normal moves. Currently the normal choice uses next-piece lookahead, but the discard comparison ranks immediate placements and uses a fixed heuristic threshold. Compare both options at the same depth and on the same value scale. Spend a discard when the next piece enables a strong clear or avoids a bad board state—not merely because its immediate heuristic looks better.

Tune for points per game, not just survival. The current heuristic favors a safe board, but that can miss chances to prepare for high-scoring clears. Track score components over complete games, then tune the weights for line setup, holes, height, bumpiness, and survival. Use several fixed seeds for tuning and separate seeds to check that improvements generalize.

Evaluate bomb placements more fully. Bombs don’t score for destroyed cells, so use them when their removal and resulting falls enable better future clears or prevent top-out. Compare multiple bomb landing locations with normal placements, and account for the value of keeping a bomb for later.

Add expected lookahead for unknown future pieces. The next piece is known, but later pieces aren’t. Since the local adversary selects uniformly, estimate future value across all seven shapes after the known piece. A bounded beam or expected-value search can evaluate whether a move preserves useful wells without searching every possible move sequence.

Expand placement search to include tucks. The fast rotation-then-shift search is efficient, but can miss placements where a piece moves sideways or rotates later to fit beneath an overhang. Search deduplicated reachable states to capture those placements, while keeping the search bounded.

Measure discard and bomb use explicitly. For every seed, record clears by size, total score, survival, and remaining resources. This will reveal whether the strategy is leaving valuable resources unused or spending them without earning enough back.