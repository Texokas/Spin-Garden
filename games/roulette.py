import random
from typing import List, Dict, Tuple, Optional
from config import ROULETTE_MIN_BET, ROULETTE_MULTIPLIERS

# Номера рулетки
NUMBERS = list(range(37))  # 0-36

# Цвета чисел
RED_NUMBERS = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
BLACK_NUMBERS = [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]

# Дюжины
DOZENS = {
    'first': list(range(1, 13)),
    'second': list(range(13, 25)),
    'third': list(range(25, 37))
}

# Колонки
COLUMNS = {
    'first': list(range(1, 37, 3)),
    'second': list(range(2, 37, 3)),
    'third': list(range(3, 37, 3))
}

class Bet:
    def __init__(self, bet_type: str, value: str, amount: int):
        self.bet_type = bet_type
        self.value = value
        self.amount = amount

    def is_valid(self) -> bool:
        """Проверить валидность ставки"""
        if self.amount < ROULETTE_MIN_BET:
            return False
        
        if self.bet_type == 'number':
            try:
                number = int(self.value)
                return 0 <= number <= 36
            except ValueError:
                return False
        
        elif self.bet_type == 'color':
            return self.value in ['red', 'black']
        
        elif self.bet_type == 'even_odd':
            return self.value in ['even', 'odd']
        
        elif self.bet_type == 'dozen':
            return self.value in ['first', 'second', 'third']
        
        elif self.bet_type == 'column':
            return self.value in ['first', 'second', 'third']
        
        return False

class RouletteGame:
    def __init__(self, game_mode: str = "single", room_id: Optional[str] = None, chat_id: Optional[int] = None):
        self.game_mode = game_mode  # "single" или "multi"
        self.players: Dict[int, List[Bet]] = {}  # user_id -> list of bets
        self.game_started = False
        self.waiting_for_players = True
        self.room_id = room_id
        self.chat_id = chat_id
        self.current_number = None
        self.betting_time = True
        
        if game_mode == "single":
            self.max_players = 1
            self.min_players = 1
        else:
            self.max_players = int(room_id.split('_')[2]) if room_id else 6
            self.min_players = self.max_players
    
    def add_player(self, user_id: int, bet: int, username: str = "") -> Tuple[bool, str]:
        """Добавить игрока в игру"""
        if self.game_started:
            return False, "Игра уже началась"
        if len(self.players) >= self.max_players:
            return False, f"Максимальное количество игроков: {self.max_players}"
        if user_id in self.players:
            return False, "Вы уже в игре"
        
        self.players[user_id] = []
        return True, "Игрок добавлен"
    
    def start_game(self) -> Tuple[bool, str]:
        """Начать игру"""
        if len(self.players) < self.min_players:
            return False, f"Необходимо минимум {self.min_players} игроков"
        
        self.game_started = True
        self.waiting_for_players = False
        self.betting_time = True
        return True, "Игра началась"
    
    def place_bet(self, user_id: int, bet: Bet) -> Tuple[bool, str]:
        """Сделать ставку"""
        if not self.game_started:
            return False, "Игра еще не началась"
        if not self.betting_time:
            return False, "Время для ставок истекло"
        
        if user_id not in self.players:
            return False, "Вы не в игре"
        
        if not bet.is_valid():
            return False, "Неверная ставка"
        
        self.players[user_id].append(bet)
        return True, f"Ставка принята: {bet.bet_type} {bet.value} на {bet.amount}"
    
    def spin(self) -> Dict[int, int]:
        """Крутить рулетку и определить выигрыши"""
        if not self.game_started:
            return {}
        self.betting_time = False
        self.current_number = random.choice(NUMBERS)
        results = {}
        for user_id, bets in self.players.items():
            total_win = 0
            for bet in bets:
                if self._is_winning_bet(bet):
                    if bet.bet_type == 'color':
                        multiplier = ROULETTE_MULTIPLIERS.get('color', 2)
                    else:
                        multiplier = ROULETTE_MULTIPLIERS[bet.bet_type]
                    total_win += bet.amount * multiplier
                else:
                    total_win -= bet.amount
            results[user_id] = total_win
        return results
    
    def _is_winning_bet(self, bet: Bet) -> bool:
        """Проверить, выиграла ли ставка"""
        if self.current_number == 0:
            return bet.bet_type == 'number' and int(bet.value) == 0
        
        if bet.bet_type == 'number':
            return int(bet.value) == self.current_number
        
        elif bet.bet_type == 'color':
            if bet.value == 'red':
                return self.current_number in RED_NUMBERS
            else:  # black
                return self.current_number in BLACK_NUMBERS
        
        elif bet.bet_type == 'even_odd':
            if bet.value == 'even':
                return self.current_number is not None and self.current_number % 2 == 0 and self.current_number != 0
            else:  # odd
                return self.current_number is not None and self.current_number % 2 == 1 and self.current_number != 0
        
        elif bet.bet_type == 'dozen':
            return self.current_number in DOZENS[bet.value]
        
        elif bet.bet_type == 'column':
            return self.current_number in COLUMNS[bet.value]
        
        return False
    
    def get_game_state(self) -> str:
        """Получить текущее состояние игры в виде строки"""
        state = []
        
        if self.current_number is not None:
            color = "🔴" if self.current_number in RED_NUMBERS else "⚫" if self.current_number in BLACK_NUMBERS else "🟢"
            state.append(f"Выпало: {color} {self.current_number}")
        else:
            state.append("Рулетка готова к вращению!")
        
        # Добавляем ставки игроков
        for user_id, bets in self.players.items():
            if bets:
                state.append(f"\nИгрок {user_id}:")
                for bet in bets:
                    bet_type_display = {
                        'red': '🔴 Красное',
                        'black': '⚫ Черное',
                        'even': '2️⃣ Четное',
                        'odd': '1️⃣ Нечетное'
                    }.get(bet.value, f"{bet.bet_type} {bet.value}")
                    state.append(f"- {bet_type_display}: {bet.amount}")
        
        return "\n".join(state)
    
    def play(self, bet_type: str) -> Dict:
        """Быстрая игра в рулетку"""
        # Определяем ставку
        bet_amount = ROULETTE_MIN_BET
        bet = None
        if bet_type == "red":
            bet = Bet("color", "red", bet_amount)
        elif bet_type == "black":
            bet = Bet("color", "black", bet_amount)
        elif bet_type == "zero":
            bet = Bet("number", "0", bet_amount)
        elif bet_type == "even":
            bet = Bet("even_odd", "even", bet_amount)
        elif bet_type == "odd":
            bet = Bet("even_odd", "odd", bet_amount)
        if not bet:
            return {"win": False, "error": "Неверный тип ставки"}
        # Крутим рулетку
        self.current_number = random.choice(NUMBERS)
        color = "🔴" if self.current_number in RED_NUMBERS else "⚫" if self.current_number in BLACK_NUMBERS else "🟢"
        # Проверяем выигрыш
        win = self._is_winning_bet(bet)
        if bet.bet_type == 'color':
            multiplier = ROULETTE_MULTIPLIERS.get('color', 2)
        else:
            multiplier = ROULETTE_MULTIPLIERS[bet.bet_type]
        prize = bet_amount * multiplier if win else 0
        return {
            "win": win,
            "number": self.current_number,
            "color": color,
            "bet": bet_amount,
            "prize": prize
        } 