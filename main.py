import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime
import aiohttp

# Настройки из переменных Bothost
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

raw_channel_id = os.getenv("CHANNEL_ID")
try:
    CHANNEL_ID = int(raw_channel_id)
except (ValueError, TypeError):
    CHANNEL_ID = raw_channel_id

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

stats = {"posts": 0, "start_time": datetime.now().strftime("%d.%m.%Y %H:%M")}

async def get_usdt_price():
    """Получаем курс напрямую с CoinGecko (как на твоем скриншоте)"""
    url = "https://api.coingecko.com/api/v3/simple/price?ids=tether&vs_currencies=rub"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    # Извлекаем цену из формата {"tether": {"rub": 71.04}}
                    price = data['tether']['rub']
                    return float(price)
                else:
                    logging.error(f"CoinGecko ошибка: {response.status}")
                    return None
        except Exception as e:
            logging.error(f"Ошибка запроса к CoinGecko: {e}")
            return None

async def post_price():
    price = await get_usdt_price()
    if price:
        # Формат: 71.04₽ (1.00$)
        text = f"<b>{round(price, 2)}₽ (1.00$)</b>"
        try:
            await bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode="HTML")
            stats["posts"] += 1
            return True
        except Exception as e:
            logging.error(f"Ошибка отправки: {e}")
    return False

async def auto_post_rate():
    while True:
        await post_price()
        await asyncio.sleep(300) # 5 минут

# --- АДМИН ПАНЕЛЬ ---

def get_admin_kb():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🚀 Опубликовать сейчас", callback_data="post_now"))
    builder.row(types.InlineKeyboardButton(text="📊 Статус", callback_data="status"))
    return builder.as_markup()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    await message.answer(f"⚙️ <b>Админка (CoinGecko)</b>\nКанал: <code>{CHANNEL_ID}</code>", 
                         reply_markup=get_admin_kb(), parse_mode="HTML")

@dp.callback_query(F.data == "post_now")
async def call_post_now(callback: types.CallbackQuery):
    await callback.answer("⏳ Запрос к CoinGecko...")
    success = await post_price()
    if success:
        await callback.message.answer("✅ Курс отправлен в канал!")
    else:
        await callback.message.answer("❌ Ошибка получения данных.")

@dp.callback_query(F.data == "status")
async def call_status(callback: types.CallbackQuery):
    status_text = (
        f"ℹ️ <b>Инфо (CoinGecko):</b>\n"
        f"🔹 Канал: <code>{CHANNEL_ID}</code>\n"
        f"🔹 Постов сделано: {stats['posts']}\n"
        f"🔹 Источник: CoinGecko API\n"
        f"🕒 Время: {datetime.now().strftime('%H:%M:%S')}"
    )
    try:
        await callback.message.edit_text(status_text, reply_markup=get_admin_kb(), parse_mode="HTML")
    except Exception:
        await callback.answer("Данные не изменились")

async def main():
    asyncio.create_task(auto_post_rate())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
