import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime
import aiohttp

# Данные из переменных Bothost
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID") # Твой числовой ID
CHANNEL_ID = os.getenv("CHANNEL_ID") # ID канала

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Глобальная переменная для статистики
stats = {"posts": 0, "start_time": datetime.now().strftime("%d.%m.%Y %H:%M")}

async def get_usdt_price():
    url = "https://api.binance.com/api/v3/ticker/price?symbol=USDTRUB"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return float(data['price'])
        except Exception as e:
            logging.error(f"Ошибка API: {e}")
            return None

# Функция отправки поста
async def post_price():
    price = await get_usdt_price()
    if price:
        text = f"<b>{round(price, 2)}₽ (1.00$)</b>"
        try:
            await bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode="HTML")
            stats["posts"] += 1
            return True
        except Exception as e:
            logging.error(f"Ошибка отправки: {e}")
    return False

# Фоновая задача
async def auto_post_rate():
    while True:
        await post_price()
        await asyncio.sleep(300)

# --- АДМИН ПАНЕЛЬ ---

def get_admin_kb():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🚀 Опубликовать сейчас", callback_data="post_now"))
    builder.row(types.InlineKeyboardButton(text="📊 Статус и инфо", callback_data="status"))
    builder.row(types.InlineKeyboardButton(text="📢 Перейти в канал", url=f"https://t.me/{str(CHANNEL_ID).replace('-100', '')}"))
    return builder.as_markup()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    # Проверка на админа
    if str(message.from_user.id) != str(ADMIN_ID):
        await message.answer("У вас нет доступа к управлению этим ботом.")
        return

    await message.answer(
        f"👋 <b>Админ-панель</b>\n\nБот работает в канале <code>{CHANNEL_ID}</code>\nИнтервал: 5 минут.",
        reply_markup=get_admin_kb(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "post_now")
async def call_post_now(callback: types.CallbackQuery):
    if str(callback.from_user.id) != str(ADMIN_ID): return
    
    success = await post_price()
    if success:
        await callback.answer("✅ Опубликовано!")
    else:
        await callback.answer("❌ Ошибка при публикации")

@dp.callback_query(F.data == "status")
async def call_status(callback: types.CallbackQuery):
    if str(callback.from_user.id) != str(ADMIN_ID): return
    
    status_text = (
        f"ℹ️ <b>Информация:</b>\n\n"
        f"🔹 Канал: <code>{CHANNEL_ID}</code>\n"
        f"🔹 Постов с запуска: {stats['posts']}\n"
        f"🔹 Бот запущен: {stats['start_time']}\n"
        f"🔹 Статус: Работает ✅"
    )
    await callback.message.edit_text(status_text, reply_markup=get_admin_kb(), parse_mode="HTML")

async def main():
    # Уведомление админа о запуске
    try:
        await bot.send_message(ADMIN_ID, "✅ Бот успешно запущен и начал работу!")
    except:
        pass
        
    asyncio.create_task(auto_post_rate())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
