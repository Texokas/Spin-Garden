import random
from typing import List, Tuple
from config import SLOTS_MULTIPLIER, MIN_SLOTS_BET

# Символы для слотов
SYMBOLS = ['🍒', '🍊', '🍋', '🍇', '7️⃣', '💎']

def spin(bet: int) -> Tuple[List[str], int, bool]:
    """
    Крутить слоты
    
    Args:
        bet: Ставка игрока
        
    Returns:
        Tuple[List[str], int, bool]: (комбинация, выигрыш, успех)
    """
    if bet < MIN_SLOTS_BET:
        return [], 0, False
    
    # Генерация случайной комбинации
    combination = [random.choice(SYMBOLS) for _ in range(3)]
    
    # Проверка выигрыша
    if len(set(combination)) == 1:  # Все символы одинаковые
        win = bet * SLOTS_MULTIPLIER
        return combination, win, True
    
    return combination, 0, True

def get_symbol_value(symbol: str) -> int:
    """Получить стоимость символа"""
    return SYMBOLS.index(symbol) + 1

def calculate_win(combination: List[str], bet: int) -> int:
    """Рассчитать выигрыш"""
    if len(set(combination)) == 1:  # Все символы одинаковые
        return bet * SLOTS_MULTIPLIER
    return 0 