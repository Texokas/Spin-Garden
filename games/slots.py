import random
from typing import List, Dict, Tuple, Optional
from config import SLOTS_MIN_BET, SLOTS_MULTIPLIER

# Символы слотов
SYMBOLS = ['🍒', '🍋', '🍊', '🍇', '💎', '7️⃣']

class SlotsGame:
    def __init__(self, game_mode: str = "single", room_id: Optional[str] = None, chat_id: Optional[int] = None):
        self.game_mode = game_mode  # "single" или "multi"
        self.players: Dict[int, int] = {}  # user_id -> bet
        self.game_started = False
        self.waiting_for_players = True
        self.room_id = room_id
        self.chat_id = chat_id
        self.reels: List[List[str]] = [[], [], []]
        
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
        if bet < SLOTS_MIN_BET:
            return False, f"Минимальная ставка: {SLOTS_MIN_BET}"
        if len(self.players) >= self.max_players:
            return False, f"Максимальное количество игроков: {self.max_players}"
        if user_id in self.players:
            return False, "Вы уже в игре"
        
        self.players[user_id] = bet
        return True, "Игрок добавлен"
    
    def start_game(self) -> Tuple[bool, str]:
        """Начать игру"""
        if len(self.players) < self.min_players:
            return False, f"Необходимо минимум {self.min_players} игроков"
        
        self.game_started = True
        self.waiting_for_players = False
        
        # Генерируем случайные символы для каждого барабана
        for i in range(3):
            self.reels[i] = [random.choice(SYMBOLS) for _ in range(3)]
        
        return True, "Игра началась"
    
    def get_win_amount(self, symbols: List[str]) -> int:
        """Рассчитать выигрыш"""
        # Проверяем выигрышные комбинации
        if all(s == '7️⃣' for s in symbols):
            return 10  # Джекпот
        elif all(s == '💎' for s in symbols):
            return 5   # Большой выигрыш
        elif all(s == symbols[0] for s in symbols):
            return 3   # Обычный выигрыш
        elif len(set(symbols)) == 2:
            return 2   # Маленький выигрыш
        return 0      # Проигрыш
    
    def spin(self) -> Dict[int, Tuple[List[str], int]]:
        """Крутить слоты и определить выигрыши"""
        results = {}
        
        for user_id, bet in self.players.items():
            # Выбираем случайную линию из среднего барабана
            line_index = random.randint(0, 2)
            symbols = [reel[line_index] for reel in self.reels]
            
            # Рассчитываем выигрыш
            multiplier = self.get_win_amount(symbols)
            win_amount = bet * multiplier
            
            results[user_id] = (symbols, win_amount)
        
        return results
    
    def get_game_state(self) -> str:
        """Получить текущее состояние игры в виде строки"""
        state = []
        
        # Добавляем барабаны
        state.append("🎰 Слоты:")
        for i in range(3):
            reel = " | ".join(self.reels[i])
            state.append(f"Барабан {i+1}: {reel}")
        
        # Добавляем ставки игроков
        for user_id, bet in self.players.items():
            state.append(f"\nИгрок {user_id}: Ставка {bet}")
        
        return "\n".join(state) 