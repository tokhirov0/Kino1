import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.environ.get('TOKEN', '8344008207:AAEVYspXdqtHVmwTsQwfxBfxPmIfYtCV0FY')
ADMINS = [int(x) for x in os.environ.get('ADMINS', '6733100026').split(',')]

CHANNELS = [
    '@shaxsiy_blog1o',
    '@kinoda23'
]

bot = telebot.TeleBot(TOKEN)

movies = {}  # kod: {"name": str, "parts": [{"title": str, "file_id": str}]}
ad_text = ""

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
        InlineKeyboardButton("🎬 Kod orqali kino/serial olish", callback_data="get_movie"),
    )
    if is_admin(user_id):
        markup.add(
            InlineKeyboardButton("⚙️ Admin panel", callback_data="admin_panel"),
        )
    return markup

def admin_menu():
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("➕ Serial/kino qo‘shish", callback_data="add_movie"),
        InlineKeyboardButton("📢 Reklama o‘rnatish", callback_data="set_ad"),
        InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_main"),
    )
    return markup

@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.from_user.id
    if not check_channels(user_id):
        markup = InlineKeyboardMarkup()
        for ch in CHANNELS:
            markup.add(InlineKeyboardButton(f"Obuna bo‘lish: {ch}", url=f"https://t.me/{ch.lstrip('@')}"))
        bot.send_message(message.chat.id, "Botdan foydalanish uchun barcha kanallarga obuna bo‘ling!", reply_markup=markup)
        return
    bot.send_message(message.chat.id, "Xush kelibsiz! Kodni yozing yoki menyudan foydalaning 👇", reply_markup=main_menu(user_id))
    if ad_text:
        bot.send_message(message.chat.id, ad_text)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    if call.data == "get_movie":
        bot.send_message(call.message.chat.id, "Kino yoki serial kodi kiriting:")
        bot.register_next_step_handler(call.message, process_code)
    elif call.data == "admin_panel" and is_admin(user_id):
        bot.send_message(call.message.chat.id, "Admin paneliga xush kelibsiz!", reply_markup=admin_menu())
    elif call.data == "add_movie" and is_admin(user_id):
        msg = bot.send_message(call.message.chat.id, "Serial yoki kino nomini kiriting:")
        bot.register_next_step_handler(msg, lambda m: process_movie_name(m, user_id))
    elif call.data == "set_ad" and is_admin(user_id):
        msg = bot.send_message(call.message.chat.id, "Reklama matnini kiriting:")
        bot.register_next_step_handler(msg, process_ad_text)
    elif call.data == "back_to_main":
        bot.send_message(call.message.chat.id, "Asosiy menyu", reply_markup=main_menu(user_id))
    elif call.data.startswith("get_part:"):
        # get_part:<code>:<idx>
        _, code, idx = call.data.split(":")
        idx = int(idx)
        part = movies[code]["parts"][idx]
        bot.send_document(call.message.chat.id, part["file_id"], caption=part["title"])
        if ad_text:
            bot.send_message(call.message.chat.id, ad_text)

def process_code(message):
    code = message.text.strip()
    if code in movies:
        parts = movies[code]["parts"]
        name = movies[code]["name"]
        markup = InlineKeyboardMarkup(row_width=2)
        for idx, part in enumerate(parts):
            markup.add(InlineKeyboardButton(part["title"], callback_data=f"get_part:{code}:{idx}"))
        bot.send_message(message.chat.id, f"\"{name}\" serial/kino qismlari:", reply_markup=markup)
        if ad_text:
            bot.send_message(message.chat.id, ad_text)
    else:
        bot.send_message(message.chat.id, "Bunday kod topilmadi. Kodni tekshirib, qayta urinib ko‘ring.")

def process_movie_name(message, admin_id):
    if not is_admin(admin_id):
        return
    name = message.text.strip()
    msg = bot.send_message(message.chat.id, "Serial/kino uchun kod kiriting (masalan: serial123):")
    bot.register_next_step_handler(msg, lambda m: process_movie_code(m, name))

def process_movie_code(message, name):
    code = message.text.strip()
    if not code or ' ' in code or not code.isalnum():
        msg = bot.send_message(message.chat.id, "Kod faqat lotin harflari va raqamlardan iborat bo‘lishi kerak. Qayta kiriting:")
        bot.register_next_step_handler(msg, lambda m: process_movie_code(m, name))
        return
    if code in movies:
        bot.send_message(message.chat.id, "Bu kod allaqachon mavjud! Boshqa kod tanlang.")
        return
    movies[code] = {"name": name, "parts": []}
    msg = bot.send_message(message.chat.id, "Serial yoki kinoning nechta qismini yuklamoqchisiz? (raqam yozing, masalan: 5):")
    bot.register_next_step_handler(msg, lambda m: process_parts_count(m, code))

def process_parts_count(message, code):
    try:
        count = int(message.text.strip())
        if not (1 <= count <= 100):
            raise Exception
    except Exception:
        msg = bot.send_message(message.chat.id, "Faqat 1 dan 100 gacha bo‘lgan raqam kiriting:")
        bot.register_next_step_handler(msg, lambda m: process_parts_count(m, code))
        return
    movies[code]["expected_parts"] = count
    movies[code]["cur_part"] = 0
    bot.send_message(message.chat.id, f"Endi {count} ta qismlarni ketma-ket yuklang (har bir qism uchun nom va fayl yuboring):")
    ask_next_part(message, code)

def ask_next_part(message, code):
    cur = movies[code]["cur_part"]
    total = movies[code]["expected_parts"]
    if cur >= total:
        del movies[code]["cur_part"]
        del movies[code]["expected_parts"]
        bot.send_message(message.chat.id, f"{movies[code]['name']} yuklandi! Kod: `{code}`", parse_mode="Markdown", reply_markup=admin_menu())
        return
    msg = bot.send_message(message.chat.id, f"{cur+1}-qism nomini kiriting:")
    bot.register_next_step_handler(msg, lambda m: process_part_title(m, code))

def process_part_title(message, code):
    title = message.text.strip()
    msg = bot.send_message(message.chat.id, f"{title} faylini yuboring (yoki fayl id):")
    bot.register_next_step_handler(msg, lambda m: process_part_file(m, code, title))

def process_part_file(message, code, title):
    admin_id = message.from_user.id
    if not is_admin(admin_id): return
    if message.document:
        file_id = message.document.file_id
    else:
        file_id = message.text.strip()
    movies[code]["parts"].append({"title": title, "file_id": file_id})
    movies[code]["cur_part"] += 1
    ask_next_part(message, code)

def process_ad_text(message):
    global ad_text
    admin_id = message.from_user.id
    if not is_admin(admin_id): return
    ad_text = message.text.strip()
    bot.send_message(message.chat.id, "Reklama saqlandi!", reply_markup=admin_menu())

@bot.message_handler(content_types=['text'])
def text_handler(message):
    user_id = message.from_user.id
    text = message.text.strip()
    if not check_channels(user_id):
        markup = InlineKeyboardMarkup()
        for ch in CHANNELS:
            markup.add(InlineKeyboardButton(f"Obuna bo‘lish: {ch}", url=f"https://t.me/{ch.lstrip('@')}"))
        bot.send_message(message.chat.id, "Botdan foydalanish uchun barcha kanallarga obuna bo‘ling!", reply_markup=markup)
        return
    if text in movies:
        process_code(message)
    elif is_admin(user_id) and text.startswith("/admin"):
        bot.send_message(message.chat.id, "Admin paneli", reply_markup=admin_menu())
    else:
        bot.send_message(message.chat.id, "Kod noto‘g‘ri. Kodni tekshirib, qayta urinib ko‘ring yoki menyudan foydalaning.", reply_markup=main_menu(user_id))

if __name__ == "__main__":
    print("Bot ishga tushdi!")
    bot.infinity_polling()
