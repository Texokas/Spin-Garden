import random
from typing import Dict, List, Tuple
from config import MIN_ROULETTE_BET, ROULETTE_MULTIPLIERS

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
        if self.amount < MIN_ROULETTE_BET:
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
    def __init__(self):
        self.bets: Dict[int, List[Bet]] = {}  # user_id -> list of bets
    
    def place_bet(self, user_id: int, bet: Bet) -> bool:
        """Сделать ставку"""
        if not bet.is_valid():
            return False
        
        if user_id not in self.bets:
            self.bets[user_id] = []
        
        self.bets[user_id].append(bet)
        return True
    
    def spin(self) -> Tuple[int, Dict[int, int]]:
        """Крутить рулетку и определить выигрыши"""
        if not self.bets:
            return 0, {}
        
        # Выпадение числа
        number = random.choice(NUMBERS)
        
        # Определение характеристик выпавшего числа
        is_red = number in RED_NUMBERS
        is_black = number in BLACK_NUMBERS
        is_even = number % 2 == 0 and number != 0
        is_odd = number % 2 == 1
        
        # Определение дюжины и колонки
        dozen = None
        column = None
        if number > 0:
            for d, nums in DOZENS.items():
                if number in nums:
                    dozen = d
                    break
            for c, nums in COLUMNS.items():
                if number in nums:
                    column = c
                    break
        
        # Расчет выигрышей
        results = {}
        for user_id, user_bets in self.bets.items():
            total_win = 0
            for bet in user_bets:
                win = 0
                
                if bet.bet_type == 'number' and int(bet.value) == number:
                    win = bet.amount * ROULETTE_MULTIPLIERS['number']
                
                elif bet.bet_type == 'color':
                    if (bet.value == 'red' and is_red) or (bet.value == 'black' and is_black):
                        win = bet.amount * ROULETTE_MULTIPLIERS['red_black']
                
                elif bet.bet_type == 'even_odd':
                    if (bet.value == 'even' and is_even) or (bet.value == 'odd' and is_odd):
                        win = bet.amount * ROULETTE_MULTIPLIERS['even_odd']
                
                elif bet.bet_type == 'dozen' and bet.value == dozen:
                    win = bet.amount * ROULETTE_MULTIPLIERS['dozen']
                
                elif bet.bet_type == 'column' and bet.value == column:
                    win = bet.amount * ROULETTE_MULTIPLIERS['column']
                
                total_win += win
            
            results[user_id] = total_win
        
        # Очистка ставок
        self.bets.clear()
        
        return number, results
    
    def get_number_color(self, number: int) -> str:
        """Получить цвет числа"""
        if number == 0:
            return 'green'
        return 'red' if number in RED_NUMBERS else 'black'
    
    def get_number_dozen(self, number: int) -> str:
        """Получить дюжину числа"""
        if number == 0:
            return None
        for dozen, numbers in DOZENS.items():
            if number in numbers:
                return dozen
        return None
    
    def get_number_column(self, number: int) -> str:
        """Получить колонку числа"""
        if number == 0:
            return None
        for column, numbers in COLUMNS.items():
            if number in numbers:
                return column
        return None 