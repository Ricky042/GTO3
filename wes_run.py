from pypokerengine.api.game import setup_config, start_poker
from submission.rand import rand
from submission.mybot import MyBot
from submission.gto3 import gto3
from submission.allin import allin
from submission.GPTBot import GPTBot
from submission.pokermon import pokermon
from submission.teammasbot import TeamMasBot
from submission.abc import abc

BASE_CONFIG = [
    10,    # Max round
    100,    # initial stack
    5,      # Small blind
    0       # Ante
]

PLAYER_LIST = [
    ("gto3", gto3()),
    ("pokermon", pokermon()),
    ("GPTBot1", GPTBot()),
    ("abc", abc()),
    ("GPTBot2", rand()),
    ("allin", allin())
]

# Number of games to simulate
# Must be at least 4 games played
GAME_AMOUNT = 5

# Simulates X games of Games Amount
SIMULATE_COUNT = 1000

def main():
    final_stack = {} # The final stack of chips for each bot (array)
    total_bot_score = {}
    average_bot_score = {}
    total_win_count = {}
    config = setup_config(BASE_CONFIG[0], BASE_CONFIG[1], BASE_CONFIG[2], BASE_CONFIG[3])
    for player in PLAYER_LIST:
        config.register_player(name=player[0], algorithm=player[1])
        total_win_count[player[0]] = 0
    
    for _ in range(SIMULATE_COUNT):

        for player in PLAYER_LIST:
            final_stack[player[0]] = []


        for _ in range(GAME_AMOUNT):

            # Set final stack for the game (Appending each game final stack)
            for player_stats in start_poker(config, verbose=0)["players"]:
                final_stack[player_stats['name']].append(player_stats['stack'])   

        for player in final_stack:
            score_array = sorted(final_stack[player])

            non_zero_score = 0
            for num in range(len(score_array) -2):
                if score_array[num] == 0:
                    pass
                else:
                    non_zero_score = num
                    break
                
            # TOTAL FINAL SCORE 
            total_bot_score[player] = [score_array[non_zero_score], score_array[-2], score_array[-1]]
            average_bot_score[player] = [sum(score_array) / len(score_array)]

        max_score = 0
        winner = []
        for player in total_bot_score:
            if sum(total_bot_score[player]) > max_score:
                max_score = sum(total_bot_score[player])
                winner = []
                winner.append(player)
            elif sum(total_bot_score[player]) == max_score:
                winner.append(player)
        if len(winner) >1:
            win_score = 0.5
        else: 
            win_score = 1
        
        for player in winner:
            total_win_count[player] += win_score

    print(total_win_count)



if __name__ == "__main__":
    main()