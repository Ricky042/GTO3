# GTO3

### Submission for PokerHack 2025 by HackMelbourne

This bot was inspired by Game Theory Optimal (GTO) play and it is designed to play in careful consideration of pot size, hand strength and position.

Designed for use with [PyPokerEngine](https://github.com/ishikota/PyPokerEngine).

## Strategy Overview

- **Preflop Evaluation**: Considers hand strength (pairs, suited connectors, high cards).
- **Postflop Strategy**: Evaluates hand potential and board texture.
- **Position Awareness**: Plays tighter in early position, looser in late position.
- **Round-Based Aggression**: Becomes more aggressive as rounds progress.
- **Probabilistic Bluffing**: Occasionally bluffs to stay unpredictable.
- **Pot Odds & Stack Size**: Adjusts behavior based on pot odds and current stack.

## Playing the poker games
Before you can run the code, run
```bash
pip install -r requirements.txt
```

### Testing 
To see how your bot plays against other bots:
- Register your bot in poker_conf.yaml:
```yaml
ai_players:
  - name: Fish1
    path: sample_player/fish_player_setup.py
  - name: Fish2
    path: sample_player/fish_player_setup.py
  - name: Fish3
    path: sample_player/random_player_setup.py
  - name: Team-Bots
    path: submission/Team-Bots.py
ante: 0
blind_structure: null
initial_stack: 100
max_round: 10
small_blind: 10
```
In this code block, your bot is the fourth player
The other players codes are in the sample_player folder (you do not need to work in this folder)
You can also play around with different ante's, initial stacks, max number of rounds and the small blind

Then, start the server

If running locally on your computer, run
```bash
python -m pypokergui serve ./poker_conf.yaml --port 8000 --speed moderate
```
You can also use "slow" or "fast"
- Their game event speeds are defined in pypokergui/message_manager/py from line 279 onwards

A new browser tab should open
Then you can click on Start Poker to start the simulation
Alternatively, you can also register yourself as a player to play against the AI players

If a port error shows up, such as "OSError: [WinError 10048] Only one usage of each socket address (protocol/network address/port) is normally permitted"
- Rerun the bash command but with a different port (such as 8001)

To close the server, go to the terminal and input Ctrl+C

Additional resources:

PyPokerEngine resources : https://ishikota.github.io/PyPokerEngine/
How to play poker : https://www.youtube.com/watch?v=CpSewSHZhmo
Notion on Poker : https://www.notion.so/How-to-play-poker-An-extensive-guide-for-beginners-1e63f0dcdde3803996e5d2e85a437303?pvs=4
