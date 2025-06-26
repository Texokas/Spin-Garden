from aiohttp import web
import ssl
import logging
from games.slots import spin
from games.blackjack import BlackjackGame
from games.roulette import RouletteGame, Bet
from database import update_balance, create_game_session, update_game_session, get_user_balance
from models import TransactionType
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from config import DATABASE_URL
import json
import os
from aiohttp_cors import setup as cors_setup, ResourceOptions, CorsViewMixin

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация базы данных
engine = create_engine(DATABASE_URL)

# Активные игры
active_blackjack_games = {}
active_roulette_games = {}

async def handle_index(request):
    """Обработчик главной страницы"""
    game_type = request.query.get('game', '')
    user_id = request.query.get('user_id', '')
    
    # Читаем HTML файл
    with open('static/index.html', 'r', encoding='utf-8') as f:
        html = f.read()
    
    # Добавляем параметры в URL для JavaScript
    html = html.replace('</head>', f'''
        <script>
            window.GAME_TYPE = "{game_type}";
            window.USER_ID = "{user_id}";
        </script>
    </head>''')
    
    return web.Response(text=html, content_type='text/html')

async def handle_balance(request):
    """Обработчик запроса баланса"""
    try:
        user_id = int(request.query['user_id'])
        with Session(engine) as session:
            balance = get_user_balance(session, user_id)
            return web.json_response({
                'balance': balance
            })
    except Exception as e:
        logger.error(f"Ошибка при получении баланса: {e}")
        return web.json_response({
            'error': str(e)
        }, status=500)

async def handle_slots(request):
    """Обработчик игры в слоты"""
    try:
        data = await request.json()
        user_id = int(data['user_id'])
        bet = int(data['bet'])
        
        # Крутим слоты
        combination, win, success = spin(bet)
        
        if not success:
            return web.json_response({
                'error': 'Invalid bet'
            }, status=400)
        
        # Обновляем баланс
        with Session(engine) as session:
            if win > 0:
                update_balance(session, user_id, win, TransactionType.GAME_WIN, 'slots')
            else:
                update_balance(session, user_id, -bet, TransactionType.GAME_LOSS, 'slots')
            
            # Создаем запись об игре
            game_id = create_game_session(session, 'slots', [{
                'user_id': user_id,
                'bet': bet,
                'result': win
            }])
        
        return web.json_response({
            'combination': combination,
            'win': win,
            'game_id': game_id
        })
    
    except Exception as e:
        logger.error(f"Ошибка в слотах: {e}")
        return web.json_response({
            'error': str(e)
        }, status=500)

async def handle_blackjack(request):
    """Обработчик игры в блэкджек"""
    try:
        data = await request.json()
        action = data['action']
        user_id = int(data['user_id'])
        
        if action == 'create':
            bet = int(data['bet'])
            game = BlackjackGame()
            if game.add_player(user_id, bet):
                game_id = len(active_blackjack_games) + 1
                active_blackjack_games[game_id] = game
                return web.json_response({
                    'game_id': game_id,
                    'message': 'Game created'
                })
            return web.json_response({
                'error': 'Could not create game'
            }, status=400)
        
        elif action == 'join':
            game_id = int(data['game_id'])
            bet = int(data['bet'])
            if game_id in active_blackjack_games:
                game = active_blackjack_games[game_id]
                if game.add_player(user_id, bet):
                    return web.json_response({
                        'message': 'Joined game'
                    })
            return web.json_response({
                'error': 'Could not join game'
            }, status=400)
        
        elif action == 'start':
            game_id = int(data['game_id'])
            if game_id in active_blackjack_games:
                game = active_blackjack_games[game_id]
                if game.start_game():
                    return web.json_response({
                        'message': 'Game started',
                        'dealer_card': str(game.dealer.hand[0])
                    })
            return web.json_response({
                'error': 'Could not start game'
            }, status=400)
        
        elif action == 'hit':
            game_id = int(data['game_id'])
            if game_id in active_blackjack_games:
                game = active_blackjack_games[game_id]
                success, message = game.hit(user_id)
                if success:
                    return web.json_response({
                        'message': message,
                        'hand': [str(card) for card in game.players[user_id].hand]
                    })
            return web.json_response({
                'error': 'Could not hit'
            }, status=400)
        
        elif action == 'stand':
            game_id = int(data['game_id'])
            if game_id in active_blackjack_games:
                game = active_blackjack_games[game_id]
                if game.stand(user_id):
                    if game.is_game_over():
                        results = game.finish_game()
                        # Обновляем балансы
                        with Session(engine) as session:
                            for player_id, amount in results.items():
                                if amount > 0:
                                    update_balance(session, player_id, amount, TransactionType.GAME_WIN, 'blackjack')
                                else:
                                    update_balance(session, player_id, -amount, TransactionType.GAME_LOSS, 'blackjack')
                        
                        # Удаляем игру
                        del active_blackjack_games[game_id]
                        
                        return web.json_response({
                            'message': 'Game over',
                            'results': results
                        })
                    return web.json_response({
                        'message': 'Stand successful'
                    })
            return web.json_response({
                'error': 'Could not stand'
            }, status=400)
    
    except Exception as e:
        logger.error(f"Ошибка в блэкджеке: {e}")
        return web.json_response({
            'error': str(e)
        }, status=500)

async def handle_roulette(request):
    """Обработчик игры в рулетку"""
    try:
        data = await request.json()
        action = data['action']
        user_id = int(data['user_id'])
        
        if action == 'bet':
            bet_type = data['bet_type']
            value = data['value']
            amount = int(data['amount'])
            
            bet = Bet(bet_type, value, amount)
            
            if user_id not in active_roulette_games:
                active_roulette_games[user_id] = RouletteGame()
            
            game = active_roulette_games[user_id]
            if game.place_bet(user_id, bet):
                return web.json_response({
                    'message': 'Bet placed'
                })
            return web.json_response({
                'error': 'Invalid bet'
            }, status=400)
        
        elif action == 'spin':
            if user_id in active_roulette_games:
                game = active_roulette_games[user_id]
                number, results = game.spin()
                
                # Обновляем балансы
                with Session(engine) as session:
                    for player_id, amount in results.items():
                        if amount > 0:
                            update_balance(session, player_id, amount, TransactionType.GAME_WIN, 'roulette')
                
                # Удаляем игру
                del active_roulette_games[user_id]
                
                return web.json_response({
                    'number': number,
                    'color': game.get_number_color(number),
                    'dozen': game.get_number_dozen(number),
                    'column': game.get_number_column(number),
                    'results': results
                })
            return web.json_response({
                'error': 'No active game'
            }, status=400)
    
    except Exception as e:
        logger.error(f"Ошибка в рулетке: {e}")
        return web.json_response({
            'error': str(e)
        }, status=500)

def setup_routes(app):
    """Настройка маршрутов"""
    # Статические файлы
    app.router.add_static('/static', 'static')
    
    # API маршруты
    app.router.add_get('/', handle_index)
    app.router.add_get('/api/balance', handle_balance)
    app.router.add_post('/api/slots', handle_slots)
    app.router.add_post('/api/blackjack', handle_blackjack)
    app.router.add_post('/api/roulette', handle_roulette)

def create_app():
    """Создание приложения"""
    app = web.Application()
    
    # Настройка CORS
    cors = cors_setup(app, defaults={
        "*": ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods="*"
        )
    })
    
    # Настройка маршрутов
    setup_routes(app)
    
    # Применяем CORS ко всем маршрутам
    for route in list(app.router.routes()):
        cors.add(route)
    
    return app

if __name__ == '__main__':
    # Создаем директорию для статических файлов, если её нет
    os.makedirs('static', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    # Настройка SSL
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain('cert.pem', 'key.pem')
    
    app = create_app()
    web.run_app(app, ssl_context=ssl_context, port=8443) 