import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
from threading import Thread

# ===== ENVIRONMENT VARIABLES =====
TOKEN = os.environ.get('TOKEN', 'BOT_TOKEN')
ADMINS = [int(x) for x in os.environ.get('ADMINS', '6733100026').split(',')]
CHANNELS = [
    '@shaxsiy_blog1o',
    '@kinoda23'
]

bot = telebot.TeleBot(TOKEN)

movies = {}
serials = {}
ad_text = ""
users = set()

# ===== HELPER FUNKSIYALAR =====
def is_admin(user_id):
    return user_id in ADMINS

def check_channels(user_id):
    for ch in CHANNELS:
        try:
            status = bot.get_chat_member(ch, user_id).status
            if status not in ['member', 'administrator', 'creator']:
                return False
        except Exception:
            return False
    return True

def main_menu(user_id):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🎬 Kino kodi orqali olish", callback_data="get_movie"),
        InlineKeyboardButton("📺 Serial kodi orqali olish", callback_data="get_serial"),
    )
    if is_admin(user_id):
        markup.add(
            InlineKeyboardButton("⚙️ Admin panel", callback_data="admin_panel"),
        )
    return markup

def admin_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("➕ Kino qo‘shish", callback_data="add_movie"),
        InlineKeyboardButton("➕ Serial qo‘shish", callback_data="add_serial"),
    )
    markup.add(
        InlineKeyboardButton("📢 Reklama matni o‘rnatish", callback_data="set_ad"),
        InlineKeyboardButton("🚀 Reklamani hammaga yuborish", callback_data="broadcast_ad"),
    )
    markup.add(
        InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_main"),
    )
    return markup

# ===== START HANDLER =====
@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.from_user.id
    users.add(user_id)
    if not check_channels(user_id):
        markup = InlineKeyboardMarkup()
        for ch in CHANNELS:
            markup.add(InlineKeyboardButton(f"Obuna bo‘lish: {ch}", url=f"https://t.me/{ch.lstrip('@')}"))
        bot.send_message(message.chat.id, "Botdan foydalanish uchun barcha kanallarga obuna bo‘ling!", reply_markup=markup)
        return
    bot.send_message(message.chat.id, "Xush kelibsiz! Kodni yozing yoki menyudan foydalaning 👇", reply_markup=main_menu(user_id))

# ===== CALLBACK HANDLER =====
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    # ... (siz yozgan callback kodlari shu yerda turadi, o‘zgarmaydi)
    pass

# ===== TEXT HANDLER =====
@bot.message_handler(content_types=['text'])
def text_handler(message):
    # ... (siz yozgan text handler kodi shu yerda turadi, o‘zgarmaydi)
    pass

# ===== FLASK SERVER =====
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot ishlayapti ✅"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# ===== BOT POLLING =====
def run_bot():
    print("Bot ishga tushdi!")
    bot.infinity_polling()

if __name__ == "__main__":
    Thread(target=run_flask).start()
    run_bot()
