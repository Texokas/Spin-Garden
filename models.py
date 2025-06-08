from sqlalchemy import create_engine, Column, Integer, String, BigInteger, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from enum import Enum
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLEnum

Base = declarative_base()

class TransactionType(Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    GAME = "game"
    BONUS = "bonus"
    REFUND = "refund"

class User(Base):
    __tablename__ = 'users'

    user_id = Column(BigInteger, primary_key=True)
    username = Column(String(32), unique=True)
    balance = Column(Integer, default=50)
    registration_date = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)

    transactions = relationship("Transaction", back_populates="user")

class Transaction(Base):
    __tablename__ = 'transactions'

    transaction_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id'))
    amount = Column(Integer, nullable=False)
    type = Column(SQLEnum(TransactionType), nullable=False)
    game_type = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="transactions")

class GameSession(Base):
    __tablename__ = 'game_sessions'

    session_id = Column(Integer, primary_key=True)
    game_type = Column(String(20), nullable=False)
    players = Column(JSON, nullable=False)  # [{user_id, bet, result}]
    outcome = Column(JSON)  # {winner_id, prize}
    created_at = Column(DateTime, default=datetime.utcnow)

# Создание таблиц
def init_db():
    engine = create_engine('sqlite:///casino.db')
    Base.metadata.create_all(engine) 