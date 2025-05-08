#!/usr/bin/env python3
import subprocess
import re
import ast
from collections import defaultdict

# ─── CONFIG ────────────────────────────────────────────────────────────────────
N_SIMULATIONS = 100  # default number of games per batch
PLAYERS = [
    "gto3",
    "pokermon",
    "allin",
    "abc",
    "rand",
    "GPTBot"
]
GAME_CMD = ["python", "run.py"]

# ─── PARSING HELPERS ───────────────────────────────────────────────────────────
_stack_re = re.compile(r"\(stack\s*=\s*(\{.*\})\)")

def extract_winner(line, players):
    for name in players:
        if f'"[\'{name}\']"' in line:
            return name
    return None

def parse_stack(line):
    m = _stack_re.search(line)
    if not m:
        raise ValueError(f"Couldn't find stack dict in: {line!r}")
    return ast.literal_eval(m.group(1))

# ─── SCORING HELPER ────────────────────────────────────────────────────────────
def compute_final_score(scores):
    sorted_scores = sorted(scores, reverse=True)
    top2 = sorted_scores[:2]
    remaining = sorted_scores[2:]
    non_zero_remaining = [s for s in remaining if s > 0]
    bottom_nz = min(non_zero_remaining) if non_zero_remaining else 0
    return sum(top2) + bottom_nz

# ─── BATCH SIMULATION ──────────────────────────────────────────────────────────
def simulate_games(n):
    """
    Runs the game n times, returns:
      - win_counts: dict bot->win count
      - final_scores: dict bot->computed final score
    """
    win_counts = defaultdict(int)
    all_stacks = {p: [] for p in PLAYERS}

    for i in range(1, n+1):
        res = subprocess.run(GAME_CMD, capture_output=True, text=True)
        last = next((l for l in reversed(res.stdout.splitlines()) if l.strip()), "")
        try:
            stack = parse_stack(last)
        except ValueError:
            continue

        # record each bot's stack
        for p, val in stack.items():
            all_stacks[p].append(val)

        # record winner by highest stack
        winner = max(stack, key=stack.get)
        win_counts[winner] += 1

    # compute final scores
    final_scores = {p: compute_final_score(all_stacks[p]) for p in PLAYERS}
    return win_counts, final_scores

# ─── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run batch poker simulations.")
    parser.add_argument('-n', '--num-games', type=int, default=N_SIMULATIONS,
                        help='Number of poker games per batch')
    args = parser.parse_args()

    wc, fs = simulate_games(args.num_games)
    print(f"\nSimulated {args.num_games} games.\n")
    print("Win counts per bot:")
    for p in PLAYERS:
        print(f"  • {p:6s} : {wc[p]} wins")
    print("\nFinal scores per bot:")
    for p in PLAYERS:
        print(f"  • {p:6s} : {fs[p]}")