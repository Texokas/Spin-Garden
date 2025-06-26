import os
import logging
import traceback
import asyncio
import sys
import nest_asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, filters
from config import BOT_TOKEN, INITIAL_BALANCE, BLACKJACK_MIN_BET, SLOTS_MIN_BET, ROULETTE_MIN_BET
from models import User, Transaction, TransactionType
from database import init_db, get_db, update_balance
from datetime import datetime
from games.blackjack import BlackjackGame
from games.roulette import RouletteGame, Bet
from games.slots import SlotsGame

if sys.platform.startswith('win') and sys.version_info >= (3, 8):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

nest_asyncio.apply()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальный словарь для хранения активных игр
active_games = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    if not update.effective_user:
        logger.error("Не удалось получить информацию о пользователе")
        return
    
    if not update.effective_message:
        logger.error("Не удалось получить сообщение")
        return
    
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or str(user_id)
    
    with get_db() as session:
        # Проверяем, существует ли пользователь
        user = session.query(User).filter(User.user_id == user_id).first()
        if not user:
            # Создаем нового пользователя
            user = User(user_id=user_id, username=username, balance=INITIAL_BALANCE)
            session.add(user)
            session.commit()
            logger.info(f"Создан новый пользователь: {username} (ID: {user_id})")
        
        if user and getattr(user, 'is_banned', 0):
            await update.effective_message.reply_text("Гетаут отсюда позорник нищий")
            return
        
        # Создаем клавиатуру
        keyboard = [
            [InlineKeyboardButton("💰 Баланс", callback_data="balance")],
            [
                InlineKeyboardButton("🎰 Крутилка", callback_data="slots_menu"),
                InlineKeyboardButton("🎲 Рулетка", callback_data="roulette_menu")
            ],
            [InlineKeyboardButton("🃏 21", callback_data="blackjack_menu")],
            [InlineKeyboardButton("🏆 Таблица лидеров", callback_data="leaderboard")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.effective_message.reply_text(
            f"Добро пожаловать в казино, {username}!\n"
            f"Ваш текущий баланс: {user.balance} монет",
            reply_markup=reply_markup
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатий на кнопки"""
    if not update.callback_query:
        logger.error("Не удалось получить callback_query")
        return
    
    query = update.callback_query
    if not query.from_user or not query.message or not query.data:
        logger.error("Не удалось получить необходимые данные из callback_query")
        return
    
    user_id = query.from_user.id
    username = query.from_user.username or query.from_user.first_name or str(user_id)
    
    await query.answer()  # Отвечаем на callback_query
    
    with get_db() as session:
        # Получаем пользователя из базы данных
        user = session.query(User).filter(User.user_id == user_id).first()
        if not user:
            logger.error(f"Пользователь не найден в базе данных: {user_id}")
            await query.message.reply_text("Произошла ошибка. Пожалуйста, используйте /start")
            return
            
        if user and getattr(user, 'is_banned', 0):
            await query.message.reply_text("Гетаут отсюда позорник нищий")
            return
            
        if query.data == "balance":
            await query.message.reply_text(f"Ваш баланс: {user.balance} монет")
            
        elif query.data == "slots_menu":
            keyboard = [
                [InlineKeyboardButton("🎰 Крутить (10 монет)", callback_data="slots_spin")],
                [InlineKeyboardButton("« Назад", callback_data="main_menu")]
            ]
            await query.message.edit_text(
                "🎰 Крутилка\nМинимальная ставка: 10 монет",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        elif query.data == "roulette_menu":
            keyboard = [
                [InlineKeyboardButton("🔴 Красное", callback_data="roulette_red")],
                [InlineKeyboardButton("⚫ Чёрное", callback_data="roulette_black")],
                [InlineKeyboardButton("🟢 Зеро", callback_data="roulette_zero")],
                [InlineKeyboardButton("2️⃣ Четное", callback_data="roulette_even")],
                [InlineKeyboardButton("1️⃣ Нечетное", callback_data="roulette_odd")],
                [InlineKeyboardButton("« Назад", callback_data="main_menu")]
            ]
            await query.message.edit_text(
                "🎲 Рулетка\nВыберите тип ставки:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        elif query.data == "blackjack_menu":
            keyboard = [
                [InlineKeyboardButton("🃏 Начать игру (50 монет)", callback_data="blackjack_start")],
                [InlineKeyboardButton("« Назад", callback_data="main_menu")]
            ]
            await query.message.edit_text(
                "🃏 21\nМинимальная ставка: 50 монет",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        elif query.data == "main_menu":
            keyboard = [
                [InlineKeyboardButton("💰 Баланс", callback_data="balance")],
                [
                    InlineKeyboardButton("🎰 Крутилка", callback_data="slots_menu"),
                    InlineKeyboardButton("🎲 Рулетка", callback_data="roulette_menu")
                ],
                [InlineKeyboardButton("🃏 21", callback_data="blackjack_menu")],
                [InlineKeyboardButton("🏆 Таблица лидеров", callback_data="leaderboard")]
            ]
            await query.message.edit_text(
                f"Добро пожаловать в казино, {username}!\nВаш текущий баланс: {user.balance} монет",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        elif query.data.startswith("roulette_"):
            bet_type = query.data.split("_")[1]
            if bet_type in ["red", "black", "zero", "even", "odd"]:
                user = session.query(User).filter(User.user_id == user_id).with_for_update().first()
                if user is None or user.balance < ROULETTE_MIN_BET:
                    await query.message.reply_text(
                        f"Недостаточно монет. Минимальная ставка: {ROULETTE_MIN_BET}"
                    )
                    return
                game = RouletteGame()
                result = game.play(bet_type)
                if "error" in result:
                    await query.message.reply_text(result["error"])
                    return
                if result["win"]:
                    update_balance(session, user_id, result["prize"], TransactionType.GAME_WIN, "roulette")
                    user.balance += result["prize"]
                    await query.message.reply_text(
                        f"🎲 Выпало число {result['number']} {result['color']}\nВы выиграли {result['prize']} монет!\nВаш новый баланс: {user.balance}"
                    )
                else:
                    update_balance(session, user_id, -result["bet"], TransactionType.GAME_LOSS, "roulette")
                    user.balance -= result["bet"]
                    await query.message.reply_text(
                        f"🎲 Выпало число {result['number']} {result['color']}\nВы проиграли {result['bet']} монет.\nВаш новый баланс: {user.balance}"
                    )
                # Кнопки после игры
                keyboard = [
                    [InlineKeyboardButton("Сыграть снова", callback_data="roulette_menu")],
                    [InlineKeyboardButton("« Выйти в меню", callback_data="main_menu")]
                ]
                await query.message.reply_text("Выберите действие:", reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                await query.message.reply_text("Неверный тип ставки")
        
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
                "🏆 /leaderboard - Таблица лидеров\n"
                "💰 /balance - Проверить баланс\n"
                "/start - Главное меню\n"
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
            # Восстановленное меню с game_*
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
            if game_type == "blackjack":
                # Существующая логика для блэкджека
                keyboard = [
                    [
                        InlineKeyboardButton("🎮 Одиночная игра", callback_data="blackjack_single"),
                        InlineKeyboardButton("👥 Мультиплеер", callback_data="blackjack_multi")
                    ],
                    [
                        InlineKeyboardButton("🔙 Вернуться в меню", callback_data="back_to_menu")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.message.edit_text("Выберите режим игры:", reply_markup=reply_markup)
            elif game_type == "slots":
                game = SlotsGame(game_mode="single", chat_id=query.message.chat_id)
                username = query.from_user.username or query.from_user.first_name
                success, message = game.add_player(query.from_user.id, SLOTS_MIN_BET, username)
                if not success:
                    await query.message.reply_text(message)
                    return
                success, message = game.start_game()
                if not success:
                    await query.message.reply_text(message)
                    return
                active_games[query.from_user.id] = game
                keyboard = [
                    [InlineKeyboardButton("🎰 Крутить", callback_data="slots_spin")],
                    [InlineKeyboardButton("🔙 Выйти из игры", callback_data="slots_exit")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.message.edit_text(
                    f"Игра началась!\n\n{game.get_game_state()}",
                    reply_markup=reply_markup
                )
            elif game_type == "roulette":
                game = RouletteGame(game_mode="single", chat_id=query.message.chat_id)
                username = query.from_user.username or query.from_user.first_name
                success, message = game.add_player(query.from_user.id, ROULETTE_MIN_BET, username)
                if not success:
                    await query.message.reply_text(message)
                    return
                success, message = game.start_game()
                if not success:
                    await query.message.reply_text(message)
                    return
                active_games[query.from_user.id] = game
                keyboard = [
                    [InlineKeyboardButton("🔴 Красное", callback_data="roulette_bet_red"),
                     InlineKeyboardButton("⚫ Черное", callback_data="roulette_bet_black")],
                    [InlineKeyboardButton("2️⃣ Четное", callback_data="roulette_bet_even"),
                     InlineKeyboardButton("1️⃣ Нечетное", callback_data="roulette_bet_odd")],
                    [InlineKeyboardButton("🎲 Крутить", callback_data="roulette_spin")],
                    [InlineKeyboardButton("🔙 Выйти из игры", callback_data="roulette_exit")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.message.edit_text(
                    f"Игра началась!\n\n{game.get_game_state()}",
                    reply_markup=reply_markup
                )
        
        # Крутилка (слоты)
        elif query.data == "slots_spin":
            game = active_games.get(query.from_user.id)
            chat_id = query.message.chat_id
            if not game:
                game = SlotsGame()
                active_games[query.from_user.id] = game
            # Добавляем игрока и стартуем игру перед spin
            add_ok, add_msg = game.add_player(query.from_user.id, SLOTS_MIN_BET, query.from_user.username or query.from_user.first_name)
            if not add_ok:
                print(f"[ERROR] Не удалось добавить игрока в крутилку: {add_msg}")
            start_ok, start_msg = game.start_game()
            if not start_ok:
                print(f"[ERROR] Не удалось стартовать игру в крутилке: {start_msg}")
            # Проверяем баланс
            if user.balance < SLOTS_MIN_BET:
                await query.message.reply_text("Недостаточно средств для игры!")
                return
            # Списываем ставку
            user.balance -= SLOTS_MIN_BET
            session.add(Transaction(
                user_id=query.from_user.id,
                amount=-SLOTS_MIN_BET,
                type=TransactionType.GAME_LOSS,
                game_type="slots"
            ))
            session.commit()
            # Крутим слоты
            results = game.spin()
            if query.from_user.id not in results:
                print(f"[ERROR] Нет результата для user_id {query.from_user.id} в крутилке")
                await query.message.reply_text("Произошла ошибка при определении результата. Попробуйте еще раз.")
                del active_games[query.from_user.id]
                return
            symbols, win_amount = results[query.from_user.id]
            # Формируем сообщение для текущего чата
            game_message = "🎰 Крутилка\n\n"
            game_message += f"Игрок: {query.from_user.username or query.from_user.first_name}\n"
            game_message += f"Ставка: {SLOTS_MIN_BET} монет\n\n"
            game_message += f"{symbols[0]} | {symbols[1]} | {symbols[2]}\n\n"
            if win_amount > 0:
                game_message += f"🎉 Поздравляем! Выигрыш: {win_amount} монет!"
                user.balance += win_amount
                session.add(Transaction(
                    user_id=query.from_user.id,
                    amount=win_amount,
                    type=TransactionType.GAME_WIN,
                    game_type="slots"
                ))
            else:
                game_message += f"😔 К сожалению, проигрыш. Вы проиграли {SLOTS_MIN_BET} монет. Попробуйте еще раз!"
            session.commit()
            # Создаем клавиатуру
            keyboard = [
                [
                    InlineKeyboardButton("🎰 Крутить еще раз", callback_data="slots_spin"),
                    InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            print(f"[DEBUG] Отправляю сообщение о результате крутилки: {game_message}")
            await query.message.reply_text(game_message, reply_markup=reply_markup)
            del active_games[query.from_user.id]
        
        elif query.data == "slots_exit":
            if query.from_user.id in active_games:
                del active_games[query.from_user.id]
            await query.message.edit_text(
                "Вы вышли из игры.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Вернуться в меню", callback_data="back_to_menu")
                ]])
            )
        
        # Обработка действий в рулетке
        elif query.data.startswith("roulette_bet_"):
            bet_type = query.data.split("_")[2]
            game = active_games.get(query.from_user.id)
            chat_id = query.message.chat_id
            
            if not game:
                game = RouletteGame()
                active_games[query.from_user.id] = game
            
            # Создаем сообщение для текущего чата
            game_message = "🎰 Рулетка\n\n"
            game_message += f"Ставки игрока {query.from_user.username or query.from_user.first_name}:\n"
            for bet in game.players.get(query.from_user.id, []):  # Используем словарь players из класса RouletteGame
                game_message += f"• {bet.amount} монет на {bet.bet_type} {bet.value}\n"
            
            keyboard = []
            # Добавляем кнопки для ставок
            if bet_type == "number":
                rows = []
                for i in range(0, 37, 3):
                    row = []
                    for j in range(3):
                        if i + j <= 36:
                            row.append(InlineKeyboardButton(
                                str(i + j),
                                callback_data=f"roulette_number_{i+j}"
                            ))
                    rows.append(row)
                keyboard.extend(rows)
            elif bet_type == "color":
                keyboard.append([
                    InlineKeyboardButton("🔴 Красное", callback_data="roulette_color_red"),
                    InlineKeyboardButton("⚫ Черное", callback_data="roulette_color_black")
                ])
            elif bet_type == "parity":
                keyboard.append([
                    InlineKeyboardButton("Четное", callback_data="roulette_parity_even"),
                    InlineKeyboardButton("Нечетное", callback_data="roulette_parity_odd")
                ])
            
            # Добавляем общие кнопки управления
            keyboard.append([
                InlineKeyboardButton("🔄 Спин", callback_data="roulette_spin"),
                InlineKeyboardButton("🔙 Назад", callback_data="roulette_menu")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем сообщение в текущий чат
            await query.message.reply_text(game_message, reply_markup=reply_markup)
        
        elif query.data.startswith("roulette_number_") or \
             query.data.startswith("roulette_color_") or \
             query.data.startswith("roulette_parity_"):
            
            game = active_games.get(query.from_user.id)
            if not game:
                await query.message.reply_text("Вы не в игре!")
                return
            
            bet_parts = query.data.split("_")
            bet_type = bet_parts[1]
            bet_value = bet_parts[2]
            
            # Создаем ставку с правильными типами
            bet = Bet(
                bet_type=bet_type,  # str
                value=str(bet_value),  # конвертируем в str
                amount=ROULETTE_MIN_BET  # int
            )
            # Передаем user_id в place_bet
            success, msg = game.place_bet(query.from_user.id, bet)
            if not success:
                await query.message.reply_text(msg)
                return
            
            # Обновляем персональное сообщение игрока
            personal_message = "🎰 Рулетка\n\n"
            personal_message += "Ваши текущие ставки:\n"
            for bet in game.players.get(query.from_user.id, []):
                personal_message += f"• {bet.amount} монет на {bet.bet_type} {bet.value}\n"
            if query.message.reply_markup is not None:
                await query.message.edit_text(
                    text=personal_message,
                    reply_markup=query.message.reply_markup
                )
            else:
                await query.message.edit_text(
                    text=personal_message
                )
        
        elif query.data == "roulette_spin":
            game = active_games.get(query.from_user.id)
            if not game:
                await query.message.reply_text("Вы не в игре!")
                return
            
            if not game.has_bets():
                await query.message.reply_text("Сделайте хотя бы одну ставку!")
                return
            
            # Крутим рулетку
            result = game.spin()
            
            # Отправляем общий результат в чат
            result_message = f"🎲 Выпало число: {result}\n"
            if result in game.RED_NUMBERS:
                result_message += "🔴 Красное"
            else:
                result_message += "⚫ Черное"
            result_message += ", " + ("Четное" if result % 2 == 0 else "Нечетное")
            
            await query.message.reply_text(result_message)
            
            # Обрабатываем результаты для каждого игрока
            results = game.process_bets(result)
            for player_id, player_result in results.items():
                # Обновляем баланс
                player = session.query(User).filter(User.user_id == player_id).first()
                if player:
                    player.balance += player_result
                    session.add(Transaction(
                        user_id=player_id,
                        amount=player_result,
                        type=TransactionType.GAME_WIN if player_result > 0 else TransactionType.GAME_LOSS,
                        game_type="roulette"
                    ))
                
                # Отправляем персональный результат
                personal_result = f"🎲 Результаты:\n\n"
                personal_result += f"Выпало число: {result}\n"
                if result in game.RED_NUMBERS:
                    personal_result += "🔴 Красное"
                else:
                    personal_result += "⚫ Черное"
                personal_result += ", " + ("Четное" if result % 2 == 0 else "Нечетное") + "\n\n"
                
                personal_result += "Ваши ставки:\n"
                for bet in game.players.get(player_id, []):  # Используем словарь players из класса RouletteGame
                    personal_result += f"• {bet.amount} монет на {bet.bet_type} {bet.value}\n"
                
                personal_result += f"\nИтого: {'+' if player_result > 0 else ''}{player_result} монет"
                
                keyboard = [[
                    InlineKeyboardButton("🔄 Играть снова", callback_data="roulette_menu"),
                    InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")
                ]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                print(f"[DEBUG] Отправляю сообщение: {personal_result}")
                await query.message.reply_text(
                    personal_result,
                    reply_markup=reply_markup
                )
            
            session.commit()
            
            # Очищаем игру
            del active_games[query.from_user.id]
        
        elif query.data == "roulette_exit" or query.data == "roulette_menu":
            if query.from_user.id in active_games:
                del active_games[query.from_user.id]
            await query.message.edit_text(
                "Вы вышли из игры.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Вернуться в меню", callback_data="back_to_menu")
                ]])
            )

async def blackjack_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик игры в блэкджек"""
    query = update.callback_query
    if query is None or query.message is None or query.from_user is None or query.data is None:
        print("[ERROR] Некорректный callback_query в blackjack_handler")
        return
    await query.answer()
    print(f"[DEBUG] blackjack_handler: callback_data={query.data}")
    
    user_id = query.from_user.id
    username = query.from_user.username or query.from_user.first_name
    chat_id = query.message.chat_id  # Получаем ID чата
    
    try:
        with get_db() as session:
            user = session.query(User).filter(User.user_id == user_id).first()
            if not user:
                await query.message.reply_text("Ошибка: пользователь не найден")
                return
            
            if user and getattr(user, 'is_banned', 0):
                await query.message.reply_text("Гетаут отсюда позорник нищий")
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
                    if hasattr(g, 'room_id') and g.room_id == f"room_{room_id}_{max_players}":
                        game = g
                        break
                
                # Если игры нет, создаем новую
                if not game:
                    game = BlackjackGame(game_mode="multi", room_id=f"room_{room_id}_{max_players}", chat_id=chat_id)
                
                # Добавляем игрока
                success, message = game.add_player(user_id, BLACKJACK_MIN_BET, username)
                if not success:
                    await query.message.reply_text(message)
                    return
                
                # ВАЖНО: всем игрокам комнаты присваиваем ссылку на одну и ту же игру
                for pid in game.players:
                    active_games[pid] = game
                
                # Создаем клавиатуру для ожидания
                keyboard = [
                    [InlineKeyboardButton("🔙 Вернуться в меню комнат", callback_data="blackjack_multi")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                if len(game.players) >= game.min_players:
                    success, message = game.start_game()
                    if success:
                        # Отправляем состояние игры в текущий чат
                        game_message = f"Игра началась! Комната {room_id}\n"
                        game_message += f"Игроки: {', '.join(p.username for p in game.players.values())}\n\n"
                        game_message += "Карты игроков:\n"
                        for player in game.players.values():
                            game_message += f"{player.username}: {' '.join(str(card) for card in player.hand)} (Счет: {player.get_score()})\n"
                        game_message += f"\nКарты дилера: {game.dealer.hand[0]} ?\n\n"
                        
                        current_player = game.get_current_player()
                        if current_player:
                            game_message += f"Ход игрока: {current_player.username}\n\n"
                        
                        # Создаем клавиатуру для текущего игрока
                        if current_player and current_player.user_id == user_id:
                            keyboard = [
                                [
                                    InlineKeyboardButton("🎴 Взять карту", callback_data="blackjack_hit"),
                                    InlineKeyboardButton("✋ Стоп", callback_data="blackjack_stand")
                                ],
                                [
                                    InlineKeyboardButton("💰 Удвоить", callback_data="blackjack_double")
                                ]
                            ]
                        keyboard.append([InlineKeyboardButton("🚪 Выйти из игры", callback_data="blackjack_exit")])
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        await query.message.reply_text(
                            game_message,
                            reply_markup=reply_markup
                        )
                else:
                    # Обновляем информацию о комнате
                    room_info = f"Комната {room_id} ({max_players} игроков)\n"
                    room_info += f"Ожидание игроков... ({len(game.players)}/{max_players})\n\n"
                    room_info += "Игроки в комнате:\n"
                    for player in game.players.values():
                        room_info += f"• {player.username}\n"
                    
                    await query.message.reply_text(
                        room_info,
                        reply_markup=reply_markup
                    )
            
            elif query.data in ["blackjack_hit", "blackjack_stand", "blackjack_double"]:
                logger.info(f"Действие в игре: {query.data} от пользователя {user_id}")
                
                game = active_games.get(user_id)
                if not game or user_id not in game.players:
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
                                type=TransactionType.GAME_WIN if result > 0 else TransactionType.GAME_LOSS,
                                game_type="blackjack"
                            ))
                    session.commit()
                    # Формируем и отправляем персональное сообщение каждому игроку
                    for player_id, result in results.items():
                        player = game.players[player_id]
                        personal_result = f"Игра завершена!\n\n"
                        personal_result += f"Ваши карты: {' '.join(str(card) for card in player.hand)}\n"
                        personal_result += f"Ваш счет: {player.get_score()}\n"
                        personal_result += f"Ваш результат: {'+' if result > 0 else ''}{result} монет\n\n"
                        personal_result += f"Карты дилера: {' '.join(str(card) for card in game.dealer.hand)}\n"
                        personal_result += f"Счет дилера: {game.dealer.get_score()}\n\n"
                        # Общий результат по всем игрокам
                        personal_result += "Результаты всех игроков:\n"
                        for pid, res in results.items():
                            p = game.players[pid]
                            personal_result += f"{p.username}: {'+' if res > 0 else ''}{res} монет\n"
                        keyboard = [[
                            InlineKeyboardButton("🔙 Вернуться в меню", callback_data="back_to_menu")
                        ]]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        print(f"[DEBUG] Отправляю сообщение: {personal_result}")
                        await query.message.reply_text(
                            personal_result,
                            reply_markup=reply_markup
                        )
                    # Удаляем игру у всех участников
                    for pid in list(active_games.keys()):
                        if active_games.get(pid) is game:
                            del active_games[pid]
                else:
                    # Обновляем состояние для всех игроков
                    for player_id, player in game.players.items():
                        # Формируем персональное состояние для игрока
                        player_state = f"Ваши карты: {' '.join(str(card) for card in player.hand)}\n"
                        player_state += f"Ваш счет: {player.get_score()}\n"
                        player_state += f"Ваша ставка: {player.bet}\n\n"
                        player_state += f"Карты дилера: {game.dealer.hand[0]} ?\n\n"
                        
                        current = game.get_current_player()
                        if current:
                            if current.user_id == player_id:
                                player_state += "Сейчас ваш ход!"
                            else:
                                player_state += f"Ход игрока: {current.username}"
                        
                        # Создаем клавиатуру (активную только для текущего игрока)
                        keyboard = []
                        if current and current.user_id == player_id:
                            keyboard = [
                                [
                                    InlineKeyboardButton("🎴 Взять карту", callback_data="blackjack_hit"),
                                    InlineKeyboardButton("✋ Стоп", callback_data="blackjack_stand")
                                ],
                                [
                                    InlineKeyboardButton("💰 Удвоить", callback_data="blackjack_double")
                                ]
                            ]
                        keyboard.append([InlineKeyboardButton("🚪 Выйти из игры", callback_data="blackjack_exit")])
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        await query.message.reply_text(
                            player_state,
                            reply_markup=reply_markup
                        )
                    
                    # Отправляем общее состояние в чат
                    await query.message.reply_text(
                        f"Ход игрока: {current_player.username}"
                    )
    
    except Exception as e:
        logger.error(f"Ошибка в блэкджеке: {e}")
        logger.error(traceback.format_exc())
        await query.message.reply_text("Произошла ошибка. Пожалуйста, попробуйте позже.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
        "🏆 /leaderboard - Таблица лидеров\n"
        "💰 /balance - Проверить баланс\n"
        "/start - Главное меню\n"
        "/help - Это сообщение"
    )
    await update.message.reply_text(help_text)

async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with get_db() as session:
        top_users = session.query(User).order_by(User.balance.desc()).limit(10).all()
        leaderboard_text = "🏆 Таблица лидеров:\n\n"
        for i, user in enumerate(top_users, 1):
            leaderboard_text += f"{i}. {user.username}: {user.balance} монет\n"
        await update.message.reply_text(leaderboard_text)

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    user_id = update.effective_user.id
    with get_db() as session:
        user = session.query(User).filter(User.user_id == user_id).first()
        if user:
            await update.message.reply_text(f"Ваш баланс: {user.balance} монет")
        else:
            await update.message.reply_text("Пользователь не найден. Используйте /start")

async def addmoney_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    user = update.effective_user
    if user.username != "#Поменять":
        await update.message.reply_text("У вас нет прав для этой команды.")
        return
    if not context.args or len(context.args) != 2:
        await update.message.reply_text("Использование: /addmoney <username> <amount>")
        return
    target_username = context.args[0].lstrip('@')
    try:
        amount = int(context.args[1])
    except (ValueError, TypeError):
        await update.message.reply_text("Сумма должна быть числом.")
        return
    with get_db() as session:
        target_user = session.query(User).filter(User.username == target_username).first()
        if not target_user:
            await update.message.reply_text("Пользователь не найден.")
            return
        target_user.balance += amount
        session.commit()
        await update.message.reply_text(f"Пользователю @{target_username} начислено {amount} монет. Новый баланс: {target_user.balance}")

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    user = update.effective_user
    if user.username != "#Поменять":
        await update.message.reply_text("У вас нет прав для этой команды.")
        return
    if not context.args or len(context.args) != 1:
        await update.message.reply_text("Использование: /ban <username>")
        return
    target_username = context.args[0].lstrip('@')
    with get_db() as session:
        target_user = session.query(User).filter(User.username == target_username).first()
        if not target_user:
            await update.message.reply_text("Пользователь не найден.")
            return
        target_user.is_banned = 1
        session.commit()
        await update.message.reply_text(f"Пользователь @{target_username} забанен.")

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    user = update.effective_user
    if user.username != "#Поменять":
        await update.message.reply_text("У вас нет прав для этой команды.")
        return
    if not context.args or len(context.args) != 1:
        await update.message.reply_text("Использование: /unban <username>")
        return
    target_username = context.args[0].lstrip('@')
    with get_db() as session:
        target_user = session.query(User).filter(User.username == target_username).first()
        if not target_user:
            await update.message.reply_text("Пользователь не найден.")
            return
        target_user.is_banned = 0
        session.commit()
        await update.message.reply_text(f"Пользователь @{target_username} разбанен.")

async def main() -> None:
    """Запуск бота"""
    try:
        print("[DEBUG] main() started")
        logger.info("main() started")
        # Инициализация базы данных
        init_db()
        print("[DEBUG] DB initialized")
        logger.info("DB initialized")
        # Создание и настройка приложения
        application = Application.builder().token(BOT_TOKEN).build()
        print("[DEBUG] Application built")
        logger.info("Application built")
        # Регистрация обработчиков
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(blackjack_handler, pattern="^blackjack_"))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("leaderboard", leaderboard_command))
        application.add_handler(CommandHandler("balance", balance_command))
        application.add_handler(CommandHandler("addmoney", addmoney_command, filters.ALL))
        application.add_handler(CommandHandler("ban", ban_command, filters.ALL))
        application.add_handler(CommandHandler("unban", unban_command, filters.ALL))
        print("[DEBUG] Handlers added")
        logger.info("Handlers added")
        # Запуск бота
        print("[DEBUG] About to run_polling")
        logger.info("About to run_polling")
        await application.run_polling()
        print("[DEBUG] run_polling finished")
        logger.info("run_polling finished")
    except Exception as e:
        print(f"[EXCEPTION] {e}")
        print(traceback.format_exc())
        logger.error(f"Ошибка при запуске бота: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    if sys.platform.startswith('win') and sys.version_info >= (3, 8):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main()) 