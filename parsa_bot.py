import asyncio
import logging
import os
import sqlite3
from datetime import datetime
from typing import Optional

import requests
from better_profanity import profanity
from telegram import Update, ChatPermissions
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

BOT_TOKEN = os.getenv('TG_BOT_TOKEN') or '8528331514:AAEAi_Kba3_Y9KXT1eeQoJuZxQ6fHGLy2Y0'
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY') or 'PASTE_WEATHER_KEY'
DB_PATH = 'messages.db'
WELCOME_MESSAGE = "سلام {name} خوش اومدی"
AUTORESPONSES = {'سلام': 'سلام', 'help': ' /help '}

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

profanity.load_censor_words()
CUSTOM_BANNED = set()

def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, user_id INTEGER, username TEXT, chat_id INTEGER, text TEXT, date TEXT)')
    cur.execute('CREATE TABLE IF NOT EXISTS actions (id INTEGER PRIMARY KEY, action TEXT, target_user INTEGER, reason TEXT, date TEXT)')
    conn.commit()
    return conn

DB_CONN = init_db()

def log_message(uid, user, cid, text):
    cur = DB_CONN.cursor()
    cur.execute('INSERT INTO messages (user_id, username, chat_id, text, date) VALUES (?, ?, ?, ?, ?)', (uid, user, cid, text, datetime.utcnow().isoformat()))
    DB_CONN.commit()

def log_action(action, target, reason):
    cur = DB_CONN.cursor()
    cur.execute('INSERT INTO actions (action, target_user, reason, date) VALUES (?, ?, ?, ?)', (action, target, reason or '', datetime.utcnow().isoformat()))
    DB_CONN.commit()

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Parsa bot ready')

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('/kick  /mute  /unmute  /dice  /trivia  /weather')

async def new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for m in update.message.new_chat_members:
        await update.message.reply_text(WELCOME_MESSAGE.format(name=m.full_name))

async def main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    txt = msg.text or ''
    log_message(msg.from_user.id, msg.from_user.username, msg.chat_id, txt)

    if profanity.contains_profanity(txt) or any(w in txt.lower() for w in CUSTOM_BANNED):
        await msg.delete()
        return

    for k, v in AUTORESPONSES.items():
        if k in txt:
            await msg.reply_text(v)
            break

async def kick_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return
    uid = update.message.reply_to_message.from_user.id
    await update.effective_chat.ban_member(uid)
    log_action('kick', uid, None)

async def mute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return
    uid = update.message.reply_to_message.from_user.id
    await update.effective_chat.set_permissions(uid, ChatPermissions(can_send_messages=False))
    log_action('mute', uid, None)

async def unmute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return
    uid = update.message.reply_to_message.from_user.id
    await update.effective_chat.set_permissions(uid, ChatPermissions(can_send_messages=True))
    log_action('unmute', uid, None)

async def dice_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_dice()

async def trivia_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('سوال: پایتخت ایران؟ تهران')

async def weather_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text('شهر؟')
    city = ' '.join(context.args)
    url = f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=fa'
    r = requests.get(url).json()
    if 'main' not in r:
        return await update.message.reply_text('یافت نشد')
    await update.message.reply_text(f"دما: {r['main']['temp']}")

async def rate_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        return await update.message.reply_text('مثال: /rate USD IRR')
    f, t = context.args[0].upper(), context.args[1].upper()
    r = requests.get(f'https://api.exchangerate.host/convert?from={f}&to={t}').json()
    if 'result' not in r:
        return await update.message.reply_text('خطا')
    await update.message.reply_text(f"نرخ: {r['result']}")

async def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler('start', start_cmd))
    app.add_handler(CommandHandler('help', help_cmd))
    app.add_handler(CommandHandler('kick', kick_cmd))
    app.add_handler(CommandHandler('mute', mute_cmd))
    app.add_handler(CommandHandler('unmute', unmute_cmd))
    app.add_handler(CommandHandler('dice', dice_cmd))
    app.add_handler(CommandHandler('trivia', trivia_cmd))
    app.add_handler(CommandHandler('weather', weather_cmd))
    app.add_handler(CommandHandler('rate', rate_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, main_handler))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member))
    await app.run_polling()

import asyncio
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from telegram.ext import Application, CommandHandler, MessageHandler, filters

if __name__ == "__main__":
    import asyncio
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

    
    app = Application.builder().token(BOT_TOKEN).build()

    
    app.add_handler(CommandHandler('start', start_cmd))
    app.add_handler(CommandHandler('help', help_cmd))
    app.add_handler(CommandHandler('kick', kick_cmd))
    app.add_handler(CommandHandler('mute', mute_cmd))
    app.add_handler(CommandHandler('unmute', unmute_cmd))
    app.add_handler(CommandHandler('dice', dice_cmd))
    app.add_handler(CommandHandler('trivia', trivia_cmd))
    app.add_handler(CommandHandler('weather', weather_cmd))
    app.add_handler(CommandHandler('rate', rate_cmd))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, main_handler))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member))

    
    app.run_polling()
