// Получаем параметры из URL
const urlParams = new URLSearchParams(window.location.search);
const gameType = urlParams.get('game');
const userId = urlParams.get('user_id');

// Базовый URL для API
const API_URL = '/api';

// Обновление баланса
async function updateBalance() {
    try {
        const response = await fetch(`${API_URL}/balance?user_id=${userId}`);
        const data = await response.json();
        document.getElementById('balance').textContent = data.balance;
    } catch (error) {
        console.error('Ошибка при обновлении баланса:', error);
    }
}

// Инициализация игры
function initGame() {
    const gameContainer = document.getElementById('game-container');
    
    switch (gameType) {
        case 'slots':
            initSlots(gameContainer);
            break;
        case 'blackjack':
            initBlackjack(gameContainer);
            break;
        case 'roulette':
            initRoulette(gameContainer);
            break;
        default:
            gameContainer.innerHTML = '<h2>Игра не найдена</h2>';
    }
    
    // Обновляем баланс при загрузке
    updateBalance();
}

// Инициализация слотов
function initSlots(container) {
    container.innerHTML = `
        <h2>🎰 Крутилка</h2>
        <div class="slots-container">
            <div class="slot">?</div>
            <div class="slot">?</div>
            <div class="slot">?</div>
        </div>
        <div class="controls">
            <input type="number" id="bet" min="5" value="5" step="5">
            <button onclick="spinSlots()">Крутить</button>
        </div>
    `;
}

// Функция для кручения слотов
async function spinSlots() {
    const bet = document.getElementById('bet').value;
    const button = document.querySelector('.controls button');
    button.disabled = true;
    
    try {
        const response = await fetch(`${API_URL}/slots`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: userId,
                bet: parseInt(bet)
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            alert(data.error);
            return;
        }
        
        // Анимация вращения
        const slots = document.querySelectorAll('.slot');
        slots.forEach((slot, index) => {
            setTimeout(() => {
                slot.textContent = data.combination[index];
            }, 500 * (index + 1));
        });
        
        // Обновляем баланс
        setTimeout(updateBalance, 2000);
        
        // Показываем результат
        setTimeout(() => {
            if (data.win > 0) {
                alert(`Поздравляем! Вы выиграли ${data.win} монет!`);
            } else {
                alert('К сожалению, вы проиграли. Попробуйте еще раз!');
            }
            button.disabled = false;
        }, 2000);
        
    } catch (error) {
        console.error('Ошибка при игре в слоты:', error);
        button.disabled = false;
    }
}

// Инициализация блэкджека
function initBlackjack(container) {
    container.innerHTML = `
        <h2>🃏 21</h2>
        <div class="blackjack-container">
            <div class="dealer-hand"></div>
            <div class="player-hand"></div>
            <div class="controls">
                <input type="number" id="bet" min="15" value="15" step="5">
                <button onclick="createGame()">Создать игру</button>
                <button onclick="joinGame()">Присоединиться</button>
                <button onclick="hit()">Взять карту</button>
                <button onclick="stand()">Хватит</button>
            </div>
        </div>
    `;
}

// Инициализация рулетки
function initRoulette(container) {
    container.innerHTML = `
        <h2>🎲 Рулетка</h2>
        <div class="roulette-container">
            ${generateRouletteNumbers()}
        </div>
        <div class="controls">
            <input type="number" id="bet" min="10" value="10" step="5">
            <button onclick="placeBet()">Сделать ставку</button>
            <button onclick="spinRoulette()">Крутить</button>
        </div>
    `;
}

// Генерация чисел для рулетки
function generateRouletteNumbers() {
    const numbers = [];
    for (let i = 0; i <= 36; i++) {
        const color = i === 0 ? 'green' : (i % 2 === 0 ? 'black' : 'red');
        numbers.push(`<div class="roulette-number ${color}" data-number="${i}">${i}</div>`);
    }
    return numbers.join('');
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', initGame); 