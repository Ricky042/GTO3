from pypokerengine.api.game import setup_config, start_poker

from submission.rand import rand
from submission.mybot import MyBot
from submission.gto1 import gto1
from submission.gto2 import gto2
from submission.gto3 import gto3
from submission.allin import allin

from submission.GPTBot import GPTBot


config = setup_config(max_round=100, initial_stack=100, small_blind_amount=5)
config.register_player(name="rand", algorithm=rand())
config.register_player(name="rand1", algorithm=rand())
config.register_player(name="rand2", algorithm=rand())
config.register_player(name="allin", algorithm=allin())
config.register_player(name="GPTBot", algorithm=GPTBot())
config.register_player(name="gto3", algorithm=gto3())

game_result = start_poker(config, verbose=1)