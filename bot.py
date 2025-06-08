import logging
import traceback
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from config import BOT_TOKEN, INITIAL_BALANCE, BLACKJACK_MIN_BET
from models import User, Transaction, GameSession, TransactionType
from database import init_db, get_db
from datetime import datetime
from games.blackjack import BlackjackGame

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

# Словарь для хранения активных игр
active_games = {}

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
                    "- Одиночная игра против дилера\n"
                    "- Мультиплеер (2-6 игроков)\n\n"
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
            
            elif query.data == "game_blackjack":
                logger.info("Пользователь выбрал игру в блэкджек")
                # Создаем клавиатуру для выбора режима игры
                keyboard = [
                    [
                        InlineKeyboardButton("🎮 Одиночная игра", callback_data="blackjack_single"),
                        InlineKeyboardButton("👥 Мультиплеер", callback_data="blackjack_multi")
                    ],
                    [
                        InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.message.edit_text(
                    "Выберите режим игры в 21:\n\n"
                    "🎮 Одиночная игра - игра против дилера\n"
                    "👥 Мультиплеер - игра с другими игроками (2-6 человек)",
                    reply_markup=reply_markup
                )
            
            elif query.data == "back_to_menu":
                logger.info("Пользователь вернулся в главное меню")
                # Создаем клавиатуру с играми
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
                await query.message.edit_text("Выберите игру:", reply_markup=reply_markup)
            
            elif query.data.startswith("game_"):
                game_type = query.data.split("_")[1]
                if game_type != "blackjack":  # Обработка других игр
                    await query.message.reply_text(f"🎮 Игра {game_type} находится в разработке и будет доступна в ближайшее время!")
                    logger.info(f"Пользователь {query.from_user.id} попытался открыть игру {game_type}")
    
    except Exception as e:
        logger.error(f"Ошибка при обработке кнопки: {e}")
        logger.error(traceback.format_exc())
        await query.message.reply_text("Произошла ошибка. Пожалуйста, попробуйте позже.")

async def blackjack_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик игры в блэкджек"""
    query = update.callback_query
    await query.answer()
    
    logger.info(f"Получен callback_data: {query.data}")
    
    user_id = query.from_user.id
    username = query.from_user.username or query.from_user.first_name
    chat_id = query.message.chat_id  # Получаем ID чата
    
    try:
        with get_db() as session:
            user = session.query(User).filter(User.user_id == user_id).first()
            if not user:
                await query.message.reply_text("Ошибка: пользователь не найден")
                return
            
            if query.data == "blackjack_single":
                logger.info(f"Начало одиночной игры для пользователя {user_id}")
                # Создаем новую одиночную игру
                game = BlackjackGame(game_mode="single", chat_id=chat_id)
                success, message = game.add_player(user_id, BLACKJACK_MIN_BET, username)
                if not success:
                    await query.message.reply_text(message)
                    return
                
                success, message = game.start_game()
                if not success:
                    await query.message.reply_text(message)
                    return
                
                active_games[user_id] = game
                
                # Создаем клавиатуру для игры
                keyboard = [
                    [
                        InlineKeyboardButton("🎴 Взять карту", callback_data="blackjack_hit"),
                        InlineKeyboardButton("✋ Стоп", callback_data="blackjack_stand")
                    ],
                    [
                        InlineKeyboardButton("💰 Удвоить", callback_data="blackjack_double")
                    ],
                    [
                        InlineKeyboardButton("🚪 Выйти из игры", callback_data="blackjack_exit")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.message.edit_text(
                    f"Игра началась!\n\n{game.get_game_state()}",
                    reply_markup=reply_markup
                )
            
            elif query.data == "blackjack_multi":
                logger.info(f"Пользователь выбрал мультиплеер")
                # Создаем клавиатуру с комнатами
                keyboard = []
                # Комнаты для 2 игроков
                keyboard.append([
                    InlineKeyboardButton("Комната 1 (2 игрока)", callback_data="blackjack_room_1_2"),
                    InlineKeyboardButton("Комната 2 (2 игрока)", callback_data="blackjack_room_2_2")
                ])
                # Комнаты для 3 игроков
                keyboard.append([
                    InlineKeyboardButton("Комната 3 (3 игрока)", callback_data="blackjack_room_3_3"),
                    InlineKeyboardButton("Комната 4 (3 игрока)", callback_data="blackjack_room_4_3")
                ])
                # Комнаты для 4 игроков
                keyboard.append([
                    InlineKeyboardButton("Комната 5 (4 игрока)", callback_data="blackjack_room_5_4"),
                    InlineKeyboardButton("Комната 6 (4 игрока)", callback_data="blackjack_room_6_4")
                ])
                # Комнаты для 5 игроков
                keyboard.append([
                    InlineKeyboardButton("Комната 7 (5 игроков)", callback_data="blackjack_room_7_5"),
                    InlineKeyboardButton("Комната 8 (5 игроков)", callback_data="blackjack_room_8_5")
                ])
                # Комнаты для 6 игроков
                keyboard.append([
                    InlineKeyboardButton("Комната 9 (6 игроков)", callback_data="blackjack_room_9_6"),
                    InlineKeyboardButton("Комната 10 (6 игроков)", callback_data="blackjack_room_10_6")
                ])
                keyboard.append([
                    InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")
                ])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.message.edit_text(
                    "Выберите комнату для игры:",
                    reply_markup=reply_markup
                )
            
            elif query.data.startswith("blackjack_room_"):
                room_id = query.data.split("_")[2]
                max_players = int(query.data.split("_")[3])
                logger.info(f"Пользователь {user_id} пытается присоединиться к комнате {room_id}")
                
                # Проверяем, не находится ли пользователь уже в игре
                if user_id in active_games:
                    await query.message.reply_text("Вы уже в игре!")
                    return
                
                # Ищем существующую игру в этой комнате
                game = None
                for g in active_games.values():
                    if g.room_id == f"room_{room_id}_{max_players}":
                        game = g
                        break
                
                # Если игры нет, создаем новую
                if not game:
                    game = BlackjackGame(game_mode="multi", room_id=f"room_{room_id}_{max_players}", chat_id=chat_id)
                    active_games[user_id] = game
                
                # Добавляем игрока
                success, message = game.add_player(user_id, BLACKJACK_MIN_BET, username)
                if not success:
                    await query.message.reply_text(message)
                    return
                
                # Создаем клавиатуру для ожидания
                keyboard = [
                    [InlineKeyboardButton("🔙 Вернуться в меню комнат", callback_data="blackjack_multi")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                if len(game.players) >= game.min_players:
                    success, message = game.start_game()
                    if success:
                        # Отправляем сообщение всем игрокам
                        for player_id in game.players:
                            game_keyboard = [
                                [
                                    InlineKeyboardButton("🎴 Взять карту", callback_data="blackjack_hit"),
                                    InlineKeyboardButton("✋ Стоп", callback_data="blackjack_stand")
                                ],
                                [
                                    InlineKeyboardButton("💰 Удвоить", callback_data="blackjack_double")
                                ],
                                [
                                    InlineKeyboardButton("🚪 Выйти из игры", callback_data="blackjack_exit")
                                ]
                            ]
                            game_reply_markup = InlineKeyboardMarkup(game_keyboard)
                            await context.bot.send_message(
                                chat_id=game.chat_id,  # Используем chat_id игры
                                text=f"Игра началась!\n\n{game.get_game_state()}",
                                reply_markup=game_reply_markup
                            )
                else:
                    # Обновляем информацию о комнате для всех игроков в этой комнате
                    room_info = f"Комната {room_id} ({max_players} игроков)\n"
                    room_info += f"Ожидание игроков... ({len(game.players)}/{max_players})\n\n"
                    room_info += "Игроки в комнате:\n"
                    for player in game.players.values():
                        room_info += f"• {player.username}\n"
                    
                    await context.bot.send_message(
                        chat_id=game.chat_id,  # Используем chat_id игры
                        text=room_info,
                        reply_markup=reply_markup
                    )
            
            elif query.data == "blackjack_exit":
                # Находим игру пользователя
                game = None
                for g in active_games.values():
                    if user_id in g.players:
                        game = g
                        break
                
                if not game:
                    await query.message.reply_text("Вы не в игре!")
                    return
                
                # Возвращаем ставку игроку
                player = game.players[user_id]
                user.balance += player.bet
                session.add(Transaction(
                    user_id=user_id,
                    amount=player.bet,
                    type=TransactionType.REFUND,
                    game_type="blackjack_exit"
                ))
                session.commit()
                
                # Удаляем игрока из игры
                del game.players[user_id]
                
                if not game.players:  # Если больше нет игроков
                    for player_id in list(active_games.keys()):
                        if player_id in active_games:
                            del active_games[player_id]
                else:
                    # Обновляем состояние игры для оставшихся игроков
                    await context.bot.send_message(
                        chat_id=game.chat_id,  # Используем chat_id игры
                        text=f"Игрок {username} вышел из игры.\n\n{game.get_game_state()}"
                    )
                
                await query.message.edit_text(
                    "Вы вышли из игры. Ваша ставка возвращена.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Вернуться в меню", callback_data="back_to_menu")
                    ]])
                )
            
            elif query.data in ["blackjack_hit", "blackjack_stand", "blackjack_double"]:
                logger.info(f"Действие в игре: {query.data} от пользователя {user_id}")
                
                # Находим игру пользователя
                game = None
                for g in active_games.values():
                    if user_id in g.players:
                        game = g
                        break
                
                if not game:
                    await query.message.reply_text("Вы не в игре!")
                    return
                
                current_player = game.get_current_player()
                if not current_player or current_player.user_id != user_id:
                    await query.message.reply_text("Сейчас не ваш ход!")
                    return
                
                # Выполняем действие
                if query.data == "blackjack_hit":
                    success, message = game.hit(user_id)
                elif query.data == "blackjack_stand":
                    success, message = game.stand(user_id)
                else:  # blackjack_double
                    success, message = game.double(user_id)
                
                if not success:
                    await query.message.reply_text(message)
                    return
                
                # Обновляем состояние игры
                if game.is_game_over():
                    logger.info("Игра завершена, подсчет результатов")
                    results = game.finish_game()
                    
                    # Обновляем балансы игроков
                    for player_id, result in results.items():
                        player = session.query(User).filter(User.user_id == player_id).first()
                        if player:
                            player.balance += result
                            session.add(Transaction(
                                user_id=player_id,
                                amount=result,
                                type=TransactionType.GAME,
                                game_type="blackjack"
                            ))
                    session.commit()
                    
                    # Отправляем результаты всем игрокам
                    result_text = "Результаты игры:\n\n"
                    for player_id, result in results.items():
                        player = game.players[player_id]
                        result_text += f"{player.username}:\n"
                        result_text += f"Карты: {' '.join(str(card) for card in player.hand)}\n"
                        result_text += f"Счет: {player.get_score()}\n"
                        result_text += f"Результат: {'+' if result > 0 else ''}{result} монет\n\n"
                    
                    # Добавляем карты дилера в результаты
                    dealer_cards = " ".join(str(card) for card in game.dealer.hand)
                    result_text += f"Дилер:\nКарты: {dealer_cards}\nСчет: {game.dealer.get_score()}"
                    
                    # Создаем клавиатуру с кнопками в зависимости от режима игры
                    if game.game_mode == "single":
                        keyboard = [
                            [
                                InlineKeyboardButton("🔄 Играть снова", callback_data="blackjack_single"),
                                InlineKeyboardButton("🔙 Вернуться в меню", callback_data="back_to_menu")
                            ]
                        ]
                    else:
                        keyboard = [[
                            InlineKeyboardButton("🔙 Вернуться в меню", callback_data="back_to_menu")
                        ]]
                    
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await context.bot.send_message(
                        chat_id=game.chat_id,  # Используем chat_id игры
                        text=result_text,
                        reply_markup=reply_markup
                    )
                    
                    # Удаляем игру
                    for player_id in game.players:
                        if player_id in active_games:
                            del active_games[player_id]
                else:
                    # Обновляем состояние игры для текущего игрока
                    keyboard = [
                        [
                            InlineKeyboardButton("🎴 Взять карту", callback_data="blackjack_hit"),
                            InlineKeyboardButton("✋ Стоп", callback_data="blackjack_stand")
                        ],
                        [
                            InlineKeyboardButton("💰 Удвоить", callback_data="blackjack_double")
                        ],
                        [
                            InlineKeyboardButton("🚪 Выйти из игры", callback_data="blackjack_exit")
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    current_player = game.get_current_player()
                    if current_player:
                        await context.bot.send_message(
                            chat_id=game.chat_id,  # Используем chat_id игры
                            text=f"{game.get_game_state()}",
                            reply_markup=reply_markup
                        )
    
    except Exception as e:
        logger.error(f"Ошибка в блэкджеке: {e}")
        logger.error(traceback.format_exc())
        await query.message.reply_text("Произошла ошибка. Пожалуйста, попробуйте позже.")

def main():
    """Запуск бота"""
    try:
        application = Application.builder().token(BOT_TOKEN).build()

        # Регистрация обработчиков
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(blackjack_handler, pattern="^blackjack_"))
        application.add_handler(CallbackQueryHandler(button_handler))

        # Запуск бота
        logger.info("Бот запущен")
        application.run_polling()
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        logger.error(traceback.format_exc())

if __name__ == '__main__':
    main() 