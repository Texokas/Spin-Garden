import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Конфигурация бота
BOT_TOKEN = "8068930998:AAG1Sq1L7agCGL6kmSH6opXKE8zOLl90_-s"

# Настройки базы данных
DATABASE_URL = "sqlite:///casino.db"

# Начальный баланс
INITIAL_BALANCE = 1000

# Настройки игр
SLOTS_MIN_BET = 5
BLACKJACK_MIN_BET = 15
ROULETTE_MIN_BET = 10

# Максимальное количество игроков в блэкджеке
BLACKJACK_MAX_PLAYERS = 6

# Временные интервалы
BLACKJACK_TURN_TIMEOUT = 30  # секунды
ROULETTE_BET_TIMEOUT = 30    # секунды

# Игровые настройки
MAX_BET = 1000

# Ограничения
MAX_GAMES_PER_HOUR = 50
MIN_TIME_BETWEEN_BETS = 5  # секунды

# Множители выигрышей
SLOTS_MULTIPLIER = 5
ROULETTE_MULTIPLIERS = {
    'number': 10,
    'red_black': 2,
    'even_odd': 2,
    'dozen': 3,
    'column': 3
} 