import random
from pypokerengine.players import BasePokerPlayer
from collections import defaultdict
import time
import math

# For card evaluation and hand strength calculations
CARD_RANKS = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
CARD_SUITS = {'S': 0, 'C': 1, 'D': 2, 'H': 3}

def setup_ai():
    return gto2()

class gto2(BasePokerPlayer):
    def __init__(self):
        super().__init__()
        self.uuid = None
        self.hand_history = []
        self.player_stats = defaultdict(lambda: {
            'vpip': 0, 'pfr': 0, 'total_hands': 0, 
            'fold_to_3bet': 0, '3bet_opportunities': 0,
            'aggression_factor': 0, 'cont_bet': 0, 'cont_bet_opps': 0
        })
        self.position_stats = defaultdict(int)
        self.starting_stack = 0
        self.hand_strength_cache = {}
        self.preflop_ranges = self.initialize_preflop_ranges()
        self.bluff_freq = 0.2  # Base bluffing frequency - will be adjusted
    
    def initialize_preflop_ranges(self):
        """Initialize preflop hand ranges by position"""
        # Premium hands (play from any position)
        premium = ['AA', 'KK', 'QQ', 'JJ', 'AKs', 'AK']
        
        # Strong hands (play from middle to late position)
        strong = ['TT', '99', '88', 'AQs', 'AQ', 'AJs', 'AJ', 'KQs', 'KJs']
        
        # Playable hands (mostly play from late position)
        playable = ['77', '66', '55', 'A9s+', 'KTs+', 'QJs', 'JTs', 'T9s', '98s']
        
        # Speculative hands (play from late position or with good pot odds)
        speculative = ['44', '33', '22', 'A8s-A2s', 'K9s-K2s', 'Q9s-Q2s', 'J9s-J2s']
        
        # Position-based ranges (early = tight, late = looser)
        return {
            'early': premium,
            'middle': premium + strong,
            'late': premium + strong + playable,
            'button': premium + strong + playable + speculative
        }
    
    def determine_position(self, dealer_btn, my_position, total_players):
        """Determine position relative to the dealer button"""
        positions_from_button = (my_position - dealer_btn) % total_players
        
        # Early position
        if positions_from_button < total_players * 0.33:
            return 'early'
        # Middle position
        elif positions_from_button < total_players * 0.66:
            return 'middle'
        # Button
        elif positions_from_button == total_players - 1:
            return 'button'
        # Late position
        else:
            return 'late'
    
    def declare_action(self, valid_actions, hole_card, round_state):
        """GTO-based decision making for poker actions"""
        # Start timing for performance monitoring
        start_time = time.time()
        
        # Parse game state
        community_card = round_state['community_card']
        street = round_state['street']
        pot = round_state['pot']['main']['amount']
        dealer_btn = round_state['dealer_btn']
        next_player = round_state['next_player']
        seats = round_state['seats']
        action_histories = round_state['action_histories']
        
        # Find our position and ID
        my_seat = next((seat for seat in seats if seat['uuid'] == self.uuid), None)
        if not my_seat:
            for seat in seats:
                if seat['name'] == self.__class__.__name__:
                    self.uuid = seat['uuid']
                    my_seat = seat
                    break
        
        my_position = seats.index(my_seat)
        total_players = len(seats)
        position_type = self.determine_position(dealer_btn, my_position, total_players)
        
        # Parse valid actions and their limits
        fold_action = valid_actions[0]
        call_action = valid_actions[1]
        call_amount = call_action['amount']
        
        # Determine if we can raise
        can_raise = len(valid_actions) > 2
        min_raise, max_raise = 0, 0
        if can_raise:
            min_raise = valid_actions[2]['amount']['min']
            max_raise = valid_actions[2]['amount']['max']
        
        # Choose action based on game state
        action, amount = self.choose_action(
            hole_card, community_card, street, pot, call_amount,
            min_raise, max_raise, can_raise, position_type,
            action_histories, seats, valid_actions
        )
        
        # Performance monitoring
        end_time = time.time()
        decision_time = end_time - start_time
        if decision_time > 0.1:  # Log slow decisions for optimization
            print(f"WARNING: Decision took {decision_time:.3f} seconds")
        
        return action, amount
    
    def choose_action(self, hole_card, community_card, street, pot, call_amount, 
                      min_raise, max_raise, can_raise, position_type,
                      action_histories, seats, valid_actions):
        """Core GTO decision logic for selecting poker actions"""
        # Convert hole cards to a more usable format
        hand_cards = [self.parse_card(card) for card in hole_card]
        community = [self.parse_card(card) for card in community_card]
        
        # Preflop strategy
        if street == 'preflop':
            return self.preflop_strategy(hand_cards, position_type, call_amount, min_raise, max_raise, can_raise, action_histories, pot, valid_actions)
        
        # Postflop strategy (flop, turn, river)
        else:
            return self.postflop_strategy(hand_cards, community, street, pot, call_amount, min_raise, max_raise, can_raise, action_histories, valid_actions)
    
    def preflop_strategy(self, hand_cards, position_type, call_amount, min_raise, max_raise, can_raise, action_histories, pot, valid_actions):
        """Preflop GTO strategy based on position and hand strength"""
        # Calculate hand strength for preflop
        hand_rank = self.get_preflop_hand_rank(hand_cards)
        hand_percentile = hand_rank / 169.0  # Normalize to 0-1 range (169 possible starting hands)
        
        # Check if we've seen a raise or 3-bet
        has_raise = False
        has_three_bet = False
        if 'preflop' in action_histories:
            for action in action_histories['preflop']:
                if action['action'] == 'RAISE':
                    has_raise = True
                    if has_raise:  # Second raise would be a 3-bet
                        has_three_bet = True
                        break
        
        # No one has raised yet - we can open
        if not has_raise:
            # Open raising strategy based on position
            if hand_percentile > (0.85 - 0.15 * self.position_value(position_type)):
                if can_raise:
                    raise_amount = min(max_raise, pot * 3)  # Standard open is 3x pot
                    return self.do_raise(valid_actions, raise_amount)
            
            # Limping strategy (mostly avoid except in late position with speculative hands)
            if position_type in ['button', 'late'] and hand_percentile > 0.4:
                return self.do_call(valid_actions)
            
            # Fold weak hands
            if hand_percentile < 0.3:
                return self.do_fold(valid_actions)
            
            # Call with medium strength hands
            return self.do_call(valid_actions)
        
        # Facing a raise - consider 3-betting or calling
        elif has_raise and not has_three_bet:
            # Strong hand - 3-bet for value
            if hand_percentile > 0.9:
                if can_raise:
                    raise_amount = min(max_raise, min_raise * 3)
                    return self.do_raise(valid_actions, raise_amount)
            
            # Medium-strong hand or position advantage - call
            if hand_percentile > (0.7 - 0.1 * self.position_value(position_type)):
                return self.do_call(valid_actions)
            
            # Bluff 3-bet with select hands based on position
            if hand_percentile > 0.5 and random.random() < self.bluff_freq * self.position_value(position_type):
                if can_raise:
                    raise_amount = min(max_raise, min_raise * 2.5)
                    return self.do_raise(valid_actions, raise_amount)
            
            # Fold weak hands
            return self.do_fold(valid_actions)
        
        # Facing a 3-bet - consider 4-betting or calling
        else:
            # Very strong hand - 4-bet for value
            if hand_percentile > 0.95:
                if can_raise:
                    raise_amount = min(max_raise, min_raise * 2.5)
                    return self.do_raise(valid_actions, raise_amount)
            
            # Strong hand - call the 3-bet
            if hand_percentile > 0.85:
                return self.do_call(valid_actions)
            
            # Occasional bluff 4-bet
            if hand_percentile > 0.6 and random.random() < self.bluff_freq * 0.5:
                if can_raise:
                    raise_amount = min(max_raise, min_raise * 2.5)
                    return self.do_raise(valid_actions, raise_amount)
            
            # Fold everything else to a 3-bet
            return self.do_fold(valid_actions)
    
    def postflop_strategy(self, hand_cards, community, street, pot, call_amount, min_raise, max_raise, can_raise, action_histories, valid_actions):
        """Postflop GTO strategy combining hand strength, equity, and strategic considerations"""
        # Calculate hand strength and potential
        hand_strength = self.evaluate_hand_strength(hand_cards, community)
        pot_odds = call_amount / (pot + call_amount)
        
        # Determine if we're facing aggression in this street
        facing_aggression = False
        if street in action_histories:
            for action in action_histories[street]:
                if action['action'] in ['RAISE', 'BET'] and action['uuid'] != self.uuid:
                    facing_aggression = True
                    break
        
        # Calculate our equity against likely opponent ranges
        hand_equity = self.estimate_equity(hand_cards, community, street)
        
        # Calculate implied odds and reverse implied odds
        implied_odds_factor = self.calculate_implied_odds_factor(street, hand_cards, community)
        reverse_implied_odds = 1.0 - implied_odds_factor
        
        # Adjust equity based on implied odds
        adjusted_equity = hand_equity * implied_odds_factor
        
        # Determine if this is a check-around situation (no bets on this street)
        check_around = True
        if street in action_histories:
            for action in action_histories[street]:
                if action['action'] in ['RAISE', 'BET']:
                    check_around = False
                    break
        
        # Strategy when we're facing aggression
        if facing_aggression:
            # Call when we have good odds and equity
            if adjusted_equity > pot_odds + 0.05:
                # Sometimes raise for value with strong hands
                if hand_strength > 0.8 and can_raise:
                    # Size raise based on board texture and hand strength
                    raise_size = self.calculate_optimal_raise_size(pot, min_raise, max_raise, hand_strength, street)
                    return self.do_raise(valid_actions, raise_size)
                return self.do_call(valid_actions)
            
            # Bluff raise with certain hands that have potential
            if not check_around and can_raise and self.should_bluff(hand_cards, community, hand_strength, hand_equity, street):
                raise_size = min(max_raise, pot * 0.75)
                return self.do_raise(valid_actions, raise_size)
            
            # Call with marginal hands getting close to correct odds
            if adjusted_equity > pot_odds - 0.1 and call_amount < pot * 0.3:
                return self.do_call(valid_actions)
            
            # Fold everything else
            return self.do_fold(valid_actions)
        
        # Strategy when we can be the aggressor
        else:
            # Value bet with strong hands
            if hand_strength > 0.7 and can_raise:
                # Size bet based on board texture and hand strength
                bet_size = self.calculate_optimal_bet_size(pot, min_raise, max_raise, hand_strength, street)
                return self.do_raise(valid_actions, bet_size)
            
            # Semi-bluff with drawing hands
            if self.has_draw(hand_cards, community) and can_raise:
                # Smaller bet for semi-bluffs
                bet_size = min(max_raise, pot * 0.5)
                return self.do_raise(valid_actions, bet_size)
            
            # Bluff on favorable boards with position
            if self.is_good_bluff_spot(community, street, action_histories) and can_raise:
                bet_size = min(max_raise, pot * 0.6)
                return self.do_raise(valid_actions, bet_size)
            
            # Check with everything else
            return self.do_call(valid_actions)
    
    def position_value(self, position_type):
        """Return a numerical value for position advantage"""
        position_values = {
            'early': 0.2,
            'middle': 0.5,
            'late': 0.8,
            'button': 1.0
        }
        return position_values.get(position_type, 0.5)
    
    def calculate_optimal_bet_size(self, pot, min_raise, max_raise, hand_strength, street):
        """Calculate the optimal bet size based on hand strength and board texture"""
        # Larger bets with stronger hands and on later streets
        street_multiplier = {
            'flop': 0.6,
            'turn': 0.75,
            'river': 0.9
        }
        
        # Scale bet size by pot and hand strength
        base_size = pot * street_multiplier.get(street, 0.7)
        strength_adjustment = base_size * (hand_strength - 0.5) * 0.5
        
        bet_size = base_size + strength_adjustment
        
        # Ensure bet is within valid range
        return max(min_raise, min(max_raise, bet_size))
    
    def calculate_optimal_raise_size(self, pot, min_raise, max_raise, hand_strength, street):
        """Calculate the optimal raise size based on hand strength and street"""
        # Similar to bet sizing but larger to account for already being raised
        street_multiplier = {
            'flop': 0.8,
            'turn': 1.0,
            'river': 1.2
        }
        
        base_size = pot * street_multiplier.get(street, 1.0)
        strength_adjustment = base_size * (hand_strength - 0.5) * 0.8
        
        raise_size = base_size + strength_adjustment
        
        # Ensure raise is within valid range
        return max(min_raise, min(max_raise, raise_size))
    
    def should_bluff(self, hand_cards, community, hand_strength, hand_equity, street):
        """Determine if this is a good spot to bluff"""
        # More likely to bluff on early streets
        street_bluff_threshold = {
            'flop': 0.15,
            'turn': 0.2,
            'river': 0.3
        }
        
        threshold = street_bluff_threshold.get(street, 0.2)
        
        # Consider bluffing with hands that have backdoor potential
        if hand_equity > hand_strength + 0.1:
            threshold -= 0.1
        
        # Check if we have good blockers
        if self.has_good_blockers(hand_cards, community):
            threshold -= 0.05
        
        # Randomize bluffing to be unpredictable
        return random.random() < self.bluff_freq and hand_strength < threshold
    
    def has_good_blockers(self, hand_cards, community):
        """Check if we have cards that block strong hands our opponent might have"""
        # Look for aces that block top pair, nuts flush draws, etc.
        for card in hand_cards:
            if card[1] == 14:  # Ace
                return True
            
            # If there's a possible straight on board, check if we block it
            if self.blocks_straight(card, community):
                return True
            
            # If there's a possible flush on board, check if we block it
            if self.blocks_flush(card, community):
                return True
        
        return False
    
    def blocks_straight(self, card, community):
        """Check if our card blocks a potential straight"""
        if len(community) < 3:
            return False
            
        ranks = [c[1] for c in community] + [card[1]]
        ranks.sort()
        
        # Check for 3 consecutive cards
        for i in range(len(ranks) - 2):
            if ranks[i] + 1 == ranks[i+1] and ranks[i+1] + 1 == ranks[i+2]:
                return True
                
        return False
    
    def blocks_flush(self, card, community):
        """Check if our card blocks a potential flush"""
        if len(community) < 3:
            return False
            
        suit_counts = [0, 0, 0, 0]
        for c in community:
            suit_counts[c[0]] += 1
            
        # Check if we have a card of the same suit as a potential flush
        return suit_counts[card[0]] >= 2
    
    def has_draw(self, hand_cards, community):
        """Check if we have a strong drawing hand"""
        if len(community) < 3:
            return False
            
        # Check for flush draw
        if self.has_flush_draw(hand_cards, community):
            return True
            
        # Check for open-ended or gutshot straight draw
        if self.has_straight_draw(hand_cards, community):
            return True
            
        # Check for two overcards
        if self.has_overcards(hand_cards, community):
            return True
            
        return False
    
    def has_flush_draw(self, hand_cards, community):
        """Check if we have a flush draw"""
        suit_counts = [0, 0, 0, 0]
        
        # Count suits in our hand
        for card in hand_cards:
            suit_counts[card[0]] += 1
            
        # Count suits on the board
        for card in community:
            suit_counts[card[0]] += 1
            
        # Check if we have 4 cards of any suit (need 1 more for a flush)
        return max(suit_counts) >= 4
    
    def has_straight_draw(self, hand_cards, community):
        """Check if we have an open-ended or gutshot straight draw"""
        all_cards = hand_cards + community
        ranks = sorted([card[1] for card in all_cards])
        
        # Count consecutive ranks
        consecutive = 1
        max_consecutive = 1
        for i in range(1, len(ranks)):
            if ranks[i] == ranks[i-1] + 1:
                consecutive += 1
                max_consecutive = max(max_consecutive, consecutive)
            elif ranks[i] != ranks[i-1]:  # Skip duplicate ranks
                consecutive = 1
                
        # Open-ended draw (4 consecutive cards)
        if max_consecutive >= 4:
            return True
            
        # Check for gutshot (3 consecutive with a gap)
        for i in range(len(ranks) - 3):
            if ranks[i+3] - ranks[i] == 4:  # There's exactly one gap
                return True
                
        return False
    
    def has_overcards(self, hand_cards, community):
        """Check if we have two overcards to the board"""
        if len(community) == 0:
            return False
            
        board_high = max([card[1] for card in community])
        overcard_count = sum(1 for card in hand_cards if card[1] > board_high)
        
        return overcard_count >= 2
    
    def is_good_bluff_spot(self, community, street, action_histories):
        """Identify good spots to bluff based on board texture and history"""
        # More likely to bluff on certain board textures
        if self.is_dry_board(community):
            bluff_chance = 0.3
        else:
            bluff_chance = 0.15
            
        # More likely to bluff if we've shown strength before
        if self.has_shown_strength(action_histories):
            bluff_chance += 0.1
            
        # Adjust based on street
        if street == 'river':
            bluff_chance += 0.05
            
        return random.random() < bluff_chance
    
    def is_dry_board(self, community):
        """Check if the board is dry (disconnected, no obvious draws)"""
        if len(community) < 3:
            return True
            
        # Check for flush possibilities
        suit_counts = [0, 0, 0, 0]
        for card in community:
            suit_counts[card[0]] += 1
        if max(suit_counts) >= 3:
            return False
            
        # Check for straight possibilities
        ranks = sorted([card[1] for card in community])
        for i in range(len(ranks) - 2):
            if ranks[i+2] - ranks[i] <= 4:  # Three cards within 4 ranks
                return False
                
        # No paired cards on board
        if len(set(ranks)) < len(ranks):
            return False
            
        return True
    
    def has_shown_strength(self, action_histories):
        """Check if we've shown strength in previous streets"""
        for street in ['preflop', 'flop', 'turn']:
            if street in action_histories:
                for action in action_histories[street]:
                    if action['uuid'] == self.uuid and action['action'] in ['RAISE', 'BET']:
                        return True
        return False
    
    def calculate_implied_odds_factor(self, street, hand_cards, community):
        """Calculate implied odds factor based on hand potential"""
        # Base factor
        factor = 1.0
        
        # Drawing hands have better implied odds
        if self.has_draw(hand_cards, community):
            factor += 0.2
            
        # Set mining has good implied odds
        if self.has_pocket_pair(hand_cards) and len(community) >= 3:
            board_ranks = [card[1] for card in community]
            if hand_cards[0][1] not in board_ranks:
                factor += 0.2
                
        # Adjust based on street (implied odds are lower on later streets)
        street_adjustment = {
            'flop': 0.0,
            'turn': -0.1,
            'river': -0.3
        }
        factor += street_adjustment.get(street, 0.0)
        
        # Cap the factor
        return max(0.8, min(1.5, factor))
    
    def has_pocket_pair(self, hand_cards):
        """Check if we have a pocket pair"""
        return len(hand_cards) == 2 and hand_cards[0][1] == hand_cards[1][1]
    
    def get_preflop_hand_rank(self, hand_cards):
        """Evaluate preflop hand strength (1-169, lower is better)"""
        if len(hand_cards) != 2:
            return 169  # Worst rank
            
        rank1, rank2 = hand_cards[0][1], hand_cards[1][1]
        suited = hand_cards[0][0] == hand_cards[1][0]
        
        # Make sure rank1 >= rank2
        if rank1 < rank2:
            rank1, rank2 = rank2, rank1
            
        # Preflop hand rankings (approximated)
        if rank1 == rank2:  # Pocket pairs
            return 14 - rank1 + 1
        elif suited:  # Suited cards
            if rank1 == 14:  # Ax suited
                return 20 + (14 - rank2)
            return 30 + (rank1 * 13 + rank2) / 20
        else:  # Offsuit
            if rank1 == 14:  # Ax offsuit
                return 50 + (14 - rank2)
            return 70 + (rank1 * 13 + rank2) / 15
    
    def evaluate_hand_strength(self, hand_cards, community):
        """Evaluate the current hand strength (0-1 scale)"""
        if not community:
            # Use preflop rankings if no community cards
            return 1 - (self.get_preflop_hand_rank(hand_cards) / 169.0)
            
        # Cache key for performance
        cache_key = (tuple(sorted((c[0], c[1]) for c in hand_cards)),
                     tuple(sorted((c[0], c[1]) for c in community)))
                     
        if cache_key in self.hand_strength_cache:
            return self.hand_strength_cache[cache_key]
            
        # Calculate hand type and rank
        hand_type, hand_rank = self.get_hand_rank(hand_cards + community)
        
        # Normalize to 0-1 scale
        max_rank = 7462  # Total number of distinct poker hands
        normalized_strength = hand_rank / max_rank
        
        # Cache result
        self.hand_strength_cache[cache_key] = normalized_strength
        return normalized_strength
    
    def get_hand_rank(self, cards):
        """
        Simplified hand rank evaluation
        Returns (hand_type, hand_rank) where:
        - hand_type: 0=High Card, 1=Pair, 2=Two Pair, 3=Three of a Kind,
                    4=Straight, 5=Flush, 6=Full House, 7=Four of a Kind, 8=Straight Flush
        - hand_rank: Numerical rank of the hand within its type
        """
        if len(cards) < 5:
            return (0, 0)  # Not enough cards for a full hand
            
        # Take best 5 cards
        best_cards = self.get_best_five_cards(cards)
        
        # Count ranks and suits
        rank_count = defaultdict(int)
        suit_count = defaultdict(int)
        for card in best_cards:
            rank_count[card[1]] += 1
            suit_count[card[0]] += 1
            
        # Check for flush
        flush = max(suit_count.values()) >= 5
        
        # Check for straight
        ranks = sorted(set(card[1] for card in best_cards), reverse=True)
        straight = False
        for i in range(len(ranks) - 4):
            if ranks[i] - ranks[i+4] == 4:
                straight = True
                straight_high = ranks[i]
                break
                
        # Special case for A-5 straight
        if not straight and 14 in ranks and set([2, 3, 4, 5, 14]).issubset(set(ranks)):
            straight = True
            straight_high = 5
            
        # Determine hand type
        pairs = sum(1 for count in rank_count.values() if count == 2)
        trips = sum(1 for count in rank_count.values() if count == 3)
        quads = sum(1 for count in rank_count.values() if count == 4)
        
        # Straight flush
        if straight and flush:
            return (8, straight_high)
            
        # Four of a kind
        if quads:
            quad_rank = next(rank for rank, count in rank_count.items() if count == 4)
            kicker = next(rank for rank, count in rank_count.items() if count == 1 and rank != quad_rank)
            return (7, quad_rank * 15 + kicker)
            
        # Full house
        if trips and pairs or trips >= 2:
            trip_rank = max(rank for rank, count in rank_count.items() if count >= 3)
            pair_candidates = [rank for rank, count in rank_count.items() if count >= 2 and rank != trip_rank]
            if pair_candidates:
                pair_rank = max(pair_candidates)
            else:
                pair_rank = 0
            return (6, trip_rank * 15 + pair_rank)
            
        # Flush
        if flush:
            flush_ranks = sorted([card[1] for card in best_cards if suit_count[card[0]] >= 5], reverse=True)[:5]
            return (5, sum(r * (15 ** i) for i, r in enumerate(flush_ranks)))
            
        # Straight
        if straight:
            return (4, straight_high)
            
        # Three of a kind
        if trips:
            trip_rank = next(rank for rank, count in rank_count.items() if count == 3)
            kickers = sorted([rank for rank, count in rank_count.items() if count == 1], reverse=True)[:2]
            return (3, trip_rank * 15**2 + kickers[0] * 15 + kickers[1])
            
        # Two pair
        if pairs >= 2:
            pair_ranks = sorted([rank for rank, count in rank_count.items() if count == 2], reverse=True)[:2]
            kicker = next(rank for rank, count in rank_count.items() if count == 1)
            return (2, pair_ranks[0] * 15**2 + pair_ranks[1] * 15 + kicker)
            
        # One pair
        if pairs:
            pair_rank = next(rank for rank, count in rank_count.items() if count == 2)
            kickers = sorted([rank for rank, count in rank_count.items() if count == 1], reverse=True)[:3]
            return (1, pair_rank * 15**3 + kickers[0] * 15**2 + kickers[1] * 15 + kickers[2])
            
        # High card
        ranks = sorted([card[1] for card in best_cards], reverse=True)[:5]
        return (0, sum(r * (15 ** i) for i, r in enumerate(ranks)))
    
    def get_best_five_cards(self, cards):
        """Select the best 5 cards from the available cards"""
        if len(cards) <= 5:
            return cards
            
        # Generate all 5-card combinations
        best_rank = (-1, -1)
        best_hand = None
        
        # Optimization: instead of generating all combinations, prioritize by rank counts
        rank_count = defaultdict(int)
        for card in cards:
            rank_count[card[1]] += 1
            
        # Sort cards by rank frequency (descending) and then by rank (descending)
        sorted_cards = sorted(cards, key=lambda c: (rank_count[c[1]], c[1]), reverse=True)
        
        # Always include high-frequency cards first
        high_freq_cards = [c for c in sorted_cards if rank_count[c[1]] >= 2]
        
        # If we have <= 5 high-frequency cards, fill with highest remaining cards
        if len(high_freq_cards) <= 5:
            remaining = [c for c in sorted_cards if c not in high_freq_cards]
            candidate = high_freq_cards + remaining[:5-len(high_freq_cards)]
            return candidate[:5]
            
        # Otherwise, need to find best combination
        # This is simplified - full implementation would check all valid 5-card hands
        return sorted_cards[:5]
    
    def estimate_equity(self, hole_cards, community, street):
        """Estimate our equity (probability of winning) against opponent ranges"""
        # Simplified Monte Carlo simulation for equity calculation
        # Performance optimization: only run a limited number of simulations
        num_simulations = 100 if street == 'flop' else 50 if street == 'turn' else 20
        
        wins = 0
        
        for _ in range(num_simulations):
            # Create a deck excluding our cards and community cards
            deck = [(suit, rank) for suit in range(4) for rank in range(2, 15)]
            deck = [card for card in deck if card not in hole_cards and card not in community]
            
            # Randomly complete the board
            remaining_community = 5 - len(community)
            if remaining_community > 0:
                sim_community = community + random.sample(deck, remaining_community)
                deck = [card for card in deck if card not in sim_community]
            else:
                sim_community = community
            
            # Generate random opponent hand
            opponent_hole = random.sample(deck, 2)
            
            # Evaluate our hand vs opponent hand
            our_hand_type, our_hand_rank = self.get_hand_rank(hole_cards + sim_community)
            opp_hand_type, opp_hand_rank = self.get_hand_rank(opponent_hole + sim_community)
            
            if (our_hand_type, our_hand_rank) > (opp_hand_type, opp_hand_rank):
                wins += 1
            elif (our_hand_type, our_hand_rank) == (opp_hand_type, opp_hand_rank):
                wins += 0.5  # Split pot
                
        return wins / num_simulations
    
    def parse_card(self, card_str):
        """Parse card string (e.g., 'AS' for Ace of Spades) to (suit, rank) tuple"""
        if len(card_str) != 2:
            raise ValueError(f"Invalid card format: {card_str}")
            
        rank_char = card_str[0]
        suit_char = card_str[1]
        
        rank = CARD_RANKS.get(rank_char)
        suit = CARD_SUITS.get(suit_char)
        
        if rank is None or suit is None:
            raise ValueError(f"Invalid card: {card_str}")
            
        return (suit, rank)
    
    # Helper functions for poker actions
    def do_fold(self, valid_actions):
        action_info = valid_actions[0]
        amount = action_info["amount"]
        return action_info['action'], amount

    def do_call(self, valid_actions):
        action_info = valid_actions[1]
        amount = action_info["amount"]
        return action_info['action'], amount
    
    def do_raise(self, valid_actions, raise_amount):
        action_info = valid_actions[2]
        amount = max(action_info['amount']['min'], raise_amount)
        # Ensure the amount doesn't exceed the maximum
        amount = min(amount, action_info['amount']['max'])
        return action_info['action'], amount
    
    def do_all_in(self, valid_actions):
        action_info = valid_actions[2]
        amount = action_info['amount']['max']
        return action_info['action'], amount
    
    # Game state tracking methods
    def receive_game_start_message(self, game_info):
        self.player_num = game_info["player_num"]
        self.max_round = game_info["rule"]["max_round"]
        self.small_blind_amount = game_info["rule"]["small_blind_amount"]
        self.ante_amount = game_info["rule"]["ante"]
        self.blind_structure = game_info["rule"]["blind_structure"]
        
        # Reset statistics for new game
        self.hand_history = []
        self.player_stats = defaultdict(lambda: {
            'vpip': 0, 'pfr': 0, 'total_hands': 0, 
            'fold_to_3bet': 0, '3bet_opportunities': 0,
            'aggression_factor': 0, 'cont_bet': 0, 'cont_bet_opps': 0
        })
        
        # Adjust bluffing frequency based on tournament stage
        if self.max_round > 0:
            stage = 0  # Early
            self.bluff_freq = 0.15  # More conservative early
        else:
            self.bluff_freq = 0.2  # Default

    def receive_round_start_message(self, round_count, hole_card, seats):
        # Track our starting stack
        for seat in seats:
            if seat['uuid'] == self.uuid:
                self.starting_stack = seat['stack']
                break
                
        # Clear per-hand cache
        self.hand_strength_cache = {}

    def receive_street_start_message(self, street, round_state):
        # We could track board development here if needed
        pass

    def receive_game_update_message(self, action, round_state):
        # Track player actions to build profiles
        if action['player_uuid'] != self.uuid:
            action_type = action['action']
            player_id = action['player_uuid']
            
            if action_type == 'RAISE' and round_state['street'] == 'preflop':
                self.player_stats[player_id]['pfr'] += 1
                
            if action_type in ['CALL', 'RAISE'] and round_state['street'] == 'preflop':
                self.player_stats[player_id]['vpip'] += 1
                
            # Update total hands for each player
            self.player_stats[player_id]['total_hands'] += 1

    def receive_round_result_message(self, winners, hand_info, round_state):
        # Store hand history
        self.hand_history.append({
            'winners': winners,
            'hand_info': hand_info
        })
        
        # Adjust strategy based on results
        # In GTO, we don't adjust based on results, but we could track stats here
        
        # Periodically adjust bluffing frequency
        if len(self.hand_history) % 10 == 0:
            # Slight random adjustment to avoid being predictable
            self.bluff_freq = max(0.1, min(0.3, self.bluff_freq + random.uniform(-0.05, 0.05)))