import json
import requests
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters, CallbackQueryHandler
from config import TELEGRAM_TOKEN, ADMIN_ID, FREE_ANALYSIS_LIMIT, SUPPORT_USERNAME
from binance_data import get_klines
from analysis import analyze_symbol, plot_chart, generate_gpt_analysis
import time

USERS_FILE = "users.json"

def load_users():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump({}, f)
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def start(update: Update, context: CallbackContext):
    user = update.effective_user
    user_id = str(user.id)
    username = user.username
    first_name = user.first_name

    users = load_users()
    if user_id not in users:
        users[user_id] = {
            "subscribed": False,
            "analysis_used": 0,
            "username": username,
            "name": first_name
        }
        save_users(users)

    update.message.reply_text(
    "👋 أهلاً بك في <b>CRYPTO MIND BOT</b>!\n\n"
    "🤖 هذا البوت يقدم لك تحليل فني دقيق وذكي للعملات الرقمية.\n\n"
    "🔹 لاستخدام البوت:\n"
    "1️⃣ أرسل اسم العملة مباشرة مثل: <code>BTCUSDT</code>\n"
    "2️⃣ اختر الفريم الزمني (1h - 4h - 1d)\n"
    "3️⃣ سيصلك تحليل فني + رسم بياني + تحليل ذكي مدعوم\n\n"
    "📌 أوامر البوت:\n"
    "/start - عرض هذه الرسالة\n"
    "/status - معرفة حالة اشتراكك\n"
    "/help - عرض المساعدة\n\n"
    "🎁 أول تحليل مجاني، وبعدها تحتاج اشتراك شهري بـ 20 USDT\n"
    "📞 للاشتراك: <a href='https://t.me/sup_cry'>@sup_cry</a>",
    parse_mode="HTML"
    )

def activate_user(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        update.message.reply_text("❌ ليس لديك صلاحية تنفيذ هذا الأمر.")
        return
    if len(context.args) != 1:
        update.message.reply_text("❌ يجب استخدام الأمر بهذا الشكل: /activate USER_ID")
        return
    user_id = context.args[0]
    users = load_users()
    if user_id in users:
        users[user_id]["subscribed"] = True
        save_users(users)
        update.message.reply_text(f"✅ تم تفعيل الاشتراك للمستخدم {user_id}.")
    else:
        update.message.reply_text("❌ لم يتم العثور على هذا المستخدم.")

def status(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    users = load_users()
    if user_id not in users:
        update.message.reply_text("❌ لم يتم العثور على حسابك في النظام.")
        return
    user = users[user_id]
    subscribed = user.get("subscribed", False)
    used = user.get("analysis_used", 0)
    remaining = max(0, FREE_ANALYSIS_LIMIT - used)
    status_emoji = "✅ مفعل" if subscribed else "❌ غير مفعل"
    msg = "📊 حالة حسابك:\n"
    msg += f"🔐 الاشتراك: {status_emoji}\n"
    msg += f"📈 التحليلات المستخدمة: {used}\n"
    msg += f"🎁 التحليلات المجانية المتبقية: {remaining if not subscribed else '∞'}"
    update.message.reply_text(msg)

def help_command(update: Update, context: CallbackContext):
    msg = (
        "🤖 *بوت تحليل العملات الرقمية*\n\n"
        "✨ أرسل اسم العملة مثل `BTCUSDT` لتحليلها.\n"
        "✅ التحليل مجاني لأول مرة فقط.\n"
        "💳 بعد ذلك، يتطلب اشتراك شهري 20 USDT.\n"
        f"📞 للاشتراك: {SUPPORT_USERNAME}\n\n"
        "🔧 الأوامر:\n"
        "/start - بدء الاستخدام\n"
        "/status - معرفة حالتك\n"
        "/help - عرض هذه الرسالة\n"
    )
    update.message.reply_text(msg, parse_mode="Markdown")

def is_valid_symbol(symbol):
    url = "https://api.binance.com/api/v3/exchangeInfo"
    try:
        response = requests.get(url)
        data = response.json()
        symbols = [item['symbol'] for item in data['symbols']]
        return symbol.upper() in symbols
    except:
        return False

def handle_symbol(update: Update, context: CallbackContext):
    symbol = update.message.text.upper()
    if not is_valid_symbol(symbol):
        update.message.reply_text(f"❌ الرمز '{symbol}' غير صحيح أو غير مدعوم في Binance.")
        return
    user_id = str(update.effective_user.id)
    users = load_users()
    if user_id not in users:
        users[user_id] = {"subscribed": False, "analysis_used": 0}
    subscribed = users[user_id]["subscribed"]
    analysis_used = users[user_id]["analysis_used"]
    if not subscribed and analysis_used >= FREE_ANALYSIS_LIMIT:
        update.message.reply_text(
            f"⚠️ لقد استخدمت التحليل المجاني.\n💳 للاشتراك الشهري (20 USDT)، تواصل معنا: {SUPPORT_USERNAME}"
        )
        return
    keyboard = [
        [InlineKeyboardButton("🕐 1 ساعة", callback_data=f"{symbol}|1h")],
        [InlineKeyboardButton("⏰ 4 ساعات", callback_data=f"{symbol}|4h")],
        [InlineKeyboardButton("📅 يومي", callback_data=f"{symbol}|1d")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        f"🔍 اختر الفريم الذي تريد تحليل {symbol} عليه:",
        reply_markup=reply_markup
    )

def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    try:
        data = query.data
        symbol, tf = data.split("|")
        query.edit_message_text(f"⏳ جاري تحليل {symbol} على فريم {tf}...")
        df = get_klines(symbol, interval=tf, limit=200)
        result = analyze_symbol(df)
        query.message.reply_text(f"📉 *تحليل {symbol} على فريم {tf}:*\n\n{result}", parse_mode="Markdown")
        filename = plot_chart(df, f"{symbol}_{tf}")
        with open(filename, 'rb') as photo:
            query.message.reply_photo(photo=photo)
        os.remove(filename)
        gpt_result = generate_gpt_analysis(symbol, tf, result)
        query.message.reply_text(f"*التحليل :*\n\n{gpt_result}", parse_mode="Markdown")
        user_id = str(query.from_user.id)
        users = load_users()
        if user_id in users and not users[user_id]["subscribed"]:
            users[user_id]["analysis_used"] += 1
            save_users(users)
    except Exception as e:
        query.message.reply_text(f"❌ خطأ أثناء التحليل: {e}")

def users_count(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        update.message.reply_text("🚫 هذا الأمر مخصص للإدارة فقط.")
        return

    users = load_users()
    count = len(users)
    msg = f"👥 عدد المستخدمين الكلي: {count}\n\n"

    for uid, info in users.items():
        name = info.get("name", "—")
        username = info.get("username", "—")
        subscribed = "✅" if info.get("subscribed") else "❌"
        msg += f"🆔 {uid}\n👤 {name} (@{username})\n🔐 اشتراك: {subscribed}\n\n"

    update.message.reply_text(msg)

def broadcast(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        update.message.reply_text("🚫 هذا الأمر مخصص للإدارة فقط.")
        return

    if not context.args:
        update.message.reply_text("❌ استخدم الأمر بهذا الشكل: /broadcast رسالتك هون")
        return

    message = ' '.join(context.args)
    users = load_users()
    success = 0
    failed = 0

    for user_id in users:
        try:
            context.bot.send_message(chat_id=int(user_id), text=message)
            success += 1
            time.sleep(1)
        except:
            failed += 1
            continue

    update.message.reply_text(f"📬 تم الإرسال إلى {success} مستخدم ✅\n❌ فشل الإرسال إلى {failed} مستخدم.")


def main():
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("status", status))
    dp.add_handler(CommandHandler("activate", activate_user))
    dp.add_handler(CommandHandler("broadcast", broadcast))
    dp.add_handler(CommandHandler("users", users_count))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_symbol))
    dp.add_handler(CallbackQueryHandler(button_callback))
    

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
