from sqlalchemy.orm import Session
from models import User, Transaction, GameSession, TransactionType
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base
import logging
from contextlib import contextmanager
import traceback

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создание движка базы данных
try:
    engine = create_engine('sqlite:///casino.db', echo=True)
    logger.info("Движок базы данных успешно создан")
except Exception as e:
    logger.error(f"Ошибка при создании движка базы данных: {e}")
    logger.error(traceback.format_exc())
    raise

# Создание фабрики сессий
try:
    SessionLocal = sessionmaker(bind=engine)
    logger.info("Фабрика сессий успешно создана")
except Exception as e:
    logger.error(f"Ошибка при создании фабрики сессий: {e}")
    logger.error(traceback.format_exc())
    raise

def init_db():
    """Инициализация базы данных"""
    try:
        # Создание всех таблиц
        Base.metadata.create_all(engine)
        logger.info("База данных успешно инициализирована")
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        logger.error(traceback.format_exc())
        raise

@contextmanager
def get_db():
    """Получение сессии базы данных"""
    session = SessionLocal()
    try:
        logger.info("Создана новая сессия базы данных")
        yield session
    except Exception as e:
        logger.error(f"Ошибка в сессии базы данных: {e}")
        logger.error(traceback.format_exc())
        session.rollback()
        raise
    finally:
        session.close()
        logger.info("Сессия базы данных закрыта")

def get_user_balance(session: Session, user_id: int) -> int:
    """Получить баланс пользователя"""
    try:
        user = session.query(User).filter(User.user_id == user_id).first()
        balance = user.balance if user else 0
        logger.info(f"Получен баланс пользователя {user_id}: {balance}")
        return balance
    except Exception as e:
        logger.error(f"Ошибка при получении баланса пользователя {user_id}: {e}")
        logger.error(traceback.format_exc())
        raise

def update_balance(session: Session, user_id: int, amount: int, 
                  transaction_type: TransactionType, game_type: str = None) -> bool:
    """Обновить баланс пользователя и создать транзакцию"""
    try:
        user = session.query(User).filter(User.user_id == user_id).first()
        if not user:
            logger.error(f"Пользователь {user_id} не найден")
            return False

        # Проверка на отрицательный баланс
        if user.balance + amount < 0:
            logger.error(f"Попытка установить отрицательный баланс для пользователя {user_id}")
            return False

        # Обновление баланса
        user.balance += amount
        user.last_active = datetime.utcnow()
        logger.info(f"Обновлен баланс пользователя {user_id}: {user.balance}")

        # Создание транзакции
        transaction = Transaction(
            user_id=user_id,
            amount=amount,
            type=transaction_type,
            game_type=game_type
        )
        session.add(transaction)
        session.commit()
        logger.info(f"Создана транзакция для пользователя {user_id}: {amount} монет")
        return True
    except Exception as e:
        logger.error(f"Ошибка при обновлении баланса пользователя {user_id}: {e}")
        logger.error(traceback.format_exc())
        session.rollback()
        raise

def create_game_session(session: Session, game_type: str, players: List[Dict]) -> int:
    """Создать новую игровую сессию"""
    game = GameSession(
        game_type=game_type,
        players=players,
        created_at=datetime.utcnow()
    )
    session.add(game)
    session.commit()
    return game.session_id

def update_game_session(session: Session, session_id: int, outcome: Dict) -> bool:
    """Обновить результат игровой сессии"""
    game = session.query(GameSession).filter(GameSession.session_id == session_id).first()
    if not game:
        return False

    game.outcome = outcome
    session.commit()
    return True

def get_user_stats(session: Session, user_id: int) -> Dict:
    """Получить статистику пользователя"""
    user = session.query(User).filter(User.user_id == user_id).first()
    if not user:
        return {}

    # Получение статистики по играм
    games_played = session.query(GameSession).filter(
        GameSession.players.contains([{"user_id": user_id}])
    ).count()

    # Получение статистики по транзакциям
    wins = session.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.type == TransactionType.GAME_WIN
    ).count()

    return {
        "balance": user.balance,
        "games_played": games_played,
        "wins": wins,
        "registration_date": user.registration_date
    }

def get_leaderboard(session: Session, limit: int = 10) -> List[Dict]:
    """Получить таблицу лидеров"""
    top_users = session.query(User).order_by(User.balance.desc()).limit(limit).all()
    return [
        {
            "user_id": user.user_id,
            "username": user.username,
            "balance": user.balance
        }
        for user in top_users
    ]

def check_rate_limit(session: Session, user_id: int) -> bool:
    """Проверить ограничение на количество игр в час"""
    hour_ago = datetime.utcnow() - timedelta(hours=1)
    recent_games = session.query(GameSession).filter(
        GameSession.players.contains([{"user_id": user_id}]),
        GameSession.created_at >= hour_ago
    ).count()
    return recent_games < 50  # MAX_GAMES_PER_HOUR 