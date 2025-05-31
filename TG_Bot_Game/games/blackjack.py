import random
from typing import List, Dict, Tuple
from config import MIN_BLACKJACK_BET

# Карты
SUITS = ['♠️', '♥️', '♣️', '♦️']
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']

class Card:
    def __init__(self, suit: str, rank: str):
        self.suit = suit
        self.rank = rank
    
    def __str__(self) -> str:
        return f"{self.rank}{self.suit}"
    
    def value(self) -> int:
        if self.rank in ['J', 'Q', 'K']:
            return 10
        elif self.rank == 'A':
            return 11
        return int(self.rank)

class Deck:
    def __init__(self):
        self.cards = [Card(suit, rank) for suit in SUITS for rank in RANKS]
        random.shuffle(self.cards)
    
    def draw(self) -> Card:
        return self.cards.pop()

class Player:
    def __init__(self, user_id: int, bet: int):
        self.user_id = user_id
        self.bet = bet
        self.hand: List[Card] = []
        self.is_standing = False
    
    def add_card(self, card: Card):
        self.hand.append(card)
    
    def get_score(self) -> int:
        score = sum(card.value() for card in self.hand)
        aces = sum(1 for card in self.hand if card.rank == 'A')
        
        # Корректировка для тузов
        while score > 21 and aces > 0:
            score -= 10
            aces -= 1
        
        return score
    
    def is_bust(self) -> bool:
        return self.get_score() > 21

class BlackjackGame:
    def __init__(self):
        self.deck = Deck()
        self.players: Dict[int, Player] = {}
        self.dealer = Player(0, 0)  # Дилер с ID 0
    
    def add_player(self, user_id: int, bet: int) -> bool:
        """Добавить игрока в игру"""
        if bet < MIN_BLACKJACK_BET:
            return False
        if len(self.players) >= 4:  # Максимум 4 игрока
            return False
        if user_id in self.players:
            return False
        
        self.players[user_id] = Player(user_id, bet)
        return True
    
    def start_game(self) -> bool:
        """Начать игру"""
        if not self.players:
            return False
        
        # Раздача начальных карт
        for _ in range(2):
            for player in self.players.values():
                player.add_card(self.deck.draw())
            self.dealer.add_card(self.deck.draw())
        
        return True
    
    def hit(self, user_id: int) -> Tuple[bool, str]:
        """Взять карту"""
        if user_id not in self.players:
            return False, "Игрок не найден"
        
        player = self.players[user_id]
        if player.is_standing:
            return False, "Игрок уже остановился"
        
        player.add_card(self.deck.draw())
        
        if player.is_bust():
            player.is_standing = True
            return True, "Перебор!"
        
        return True, f"Текущий счет: {player.get_score()}"
    
    def stand(self, user_id: int) -> bool:
        """Остановиться"""
        if user_id not in self.players:
            return False
        
        self.players[user_id].is_standing = True
        return True
    
    def is_game_over(self) -> bool:
        """Проверить, закончена ли игра"""
        return all(player.is_standing for player in self.players.values())
    
    def finish_game(self) -> Dict[int, int]:
        """Завершить игру и определить победителей"""
        if not self.is_game_over():
            return {}
        
        # Дилер берет карты, пока не достигнет 17
        while self.dealer.get_score() < 17:
            self.dealer.add_card(self.deck.draw())
        
        dealer_score = self.dealer.get_score()
        results = {}
        
        for player in self.players.values():
            player_score = player.get_score()
            
            if player.is_bust():
                results[player.user_id] = -player.bet
            elif dealer_score > 21:
                results[player.user_id] = player.bet
            elif player_score > dealer_score:
                results[player.user_id] = player.bet
            elif player_score < dealer_score:
                results[player.user_id] = -player.bet
            else:
                results[player.user_id] = 0  # Ничья
        
        return results 