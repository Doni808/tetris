# main.py
from flask import Flask, request, jsonify, render_template
import telebot
import sqlite3
import os

TOKEN = 'your_bot_token_here'
WEBHOOK_URL = 'your_webhook_url_here'

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Database setup
def init_db():
    conn = sqlite3.connect('leaderboard.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS leaderboard (
                      user_id INTEGER PRIMARY KEY,
                      username TEXT,
                      score INTEGER)''')
    conn.commit()
    conn.close()

@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return '!', 200

@app.route('/')
def index():
    return render_template('index.html')

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Welcome to Tetris! Use the button below to start playing.")
    # Send Web App button
    bot.send_message(
        message.chat.id,
        text="Click below to play Tetris:",
        reply_markup=telebot.types.ReplyKeyboardMarkup(resize_keyboard=True).row(
            telebot.types.KeyboardButton(text="Play Tetris", web_app=telebot.types.WebAppInfo(url=WEBHOOK_URL))
        ),
    )

@bot.message_handler(commands=['leaderboard'])
def show_leaderboard(message):
    conn = sqlite3.connect('leaderboard.db')
    cursor = conn.cursor()
    cursor.execute('SELECT username, score FROM leaderboard ORDER BY score DESC LIMIT 10')
    results = cursor.fetchall()
    conn.close()
    leaderboard = "\n".join([f"{i+1}. {row[0]} - {row[1]}" for i, row in enumerate(results)])
    bot.reply_to(message, f"Leaderboard:\n{leaderboard}")

@app.route('/save_score', methods=['POST'])
def save_score():
    data = request.json
    user_id = data.get('user_id')
    username = data.get('username')
    score = data.get('score')

    conn = sqlite3.connect('leaderboard.db')
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO leaderboard (user_id, username, score)
                      VALUES (?, ?, ?)
                      ON CONFLICT(user_id) DO UPDATE SET score = max(score, excluded.score)''',
                   (user_id, username, score))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    init_db()
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

# Directory structure adjustment:
# Move the HTML to a templates folder (templates/index.html)
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tetris</title>
    <style>
        canvas {
            display: block;
            margin: auto;
            background-color: #000;
        }
    </style>
</head>
<body>
    <canvas id="game" width="300" height="600"></canvas>
    <script>
        window.onload = function() {
            const canvas = document.getElementById('game');
            const ctx = canvas.getContext('2d');
            const rows = 20;
            const cols = 10;
            const blockSize = 30;
            let board = Array.from({ length: rows }, () => Array(cols).fill(0));

            let currentPiece;
            let currentX = 0;
            let currentY = 0;

            const pieces = [
                [[1, 1, 1, 1]], // I
                [[2, 2], [2, 2]], // O
                [[0, 3, 0], [3, 3, 3]], // T
                [[4, 0, 0], [4, 4, 4]], // L
                [[0, 0, 5], [5, 5, 5]], // J
                [[0, 6, 6], [6, 6, 0]], // S
                [[7, 7, 0], [0, 7, 7]]  // Z
            ];

            function drawBoard() {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                for (let row = 0; row < rows; row++) {
                    for (let col = 0; col < cols; col++) {
                        if (board[row][col]) {
                            ctx.fillStyle = 'blue';
                            ctx.fillRect(col * blockSize, row * blockSize, blockSize, blockSize);
                            ctx.strokeRect(col * blockSize, row * blockSize, blockSize, blockSize);
                        }
                    }
                }
            }

            function drawPiece() {
                currentPiece.forEach((row, y) => {
                    row.forEach((value, x) => {
                        if (value) {
                            ctx.fillStyle = 'red';
                            ctx.fillRect((currentX + x) * blockSize, (currentY + y) * blockSize, blockSize, blockSize);
                            ctx.strokeRect((currentX + x) * blockSize, (currentY + y) * blockSize, blockSize, blockSize);
                        }
                    });
                });
            }

            function spawnPiece() {
                const index = Math.floor(Math.random() * pieces.length);
                currentPiece = pieces[index];
                currentX = Math.floor((cols - currentPiece[0].length) / 2);
                currentY = 0;
            }

            function movePiece(dx, dy) {
                currentX += dx;
                currentY += dy;
            }

            function dropPiece() {
                movePiece(0, 1);
                if (collision()) {
                    mergePiece();
                    spawnPiece();
                }
            }

            function collision() {
                return currentPiece.some((row, y) =>
                    row.some((value, x) =>
                        value && (board[currentY + y]?.[currentX + x] || currentY + y >= rows)
                    )
                );
            }

            function mergePiece() {
                currentPiece.forEach((row, y) => {
                    row.forEach((value, x) => {
                        if (value) {
                            board[currentY + y][currentX + x] = value;
                        }
                    });
                });
            }

            function handleSwipe(direction) {
                if (direction === 'left') movePiece(-1, 0);
                if (direction === 'right') movePiece(1, 0);
                if (direction === 'down') dropPiece();
            }

            canvas.addEventListener('touchstart', handleTouchStart, false);
            canvas.addEventListener('touchmove', handleTouchMove, false);

            let xDown = null;
            let yDown = null;

            function handleTouchStart(evt) {
                const firstTouch = evt.touches[0];
                xDown = firstTouch.clientX;
                yDown = firstTouch.clientY;
            }

            function handleTouchMove(evt) {
                if (!xDown || !yDown) {
                    return;
                }

                const xUp = evt.touches[0].clientX;
                const yUp = evt.touches[0].clientY;

                const xDiff = xDown - xUp;
                const yDiff = yDown - yUp;

                if (Math.abs(xDiff) > Math.abs(yDiff)) {
                    if (xDiff > 0) {
                        handleSwipe('left');
                    } else {
                        handleSwipe('right');
                    }
                } else {
                    if (yDiff > 0) {
                        handleSwipe('down');
                    }
                }

                xDown = null;
                yDown = null;
            }

            setInterval(() => {
                dropPiece();
                drawBoard();
                drawPiece();
            }, 500);

            spawnPiece();
        };
    </script>
</body>
</html>
