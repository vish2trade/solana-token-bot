
import requests, time, csv, schedule
from datetime import datetime, timezone
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler
from keep_alive import keep_alive

# === CONFIG ===
MORALIS_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJub25jZSI6IjMwNDIzOTBiLTllYzUtNDc0MS04MzUyLWUxYWNmZWY2OTAyYSIsIm9yZ0lkIjoiNDU1MTgwIiwidXNlcklkIjoiNDY4MzIxIiwidHlwZUlkIjoiMjE5MjM4MTctNDg5OC00MWQwLWIzZDAtMTE5Yzk1YzVjNDU5IiwidHlwZSI6IlBST0pFQ1QiLCJpYXQiOjE3NTA1NzczMDYsImV4cCI6NDkwNjMzNzMwNn0.CumR9gZhYJPPH2kyOkbSHaOr7_ZmOO5HRY1sZI_CrUk"
BOT_TOKEN = "8153543416:AAEtks8sag5BZKDMwb0l2J7z8mzcdOhwRnQ"
CHAT_ID = 987046763
MIN_VOLUME = 10000
MAX_HOLDER_PERCENT = 15
MAX_AGE_MINUTES = 60
PAUSED = False

bot = Bot(token=BOT_TOKEN)
updater = Updater(token=BOT_TOKEN, use_context=True)
dispatcher = updater.dispatcher

# === COMMAND HANDLERS ===
def pause(update, context):
    global PAUSED
    PAUSED = True
    update.message.reply_text("⏸ Bot paused.")

def resume(update, context):
    global PAUSED
    PAUSED = False
    update.message.reply_text("▶️ Bot resumed.")

def status(update, context):
    update.message.reply_text(
        f"🤖 Bot is running.\n"
        f"Volume: {MIN_VOLUME}, Age: {MAX_AGE_MINUTES} min\n"
        f"Paused: {PAUSED}"
    )

def set_volume(update, context):
    global MIN_VOLUME
    MIN_VOLUME = int(context.args[0])
    update.message.reply_text(f"📊 Min volume set to {MIN_VOLUME}")

def set_age(update, context):
    global MAX_AGE_MINUTES
    MAX_AGE_MINUTES = int(context.args[0])
    update.message.reply_text(f"⏱ Max age set to {MAX_AGE_MINUTES} minutes")

dispatcher.add_handler(CommandHandler("pause", pause))
dispatcher.add_handler(CommandHandler("resume", resume))
dispatcher.add_handler(CommandHandler("status", status))
dispatcher.add_handler(CommandHandler("setvolume", set_volume))
dispatcher.add_handler(CommandHandler("setage", set_age))

# === STARTUP MESSAGE ===
bot.send_message(chat_id=CHAT_ID, text="✅ Bot started! Monitoring EVM & Solana tokens...", parse_mode='Markdown')


import requests

def get_recent_solana_tokens():
    url = "https://api.helius.xyz/v0/addresses/11111111111111111111111111111111/transactions?limit=20&api-key=51534aa1-3f4f-4d16-996d-2a403ca359e6"
    try:
        resp = requests.get(url)
        if resp.status_code != 200:
            print("❌ Helius error", resp.status_code)
            return []

        txs = resp.json()
        new_tokens = []
        for tx in txs:
            for instr in tx.get("instructions", []):
                if instr.get("programId") == "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA" and instr.get("parsed", {}).get("type") == "initializeMint":
                    mint_addr = instr.get("accounts", [])[0]
                    new_tokens.append(mint_addr)
        return list(set(new_tokens))
    except Exception as e:
        print("Helius fetch error:", e)
        return []

def check_solana_token_with_goplus(token_address):
    try:
        goplus_url = "https://api.gopluslabs.io/api/v1/token_security/solana?contract_addresses=" + token_address
        response = requests.get(goplus_url)
        if response.status_code == 200:
            result = response.json().get("result", {})
            return result.get(token_address)
    except Exception as e:
        print("GoPlus error:", e)
    return None

def check_holder_percentage(token_address):
    try:
        url = f"https://api.helius.xyz/v0/tokens/{token_address}/holders?api-key=51534aa1-3f4f-4d16-996d-2a403ca359e6"
        resp = requests.get(url)
        if resp.status_code != 200:
            return False
        data = resp.json()
        if not data or "holders" not in data:
            return False
        holders = data["holders"]
        for holder in holders[:3]:
            percent = float(holder.get("percentage", 0))
            if percent > 15:
                return False
        return True
    except Exception as e:
        print("Holder check error:", e)
        return False

# === TOKEN MONITORING ===
def check_new_tokens():
    if PAUSED:
        return

    now = datetime.now(timezone.utc)
    headers = {"X-API-Key": MORALIS_API_KEY}
    chains = ['eth', 'bsc', 'arbitrum', 'base']

    for chain in chains:
        url = f"https://deep-index.moralis.io/api/v2/erc20/metadata?chain={chain}"
        try:
            resp = requests.get(url, headers=headers)
            if resp.status_code != 200:
                continue
            # Stub: Replace with real filter logic using Moralis data
        except Exception as e:
            print("Error EVM:", e)

    # --- Real Solana token check with holder filter ---
    try:
        new_tokens = get_recent_solana_tokens()
        for token_addr in new_tokens:
            goplus_data = check_solana_token_with_goplus(token_addr)
            if goplus_data and goplus_data.get("is_open_source") == "1" and goplus_data.get("can_take_back_ownership") == "0":
                if check_holder_percentage(token_addr):
                    msg = (
                        f"🚀 *New Solana Token*\n"
                        f"*Address:* `{token_addr}`\n"
                        f"_Ownership Renounced: Yes_\n"
                        f"_Top holder ≤ 15%_"
                    )
                    btns = [[
                        InlineKeyboardButton("🔍 Solscan", url=f"https://solscan.io/token/{token_addr}")
                    ]]
                    bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(btns))
    except Exception as e:
        print("Solana live error:", e)

    try:
        sol_token = {"name": "SolBot", "symbol": "SBOT", "address": "So11111111111111111111111111111111111111112", "age": 5}
        if sol_token["age"] <= MAX_AGE_MINUTES:
            message = (
                f"🚀 *New Solana Token*\n"
                f"*Name:* {sol_token['name']} ({sol_token['symbol']})\n"
                f"*Address:* `{sol_token['address']}`"
            )
            buttons = [[
                InlineKeyboardButton("🔍 Solscan", url=f"https://solscan.io/token/{sol_token['address']}")
            ]]
            bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        print("Error Solana:", e)

schedule.every(60).seconds.do(check_new_tokens)

print("✅ Bot is running...")
updater.start_polling()
keep_alive()

while True:
    schedule.run_pending()
    time.sleep(5)
