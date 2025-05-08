from pypokerengine.api.game import setup_config, start_poker

from submission.rand import rand
from submission.mybot import MyBot
from submission.gto3 import gto3
from submission.evolvedallin import Evo
from submission.allin import allin
from submission.GPTBot import GPTBot
from submission.pokermon import pokermon
from submission.abc import abc

PLAYER_LIST = [
    ("gto3", gto3()),
    ("pokermon", pokermon()),
    ("allin", allin()),
    ("abc", abc()),
    ("rand", rand()),
    ("GPTBot", GPTBot())
]
config = setup_config(max_round=50, initial_stack=100, small_blind_amount=5)

for player in PLAYER_LIST:
    config.register_player(name=player[0], algorithm=player[1])


game_result = start_poker(config, verbose=1)