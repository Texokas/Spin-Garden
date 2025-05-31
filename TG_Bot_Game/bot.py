import logging
import traceback
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from config import BOT_TOKEN, INITIAL_BALANCE
from models import User, Transaction, GameSession, TransactionType
from database import init_db, get_db
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация базы данных
try:
    init_db()
    logger.info("База данных успешно инициализирована")
except Exception as e:
    logger.error(f"Ошибка при инициализации базы данных: {e}")
    logger.error(traceback.format_exc())

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    logger.info(f"Получена команда /start от пользователя {user.id} ({user.username})")
    
    try:
        with get_db() as session:
            # Проверка существования пользователя
            db_user = session.query(User).filter(User.user_id == user.id).first()
            logger.info(f"Поиск пользователя в базе данных: {db_user is not None}")
            
            if not db_user:
                # Создание нового пользователя
                logger.info("Создание нового пользователя")
                db_user = User(
                    user_id=user.id,
                    username=user.username,
                    balance=INITIAL_BALANCE
                )
                session.add(db_user)
                session.commit()
                logger.info("Новый пользователь успешно создан")
                
                welcome_text = f"Добро пожаловать в Spin Garden, {user.first_name}! 🎰\n\n" \
                              f"Ваш начальный баланс: {INITIAL_BALANCE} монет"
            else:
                logger.info(f"Пользователь найден, баланс: {db_user.balance}")
                welcome_text = f"С возвращением, {user.first_name}! 🎰\n\n" \
                              f"Ваш текущий баланс: {db_user.balance} монет"

            # Создание клавиатуры с играми
            keyboard = [
                [
                    InlineKeyboardButton("🎰 Крутилка", callback_data="game_slots"),
                    InlineKeyboardButton("🃏 21", callback_data="game_blackjack")
                ],
                [
                    InlineKeyboardButton("🎲 Рулетка", callback_data="game_roulette"),
                    InlineKeyboardButton("💰 Баланс", callback_data="balance")
                ],
                [
                    InlineKeyboardButton("📊 Таблица лидеров", callback_data="leaderboard"),
                    InlineKeyboardButton("❓ Помощь", callback_data="help")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(welcome_text, reply_markup=reply_markup)
            logger.info("Сообщение успешно отправлено пользователю")
    except Exception as e:
        logger.error(f"Ошибка при обработке команды /start: {e}")
        logger.error(traceback.format_exc())
        await update.message.reply_text("Произошла ошибка. Пожалуйста, попробуйте позже.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    logger.info(f"Получено нажатие кнопки {query.data} от пользователя {query.from_user.id}")

    try:
        with get_db() as session:
            if query.data == "balance":
                user = session.query(User).filter(User.user_id == query.from_user.id).first()
                if user:
                    await query.message.reply_text(f"💰 Ваш текущий баланс: {user.balance} монет")
                    logger.info(f"Баланс пользователя {user.id}: {user.balance}")
                else:
                    logger.error(f"Пользователь {query.from_user.id} не найден в базе данных")
                    await query.message.reply_text("Ошибка: пользователь не найден")
            
            elif query.data == "leaderboard":
                top_users = session.query(User).order_by(User.balance.desc()).limit(10).all()
                logger.info(f"Получено {len(top_users)} пользователей для таблицы лидеров")
                
                leaderboard_text = "🏆 Таблица лидеров:\n\n"
                for i, user in enumerate(top_users, 1):
                    leaderboard_text += f"{i}. {user.username}: {user.balance} монет\n"
                
                await query.message.reply_text(leaderboard_text)
                logger.info("Таблица лидеров успешно отправлена")
            
            elif query.data == "help":
                help_text = (
                    "🎮 Доступные игры:\n\n"
                    "🎰 Крутилка:\n"
                    "- Минимальная ставка: 5 монет\n"
                    "- 3 одинаковых символа: x5\n\n"
                    "🃏 21:\n"
                    "- Минимальная ставка: 15 монет\n"
                    "- До 4 игроков\n\n"
                    "🎲 Рулетка:\n"
                    "- Минимальная ставка: 10 монет\n"
                    "- Разные типы ставок\n\n"
                    "💰 Команды:\n"
                    "/start - Главное меню\n"
                    "/balance - Проверить баланс\n"
                    "/help - Это сообщение"
                )
                await query.message.reply_text(help_text)
                logger.info("Справка успешно отправлена")
            
            elif query.data.startswith("game_"):
                game_type = query.data.split("_")[1]
                await query.message.reply_text(f"🎮 Игра {game_type} находится в разработке и будет доступна в ближайшее время!")
                logger.info(f"Пользователь {query.from_user.id} попытался открыть игру {game_type}")
    
    except Exception as e:
        logger.error(f"Ошибка при обработке кнопки: {e}")
        logger.error(traceback.format_exc())
        await query.message.reply_text("Произошла ошибка. Пожалуйста, попробуйте позже.")

def main():
    """Запуск бота"""
    try:
        application = Application.builder().token(BOT_TOKEN).build()

        # Регистрация обработчиков
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button_handler))

        # Запуск бота
        logger.info("Бот запущен")
        application.run_polling()
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        logger.error(traceback.format_exc())

if __name__ == '__main__':
    main() 