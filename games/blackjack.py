import random
from typing import List, Dict, Tuple, Optional
from config import BLACKJACK_MIN_BET

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
        if not self.cards:
            self.cards = [Card(suit, rank) for suit in SUITS for rank in RANKS]
            random.shuffle(self.cards)
        return self.cards.pop()

class Player:
    def __init__(self, user_id: int, bet: int, username: str = ""):
        self.user_id = user_id
        self.username = username
        self.bet = bet
        self.hand: List[Card] = []
        self.is_standing = False
        self.is_doubled = False
    
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
    
    def has_blackjack(self) -> bool:
        return len(self.hand) == 2 and self.get_score() == 21

class BlackjackGame:
    def __init__(self, game_mode: str = "single", room_id: Optional[str] = None, chat_id: Optional[int] = None):
        self.deck = Deck()
        self.players: Dict[int, Player] = {}
        self.dealer = Player(0, 0, "Дилер")
        self.game_mode = game_mode  # "single" или "multi"
        self.current_player_index = 0
        self.game_started = False
        self.waiting_for_players = True
        self.room_id = room_id
        self.chat_id = chat_id  # ID чата, где началась игра
        
        if game_mode == "single":
            self.max_players = 1
            self.min_players = 1
        else:
            # Определяем максимальное количество игроков из ID комнаты
            # Формат: room_X_Y, где X - номер комнаты, Y - максимальное количество игроков
            self.max_players = int(room_id.split('_')[2]) if room_id else 6
            # Устанавливаем минимальное количество игроков равным максимальному
            self.min_players = self.max_players
    
    def add_player(self, user_id: int, bet: int, username: str = "") -> Tuple[bool, str]:
        """Добавить игрока в игру"""
        if self.game_started:
            return False, "Игра уже началась"
        if bet < BLACKJACK_MIN_BET:
            return False, f"Минимальная ставка: {BLACKJACK_MIN_BET}"
        if len(self.players) >= self.max_players:
            return False, f"Максимальное количество игроков: {self.max_players}"
        if user_id in self.players:
            return False, "Вы уже в игре"
        
        self.players[user_id] = Player(user_id, bet, username)
        return True, "Игрок добавлен"
    
    def start_game(self) -> Tuple[bool, str]:
        """Начать игру"""
        if len(self.players) < self.min_players:
            return False, f"Необходимо минимум {self.min_players} игроков"
        
        self.game_started = True
        self.waiting_for_players = False
        
        # Раздача начальных карт игрокам
        for _ in range(2):
            for player in self.players.values():
                player.add_card(self.deck.draw())
        
        # Раздача карт дилеру с проверкой на высокие значения
        while True:
            # Очищаем руку дилера перед новой попыткой
            self.dealer.hand = []
            # Раздаем две карты дилеру
            for _ in range(2):
                self.dealer.add_card(self.deck.draw())
            # Проверяем, что у дилера не слишком высокое значение
            if self.dealer.get_score() < 16:
                break
            # Если значение высокое, возвращаем карты в колоду и перемешиваем
            self.deck.cards.extend(self.dealer.hand)
            random.shuffle(self.deck.cards)
        
        return True, "Игра началась"
    
    def get_current_player(self) -> Optional[Player]:
        """Получить текущего игрока"""
        if not self.players:
            return None
        player_ids = list(self.players.keys())
        return self.players[player_ids[self.current_player_index]]
    
    def next_player(self) -> bool:
        """Перейти к следующему игроку"""
        if not self.players:
            return False
        
        self.current_player_index = (self.current_player_index + 1) % len(self.players)
        return True
    
    def hit(self, user_id: int) -> Tuple[bool, str]:
        """Взять карту"""
        if not self.game_started:
            return False, "Игра еще не началась"
        
        current_player = self.get_current_player()
        if not current_player or current_player.user_id != user_id:
            return False, "Сейчас не ваш ход"
        
        if current_player.is_standing:
            return False, "Вы уже остановились"
        
        current_player.add_card(self.deck.draw())
        
        if current_player.is_bust():
            current_player.is_standing = True
            self.next_player()
            return True, "Перебор!"
        
        return True, f"Текущий счет: {current_player.get_score()}"
    
    def stand(self, user_id: int) -> Tuple[bool, str]:
        """Остановиться"""
        if not self.game_started:
            return False, "Игра еще не началась"
        
        current_player = self.get_current_player()
        if not current_player or current_player.user_id != user_id:
            return False, "Сейчас не ваш ход"
        
        current_player.is_standing = True
        self.next_player()
        return True, "Ход передан следующему игроку"
    
    def double(self, user_id: int) -> Tuple[bool, str]:
        """Удвоить ставку"""
        if not self.game_started:
            return False, "Игра еще не началась"
        
        current_player = self.get_current_player()
        if not current_player or current_player.user_id != user_id:
            return False, "Сейчас не ваш ход"
        
        if len(current_player.hand) != 2:
            return False, "Удвоение возможно только при двух картах"
        
        current_player.bet *= 2
        current_player.is_doubled = True
        current_player.add_card(self.deck.draw())
        current_player.is_standing = True
        self.next_player()
        return True, f"Ставка удвоена. Новый счет: {current_player.get_score()}"
    
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
            if player.has_blackjack():
                results[player.user_id] = int(player.bet * 1.5)  # Блэкджек платит 3:2
            elif player.is_bust() and dealer_score > 21:
                results[player.user_id] = 0  # Оба перебрали — ничья
            elif player.is_bust():
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
    
    def get_game_state(self) -> str:
        """Получить текущее состояние игры в виде строки"""
        state = []
        
        # Добавляем карты дилера
        dealer_cards = " ".join(str(card) for card in self.dealer.hand)
        state.append(f"Дилер: {dealer_cards} (Счет: {self.dealer.get_score()})")
        
        # Добавляем карты игроков
        for player in self.players.values():
            cards = " ".join(str(card) for card in player.hand)
            state.append(f"{player.username}: {cards} (Счет: {player.get_score()}, Ставка: {player.bet})")
        
        # Добавляем информацию о текущем игроке
        current_player = self.get_current_player()
        if current_player:
            state.append(f"\nХод игрока: {current_player.username}")
        
        return "\n".join(state)
    
    def get_room_info(self) -> str:
        """Получить информацию о комнате"""
        return f"Комната {self.room_id}\nИгроков: {len(self.players)}/{self.max_players}" 