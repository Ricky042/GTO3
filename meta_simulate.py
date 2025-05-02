#!/usr/bin/env python3
import argparse
from collections import defaultdict
from simulate import simulate_games

# ─── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Meta-simulate your poker AI batches.")
    parser.add_argument('-n', '--num-games', type=int, default=100,
                        help='Number of games per batch (passed to simulate.py)')
    parser.add_argument('-k', '--batches', type=int, default=10,
                        help='Number of batches to meta-simulate')
    args = parser.parse_args()

    meta_wins = defaultdict(int)

    for i in range(1, args.batches+1):
        _, final_scores = simulate_games(args.num_games)
        # highest final score wins the batch
        batch_winner = max(final_scores, key=final_scores.get)
        meta_wins[batch_winner] += 1
        print(f"Batch {i}: winner = {batch_winner} (score {final_scores[batch_winner]})")

    print(f"\nMeta-simulated {args.batches} batches (each {args.num_games} games):\n")
    for bot, count in meta_wins.items():
        print(f"  • {bot:6s} : {count} batch-wins")

if __name__ == '__main__':
    main()