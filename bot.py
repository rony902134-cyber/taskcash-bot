import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import sqlite3
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

# Render ফ্রি ওয়েব সার্ভিসের জন্য ডামি পোর্ট
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_dummy_server():
    server = HTTPServer(('0.0.0.0', 10000), HealthHandler)
    server.serve_forever()

BOT_TOKEN = "9047569413:AAEZNVFkuNYW_NnBVnNDlYaF-A38tIkKcPc"
ADMIN_ID = 7103959220
ADMIN_GROUP_ID = -1004196202579
ADMIN_USERNAME = "Sabibro71"

# Conversation States
(
    SUBMIT_PROOF,
    WITHDRAW_METHOD,
    WITHDRAW_ACCOUNT,
    WITHDRAW_AMOUNT,
    ADM_BAN_USER,
    ADM_UNBAN_USER,
    ADM_ADD_BAL_USER,
    ADM_ADD_BAL_AMT,
    ADM_CUT_BAL_USER,
    ADM_CUT_BAL_AMT,
    ADM_NEW_TASK_CAT,
    ADM_NEW_TASK_DESC,
    ADM_NEW_TASK_REW,
    ADM_DEL_TASK_ID,
    ADM_BROADCAST_MSG,
    ADM_NEW_BTN_NAME,
    ADM_NEW_BTN_CONTENT,
    ADM_EDIT_BTN_SELECT,
    ADM_EDIT_BTN_NEW_NAME,
    ADM_EDIT_BTN_NEW_CONTENT
) = range(20)

def init_db():
    conn = sqlite3.connect("earning_bot.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        name TEXT,
        balance REAL DEFAULT 0,
        completed_tasks INTEGER DEFAULT 0,
        referred_by INTEGER DEFAULT 0,
        ref_reward_paid INTEGER DEFAULT 0,
        is_banned INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        title TEXT,
        reward REAL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS custom_buttons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        btn_name TEXT UNIQUE,
        btn_content TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    c.execute("INSERT OR IGNORE INTO settings VALUES ('min_withdraw', '50')")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('ref_reward', '5')")
    
    c.execute("SELECT COUNT(*) FROM tasks")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO tasks (category, title, reward) VALUES ('youtube', 'ইউটিউব চ্যানেল সাবস্ক্রাইব করে স্ক্রিনশট দিন', 2.0)")
        c.execute("INSERT INTO tasks (category, title, reward) VALUES ('facebook', 'ফেসবুক পেজে লাইক ও ফলো দিয়ে স্ক্রিনশট দিন', 2.0)")
        c.execute("INSERT INTO tasks (category, title, reward) VALUES ('tiktok', 'টিকটক একাউন্ট ফলো করে স্ক্রিনশট দিন', 1.5)")

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
        [KeyboardButton("📋 কাজ / টাস্ক"), KeyboardButton("💰 ব্যালেন্স")],
        [KeyboardButton("👥 রেফার"), KeyboardButton("💳 টাকা উত্তোলন")],
        [KeyboardButton("🆔 ইউজার আইডি / ব্যাজ"), KeyboardButton("🆘 সাহায্য ও সাপোর্ট")]
    ]
    conn = sqlite3.connect("earning_bot.db")
    c = conn.cursor()
    c.execute("SELECT btn_name FROM custom_buttons")
    custom_btns = c.fetchall()
    conn.close()

    temp_row = []
    for b in custom_btns:
        temp_row.append(KeyboardButton(b[0]))
        if len(temp_row) == 2:
            keyboard.append(temp_row)
            temp_row = []
    if temp_row:
        keyboard.append(temp_row)

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = get_user(user.id)

    if u and u[6] == 1:
        await update.message.reply_text("⛔ আপনাকে এই বট থেকে ব্যান করা হয়েছে।")
        return

    referrer = 0
    if context.args and context.args[0].isdigit():
        referrer = int(context.args[0])

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
    conn.close()

    welcome_text = (
        f"স্বাগতম {user.first_name}! 👋\n\n"
        f"টাস্ক ক্যাশ বটে আপনি টাস্ক পূরণ ও রেফার করে আয় করতে পারবেন।\n"
        f"নিচের বাটনগুলো ব্যবহার করে কাজ শুরু করুন।"
    )
    await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard())

async def user_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = get_user(update.effective_user.id)
    if not u or u[6] == 1:
        return

    tasks_count = u[3]
    badge = "👑 VIP Member" if tasks_count >= 50 else f"🥈 Regular Member (VIP হতে বাকি {50 - tasks_count}টি টাস্ক)"

    conn = sqlite3.connect("earning_bot.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE referred_by=?", (u[0],))
    total_ref = c.fetchone()[0]
    conn.close()

    text = (
        f"👤 **আপনার প্রোফাইল তথ্য**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🏷 নাম: {u[1]}\n"
        f"🆔 আইডি: `{u[0]}`\n"
        f"🎖 ব্যাজ: **{badge}**\n"
        f"💵 ব্যালেন্স: {u[2]:.2f} টাকা\n"
        f"✅ সম্পন্ন টাস্ক: {tasks_count} টি\n"
        f"👥 মোট রেফার: {total_ref} জন"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = get_user(update.effective_user.id)
    if not u or u[6] == 1:
        return
    await update.message.reply_text(
        f"💰 **আপনার বর্তমান ব্যালেন্স:** {u[2]:.2f} টাকা\n"
        f"✅ সম্পন্ন টাস্ক: {u[3]} টি",
        parse_mode="Markdown"
    )

async def refer_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = get_user(update.effective_user.id)
    if not u or u[6] == 1:
        return
    bot_info = await context.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={u[0]}"
    text = (
        f"👥 **রেফারেল প্রোগ্রাম**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔗 আপনার লিংক:\n`{link}`\n\n"
        f"💰 প্রতি রেফারে: ৫ টাকা\n"
        f"⚠️ **শর্ত:** রেফারকৃত ব্যক্তিকে অবশ্যই কমপক্ষে **৫টি টাস্ক সম্পন্ন** করতে হবে। তখন স্বয়ংক্রিয়ভাবে ব্যালেন্সে ৫ টাকা যুক্ত হবে।"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def help_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        f"🆘 **সাহায্য ও সাপোর্ট:**\n\n"
        f"যেকোনো প্রয়োজনে সরাসরি যোগাযোগ করুন:\n"
        f"👉 অ্যাডমিন: @{ADMIN_USERNAME}\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def handle_custom_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    conn = sqlite3.connect("earning_bot.db")
    c = conn.cursor()
    c.execute("SELECT btn_content FROM custom_buttons WHERE btn_name=?", (text,))
    res = c.fetchone()
    conn.close()

        if res:
        await update.message.reply_text(res[0], parse_mode="Markdown")

async def show_task_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = get_user(update.effective_user.id)
    if not u or u[6] == 1:
        return
    keyboard = [
        [InlineKeyboardButton("▶️ ইউটিউব টাস্ক", callback_data="tasks_youtube")],
        [InlineKeyboardButton("📘 ফেসবুক টাস্ক", callback_data="tasks_facebook")],
        [InlineKeyboardButton("🎵 টিকটক টাস্ক", callback_data="tasks_tiktok")]
    ]
    await update.message.reply_text("কাজের ধরণ নির্বাচন করুন:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_task_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cat = query.data.split("_")[1]

    conn = sqlite3.connect("earning_bot.db")
    c = conn.cursor()
    c.execute("SELECT id, title, reward FROM tasks WHERE category=?", (cat,))
    task_list = c.fetchall()
    conn.close()

    if not task_list:
        await query.message.edit_text("বর্তমানে এই বিভাগে কোনো কাজ নেই। কিছুক্ষণ পর আবার দেখুন।")
        return

    keyboard = [[InlineKeyboardButton(f"{title} ({rew}৳)", callback_data=f"dotask_{t_id}")] for t_id, title, rew in task_list]
    await query.message.edit_text("একটি কাজ নির্বাচন করুন:", reply_markup=InlineKeyboardMarkup(keyboard))

async def pick_single_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    task_id = int(query.data.split("_")[1])

    conn = sqlite3.connect("earning_bot.db")
    c = conn.cursor()
    c.execute("SELECT title, reward FROM tasks WHERE id=?", (task_id,))
    t = c.fetchone()
    conn.close()

    if not t:
        await query.message.edit_text("টাস্ক পাওয়া যায়নি।")
        return ConversationHandler.END

    context.user_data['active_task_id'] = task_id
    context.user_data['active_task_title'] = t[0]
    context.user_data['active_task_reward'] = t[1]

    await query.message.reply_text(
        f"📌 **কাজের বিবরণ:**\n{t[0]}\n\n"
        f"💰 **রিওয়ার্ড:** {t[1]} টাকা\n\n"
        f"কাজ শেষ করে স্ক্রিনশট বা প্রুফ লিখে পাঠান। বাতিল করতে /cancel লিখুন।",
        parse_mode="Markdown"
    )
    return SUBMIT_PROOF

async def handle_task_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    t_title = context.user_data.get('active_task_title', 'Task')
    reward = context.user_data.get('active_task_reward', 0)

    admin_kb = [
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"apptask_{user.id}_{reward}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"rejtask_{user.id}")
        ]
    ]

    caption = (
        f"📩 **নতুন টাস্ক প্রুফ!**\n\n"
        f"👤 নাম: {user.first_name} (@{user.username})\n"
        f"🆔 আইডি: `{user.id}`\n"
        f"📌 টাস্ক: {t_title}\n"
        f"💰 রিওয়ার্ড: {reward} টাকা"
    )

    if update.message.photo:
        await context.bot.send_photo(
            chat_id=ADMIN_GROUP_ID,
            photo=update.message.photo[-1].file_id,
            caption=caption,
            reply_markup=InlineKeyboardMarkup(admin_kb),
            parse_mode="Markdown"
        )
    else:
        await context.bot.send_message(
            chat_id=ADMIN_GROUP_ID,
            text=f"{caption}\n\n📝 প্রুফ টেক্সট:\n{update.message.text}",
            reply_markup=InlineKeyboardMarkup(admin_kb),
            parse_mode="Markdown"
        )

    await update.message.reply_text("✅ আপনার প্রুফ অ্যাডমিন গ্রুপে পাঠানো হয়েছে! অনুমোদন দিলে ব্যালেন্স যোগ হবে।", reply_markup=get_main_keyboard())
    return ConversationHandler.END

async def start_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = get_user(update.effective_user.id)
    if not u or u[6] == 1:
        return ConversationHandler.END

    min_wd = float(get_setting('min_withdraw'))
    if u[2] < min_wd:
        await update.message.reply_text(f"❌ ব্যালেন্স পর্যাপ্ত নয়। সর্বনিম্ন উত্তোলন {min_wd} টাকা। বর্তমান ব্যালেন্স {u[2]:.2f} টাকা।")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton("বিকাশ (bKash)", callback_data="wd_bkash"), InlineKeyboardButton("নগদ (Nagad)", callback_data="wd_nagad")],
        [InlineKeyboardButton("💵 ডলার (USDT / Binance Pay)", callback_data="wd_usdt")]
    ]
    await update.message.reply_text("উত্তোলনের মাধ্যম নির্বাচন করুন:", reply_markup=InlineKeyboardMarkup(keyboard))
    return WITHDRAW_METHOD

async def withdraw_method_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    method_map = {"wd_bkash": "বিকাশ (bKash)", "wd_nagad": "নগদ (Nagad)", "wd_usdt": "USDT / Binance Pay"}
    method = method_map.get(query.data, "বিকাশ")
    context.user_data['withdraw_method'] = method

    msg = f"মাধ্যম: {method}\n\nআপনার Binance Pay ID অথবা USDT Address দিন:" if query.data == "wd_usdt" else f"মাধ্যম: {method}\n\nআপনার {method} নম্বরটি দিন:"
    await query.message.edit_text(msg)
    return WITHDRAW_ACCOUNT

async def get_withdraw_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['withdraw_account'] = update.message.text.strip()
    u = get_user(update.effective_user.id)
    min_wd = get_setting('min_withdraw')
    await update.message.reply_text(f"কত টাকা তুলতে চান?\n(সর্বনিম্ন: {min_wd}৳ | ব্যালেন্স: {u[2]:.2f}৳)")
    return WITHDRAW_AMOUNT

async def get_withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ পরিমাণ শুধু সংখ্যায় লিখুন:")
        return WITHDRAW_AMOUNT

    user = update.effective_user
    u = get_user(user.id)
    min_wd = float(get_setting('min_withdraw'))

    if amount < min_wd:
        await update.message.reply_text(f"❌ সর্বনিম্ন উত্তোলনের পরিমাণ {min_wd} টাকা। আবার লিখুন:")
        return WITHDRAW_AMOUNT
    if amount > u[2]:
        await update.message.reply_text(f"❌ অপর্যাপ্ত ব্যালেন্স! আপনার ব্যালেন্স: {u[2]:.2f} টাকা।")
        return WITHDRAW_AMOUNT

    update_balance(user.id, -amount)
    method = context.user_data.get('withdraw_method', 'N/A')
    account = context.user_data.get('withdraw_account', 'N/A')

    await update.message.reply_text(
        f"✅ উইথড্র রিকোয়েস্ট সফল হয়েছে!\n\n"
        f"💳 মাধ্যম: {method}\n"
        f"📌 একাউন্ট: `{account}`\n"
        f"💵 পরিমাণ: {amount} টাকা\n\n"
        f"অ্যাডমিন যাচাই করে দ্রুত পেমেন্ট পাঠিয়ে দেবে।",
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
        f"🆔 আইডি: `{user.id}`\n"
        f"💳 মাধ্যম: {method}\n"
        f"📌 একাউন্ট/নম্বর: `{account}`\n"
        f"💵 পরিমাণ: {amount} টাকা"
    )

    try:
        await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=admin_msg, reply_markup=InlineKeyboardMarkup(admin_kb), parse_mode="Markdown")
    except Exception as e:
        print(f"Group error: {e}")

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

        c.execute("SELECT completed_tasks, referred_by, ref_reward_paid FROM users WHERE user_id=?", (uid,))
        tasks_done, ref_by, ref_paid = c.fetchone()

        if ref_by and ref_by > 0 and ref_paid == 0 and tasks_done >= 5:
            ref_amt = float(get_setting('ref_reward'))
            c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (ref_amt, ref_by))
            c.execute("UPDATE users SET ref_reward_paid = 1 WHERE user_id=?", (uid,))
            conn.commit()
            try:
                await context.bot.send_message(chat_id=ref_by, text=f"🎉 আপনার রেফার করা মেম্বার ৫টি কাজ সম্পন্ন করায় {ref_amt} টাকা বোনাস যুক্ত হয়েছে!")
            except Exception:
                pass
        conn.close()

        await query.answer("টাস্ক অ্যাপ্রুভ হয়েছে!")
        try:
            await query.edit_message_caption(caption=f"{query.message.caption}\n\n✅ [অনুমোদন করেছেন: {query.from_user.first_name}]")
        except Exception:
            await query.edit_message_text(text=f"{query.message.text}\n\n✅ [অনুমোদন করেছেন: {query.from_user.first_name}]")
        try:
            await context.bot.send_message(chat_id=uid, text=f"🎉 আপনার টাস্ক অনুমোদিত হয়েছে! {amt} টাকা ব্যালেন্সে যোগ হয়েছে।")
        except Exception:
            pass

    elif data.startswith("rejtask_"):
        _, uid = data.split("_")
        uid = int(uid)
        await query.answer("টাস্ক বাতিল করা হয়েছে!")
        try:
            await query.edit_message_caption(caption=f"{query.message.caption}\n\n❌ [বাতিল করেছেন: {query.from_user.first_name}]")
        except Exception:
            await query.edit_message_text(text=f"{query.message.text}\n\n❌ [বাতিল করেছেন: {query.from_user.first_name}]")
        try:
            await context.bot.send_message(chat_id=uid, text="❌ আপনার টাস্ক প্রমাণটি সঠিক না হওয়ায় বাতিল করা হয়েছে।")
        except Exception:
            pass

    elif data.startswith("appwd_"):
        _, uid, amt = data.split("_")
        await query.answer("পেমেন্ট সফল হিসেবে চিহ্নিত!")
        await query.edit_message_text(text=f"{query.message.text}\n\n✅ [পেমেন্ট সাকসেস - {query.from_user.first_name}]")
        try:
            await context.bot.send_message(chat_id=int(uid), text=f"🎉 আপনার {amt} টাকা উইথড্র সফলভাবে পেমেন্ট করা হয়েছে।")
        except Exception:
            pass

    elif data.startswith("rejwd_"):
        _, uid, amt = data.split("_")
        uid, amt = int(uid), float(amt)
        update_balance(uid, amt)
        await query.answer("উইথড্র বাতিল এবং রিফান্ড সম্পন্ন!")
        await query.edit_message_text(text=f"{query.message.text}\n\n❌ [উইথড্র বাতিল ও রিফান্ড হয়েছে]")
        try:
            await context.bot.send_message(chat_id=uid, text=f"❌ আপনার {amt} টাকার উইথড্র বাতিল করা হয়েছে এবং ব্যালেন্স ফিরিয়ে দেওয়া হয়েছে।")
        except Exception:
            pass

def get_admin_panel_keyboard():
    keyboard = [
        [InlineKeyboardButton("➕ ব্যালেন্স যোগ", callback_data="adm_addbal"), InlineKeyboardButton("➖ ব্যালেন্স কাট", callback_data="adm_cutbal")],
        [InlineKeyboardButton("🚫 ইউজার ব্যান", callback_data="adm_ban"), InlineKeyboardButton("✅ ইউজার আনব্যান", callback_data="adm_unban")],
        [InlineKeyboardButton("🆕 নতুন টাস্ক যোগ", callback_data="adm_addtask"), InlineKeyboardButton("🗑 টাস্ক ডিলিট", callback_data="adm_deltask")],
        [InlineKeyboardButton("🔘 নতুন বাটন তৈরি", callback_data="adm_addbtn"), InlineKeyboardButton("✏️ বাটন ও কাজ এডিট", callback_data="adm_editbtn")],
        [InlineKeyboardButton("📢 ব্রডকাস্ট নোটিশ", callback_data="adm_broadcast")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    conn = sqlite3.connect("earning_bot.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*), SUM(balance) FROM users")
    tot_users, tot_bal = c.fetchone()
    c.execute("SELECT COUNT(*) FROM tasks")
    tot_tasks = c.fetchone()[0]
    conn.close()

    text = (
        f"👑 **এডমিন কন্ট্রোল প্যানেল**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👥 মোট ইউজার: {tot_users}\n"
        f"💰 মোট ব্যালেন্স: {tot_bal if tot_bal else 0:.2f} টাকা\n"
        f"📋 টাস্ক সংখ্যা: {tot_tasks} টি\n\n"
        f"যেকোনো অপশন নির্বাচন করুন:"
    )
    if update.message:
        await update.message.reply_text(text, reply_markup=get_admin_panel_keyboard(), parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=get_admin_panel_keyboard(), parse_mode="Markdown")

async def adm_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "adm_addbal":
        await query.message.reply_text("ব্যালেন্স যোগ করতে ইউজারের **আইডি** দিন:")
        return ADM_ADD_BAL_USER
    elif data == "adm_cutbal":
        await query.message.reply_text("ব্যালেন্স কাটতে ইউজারের **আইডি** দিন:")
        return ADM_CUT_BAL_USER
    elif data == "adm_ban":
        await query.message.reply_text("ব্যান করতে ইউজারের **আইডি** দিন:")
        return ADM_BAN_USER
    elif data == "adm_unban":
        await query.message.reply_text("আনব্যান করতে ইউজারের **আইডি** দিন:")
        return ADM_UNBAN_USER
    elif data == "adm_addtask":
        kb = [
            [InlineKeyboardButton("ইউটিউব", callback_data="addcat_youtube")],
            [InlineKeyboardButton("ফেসবুক", callback_data="addcat_facebook")],
            [InlineKeyboardButton("টিকটক", callback_data="addcat_tiktok")]
        ]
        await query.message.reply_text("টাস্কের প্ল্যাটফর্ম বেছে নিন:", reply_markup=InlineKeyboardMarkup(kb))
        return ADM_NEW_TASK_CAT
    elif data == "adm_deltask":
        conn = sqlite3.connect("earning_bot.db")
        c = conn.cursor()
        c.execute("SELECT id, category, title FROM tasks")
        rows = c.fetchall()
        conn.close()
        if not rows:
            await query.message.reply_text("কোনো টাস্ক নেই।")
            return ConversationHandler.END
        t_text = "ডিলিট করতে চাওয়া টাস্কের **ID** লিখুন:\n\n" + "\n".join([f"🔹 ID: `{r[0]}` | [{r[1]}] {r[2]}" for r in rows])
        await query.message.reply_text(t_text, parse_mode="Markdown")
        return ADM_DEL_TASK_ID
    elif data == "adm_addbtn":
        await query.message.reply_text("নতুন বাটনের নাম কী দিতে চান? নাম লিখে পাঠান:")
        return ADM_NEW_BTN_NAME
    elif data == "adm_editbtn":
        conn = sqlite3.connect("earning_bot.db")
        c = conn.cursor()
        c.execute("SELECT id, btn_name FROM custom_buttons")
        btns = c.fetchall()
        conn.close()
        if not btns:
            await query.message.reply_text("এডিট করার মতো কোনো কাস্টম বাটন তৈরি করা নেই। আগে নতুন বাটন তৈরি করুন।")
            return ConversationHandler.END
        kb = [[InlineKeyboardButton(b[1], callback_data=f"edbtn_{b[0]}")] for b in btns]
        await query.message.reply_text("কোন বাটনটি এডিট করতে চান নির্বাচন করুন:", reply_markup=InlineKeyboardMarkup(kb))
        return ADM_EDIT_BTN_SELECT
    elif data == "adm_broadcast":
        await query.message.reply_text("সকল মেম্বারদের কাছে পাঠানোর জন্য নোটিশ লিখুন:")
        return ADM_BROADCAST_MSG

async def adm_new_btn_name_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['custom_btn_name'] = update.message.text.strip()
    await update.message.reply_text("ইউজার এই বাটনে চাপ দিলে কী টেক্সট/নোটিশ দেখবে তা লিখে পাঠান:")
    return ADM_NEW_BTN_CONTENT

async def adm_new_btn_content_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    content = update.message.text.strip()
    btn_name = context.user_data['custom_btn_name']

    conn = sqlite3.connect("earning_bot.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO custom_buttons (btn_name, btn_content) VALUES (?, ?)", (btn_name, content))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"✅ নতুন বাটন **[{btn_name}]** সফলভাবে যোগ হয়েছে!", reply_markup=get_main_keyboard(), parse_mode="Markdown")
    return ConversationHandler.END

async def adm_edit_btn_select_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    btn_id = int(query.data.split("_")[1])
    context.user_data['edit_btn_id'] = btn_id

    await query.message.reply_text("বাটনের **নতুন নাম** কী রাখতে চান? (পরিবর্তন না করতে চাইলে আগের নামটিই লিখুন):")
    return ADM_EDIT_BTN_NEW_NAME

async def adm_edit_btn_name_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['edit_btn_new_name'] = update.message.text.strip()
    await update.message.reply_text("এখন ইউজার বাটনে চাপ দিলে **কী মেসেজ বা কাজ** দেখাবে তা লিখে পাঠান:")
    return ADM_EDIT_BTN_NEW_CONTENT

async def adm_edit_btn_content_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_content = update.message.text.strip()
    btn_id = context.user_data['edit_btn_id']
    new_name = context.user_data['edit_btn_new_name']

    conn = sqlite3.connect("earning_bot.db")
    c = conn.cursor()
    c.execute("UPDATE custom_buttons SET btn_name=?, btn_content=? WHERE id=?", (new_name, new_content, btn_id))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"✅ বাটন এবং ভেতরের তথ্য সফলভাবে আপডেট হয়েছে!", reply_markup=get_main_keyboard())
    return ConversationHandler.END

async def adm_add_user_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['target_uid'] = int(update.message.text.strip())
        await update.message.reply_text("টাকার পরিমাণ লিখুন:")
        return ADM_ADD_BAL_AMT
    except ValueError:
        await update.message.reply_text("সঠিক আইডি দিন:")
        return ADM_ADD_BAL_USER

async def adm_add_amt_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amt = float(update.message.text.strip())
        target = context.user_data['target_uid']
        update_balance(target, amt)
        await update.message.reply_text(f"✅ ইউজার `{target}`-এর ব্যালেন্সে {amt} টাকা যোগ হয়েছে।", parse_mode="Markdown")
        try:
            await context.bot.send_message(chat_id=target, text=f"🎁 আপনার ব্যালেন্সে {amt} টাকা যোগ করা হয়েছে!")
        except Exception:
            pass
    except Exception:
        await update.message.reply_text("সঠিক সংখ্যা দিন।")
    return ConversationHandler.END

async def adm_cut_user_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['target_cut_uid'] = int(update.message.text.strip())
        await update.message.reply_text("কত টাকা কাটবেন লিখুন:")
        return ADM_CUT_BAL_AMT
    except ValueError:
        await update.message.reply_text("সঠিক আইডি দিন:")
        return ADM_CUT_BAL_USER

async def adm_cut_amt_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amt = float(update.message.text.strip())
        target = context.user_data['target_cut_uid']
        update_balance(target, -amt)
        await update.message.reply_text(f"✅ ইউজার `{target}`-এর ব্যালেন্স থেকে {amt} টাকা কাটা হয়েছে।", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("সঠিক সংখ্যা দিন।")
    return ConversationHandler.END

async def adm_ban_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target = int(update.message.text.strip())
        conn = sqlite3.connect("earning_bot.db")
        c = conn.cursor()
        c.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (target,))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"🚫 ইউজার `{target}` ব্যান হয়েছে।", parse_mode="Markdown")
    except ValueError:
        await update.message.reply_text("সঠিক আইডি দিন।")
    return ConversationHandler.END

async def adm_unban_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target = int(update.message.text.strip())
        conn = sqlite3.connect("earning_bot.db")
        c = conn.cursor()
        c.execute("UPDATE users SET is_banned=0 WHERE user_id=?", (target,))
        conn.commit()
        conn.close()
                await update.message.reply_text(f"✅ ইউজার `{target}` আনব্যান হয়েছে।", parse_mode="Markdown")
    except ValueError:
        await update.message.reply_text("সঠিক আইডি দিন।")
    return ConversationHandler.END

async def adm_task_cat_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['new_task_cat'] = query.data.split("_")[1]
    await query.message.reply_text("টাস্কের শিরোনাম ও কাজের লিংক লিখে পাঠান:")
    return ADM_NEW_TASK_DESC

async def adm_task_desc_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_task_desc'] = update.message.text.strip()
    await update.message.reply_text("টাস্কের জন্য কত টাকা রিওয়ার্ড দিতে চান?")
    return ADM_NEW_TASK_REW

async def adm_task_rew_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        rew = float(update.message.text.strip())
        cat = context.user_data['new_task_cat']
        desc = context.user_data['new_task_desc']

        conn = sqlite3.connect("earning_bot.db")
        c = conn.cursor()
        c.execute("INSERT INTO tasks (category, title, reward) VALUES (?, ?, ?)", (cat, desc, rew))
        conn.commit()
        conn.close()
        await update.message.reply_text("✅ নতুন টাস্ক যোগ করা হয়েছে!")
    except Exception:
        await update.message.reply_text("সঠিক সংখ্যা দিন।")
    return ConversationHandler.END

async def adm_del_task_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        t_id = int(update.message.text.strip())
        conn = sqlite3.connect("earning_bot.db")
        c = conn.cursor()
        c.execute("DELETE FROM tasks WHERE id=?", (t_id,))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ টাস্ক `{t_id}` ডিলিট হয়েছে।", parse_mode="Markdown")
    except ValueError:
        await update.message.reply_text("সঠিক আইডি দিন।")
    return ConversationHandler.END

async def adm_broadcast_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    conn = sqlite3.connect("earning_bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE is_banned=0")
    rows = c.fetchall()
    conn.close()

    count = 0
    for r in rows:
        try:
            await context.bot.send_message(chat_id=r[0], text=f"📢 **নোটিশ:**\n\n{msg}", parse_mode="Markdown")
            count += 1
        except Exception:
            pass
    await update.message.reply_text(f"✅ মোট {count} জন ইউজারের কাছে নোটিশ পাঠানো হয়েছে।")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("বাতিল করা হয়েছে।", reply_markup=get_main_keyboard())
    return ConversationHandler.END
def main():
    threading.Thread(target=run_dummy_server, daemon=True).start()
    init_db()
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))

    admin_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(adm_menu_callback, pattern="^adm_")],
        states={
            ADM_ADD_BAL_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_add_user_step)],
            ADM_ADD_BAL_AMT: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_add_amt_step)],
            ADM_CUT_BAL_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_cut_user_step)],
            ADM_CUT_BAL_AMT: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_cut_amt_step)],
            ADM_BAN_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_ban_step)],
            ADM_UNBAN_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_unban_step)],
            ADM_NEW_TASK_CAT: [CallbackQueryHandler(adm_task_cat_chosen, pattern="^addcat_")],
            ADM_NEW_TASK_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_task_desc_step)],
            ADM_NEW_TASK_REW: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_task_rew_step)],
            ADM_DEL_TASK_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_del_task_step)],
            ADM_NEW_BTN_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_new_btn_name_step)],
            ADM_NEW_BTN_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_new_btn_content_step)],
            ADM_EDIT_BTN_SELECT: [CallbackQueryHandler(adm_edit_btn_select_step, pattern="^edbtn_")],
            ADM_EDIT_BTN_NEW_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_edit_btn_name_step)],
            ADM_EDIT_BTN_NEW_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_edit_btn_content_step)],
            ADM_BROADCAST_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_broadcast_step)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    withdraw_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^💳 টাকা উত্তোলন$"), start_withdraw),
            CallbackQueryHandler(withdraw_method_selected, pattern="^wd_(bkash|nagad|usdt)$")
        ],
        states={
            WITHDRAW_METHOD: [CallbackQueryHandler(withdraw_method_selected, pattern="^wd_(bkash|nagad|usdt)$")],
            WITHDRAW_ACCOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_withdraw_account)],
            WITHDRAW_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_withdraw_amount)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    task_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(pick_single_task, pattern="^dotask_")],
        states={
            SUBMIT_PROOF: [MessageHandler(filters.PHOTO | (filters.TEXT & ~filters.COMMAND), handle_task_proof)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(admin_conv)
    app.add_handler(withdraw_conv)
    app.add_handler(task_conv)

    app.add_handler(CallbackQueryHandler(group_button_handler, pattern="^(apptask_|rejtask_|appwd_|rejwd_)"))
    app.add_handler(CallbackQueryHandler(handle_task_category, pattern="^tasks_"))

    app.add_handler(MessageHandler(filters.Regex("^📋 কাজ / টাস্ক$"), show_task_categories))
    app.add_handler(MessageHandler(filters.Regex("^💰 ব্যালেন্স$"), check_balance))
    app.add_handler(MessageHandler(filters.Regex("^👥 রেফার$"), refer_info))
    app.add_handler(MessageHandler(filters.Regex("^🆔 ইউজার আইডি / ব্যাজ$"), user_profile))
    app.add_handler(MessageHandler(filters.Regex("^🆘 সাহায্য ও সাপোর্ট$"), help_support))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_button))

    print("Task Cash BD Bot চালু হয়েছে...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
    
