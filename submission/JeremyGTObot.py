import random
from pypokerengine.players import BasePokerPlayer

# Notes
# All cards follow this format: Suit + Rank : 4 of Hearts = 4H, 10 of Spades = ST [2,3,4,5,6,7,8,9,T,J,Q,K,A] [S,C,D,H]

def setup_ai():
    return JeremyGTObot()

class JeremyGTObot(BasePokerPlayer):  # Do not forget to make parent class as "BasePokerPlayer"
    def __init__(self):
        self.uuid = None
        self.hand_strength_preflop = {
            # Pairs
            "AA": 85, "KK": 82, "QQ": 80, "JJ": 78, "TT": 75,
            "99": 72, "88": 69, "77": 66, "66": 63, "55": 60,
            "44": 57, "33": 54, "22": 51,
            # Suited connectors and high cards
            "AKs": 67, "AQs": 66, "AJs": 65, "ATs": 64, "A9s": 63,
            "KQs": 63, "KJs": 62, "KTs": 61, "QJs": 60, "QTs": 59,
            "JTs": 58, "T9s": 57, "98s": 56, "87s": 55, "76s": 54,
            # Offsuit high cards
            "AKo": 65, "AQo": 64, "AJo": 63, "ATo": 62,
            "KQo": 62, "KJo": 61, "QJo": 59,
        }
        self.position_values = {
            "early": 0.7,     # UTG, UTG+1
            "middle": 0.85,   # MP, HJ
            "late": 1.0,      # CO, BTN
            "blinds": 0.8     # SB, BB
        }
        self.play_style_aggressive = 0.2  # Adjust for more or less aggressive play (0.0-0.5)
        self.history = []
        self.round_history = {}
        self.my_stack = 0
        self.opponent_profiles = {}
        
    def declare_action(self, valid_actions, hole_card, round_state):
        # For tracking and debugging
        community_card = round_state['community_card']
        street = round_state['street']
        pot = round_state['pot']['main']['amount']
        seats = round_state['seats']
        
        # Find our position and stack
        self.my_stack = 0
        my_pos = "early"  # default
        player_count = len(seats)
        dealer_btn = round_state['dealer_btn']
        next_player = round_state['next_player']
        
        for i, seat in enumerate(seats):
            if seat['uuid'] == self.uuid:
                self.my_stack = seat['stack']
                # Determine position
                relative_pos = (i - dealer_btn) % player_count
                if relative_pos <= 1:
                    my_pos = "early"
                elif relative_pos <= 3:
                    my_pos = "middle"
                elif relative_pos <= 5:
                    my_pos = "late"
                else:
                    my_pos = "blinds"
                break
                
        # Update opponent profiles based on actions
        self.update_opponent_profiles(round_state)
        
        # Call our main decision function
        action, amount = self.chooseAction(valid_actions, hole_card, community_card, 
                                          street, pot, my_pos, round_state)
        
        # Store our action in history
        self.history.append({
            'street': street,
            'hole_card': hole_card,
            'community_card': community_card,
            'action': action,
            'amount': amount
        })
        
        return action, amount

    def chooseAction(self, valid_actions, hole_card, community_card, street, pot, position, round_state):
        """
        Main decision logic for the bot.
        Returns a tuple of (action, amount)
        """
        # Get minimum and maximum raise values
        min_raise = valid_actions[2]['amount']['min']
        max_raise = valid_actions[2]['amount']['max']
        
        # Calculate pot odds and required equity
        call_amount = valid_actions[1]['amount']
        pot_odds = call_amount / (pot + call_amount) if pot + call_amount > 0 else 0
        required_equity = pot_odds  # Simplified required equity
        
        # Calculate our equity
        equity = self.calculate_equity(hole_card, community_card, street, position)
        
        # Get action history for this street
        action_history = round_state['action_histories'].get(street, [])
        aggression_count = sum(1 for act in action_history if act.get('action') in ['RAISE', 'BET'])
        
        # Decision making based on street
        if street == 'preflop':
            return self.preflop_strategy(hole_card, equity, valid_actions, position, 
                                        pot, min_raise, max_raise, aggression_count)
        else:
            return self.postflop_strategy(equity, required_equity, valid_actions, street, 
                                         pot, min_raise, max_raise, aggression_count)
    
    def preflop_strategy(self, hole_card, equity, valid_actions, position, pot, min_raise, max_raise, aggression_count):
        """Handle preflop decisions"""
        # Get hand type
        hand_type = self.get_hand_type(hole_card)
        
        # Adjust equity based on position
        position_factor = self.position_values.get(position, 0.8)
        adjusted_equity = equity * position_factor
        
        # Adjust for table aggression
        if aggression_count > 1:
            adjusted_equity *= 0.9  # Reduce equity if table is aggressive
        
        # Decision thresholds for preflop
        raise_threshold = 0.55 + self.play_style_aggressive
        call_threshold = 0.40 + self.play_style_aggressive
        
        # Premium hands - raise or re-raise
        if adjusted_equity > raise_threshold:
            # Decide bet size (25-40% of pot for strong hands)
            raise_amount = min(max(min_raise, int(pot * (0.25 + adjusted_equity * 0.15))), max_raise)
            return self.do_raise(valid_actions, raise_amount)
        
        # Playable hands - call or small raise
        elif adjusted_equity > call_threshold:
            # Check if we're facing a raise
            if valid_actions[1]['amount'] > 0:
                return self.do_call(valid_actions)
            else:
                # Small raise if we're opening
                raise_amount = min(max(min_raise, int(pot * 0.3)), max_raise)
                return self.do_raise(valid_actions, raise_amount)
        
        # Weak hands - check if possible, otherwise fold
        else:
            if valid_actions[1]['amount'] == 0:  # Can check
                return self.do_call(valid_actions)
            else:
                return self.do_fold(valid_actions)
    
    def postflop_strategy(self, equity, required_equity, valid_actions, street, pot, min_raise, max_raise, aggression_count):
        """Handle postflop decisions"""
        # Adjust our equity based on street
        if street == 'flop':
            # More cautious on flop
            equity = equity * 0.9
        elif street == 'turn':
            # More accurate on turn
            equity = equity * 0.95
        # River equity is most accurate, no adjustment
        
        # Calculate pot control factor (reduce aggression with medium strength hands)
        pot_control = 1.0
        if 0.4 < equity < 0.7:
            pot_control = 0.8
        
        # Premium hands - value bet
        if equity > 0.75:
            # Strong hands bet 50-70% of pot
            raise_amount = min(max(min_raise, int(pot * (0.5 + (equity - 0.75) * 2))), max_raise)
            return self.do_raise(valid_actions, raise_amount)
        
        # Good hands - value bet or call
        elif equity > 0.6:
            if aggression_count <= 1 and random.random() < 0.7:  # Sometimes bet for value
                raise_amount = min(max(min_raise, int(pot * 0.5 * pot_control)), max_raise)
                return self.do_raise(valid_actions, raise_amount)
            else:
                return self.do_call(valid_actions)
        
        # Drawing hands or medium strength
        elif equity > required_equity + 0.05:  # We have enough equity plus a small buffer
            if valid_actions[1]['amount'] < pot * 0.2:  # Facing small bet
                return self.do_call(valid_actions)
            else:
                # Balance calling and folding against big bets
                if random.random() < equity * 1.3:  # More likely to call with higher equity
                    return self.do_call(valid_actions)
                else:
                    return self.do_fold(valid_actions)
        
        # Bluffing opportunities
        elif street != 'river' and valid_actions[1]['amount'] == 0 and random.random() < 0.3:
            # Occasionally bluff when checking is possible
            raise_amount = min(max(min_raise, int(pot * 0.3)), max_raise)
            return self.do_raise(valid_actions, raise_amount)
        
        # Weak hands
        else:
            if valid_actions[1]['amount'] == 0:  # Can check
                return self.do_call(valid_actions)
            else:
                return self.do_fold(valid_actions)
    
    def calculate_equity(self, hole_card, community_card, street, position):
        """
        Calculate hand equity based on current cards and street
        Returns a value between 0 and 1 representing equity
        """
        if street == 'preflop':
            return self.preflop_equity(hole_card, position)
        else:
            return self.postflop_equity(hole_card, community_card, street)
    
    def preflop_equity(self, hole_card, position):
        """Calculate preflop equity using hand strength chart"""
        hand_type = self.get_hand_type(hole_card)
        
        # Look up base equity from our hand chart
        base_equity = self.hand_strength_preflop.get(hand_type, 30) / 100.0
        
        # Adjust for position
        position_factor = self.position_values.get(position, 0.8)
        
        return base_equity * position_factor
    
    def postflop_equity(self, hole_card, community_card, street):
        """Calculate postflop equity"""
        # This is a simplified equity calculation
        # In a real GTO bot, you would use more sophisticated equity calculations
        
        # Evaluate hand strength
        hand_strength = self.evaluate_hand(hole_card, community_card)
        
        # Adjust based on street - more cards means more accurate equity calculation
        if street == 'flop':
            max_strength = 8  # Trips on flop is already strong
        elif street == 'turn':
            max_strength = 9  # Straight is strong on turn
        else:  # river
            max_strength = 10  # Flush or better on river
        
        # Convert hand strength to equity (0-1 scale)
        equity = min(1.0, hand_strength / max_strength)
        
        # Add some randomness to simulate the uncertainty of actual equity calculation
        equity = min(1.0, max(0.0, equity + (random.random() * 0.1 - 0.05)))
        
        return equity
    
    def evaluate_hand(self, hole_card, community_card):
        """
        Simple hand evaluator, returns a score from 0-10
        0: High card
        1: Pair
        2: Two pair
        3: Three of a kind
        4: Straight
        5: Flush
        6: Full house
        7: Four of a kind
        8: Straight flush
        9: Royal flush
        With additional points for high cards
        """
        # Simplified evaluation for demonstration
        all_cards = hole_card + community_card
        ranks = [card[1] for card in all_cards]
        suits = [card[0] for card in all_cards]
        
        # Count frequencies
        rank_counts = {}
        for rank in ranks:
            rank_counts[rank] = rank_counts.get(rank, 0) + 1
        
        suit_counts = {}
        for suit in suits:
            suit_counts[suit] = suit_counts.get(suit, 0) + 1
        
        # Check for pairs, trips, quads
        pairs = sum(1 for count in rank_counts.values() if count == 2)
        trips = sum(1 for count in rank_counts.values() if count == 3)
        quads = sum(1 for count in rank_counts.values() if count == 4)
        
        # Check for flush
        flush = any(count >= 5 for count in suit_counts.values())
        
        # Check for straight (simplified)
        has_straight = False
        rank_values = {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, 
                     "9": 9, "T": 10, "J": 11, "Q": 12, "K": 13, "A": 14}
        values = sorted([rank_values.get(r, 0) for r in ranks])
        # Check for 5 consecutive values
        for i in range(len(values) - 4):
            if values[i:i+5] == list(range(values[i], values[i]+5)):
                has_straight = True
                break
        
        # Determine hand strength
        if flush and has_straight:
            return 8  # Straight flush
        elif quads >= 1:
            return 7  # Four of a kind
        elif trips >= 1 and pairs >= 1:
            return 6  # Full house
        elif flush:
            return 5  # Flush
        elif has_straight:
            return 4  # Straight
        elif trips >= 1:
            return 3  # Three of a kind
        elif pairs >= 2:
            return 2  # Two pair
        elif pairs == 1:
            return 1  # Pair
        else:
            # High card - add a small bonus for high cards
            high_cards = sum(1 for r in ranks if r in ['A', 'K', 'Q', 'J', 'T'])
            return 0 + (high_cards * 0.1)
    
    def get_hand_type(self, hole_card):
        """Convert hole cards to a standardized hand type format"""
        if len(hole_card) != 2:
            return "XX"
            
        # Sort cards by rank with aces high
        rank_order = "23456789TJQKA"
        rank1, suit1 = hole_card[0][1], hole_card[0][0]
        rank2, suit2 = hole_card[1][1], hole_card[1][0]
        
        if rank_order.index(rank1) > rank_order.index(rank2):
            rank1, rank2 = rank2, rank1
            suit1, suit2 = suit2, suit1
            
        # Pair
        if rank1 == rank2:
            return rank1 + rank2
        
        # Suited or offsuit
        suffix = "s" if suit1 == suit2 else "o"
        return rank2 + rank1 + suffix
    
    def update_opponent_profiles(self, round_state):
        """Update opponent profiles based on their actions"""
        if 'action_histories' not in round_state:
            return
            
        for street, actions in round_state['action_histories'].items():
            for action_data in actions:
                player_id = action_data.get('uuid')
                if player_id and player_id != self.uuid:
                    if player_id not in self.opponent_profiles:
                        self.opponent_profiles[player_id] = {
                            'aggression': 0.5,  # Initial value
                            'vpip': 0.5,       # Voluntarily put money in pot
                            'actions': []
                        }
                    
                    # Track this action
                    self.opponent_profiles[player_id]['actions'].append(action_data)
                    
                    # Update aggression metric
                    action_type = action_data.get('action')
                    if action_type in ['RAISE', 'BET']:
                        self.opponent_profiles[player_id]['aggression'] += 0.05
                    elif action_type == 'FOLD':
                        self.opponent_profiles[player_id]['aggression'] -= 0.03
                        
                    # Cap values
                    self.opponent_profiles[player_id]['aggression'] = min(1.0, max(0.0, 
                                                                            self.opponent_profiles[player_id]['aggression']))
    
    def receive_game_start_message(self, game_info):
        self.uuid = self.uuid if self.uuid else game_info['seats'][game_info['my_player_pos']]['uuid']
        player_num = game_info["player_num"]
        max_round = game_info["rule"]["max_round"]
        small_blind_amount = game_info["rule"]["small_blind_amount"]
        ante_amount = game_info["rule"]["ante"]
        blind_structure = game_info["rule"]["blind_structure"]
        
        # Reset history for new game
        self.history = []
        self.round_history = {}
        self.opponent_profiles = {}

    def receive_round_start_message(self, round_count, hole_card, seats):
        self.round_history = {
            'round_count': round_count,
            'hole_card': hole_card,
            'actions': []
        }

    def receive_street_start_message(self, street, round_state):
        pass

    def receive_game_update_message(self, action, round_state):
        if hasattr(self, 'round_history'):
            self.round_history['actions'].append({
                'action': action,
                'round_state': round_state.copy() if isinstance(round_state, dict) else round_state
            })

    def receive_round_result_message(self, winners, hand_info, round_state):
        # Learn from results
        self.analyze_round_result(winners, hand_info, round_state)

    def analyze_round_result(self, winners, hand_info, round_state):
        """Analyze round results to improve future play"""
        # Track if we won or lost
        my_uuid = self.uuid
        won_hand = any(winner['uuid'] == my_uuid for winner in winners)
        
        # If we lost after investing significantly, maybe adjust aggression
        if not won_hand and hasattr(self, 'round_history') and 'actions' in self.round_history:
            # Examine our actions
            invested_amount = 0
            for action_data in self.round_history['actions']:
                action = action_data.get('action', {})
                if isinstance(action, dict) and 'uuid' in action and action['uuid'] == my_uuid:
                    if action.get('action') in ['CALL', 'RAISE', 'BET']:
                        invested_amount += action.get('amount', 0)
            
            # If we invested a lot and lost, slightly reduce aggression
            if invested_amount > 50:  # Arbitrary threshold
                self.play_style_aggressive = max(0.0, self.play_style_aggressive - 0.01)
            
        # If we won after being aggressive, reinforce that behavior
        elif won_hand:
            self.play_style_aggressive = min(0.5, self.play_style_aggressive + 0.005)
            
    # Helper functions - call these in the declare_action function to declare your move
    def do_fold(self, valid_actions):
        action_info = valid_actions[0]
        amount = action_info["amount"]
        return action_info['action'], amount

    def do_call(self, valid_actions):
        action_info = valid_actions[1]
        amount = action_info["amount"]
        return action_info['action'], amount
    
    def do_raise(self,  valid_actions, raise_amount):
        action_info = valid_actions[2]
        amount = max(action_info['amount']['min'], min(raise_amount, action_info['amount']['max']))
        return action_info['action'], amount
    
    def do_all_in(self,  valid_actions):
        action_info = valid_actions[2]
        amount = action_info['amount']['max']
        return action_info['action'], amount