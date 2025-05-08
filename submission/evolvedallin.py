from pypokerengine.players import BasePokerPlayer

def setup_ai():
    return Evo()

class Evo(BasePokerPlayer):

    def declare_action(self, valid_actions, hole_card, round_state):
        street = round_state['street']

        if self.is_strong_hand(hole_card):
            return self.do_all_in(valid_actions)
        else:
            return self.do_fold(valid_actions)

    def is_strong_hand(self, hole_card):
        # Get ranks and check if suited
        ranks = ''.join(sorted([card[1] for card in hole_card], reverse=True))
        suits = [card[0] for card in hole_card]
        suited = suits[0] == suits[1]

        # Premium pairs
        pairs = ['77', '88', '99', 'TT', 'JJ', 'QQ', 'KK', 'AA']
        if ranks[0] == ranks[1] and ranks in pairs:
            return True

        # Ace-high hands
        if ranks[0] == 'A':
            if suited and ranks[1] in ['T', '9', 'J', 'Q', 'K']:  # ATs-AKs
                return True
            if ranks[1] in ['J', 'Q', 'K']:  # AJo-AKo
                return True

        # King-high suited hands
        if ranks[0] == 'K' and suited and ranks[1] in ['T', 'J', 'Q']:  # KTs-KQs
            return True

        # King-Queen offsuit
        if ranks == 'KQ' and not suited:  # KQo
            return True

        # Queen suited hands
        if ranks[0] == 'Q' and suited and ranks[1] in ['T', 'J']:  # QTs-QJs
            return True

        return False

    def do_fold(self, valid_actions):
        return valid_actions[0]['action'], valid_actions[0]['amount']

    def do_all_in(self, valid_actions):
        action_info = valid_actions[2]
        return action_info['action'], action_info['amount']['max']

    # Optional: Boilerplate handlers (can be left empty)
    def receive_game_start_message(self, game_info): pass
    def receive_round_start_message(self, round_count, hole_card, seats): pass
    def receive_street_start_message(self, street, round_state): pass
    def receive_game_update_message(self, action, round_state): pass
    def receive_round_result_message(self, winners, hand_info, round_state): pass
