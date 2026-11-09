import sqlite3
import time
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

BOT_TOKEN = "9047569413:AAERUCexp07o4bxBNIT6Dh9jeqY"
ADMIN_ID = 7103959220
ADMIN_GROUP_ID = -1004196202579
DEFAULT_GROUP = "https://t.me/TaskCashBDGroup"

# Conversation States
(
    SUBMIT_PROOF,
    WITHDRAW_METHOD,
    WITHDRAW_ACCOUNT,
    WITHDRAW_AMOUNT
) = range(4)

def init_db():
    conn = sqlite3.connect("earning_bot.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        name TEXT,
        balance REAL DEFAULT 0,
        completed_tasks INTEGER DEFAULT 0,
        referred_by INTEGER DEFAULT 0,
        is_banned INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    c.execute("INSERT OR IGNORE INTO settings VALUES ('min_withdraw', '50')")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('ref_reward', '5')")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('task_desc', 'আমাদের ইউটিউব চ্যানেল সাবস্ক্রাইব করুন এবং স্ক্রিনশট দিন।')")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('task_reward', '2')")
    conn.commit()
    conn.close()

def get_setting(key):
    conn = sqlite3.connect("earning_bot.db")
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else ""

def get_user(user_id):
    conn = sqlite3.connect("earning_bot.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

def update_balance(user_id, amount):
    conn = sqlite3.connect("earning_bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()

def get_main_keyboard():
    keyboard = [
        [KeyboardButton("💰 ব্যালেন্স"), KeyboardButton("📋 কাজ করুন")],
        [KeyboardButton("👥 রেফার লিংক"), KeyboardButton("💳 টাকা উত্তোলন")],
        [KeyboardButton("📢 হেল্প / সাপোর্ট")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    referrer = 0

    if args and args[0].isdigit():
        referrer = int(args[0])

    conn = sqlite3.connect("earning_bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE user_id=?", (user.id,))
    existing = c.fetchone()

    if not existing:
        c.execute(
            "INSERT INTO users (user_id, name, referred_by) VALUES (?, ?, ?)",
            (user.id, user.first_name, referrer)
        )
        conn.commit()
        if referrer and referrer != user.id:
            ref_amt = float(get_setting('ref_reward'))
            c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (ref_amt, referrer))
            conn.commit()
            try:
                await context.bot.send_message(
                    chat_id=referrer,
                    text=f"🎉 আপনার রেফারেল লিংকে নতুন মেম্বার জয়েন করেছে! {ref_amt} টাকা বোনাস যোগ হয়েছে।"
                )
            except Exception:
                pass
    conn.close()

    welcome_text = (
        f"স্বাগতম {user.first_name}! 👋\n\n"
        f"টাস্ক ক্যাশ বিডি বটে কাজ করে সহজে আয় করুন। নিচের বাটনগুলো ব্যবহার করুন।"
    )
    await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard())

async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = get_user(update.effective_user.id)
    if not u:
        return
    text = (
        f"👤 নাম: {u[1]}\n"
        f"🆔 আইডি: {u[0]}\n"
        f"💵 ব্যালেন্স: {u[2]:.2f} টাকা\n"
        f"✅ সম্পন্ন টাস্ক: {u[3]} টি"
    )
    await update.message.reply_text(text)

async def start_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    desc = get_setting('task_desc')
    reward = get_setting('task_reward')
    text = (
        f"📌 কাজের বিবরণ:\n\n{desc}\n\n"
        f"💰 কাজের বোনাস: {reward} টাকা\n\n"
        f"কাজ শেষ করে স্ক্রিনশট পাঠান। অ্যাডমিন গ্রুপে চেক করে অনুমোদন দিলে ব্যালেন্স যোগ হবে।"
    )
    await update.message.reply_text(text)
    return SUBMIT_PROOF

async def handle_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    reward = get_setting('task_reward')

    keyboard = [
        [
            InlineKeyboardButton("✅ অ্যাপ্রুভ", callback_data=f"apptask_{user.id}_{reward}"),
            InlineKeyboardButton("❌ বাতিল", callback_data=f"rejtask_{user.id}")
        ]
    ]

    caption = (
        f"📩 নতুন টাস্ক সাবমিশন!\n\n"
        f"👤 ইউজার: {user.first_name} (@{user.username})\n"
        f"🆔 আইডি: `{user.id}`\n"
        f"💵 বোনাস হবে: {reward} টাকা"
    )

    if update.message.photo:
        photo_file_id = update.message.photo[-1].file_id
        await context.bot.send_photo(
            chat_id=ADMIN_GROUP_ID,
            photo=photo_file_id,
            caption=caption,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    else:
        text_proof = update.message.text
        await context.bot.send_message(
            chat_id=ADMIN_GROUP_ID,
            text=f"{caption}\n\n📝 প্রুফ টেক্সট:\n{text_proof}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    await update.message.reply_text(
        "✅ আপনার কাজের প্রমাণ অ্যাডমিন গ্রুপে পাঠানো হয়েছে! অ্যাডমিন চেক করে অনুমোদন দিলে ব্যালেন্স যোগ হবে।",
        reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END

async def refer_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_info = await context.bot.get_me()
    uid = update.effective_user.id
    ref_amt = get_setting('ref_reward')
    link = f"https://t.me/{bot_info.username}?start={uid}"
    text = (
        f"👥 আপনার রেফারেল লিংক:\n`{link}`\n\n"
        f"প্রতি সফল রেফারে পাবেন: {ref_amt} টাকা।"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def help_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"যেকোনো হেল্প বা সাপোর্টের জন্য জয়েন করুন:\n{DEFAULT_GROUP}")

async def start_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = get_user(update.effective_user.id)
    min_wd = float(get_setting('min_withdraw'))
    
    if not u or u[2] < min_wd:
        await update.message.reply_text(
            f"❌ উত্তোলনের জন্য পর্যাপ্ত ব্যালেন্স নেই।\nসর্বনিম্ন উত্তোলন: {min_wd} টাকা।\nআপনার ব্যালেন্স: {u[2] if u else 0:.2f} টাকা।"
        )
        return ConversationHandler.END

    keyboard = [
        [
            InlineKeyboardButton("বিকাশ (bKash)", callback_data="wd_bkash"),
            InlineKeyboardButton("নগদ (Nagad)", callback_data="wd_nagad")
        ],
        [
            InlineKeyboardButton("💵 ডলার (USDT / Binance Pay)", callback_data="wd_usdt")
        ]
    ]
    await update.message.reply_text(
        "উত্তোলনের মাধ্যম নির্বাচন করুন:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return WITHDRAW_METHOD

async def method_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    method_map = {
        "wd_bkash": "বিকাশ (bKash)",
        "wd_nagad": "নগদ (Nagad)",
        "wd_usdt": "USDT / Binance Pay"
    }
    method = method_map.get(query.data, "অন্যান্য")
    context.user_data['withdraw_method'] = method

    msg = f"আপনি নির্বাচন করেছেন: {method}\n\n"
    if query.data == "wd_usdt":
        msg += "আপনার Binance Pay ID অথবা USDT (TRC20 / BEP20) অ্যাড্রেস দিন:"
    else:
        msg += f"আপনার {method} নম্বরটি লিখে পাঠান:"

    await query.message.edit_text(msg)
    return WITHDRAW_ACCOUNT

async def get_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    account = update.message.text.strip()
    context.user_data['withdraw_account'] = account
    u = get_user(update.effective_user.id)
    min_wd = get_setting('min_withdraw')

    await update.message.reply_text(
        f"কত টাকা বা সমমূল্যের উত্তোলন করতে চান?\n(সর্বনিম্ন: {min_wd} টাকা | আপনার ব্যালেন্স: {u[2]:.2f} টাকা)"
    )
    return WITHDRAW_AMOUNT

async def get_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val_text = update.message.text.strip()
    try:
        amount = float(val_text)
    except ValueError:
        await update.message.reply_text("❌ টাকার পরিমাণ শুধু সংখ্যায় লিখুন:")
        return WITHDRAW_AMOUNT

    user = update.effective_user
    u = get_user(user.id)
    min_wd = float(get_setting('min_withdraw'))

    if amount < min_wd:
        await update.message.reply_text(f"❌ সর্বনিম্ন উত্তোলনের পরিমাণ {min_wd} টাকা। আবার লিখুন:")
        return WITHDRAW_AMOUNT

    if amount > u[2]:
        await update.message.reply_text(f"❌ আপনার ব্যালেন্স পর্যাপ্ত নয়! বর্তমান ব্যালেন্স: {u[2]:.2f} টাকা।")
        return WITHDRAW_AMOUNT

    update_balance(user.id, -amount)
    method = context.user_data.get('withdraw_method', 'N/A')
    account = context.user_data.get('withdraw_account', 'N/A')

    await update.message.reply_text(
        f"✅ উত্তোলনের অনুরোধ সফলভাবে জমা হয়েছে!\n\n"
        f"💳 মাধ্যম: {method}\n"
        f"📌 একাউন্ট/নম্বর: `{account}`\n"
        f"💵 পরিমাণ: {amount} টাকা\n\n"
        f"অ্যাডমিন চেক করে দ্রুত পেমেন্ট সম্পন্ন করবে।",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

    admin_kb = [
        [
            InlineKeyboardButton("✅ পেমেন্ট সম্পন্ন", callback_data=f"appwd_{user.id}_{amount}"),
            InlineKeyboardButton("❌ রিজেক্ট (টাকা ফেরত)", callback_data=f"rejwd_{user.id}_{amount}")
        ]
    ]

    admin_msg = (
        f"🚨 **নতুন উত্তোলনের অনুরোধ!**\n\n"
        f"👤 নাম: {user.first_name} (@{user.username})\n"
        f"🆔 ইউজার আইডি: `{user.id}`\n"
        f"💳 মাধ্যম: {method}\n"
        f"📌 একাউন্ট: `{account}`\n"
        f"💵 পরিমাণ: {amount} টাকা"
    )

    try:
        await context.bot.send_message(
            chat_id=ADMIN_GROUP_ID,
            text=admin_msg,
            reply_markup=InlineKeyboardMarkup(admin_kb),
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Admin group error: {e}")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("বাতিল করা হয়েছে।", reply_markup=get_main_keyboard())
    return ConversationHandler.END

async def group_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data.startswith("apptask_"):
        _, uid, amt = data.split("_")
        uid, amt = int(uid), float(amt)
        update_balance(uid, amt)
        
        conn = sqlite3.connect("earning_bot.db")
        c = conn.cursor()
        c.execute("UPDATE users SET completed_tasks = completed_tasks + 1 WHERE user_id=?", (uid,))
        conn.commit()
        conn.close()

        await query.answer("টাস্ক অ্যাপ্রুভ হয়েছে!")
        try:
            await query.edit_message_caption(caption=f"{query.message.caption}\n\n✅ [অনুমোদিত - {query.from_user.first_name}]")
        except Exception:
            await query.edit_message_text(text=f"{query.message.text}\n\n✅ [অনুমোদিত - {query.from_user.first_name}]")
        try:
            await context.bot.send_message(chat_id=uid, text=f"🎉 আপনার টাস্ক অ্যাপ্রুভ হয়েছে! {amt} টাকা ব্যালেন্সে যোগ করা হয়েছে।")
        except Exception:
            pass

    elif data.startswith("rejtask_"):
        _, uid = data.split("_")
        uid = int(uid)
        await query.answer("টাস্ক বাতিল করা হয়েছে!")
        try:
            await query.edit_message_caption(caption=f"{query.message.caption}\n\n❌ [বাতিল করা হয়েছে]")
        except Exception:
            await query.edit_message_text(text=f"{query.message.text}\n\n❌ [বাতিল করা হয়েছে]")
        try:
            await context.bot.send_message(chat_id=uid, text="❌ দুঃখিত, আপনার দেওয়া টাস্ক প্রমাণটি সঠিক ছিল না বলে বাতিল করা হয়েছে।")
        except Exception:
            pass

    elif data.startswith("appwd_"):
        _, uid, amt = data.split("_")
        await query.answer("পেমেন্ট সফল হিসেবে চিহ্নিত!")
        await query.edit_message_text(text=f"{query.message.text}\n\n✅ [পেমেন্ট সাকসেসফুল - {query.from_user.first_name}]")
        try:
            await context.bot.send_message(chat_id=int(uid), text=f"🎉 আপনার {amt} টাকার উইথড্র পেমেন্ট সফলভাবে পাঠানো হয়েছে। ধন্যবাদ!")
        except Exception:
            pass

    elif data.startswith("rejwd_"):
        _, uid, amt = data.split("_")
        uid, amt = int(uid), float(amt)
        update_balance(uid, amt)
        await query.answer("উইথড্র বাতিল এবং ব্যালেন্স ফেরত দেওয়া হয়েছে!")
        await query.edit_message_text(text=f"{query.message.text}\n\n❌ [উইথড্র বাতিল এবং টাকা ব্যালেন্সে ফেরত হয়েছে]")
        try:
            await context.bot.send_message(chat_id=uid, text=f"❌ আপনার {amt} টাকার উইথড্র বাতিল করা হয়েছে এবং টাকা আপনার ব্যালেন্সে ফেরত পাঠানো হয়েছে।")
        except Exception:
            pass

async def add_balance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        target_uid = int(context.args[0])
        amt = float(context.args[1])
        update_balance(target_uid, amt)
        await update.message.reply_text(f"✅ ইউজার `{target_uid}`-এর ব্যালেন্সে {amt} টাকা যোগ করা হয়েছে।", parse_mode="Markdown")
        try:
            await context.bot.send_message(chat_id=target_uid, text=f"🎁 অ্যাডমিন আপনার ব্যালেন্সে {amt} টাকা যোগ করেছেন।")
        except Exception:
            pass
    except Exception:
        await update.message.reply_text("ভুল ফরম্যাট! এভাবে লিখুন: `/addbalance [ইউজার_আইডি] [টাকা]`", parse_mode="Markdown")

async def cut_balance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        target_uid = int(context.args[0])
        amt = float(context.args[1])
        update_balance(target_uid, -amt)
        await update.message.reply_text(f"✅ ইউজার `{target_uid}`-এর ব্যালেন্স থেকে {amt} টাকা কাটা হয়েছে।", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("ভুল ফরম্যাট! এভাবে লিখুন: `/cutbalance [ইউজার_আইডি] [টাকা]`", parse_mode="Markdown")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    conn = sqlite3.connect("earning_bot.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*), SUM(balance) FROM users")
    total_users, total_bal = c.fetchone()
    conn.close()

    text = (
        f"👑 **অ্যাডমিন কন্ট্রোল প্যানেল**\n\n"
        f"👥 মোট ইউজার: {total_users}\n"
        f"💰 ইউজারদের মোট ব্যালেন্স: {total_bal if total_bal else 0:.2f} টাকা\n\n"
        f"📌 কমান্ডসমূহ:\n"
        f"👉 ব্যালেন্স দিতে: `/addbalance [আইডি] [টাকা]`\n"
        f"👉 ব্যালেন্স কাটতে: `/cutbalance [আইডি] [টাকা]`"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

def main():
    init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("addbalance", add_balance_cmd))
    app.add_handler(CommandHandler("cutbalance", cut_balance_cmd))

    withdraw_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^💳 টাকা উত্তোলন$"), start_withdraw),
            CallbackQueryHandler(method_chosen, pattern="^wd_(bkash|nagad|usdt)$")
        ],
        states={
            WITHDRAW_METHOD: [
                CallbackQueryHandler(method_chosen, pattern="^wd_(bkash|nagad|usdt)$")
            ],
            WITHDRAW_ACCOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_account)
            ],
            WITHDRAW_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_amount)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    task_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^📋 কাজ করুন$"), start_task)
        ],
        states={
            SUBMIT_PROOF: [
                MessageHandler(filters.PHOTO | (filters.TEXT & ~filters.COMMAND), handle_proof)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(withdraw_conv)
    app.add_handler(task_conv)

    app.add_handler(CallbackQueryHandler(group_button_handler, pattern="^(apptask_|rejtask_|appwd_|rejwd_)"))

    app.add_handler(MessageHandler(filters.Regex("^💰 ব্যালেন্স$"), check_balance))
    app.add_handler(MessageHandler(filters.Regex("^👥 রেফার লিংক$"), refer_link))
    app.add_handler(MessageHandler(filters.Regex("^📢 হেল্প / সাপোর্ট$"), help_support))

    print("Task Cash BD Bot চালু হয়েছে...")
    app.run_polling()

if __name__ == '__main__':
    main()
    
