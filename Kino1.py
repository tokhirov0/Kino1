import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

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

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    users.add(user_id)
    if call.data == "get_movie":
        bot.send_message(call.message.chat.id, "Kino kodi kiriting:")
        bot.register_next_step_handler(call.message, process_movie_code_user)
    elif call.data == "get_serial":
        bot.send_message(call.message.chat.id, "Serial kodi kiriting:")
        bot.register_next_step_handler(call.message, process_serial_code_user)
    elif call.data == "admin_panel" and is_admin(user_id):
        bot.send_message(call.message.chat.id, "Admin paneliga xush kelibsiz!", reply_markup=admin_menu())
    elif call.data == "add_movie" and is_admin(user_id):
        msg = bot.send_message(call.message.chat.id, "Kino nomini kiriting:")
        bot.register_next_step_handler(msg, process_movie_name)
    elif call.data == "add_serial" and is_admin(user_id):
        msg = bot.send_message(call.message.chat.id, "Serial nomini kiriting:")
        bot.register_next_step_handler(msg, process_serial_name)
    elif call.data == "set_ad" and is_admin(user_id):
        msg = bot.send_message(call.message.chat.id, "Reklama matnini kiriting:")
        bot.register_next_step_handler(msg, process_ad_text)
    elif call.data == "broadcast_ad" and is_admin(user_id):
        broadcast_ad(call.message)
    elif call.data == "back_to_main":
        bot.send_message(call.message.chat.id, "Asosiy menyu", reply_markup=main_menu(user_id))
    elif call.data.startswith("get_serial_part:"):
        _, code, idx = call.data.split(":")
        idx = int(idx)
        part = serials[code]["parts"][idx]
        send_media_auto(call.message.chat.id, part["file_id"], caption=part["title"])

def process_movie_code_user(message):
    code = message.text.strip()
    if code in movies:
        data = movies[code]
        bot.send_message(message.chat.id, f"Kino: {data['name']}")
        send_media_auto(message.chat.id, data['file_id'], caption=data['name'])
    else:
        bot.send_message(message.chat.id, "Bunday kodli kino topilmadi.")

def process_serial_code_user(message):
    code = message.text.strip()
    if code in serials:
        data = serials[code]
        markup = InlineKeyboardMarkup(row_width=2)
        for idx, part in enumerate(data["parts"]):
            markup.add(InlineKeyboardButton(part["title"], callback_data=f"get_serial_part:{code}:{idx}"))
        bot.send_message(message.chat.id, f"Serial: {data['name']}\nQismlardan birini tanlang:", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "Bunday kodli serial topilmadi.")

# =========== Kino Qo'shish ==============
def process_movie_name(message):
    admin_id = message.from_user.id
    if not is_admin(admin_id): return
    name = message.text.strip()
    msg = bot.send_message(message.chat.id, "Kino uchun kod kiriting (masalan: kino123):")
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
    msg = bot.send_message(message.chat.id, "Videoni yuboring (fayl sifatida yoki boshqa kanaldan forward qiling):")
    bot.register_next_step_handler(msg, lambda m: process_movie_file(m, name, code))

def extract_file_id(message):
    # Forward qilingan yoki oddiy video/document/audio uchun file_id olish
    if message.video:
        return message.video.file_id
    if message.document:
        if getattr(message.document, 'mime_type', '') and message.document.mime_type.startswith('video'):
            return message.document.file_id
    if message.audio:
        return message.audio.file_id
    return None

def send_media_auto(chat_id, file_id, caption=None):
    try:
        bot.send_video(chat_id, file_id, caption=caption)
    except Exception:
        bot.send_document(chat_id, file_id, caption=caption)

def process_movie_file(message, name, code):
    admin_id = message.from_user.id
    if not is_admin(admin_id): return
    file_id = extract_file_id(message)
    if not file_id:
        bot.send_message(message.chat.id, "Videoni fayl sifatida yuboring yoki boshqa kanaldan forward qiling!")
        return
    movies[code] = {"name": name, "file_id": file_id}
    bot.send_message(message.chat.id, f"Kino yuklandi!\nNomi: {name}\nKod: `{code}`", parse_mode="Markdown", reply_markup=admin_menu())

# =========== Serial Qo'shish ==============
def process_serial_name(message):
    admin_id = message.from_user.id
    if not is_admin(admin_id): return
    name = message.text.strip()
    msg = bot.send_message(message.chat.id, "Serial uchun kod kiriting (masalan: serial123):")
    bot.register_next_step_handler(msg, lambda m: process_serial_code(m, name))

def process_serial_code(message, name):
    code = message.text.strip()
    if not code or ' ' in code or not code.isalnum():
        msg = bot.send_message(message.chat.id, "Kod faqat lotin harflari va raqamlardan iborat bo‘lishi kerak. Qayta kiriting:")
        bot.register_next_step_handler(msg, lambda m: process_serial_code(m, name))
        return
    if code in serials:
        bot.send_message(message.chat.id, "Bu kod allaqachon mavjud! Boshqa kod tanlang.")
        return
    serials[code] = {"name": name, "parts": []}
    msg = bot.send_message(message.chat.id, "Serial nechta qismdan iborat? (raqam):")
    bot.register_next_step_handler(msg, lambda m: process_serial_parts_count(m, code))

def process_serial_parts_count(message, code):
    try:
        count = int(message.text.strip())
        if not (1 <= count <= 100):
            raise Exception
    except Exception:
        msg = bot.send_message(message.chat.id, "Faqat 1 dan 100 gacha bo‘lgan raqam kiriting:")
        bot.register_next_step_handler(msg, lambda m: process_serial_parts_count(m, code))
        return
    serials[code]["expected_parts"] = count
    serials[code]["cur_part"] = 0
    bot.send_message(message.chat.id, f"Endi {count} ta qismlarni ketma-ket yuklang (har bir qism uchun nom va video, fayl yoki forward qiling):")
    ask_next_serial_part(message, code)

def ask_next_serial_part(message, code):
    cur = serials[code]["cur_part"]
    total = serials[code]["expected_parts"]
    if cur >= total:
        del serials[code]["cur_part"]
        del serials[code]["expected_parts"]
        bot.send_message(message.chat.id, f"{serials[code]['name']} serial yuklandi! Kod: `{code}`", parse_mode="Markdown", reply_markup=admin_menu())
        return
    msg = bot.send_message(message.chat.id, f"{cur+1}-qism nomini kiriting:")
    bot.register_next_step_handler(msg, lambda m: process_serial_part_title(m, code))

def process_serial_part_title(message, code):
    title = message.text.strip()
    msg = bot.send_message(message.chat.id, f"{title} videosini yuboring (fayl sifatida yoki boshqa kanaldan forward qiling):")
    bot.register_next_step_handler(msg, lambda m: process_serial_part_file(m, code, title))

def process_serial_part_file(message, code, title):
    admin_id = message.from_user.id
    if not is_admin(admin_id): return
    file_id = extract_file_id(message)
    if not file_id:
        bot.send_message(message.chat.id, "Videoni fayl sifatida yuboring yoki boshqa kanaldan forward qiling!")
        return
    serials[code]["parts"].append({"title": title, "file_id": file_id})
    serials[code]["cur_part"] += 1
    ask_next_serial_part(message, code)

def process_ad_text(message):
    global ad_text
    admin_id = message.from_user.id
    if not is_admin(admin_id): return
    ad_text = message.text.strip()
    bot.send_message(message.chat.id, "Reklama matni saqlandi!", reply_markup=admin_menu())

def broadcast_ad(message):
    admin_id = message.from_user.id
    if not is_admin(admin_id): return
    if not ad_text:
        bot.send_message(message.chat.id, "Reklama matni yo‘q. Avval reklama matnini o‘rnating.", reply_markup=admin_menu())
        return
    count = 0
    for uid in list(users):
        try:
            bot.send_message(uid, ad_text)
            count += 1
        except Exception:
            pass
    bot.send_message(message.chat.id, f"Reklama yuborildi! ({count} ta foydalanuvchiga)", reply_markup=admin_menu())

@bot.message_handler(content_types=['text'])
def text_handler(message):
    user_id = message.from_user.id
    users.add(user_id)
    text = message.text.strip()
    if not check_channels(user_id):
        markup = InlineKeyboardMarkup()
        for ch in CHANNELS:
            markup.add(InlineKeyboardButton(f"Obuna bo‘lish: {ch}", url=f"https://t.me/{ch.lstrip('@')}"))
        bot.send_message(message.chat.id, "Botdan foydalanish uchun barcha kanallarga obuna bo‘ling!", reply_markup=markup)
        return
    if text in movies:
        process_movie_code_user(message)
    elif text in serials:
        process_serial_code_user(message)
    elif is_admin(user_id) and text.startswith("/admin"):
        bot.send_message(message.chat.id, "Admin paneli", reply_markup=admin_menu())
    else:
        bot.send_message(message.chat.id, "Kod noto‘g‘ri. Kino yoki serial kodini kiriting yoki menyudan foydalaning.", reply_markup=main_menu(user_id))

if __name__ == "__main__":
    print("Bot ishga tushdi!")
    bot.infinity_polling()
