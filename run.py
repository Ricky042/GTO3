from pypokerengine.api.game import setup_config, start_poker

from submission.mybot import MyBot
from submission.JeremyGTObot import JeremyGTObot
from submission.JeremyBotAllin import JeremyBotAllin


config = setup_config(max_round=10, initial_stack=100, small_blind_amount=5)
config.register_player(name="p1", algorithm=MyBot())
config.register_player(name="p2", algorithm=MyBot())
config.register_player(name="gtobot", algorithm=JeremyGTObot())
config.register_player(name="allin", algorithm=JeremyBotAllin())
game_result = start_poker(config, verbose=1)