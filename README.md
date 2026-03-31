# 🃏 GTO3 — PokerHack 2025 Winner

Hackathon-winning poker bot applying Game Theory Optimal (GTO) strategy via probability-based decision trees. Built for PokerHack 2025 hosted by HackMelbourne. Competed against bots from all participating teams and won.

![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![Game Theory](https://img.shields.io/badge/Game%20Theory-Optimal-blueviolet?style=flat)
![HackMelbourne](https://img.shields.io/badge/HackMelbourne-PokerHack%202025-gold?style=flat)

> 🏆 **Winner — PokerHack 2025 (HackMelbourne)**
> [Devpost submission](https://devpost.com/software/penelopethepokerbot)

---

## Strategy

The bot implements a layered decision framework combining hand strength evaluation, pot odds calculation, positional awareness, and controlled probabilistic bluffing:

- **Preflop** — evaluates hand strength (pairs, suited connectors, high-card equity) and adjusts opening range by position
- **Postflop** — reads board texture and hand potential (made hands vs draws) to determine bet sizing
- **Position awareness** — plays tighter from early position, exploits late-position advantage
- **Pot odds** — folds draws where EV is negative, calls and raises where pot odds justify it
- **Aggression scaling** — increases aggression as the round progresses to pressure passive opponents
- **Probabilistic bluffing** — tuned bluff frequency to remain unexploitable without being too passive

---

## Why it won

Most bots in the competition played reactive strategies — call or fold based on hand strength alone. GTO3 won by combining **position awareness** with **pot odds calculation**, two factors most competitors ignored. The probabilistic bluffing layer made it impossible for opponent bots to build a static counter-strategy.

---

## Running the bot

### Install

```bash
pip install -r requirements.txt
```

### Configure opponents in `poker_conf.yaml`

```yaml
ai_players:
  - name: Opponent1
    path: sample_player/fish_player_setup.py
  - name: Opponent2
    path: sample_player/random_player_setup.py
  - name: GTO3
    path: submission/Team-Bots.py
initial_stack: 100
max_round: 10
small_blind: 10
```

### Start the server

```bash
python -m pypokergui serve ./poker_conf.yaml --port 8000 --speed moderate
```

Open the browser tab → click **Start Poker** → watch it play.

> If you get a port error, change `--port 8000` to `--port 8001`

---

## Built with

- [PyPokerEngine](https://github.com/ishikota/PyPokerEngine) — game engine and simulation framework
- Python probability utilities — hand equity calculation
- Custom decision tree — position + pot odds + bluff frequency logic
