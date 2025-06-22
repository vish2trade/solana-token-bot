import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import ClientSession

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
MORALIS_API_KEY = os.getenv("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJub25jZSI6IjMwNDIzOTBiLTllYzUtNDc0MS04MzUyLWUxYWNmZWY2OTAyYSIsIm9yZ0lkIjoiNDU1MTgwIiwidXNlcklkIjoiNDY4MzIxIiwidHlwZUlkIjoiMjE5MjM4MTctNDg5OC00MWQwLWIzZDAtMTE5Yzk1YzVjNDU5IiwidHlwZSI6IlBST0pFQ1QiLCJpYXQiOjE3NTA1NzczMDYsImV4cCI6NDkwNjMzNzMwNn0.CumR9gZhYJPPH2kyOkbSHaOr7_ZmOO5HRY1sZI_CrUk")

bot = Bot(token=8153543416:AAEtks8sag5BZKDMwb0l2J7z8mzcdOhwRnQ, parse_mode=types.ParseMode.MARKDOWN)
dp = Dispatcher(bot)

async def get_new_tokens():
    url = "https://deep-index.moralis.io/api/v2/erc20/tokens"
    headers = {"X-API-Key": MORALIS_API_KEY}

    async with ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                # Filter logic placeholder
                return data.get("result", [])
            else:
                print("Error fetching token data")
                return []

async def monitor_tokens():
    while True:
        tokens = await get_new_tokens()
        for token in tokens:
            # Apply your filters here
            if token.get("volume") and float(token["volume"]) >= 10000:
                token_name = token.get("name")
                token_address = token.get("token_address")
                message = f"\ud83d\ude80 *New Token Detected!*\n\n*Name:* {token_name}\n*Address:* `{token_address}`"
                await bot.send_message(chat_id="@LaunchCoinFinderBot", text=message)

        await asyncio.sleep(60)  # Check every 1 minute

@dp.message_handler(commands=["start", "status"])
async def cmd_status(message: types.Message):
    await message.reply("\u2705 Bot is running and monitoring tokens.")

async def main():
    # Start token monitoring in background
    asyncio.create_task(monitor_tokens())
    # Start bot polling
    await dp.start_polling()

if __name__ == "__main__":
    asyncio.run(main())
