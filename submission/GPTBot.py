import random
from collections import defaultdict
from pypokerengine.players import BasePokerPlayer

# Add missing constants
CARD_RANKS = {
    '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
    'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14
}

def setup_ai():
    return GPTBot()

class GPTBot(BasePokerPlayer):

    def declare_action(self, valid_actions, hole_card, round_state):
        community_card = round_state['community_card']
        street = round_state['street']
        min_raise = valid_actions[2]['amount']['min']
        max_raise = valid_actions[2]['amount']['max']

        hand_strength = self.evaluate_hand_strength(hole_card, community_card, street)
        print(hole_card)

        if not hasattr(self, 'position_multiplier'):
            if round_state:
                _, self.position_multiplier = self.get_position(round_state)
            else:
                self.position_multiplier = 1.0
    
        # Adjust hand strength based on position
        adjusted_strength = min(0.99, hand_strength * self.position_multiplier)
        print(adjusted_strength)
        
        # Calculate pot odds and stack-to-pot ratio if possible
        if not hasattr(self, 'pot_odds'):
            self.pot_odds = 0.5  # Default value
            
        # Get current pot size
        pot_size = 0
        if round_state and 'pot' in round_state:
            pot_size = round_state['pot']['main']['amount']
        
        # Get stack size
        stack_size = getattr(self, 'stack', 1000)  # Default large stack
        
        # Calculate stack-to-pot ratio (SPR)
        spr = stack_size / max(pot_size, 1)  # Avoid division by zero
        
        # Track the aggression at the table
        aggression_level = 0
        if round_state and 'action_histories' in round_state and 'preflop' in round_state['action_histories']:
            histories = round_state['action_histories']['preflop']
            raise_count = sum(1 for action in histories if action['action'] == 'RAISE')
            player_count = len(set(action['uuid'] for action in histories))
            if player_count > 0:
                aggression_level = raise_count / player_count
        
        # Number of players still in hand
        active_players = 0
        if round_state and 'seats' in round_state:
            active_players = len([s for s in round_state['seats'] if s['state'] != 'folded'])
        
        # Adjust strategy based on table dynamics
        # Tighten up with many players, loosen up heads-up
        player_adjustment = 1.0
        if active_players > 4:
            player_adjustment = 0.9  # Tighter with more players
        elif active_players <= 2:
            player_adjustment = 1.1  # Looser heads-up
        
        # Adjust for aggression - tighten up at aggressive tables
        aggression_adjustment = 1.0 - (aggression_level * 0.1)  # Max 10% reduction at very aggressive tables
        
        # Final adjusted strength with all factors
        final_strength = adjusted_strength * player_adjustment * aggression_adjustment
        
        # Decision making with more granularity and table dynamics awareness
        if final_strength >= 0.85:
            # Premium hands - raise big
            # In aggressive games, raise bigger
            raise_amount = max(int(valid_actions[2]['amount']['max'] * (0.7 + (aggression_level * 0.1))), 
                            valid_actions[2]['amount']['min'])
            return self.do_raise(valid_actions, raise_amount)
        
        elif final_strength >= 0.75:
            # Strong hands - standard raise
            # With high SPR, we can be more aggressive
            if spr > 10:
                raise_amount = min(valid_actions[2]['amount']['min'] * 3, 
                                valid_actions[2]['amount']['max'])
            else:
                raise_amount = min(valid_actions[2]['amount']['min'] * 2.5, 
                                valid_actions[2]['amount']['max'])
            return self.do_raise(valid_actions, raise_amount)
        
        elif final_strength >= 0.60:
            # Good hands - sized raise based on position
            if hasattr(self, 'position_type') and self.position_type in ['button', 'cutoff', 'late']:
                # Raise more from late position
                raise_amount = min(valid_actions[2]['amount']['min'] * 2, 
                                valid_actions[2]['amount']['max'])
            else:
                # Standard min raise from early/middle
                raise_amount = valid_actions[2]['amount']['min']
            return self.do_raise(valid_actions, raise_amount)
        
        elif final_strength >= 0.45:
            # Playable hands - call if pot odds are favorable
            cost_to_call = valid_actions[1]['amount']
            
            # If we're getting good pot odds, or in position, call
            if (cost_to_call <= self.pot_odds * stack_size or 
                (hasattr(self, 'position_type') and self.position_type in ['button', 'cutoff'])):
                return self.do_call(valid_actions)
            else:
                return self.do_fold(valid_actions)
        
        elif final_strength >= 0.35:
            # Speculative hands - call only if cheap and good position
            if (valid_actions[1]['amount'] <= 0.05 * stack_size and 
                hasattr(self, 'position_type') and self.position_type in ['button', 'cutoff', 'late']):
                return self.do_call(valid_actions)
            else:
                return self.do_fold(valid_actions)
        
        else:
            # Weak hands - usually fold
            # Occasionally call with garbage in the big blind if cheap
            if (hasattr(self, 'position_type') and self.position_type == 'big_blind' and 
                valid_actions[1]['amount'] <= 0.02 * stack_size):
                return self.do_call(valid_actions)
            else:
                return self.do_fold(valid_actions)

    def evaluate_hand_strength(self, hole_card, community_card, street):
        if street == "preflop":
            return self.evaluate_preflop(hole_card)
        else:
            # Simple hand strength evaluation
            return self._estimate_hand_strength(hole_card, community_card)

    def evaluate_preflop(self, hole_card):
        ranks = '23456789TJQKA'
        rank_values = {r: i for i, r in enumerate(ranks, 2)}

        card1 = hole_card[0]
        card2 = hole_card[1]

        # Fix: swap index positions - suit is at [0], rank is at [1]
        s1, s2 = card1[0], card2[0]
        r1, r2 = card1[1], card2[1]

        same_suit = s1 == s2
        pair = r1 == r2
        high_card = max(rank_values[r1], rank_values[r2])
        low_card = min(rank_values[r1], rank_values[r2])
        gap = high_card - low_card - 1  # Card gap (0 for connected cards)

        # Enhanced preflop hand strength evaluation
        if pair:
            if rank_values[r1] >= 12: return 0.95  # AA, KK
            elif rank_values[r1] == 11: return 0.90  # QQ
            elif rank_values[r1] == 10: return 0.85  # JJ
            elif rank_values[r1] == 9: return 0.80  # TT
            elif rank_values[r1] >= 7: return 0.75  # 77-99
            else: return 0.65  # 22-66
        
        # High cards
        elif high_card == 14:  # Ace high
            if low_card >= 12 and same_suit: return 0.88  # AK suited
            elif low_card >= 12: return 0.80  # AK offsuit
            elif low_card >= 10 and same_suit: return 0.75  # AQ, AJ suited
            elif low_card >= 10: return 0.70  # AQ, AJ offsuit
            elif low_card >= 8 and same_suit: return 0.65  # AT, A9, A8 suited
            elif low_card >= 8: return 0.55  # AT, A9, A8 offsuit
            elif same_suit: return 0.50  # A7-A2 suited
            else: return 0.40  # A7-A2 offsuit
        
        # King high
        elif high_card == 13:  # King high
            if low_card >= 11 and same_suit: return 0.70  # KQ suited
            elif low_card >= 11: return 0.65  # KQ offsuit
            elif low_card >= 9 and same_suit: return 0.60  # KJ, KT suited
            elif low_card >= 9: return 0.55  # KJ, KT offsuit
            elif same_suit: return 0.45  # K9-K2 suited
            else: return 0.35  # K9-K2 offsuit
        
        # Connected cards and suited connectors
        elif gap <= 1:  # Connected or 1-gap
            if high_card >= 11 and same_suit: return 0.65  # QJ, JT suited
            elif high_card >= 11: return 0.60  # QJ, JT offsuit
            elif high_card >= 9 and same_suit: return 0.55  # T9, 98 suited
            elif high_card >= 9: return 0.50  # T9, 98 offsuit
            elif same_suit: return 0.45  # Small connected suited
            else: return 0.35  # Small connected offsuit
        
        # Other suited cards
        elif same_suit and high_card >= 10:
            return 0.45  # Any other suited cards with high card T or better
        
        # Everything else
        elif same_suit:
            return 0.40  # Any other suited cards
        else:
            return 0.30  # Any other offsuit cards
        
    def _estimate_hand_strength(self, hole_cards, community_cards):
        """Estimate postflop hand strength using a simplified algorithm"""
        if not community_cards:
            return self.evaluate_preflop(hole_cards) 


        all_cards = hole_cards + community_cards


        rank_count = defaultdict(int)
        for card in all_cards:
            rank = card[1]
            rank_count[rank] += 1


        max_count = max(rank_count.values()) if rank_count else 0


        suit_count = defaultdict(int)
        for card in all_cards:
            suit = card[0]
            suit_count[suit] += 1

        has_flush = max(suit_count.values()) >= 5 if suit_count else False


        ranks_present = set()
        for card in all_cards:
            ranks_present.add(CARD_RANKS.get(card[1], 0))

        has_straight = False
        for i in range(2, 15 - 4):  # 2 through 10 as starting rank
            if all(r in ranks_present for r in range(i, i+5)):
                has_straight = True
                break

        if has_flush and has_straight:
            return 0.95  # Straight flush
        elif max_count == 4:
            return 0.9  # Four of a kind
        elif max_count == 3 and len([c for c in rank_count.values() if c >= 2]) >= 2:
            return 0.85  # Full house
        elif has_flush:
            return 0.8  # Flush
        elif has_straight:
            return 0.75  # Straight
        elif max_count == 3:
            return 0.7  # Three of a kind
        elif len([c for c in rank_count.values() if c == 2]) >= 2:
            return 0.6  # Two pair
        elif max_count == 2:
            return 0.5  # One pair
        else:
            # High card - scale by highest card
            highest_rank = max([CARD_RANKS.get(card[1], 0) for card in all_cards])
            return 0.2 + (highest_rank / 14.0) * 0.3  # Scale between 0.2 and 0.5
        

    def get_position(self, round_state):
        """
        Determine the player's position at the table.
        Returns: 
            - position_type: string (early, middle, late, blinds)
            - position_multiplier: float (value to adjust hand strength)
        """
        # Get key information
        dealer_btn = round_state['dealer_btn']
        small_blind_pos = round_state['small_blind_pos']
        big_blind_pos = round_state['big_blind_pos']
        seats = round_state['seats']
        
        # Find our uuid and seat index
        my_uuid = self.uuid
        total_active_players = len([s for s in seats if s['state'] != 'folded'])
        
        # If we have less than 4 players, positions change dramatically
        if total_active_players <= 3:
            # In heads-up or 3-handed play
            if my_uuid == dealer_btn:
                return "button", 1.2  # Button is strongest in short-handed
            elif my_uuid == small_blind_pos:
                return "small_blind", 0.9
            elif my_uuid == big_blind_pos:
                return "big_blind", 0.95
            else:
                return "middle", 1.0
        
        # For full tables, determine position relative to dealer button
        # First, create ordered list of active players starting from SB (first to act post-flop)
        active_players = []
        
        # Start from small blind and go around the table
        current_pos = small_blind_pos
        while len(active_players) < total_active_players:
            # Find the seat with this uuid
            for seat in seats:
                if seat['uuid'] == current_pos and seat['state'] != 'folded':
                    active_players.append(current_pos)
                    break
            
            # Move to next seat (circular)
            current_pos = next((s['uuid'] for s in seats if s['state'] != 'folded' and s['uuid'] not in active_players), None)
            if current_pos is None:
                break  # Safety check
        
        # Find our position in the order
        try:
            my_position = active_players.index(my_uuid)
        except ValueError:
            return "unknown", 1.0  # Fallback if we can't determine position
        
        # Divide table into positions
        total = len(active_players)
        early_cutoff = total // 3
        middle_cutoff = 2 * (total // 3)
        
        # Specific positions for blinds
        if my_uuid == small_blind_pos:
            return "small_blind", 0.9
        elif my_uuid == big_blind_pos:
            return "big_blind", 0.95
        elif my_uuid == dealer_btn:
            return "button", 1.2
        # Pre-flop specific positions
        elif my_position == 2 and total > 5:  # UTG
            return "utg", 0.85
        elif my_position == total - 2 and total > 5:  # Cutoff
            return "cutoff", 1.15
        # General position classifications
        elif my_position < early_cutoff:
            return "early", 0.9
        elif my_position < middle_cutoff:
            return "middle", 1.0
        else:
            return "late", 1.1

    def receive_game_start_message(self, game_info):
        pass

    def receive_round_start_message(self, round_count, hole_card, seats):
        pass

    def receive_street_start_message(self, street, round_state):
        pass

    def receive_game_update_message(self, action, round_state):
        pass

    def receive_round_result_message(self, winners, hand_info, round_state):
        pass

    # Action helpers
    def do_fold(self, valid_actions):
        action_info = valid_actions[0]
        return action_info['action'], action_info['amount']

    def do_call(self, valid_actions):
        action_info = valid_actions[1]
        return action_info['action'], action_info['amount']

    def do_raise(self, valid_actions, raise_amount):
        action_info = valid_actions[2]
        amount = max(action_info['amount']['min'], raise_amount)
        return action_info['action'], amount
