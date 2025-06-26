from sqlalchemy import create_engine, Column, Integer, String, BigInteger, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
import enum
from enum import Enum
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLEnum
from typing import List, Optional

Base = declarative_base()

class TransactionType(Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    GAME_WIN = "game_win"
    GAME_LOSS = "game_loss"
    BONUS = "bonus"
    REFUND = "refund"

class User(Base):
    __tablename__ = 'users'

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True)
    balance: Mapped[int] = mapped_column(Integer, default=50)
    registration_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_active: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_banned: Mapped[int] = mapped_column(Integer, default=0)  # 0 - не забанен, 1 - забанен

    transactions: Mapped[List["Transaction"]] = relationship("Transaction", back_populates="user")

class Transaction(Base):
    __tablename__ = 'transactions'

    transaction_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.user_id'))
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[TransactionType] = mapped_column(SQLEnum(TransactionType), nullable=False)
    game_type: Mapped[Optional[str]] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="transactions")

class GameSession(Base):
    __tablename__ = 'game_sessions'

    session_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_type: Mapped[str] = mapped_column(String(20), nullable=False)
    players: Mapped[dict] = mapped_column(JSON, nullable=False)  # [{user_id, bet, result}]
    outcome: Mapped[Optional[dict]] = mapped_column(JSON)  # {winner_id, prize}
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

# Создание таблиц
def init_db():
    engine = create_engine('sqlite:///casino.db')
    Base.metadata.create_all(engine) 