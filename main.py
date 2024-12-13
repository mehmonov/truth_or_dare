import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import random
import uuid
import sqlite3
import logging
from questions import truth_questions, dare_challenges

API_TOKEN = '8098150958:AAFCv3Ma6BPy_DYa_ASL0NeCHAU1nK-43aY'

bot = telebot.TeleBot(API_TOKEN)

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

conn = sqlite3.connect('games.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS games (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    partner_id INTEGER,
                    partner_name TEXT,
                    link TEXT,
                    turn TEXT
                 )''')
conn.commit()

# Game mode buttons
def get_game_mode_markup():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Online o'yin 🌐", callback_data='mode_online'))
    markup.add(InlineKeyboardButton("Offline o'yin 🎮", callback_data='mode_offline'))
    markup.add(InlineKeyboardButton("O'yinni to'xtatish 🛑", callback_data='stop_game'))
    return markup

def get_game_markup(is_offline=False):
    markup = InlineKeyboardMarkup()
    if is_offline:
        markup.add(InlineKeyboardButton("Truth 🤔", callback_data='offline_truth'))
        markup.add(InlineKeyboardButton("Dare 💪", callback_data='offline_dare'))
    else:
        markup.add(InlineKeyboardButton("Truth 🤔", callback_data='truth'))
        markup.add(InlineKeyboardButton("Dare 💪", callback_data='dare'))
    markup.add(InlineKeyboardButton("O'yinni to'xtatish 🛑", callback_data='stop_game'))
    return markup

# Handle partner joining the game
@bot.message_handler(func=lambda message: message.text.startswith('/start ') and len(message.text.split()) == 2)
def join_game(message):
    chat_id = message.chat.id
    partner_id = message.from_user.id
    link_param = message.text.split()[1]
    
    # Check if user is already in a game
    cursor.execute("""
        SELECT 1 FROM games 
        WHERE (user_id = ? OR partner_id = ?)
        AND partner_id IS NOT NULL
    """, (partner_id, partner_id))
    if cursor.fetchone():
        bot.send_message(chat_id, "Siz allaqachon boshqa o'yinda qatnashyapsiz!")
        return

    # Get the game details
    cursor.execute("SELECT user_id FROM games WHERE link LIKE ? AND partner_id IS NULL", (f"%{link_param}%",))
    result = cursor.fetchone()
    
    if not result:
        bot.send_message(chat_id, "O'yinni boshlashda xatolik yuz berdi. Yangi o'yin boshlash uchun /start ni bosing.")
        return
        
    user_id = result[0]
    
    # Check if user is trying to play with themselves
    if user_id == partner_id:
        bot.send_message(chat_id, "Siz o'zingiz bilan o'ynay olmaysiz!")
        return
        
    cursor.execute("UPDATE games SET partner_id = ? WHERE user_id = ?", (partner_id, user_id))
    conn.commit()
    bot.send_message(chat_id, "O'yinga muvaffaqiyatli qo'shildingiz! O'yin boshlanmoqda...")
    start_round(user_id)

# Command to start a new game
@bot.message_handler(commands=['start'])
def start_game(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    logger.info(f"New game started by user {user_id} in chat {chat_id}")
    
    bot.send_message(
        chat_id, 
        "O'yin rejimini tanlang:",
        reply_markup=get_game_mode_markup()
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('mode_'))
def handle_mode_selection(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    
    # Check if user is already in a game
    cursor.execute("""
        SELECT 1 FROM games 
        WHERE (user_id = ? OR partner_id = ?)
        AND partner_id IS NOT NULL
    """, (user_id, user_id))
    if cursor.fetchone():
        bot.answer_callback_query(call.id, "Siz allaqachon boshqa o'yinda qatnashyapsiz!")
        return
        
    mode = call.data.split('_')[1]
    
    logger.info(f"User {user_id} selected {mode} mode in chat {chat_id}")
    
    if mode == 'online':
        link = f"https://t.me/{bot.get_me().username}?start={uuid.uuid4()}"
        cursor.execute("INSERT INTO games (user_id, link) VALUES (?, ?)", (user_id, link))
        conn.commit()
        logger.info(f"Created new online game for user {user_id} with link {link}")
        
        bot.edit_message_text(
            "Sherigingizning ismini kiriting:", 
            chat_id, 
            call.message.message_id
        )
        bot.register_next_step_handler(call.message, get_partner_name, link)
    else:
        logger.info(f"Starting offline game setup in chat {chat_id}")
        bot.edit_message_text(
            "Birinchi o'yinchining ismini kiriting:", 
            chat_id, 
            call.message.message_id
        )
        bot.register_next_step_handler(call.message, get_offline_player1_name)

def get_offline_player1_name(message):
    chat_id = message.chat.id
    player1_name = message.text
    bot.send_message(chat_id, "Ikkinchi o'yinchining ismini kiriting:")
    bot.register_next_step_handler(message, get_offline_player2_name, player1_name)

def get_offline_player2_name(message, player1_name):
    chat_id = message.chat.id
    player2_name = message.text
    start_offline_round(chat_id, player1_name, player2_name)

def start_offline_round(chat_id, player1_name, player2_name, current_player=None):
    if current_player is None:
        current_player = random.choice([player1_name, player2_name])
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Truth 🤔", callback_data=f'offline_truth_{current_player}'))
    markup.add(InlineKeyboardButton("Dare 💪", callback_data=f'offline_dare_{current_player}'))
    
    bot.send_message(
        chat_id, 
        f"Navbat: {current_player}\nTanlang:",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('offline_'))
def handle_offline_choice(call):
    chat_id = call.message.chat.id
    action, choice, current_player = call.data.split('_')
    
    if choice == 'truth':
        question = random.choice(truth_questions)
        bot.edit_message_text(
            f"{current_player} uchun savol:\n{question}\n\n"
            "Javob bergandan so'ng, davom etish uchun tugmani bosing:",
            chat_id,
            call.message.message_id,
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("Davom etish ⏭", callback_data=f'offline_next_{current_player}')
            )
        )
    
    elif choice == 'dare':
        challenge = random.choice(dare_challenges)
        bot.edit_message_text(
            f"{current_player} uchun jasorat:\n{challenge}\n\n"
            "Bajarilgandan so'ng, davom etish uchun tugmani bosing:",
            chat_id,
            call.message.message_id,
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("Davom etish ⏭", callback_data=f'offline_next_{current_player}')
            )
        )
    
    elif choice == 'next':
        # Switch to next player
        player_names = current_player.split('|')  # Assuming we store both names in current_player
        if len(player_names) == 2:
            next_player = player_names[1] if current_player == player_names[0] else player_names[0]
            start_offline_round(chat_id, player_names[0], player_names[1], next_player)

def get_partner_name(message, link):
    chat_id = message.chat.id
    user_id = message.from_user.id
    partner_name = message.text
    cursor.execute("UPDATE games SET partner_name = ? WHERE user_id = ?", (partner_name, user_id))
    conn.commit()
    bot.send_message(chat_id, f"Sherigingizga ushbu linkni yuboring: {link}\nSherigingiz link orqali botga kirganda o'yin boshlanadi.")

def start_round(user_id):
    cursor.execute("SELECT partner_id, partner_name FROM games WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if result:
        partner_id, partner_name = result
        current_player = random.choice([user_id, partner_id])
        cursor.execute("UPDATE games SET turn = ? WHERE user_id = ?", (current_player, user_id))
        conn.commit()
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Truth", callback_data='truth'))
        markup.add(InlineKeyboardButton("Dare", callback_data='dare'))
        bot.send_message(current_player, "Sizning navbatingiz! Truth yoki Dare tanlang:", reply_markup=markup)
        bot.send_message(partner_id if current_player == user_id else user_id, "Sherigingiz tanlashini kuting.")

@bot.callback_query_handler(func=lambda call: call.data in ['truth', 'dare'])
def handle_choice(call):
    user_id = call.message.chat.id
    cursor.execute("""
        SELECT user_id, partner_id, turn 
        FROM games 
        WHERE user_id = ? OR partner_id = ?
    """, (user_id, user_id))
    result = cursor.fetchone()
    
    if not result or str(result[2]) != str(user_id):
        bot.answer_callback_query(call.id, "Hozir sizning navbatingiz emas!")
        return
    
    game_owner, partner_id, current_turn = result
    other_player = partner_id if user_id == game_owner else game_owner
    
    if call.data == 'truth':
        question = random.choice(truth_questions)
        bot.edit_message_text(
            f"Savol: {question}\n\nIltimos, ovozli xabar yoki matn ko'rinishida javob bering.", 
            call.message.chat.id, 
            call.message.message_id
        )
        # Sherigiga xabar
        bot.send_message(other_player, f"Sherigingizga berilgan savol: {question}\n\nUning javobini kuting.")
        
    else:  # dare
        challenge = random.choice(dare_challenges)
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Bajarildi ✅", callback_data=f'completed_{user_id}'))
        bot.edit_message_text(
            f"Jasorat: {challenge}", 
            call.message.chat.id, 
            call.message.message_id
        )
        # Sherigiga xabar va tugma
        bot.send_message(
            other_player, 
            f"Sherigingizga berilgan jasorat: {challenge}\n\nSherigingiz bajarganidan keyin tugmani bosing:", 
            reply_markup=markup
        )

@bot.message_handler(content_types=['voice', 'text'])
def handle_truth_response(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    logger.info(f"Received truth response from user {user_id} in chat {chat_id}")
    
    cursor.execute("""
        SELECT user_id, partner_id, turn 
        FROM games 
        WHERE (user_id = ? OR partner_id = ?)
    """, (user_id, user_id))
    result = cursor.fetchone()
    
    if not result or str(result[2]) != str(user_id):
        logger.warning(f"Invalid truth response from user {user_id}: not their turn or game not found")
        return
        
    game_owner, partner_id, _ = result
    other_player = partner_id if user_id == game_owner else game_owner
    
    # Javobni sherigiga yuborish
    if message.content_type == 'voice':
        bot.forward_message(other_player, message.chat.id, message.message_id)
    else:
        bot.send_message(other_player, f"Sherigingizning javobi: {message.text}")
    
    # Tasdiqlash tugmasini yuborish
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Bajarildi ✅", callback_data=f'completed_{user_id}'))
    bot.send_message(other_player, "Javobni qabul qildingizmi?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('completed_'))
def handle_completion(call):
    user_id = call.message.chat.id
    player_completed = call.data.split('_')[1]
    
    cursor.execute("""
        SELECT user_id, partner_id 
        FROM games 
        WHERE (user_id = ? OR partner_id = ?)
    """, (user_id, user_id))
    result = cursor.fetchone()
    
    if not result:
        bot.answer_callback_query(call.id, "O'yin topilmadi.")
        return
        
    game_owner, partner_id = result
    current_player = int(player_completed)
    
    # Faqat sherik tasdiqlashi mumkin
    if str(user_id) == str(player_completed):
        bot.answer_callback_query(call.id, "Faqat sherigingiz tasdiqlashi mumkin!")
        return
    
    bot.edit_message_text("Bajarildi ✅", call.message.chat.id, call.message.message_id)
    bot.send_message(current_player, "Sherigingiz bajarilganini tasdiqladi!")
    
    # Navbatni almashtirish
    next_player = partner_id if current_player == game_owner else game_owner
    cursor.execute("UPDATE games SET turn = ? WHERE user_id = ?", (next_player, game_owner))
    conn.commit()
    
    # Yangi raundni boshlash
    start_round(game_owner)

@bot.callback_query_handler(func=lambda call: call.data == 'stop_game')
def stop_game_handler(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    
    logger.info(f"User {user_id} requested to stop the game in chat {chat_id}")
    
    # Online o'yinni to'xtatish
    cursor.execute("""
        SELECT user_id, partner_id 
        FROM games 
        WHERE user_id = ? OR partner_id = ?
    """, (user_id, user_id))
    game = cursor.fetchone()
    
    if game:
        game_owner, partner_id = game
        # Ikkala o'yinchiga xabar yuborish
        for player_id in [game_owner, partner_id]:
            if player_id:
                try:
                    bot.send_message(player_id, "O'yin to'xtatildi! Yangi o'yin boshlash uchun /start ni bosing.")
                except Exception as e:
                    logger.error(f"Error sending stop message to user {player_id}: {e}")
        
        # O'yinni bazadan o'chirish
        cursor.execute("DELETE FROM games WHERE user_id = ?", (game_owner,))
        conn.commit()
        logger.info(f"Game deleted for users {game_owner} and {partner_id}")
    else:
        # Offline o'yin to'xtatish
        bot.edit_message_text(
            "O'yin to'xtatildi! Yangi o'yin boshlash uchun /start ni bosing.",
            chat_id,
            call.message.message_id
        )
    
    logger.info(f"Game stopped successfully in chat {chat_id}")

# Error handler
bot.polling(none_stop=True)
