import subprocess
import re
from collections import defaultdict

# Define your known player names
PLAYERS = ["p1", "p2", "gtobot", "allin"]

def extract_winner(output, player_names):
    for name in player_names:
        # Look for the exact pattern: "['p2']" (quotes included)
        if f'"[\'{name}\']"' in output:
            return name
    return None

def run_simulations(n, player_names):
    wins = defaultdict(int)
    undetermined = 0

    for i in range(n):
        try:
            result = subprocess.run(['python', 'run.py'], capture_output=True, text=True)
            output = result.stdout.strip().split('\n')[-1]
            winner = extract_winner(output, player_names)
            if winner:
                wins[winner] += 1
            else:
                undetermined += 1
                print(f"[Warning] Run {i+1}: Could not determine winner.\nOutput: {output}")
        except Exception as e:
            print(f"[Error] Run {i+1} failed: {e}")
            undetermined += 1

    print("\n=== Simulation Results ===")
    for player in player_names:
        print(f"{player}: {wins[player]} wins")
    print(f"Undetermined results: {undetermined}")

if __name__ == "__main__":
    N = 100  # You can change this
    run_simulations(N, PLAYERS)
