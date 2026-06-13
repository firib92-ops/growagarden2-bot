import requests
import json
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode

# ================= НАСТРОЙКИ =================
TOKEN = "8908099515:AAGMXzJxBC9kNL16SfJanQdPFNVG4Wm7lMs"
CHANNEL_ID = -1004416824576
API_URL = "https://grow-a-garden-2-tracker.onrender.com/api/stock"

# Файл для сохранения подписок
DATA_FILE = "user_data.json"

# Загрузка данных
try:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        user_data = json.load(f)
except:
    user_data = {}

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

last_stock = None

# ================= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =================
def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(user_data, f, ensure_ascii=False, indent=2)

def format_stock_message(data):
    msg = f"🌱 <b>Обновление стока Grow a Garden 2</b> — {datetime.now().strftime('%H:%M:%S')}\n\n"
    
    # Seeds
    msg += "🌾 <b>Семена:</b>\n"
    try:
        for item in data.get("shops", {}).get("SeedShop_Normal", []):
            if item.get("stock", 0) > 0:
                msg += f"• {item.get('name', 'Unknown')} ({item.get('rarity', 'Common')}) — {item.get('stock', 0)} шт.\n"
    except:
        msg += "Нет данных о семенах\n"
    
    # Crates
    msg += "\n📦 <b>Ящики:</b>\n"
    try:
        for item in data.get("shops", {}).get("CrateShop", []):
            if item.get("stock", 0) > 0:
                msg += f"• {item.get('name', 'Unknown')} ({item.get('rarity', 'Common')}) — {item.get('stock', 0)} шт.\n"
    except:
        msg += "Нет данных о ящиках\n"
    
    # Gears
    msg += "\n⚙️ <b>Снаряжение:</b>\n"
    try:
        for item in data.get("shops", {}).get("GearShop", []):
            if item.get("stock", 0) > 0:
                msg += f"• {item.get('name', 'Unknown')} ({item.get('rarity', 'Common')}) — {item.get('stock', 0)} шт.\n"
    except:
        msg += "Нет данных о снаряжении\n"
    
    msg += "\n🔥 Быстрей в игру! @growagarden2_L"
    return msg

# ================= КОМАНДЫ =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    # Проверка подписки на канал
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=int(user_id))
        if member.status not in ["member", "administrator", "creator"]:
            keyboard = [[InlineKeyboardButton("Подписаться на канал", url="https://t.me/growagarden2_L")]]
            await update.message.reply_text(
                "❗ <b>Для использования бота нужно подписаться на канал!</b>",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )
            return
    except:
        pass

    if user_id not in user_data:
        user_data[user_id] = {"events": True, "stock": True, "seeds": []}
        save_data()

    await update.message.reply_text(
        "🌱 <b>Добро пожаловать в Grow a Garden 2 Tracker!</b>\n\n"
        "Настрой уведомления ниже 👇",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu()
    )

def main_menu():
    keyboard = [
        [InlineKeyboardButton("📢 Ивенты", callback_data="toggle_events")],
        [InlineKeyboardButton("🛒 Сток магазина", callback_data="toggle_stock")],
        [InlineKeyboardButton("🌱 Мои семена", callback_data="seeds_menu")],
        [InlineKeyboardButton("ℹ Инфо", callback_data="info")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ================= ОБРАБОТКА КНОПОК =================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data

    if user_id not in user_data:
        user_data[user_id] = {"events": True, "stock": True, "seeds": []}

    if data == "toggle_events":
        user_data[user_id]["events"] = not user_data[user_id]["events"]
        status = "✅ Включены" if user_data[user_id]["events"] else "❌ Выключены"
        await query.answer(f"Ивенты: {status}")
    elif data == "toggle_stock":
        user_data[user_id]["stock"] = not user_data[user_id]["stock"]
        status = "✅ Включён" if user_data[user_id]["stock"] else "❌ Выключен"
        await query.answer(f"Сток: {status}")
    elif data == "seeds_menu":
        await query.edit_message_text(
            "Отправь названия семян через запятую, на которые хочешь уведомления:\n"
            "Пример: <code>Dragon Fruit, Moon Bloom, Rainbow Seed</code>",
            parse_mode=ParseMode.HTML
        )
        context.user_data["awaiting_seeds"] = user_id
        return
    elif data == "info":
        await query.edit_message_text(
            "🌱 <b>Grow a Garden 2 Tracker Bot</b>\n\n"
            "• Проверяет сток каждые 30 секунд\n"
            "• Отправляет обновления в канал\n"
            "• Персональные уведомления",
            parse_mode=ParseMode.HTML
        )

    await query.edit_message_reply_markup(reply_markup=main_menu())
    save_data()

# ================= ПРОВЕРКА СТОКА =================
async def check_stock(context: ContextTypes.DEFAULT_TYPE):
    global last_stock
    try:
        resp = requests.get(API_URL, timeout=15)
        if resp.status_code != 200:
            return
        data = resp.json()

        if last_stock is None:
            last_stock = data
            return

        stock_msg = format_stock_message(data)
        await context.bot.send_message(chat_id=CHANNEL_ID, text=stock_msg, parse_mode=ParseMode.HTML)

        last_stock = data
        save_data()

    except Exception as e:
        print("Ошибка при проверке стока:", e)

# ================= MAIN =================
def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Проверка стока каждые 30 секунд
    application.job_queue.run_repeating(check_stock, interval=30, first=5)

    print("🤖 Бот Grow a Garden 2 запущен успешно!")
    application.run_polling()

if __name__ == "__main__":
    main()
