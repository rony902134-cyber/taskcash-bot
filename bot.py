import sqlite3, time
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ConversationHandler, filters, ContextTypes
)

BOT_TOKEN = "9047569413:AAERUCexp07o4bxBNIT6Dh9jecRnxzL3H9I"
ADMIN_ID = 7103959220
DEFAULT_GROUP = "https://t.me/TaskCashBDGroup"

(
    SUBMIT_PROOF, WITHDRAW_NUMBER, WITHDRAW_AMOUNT, BROADCAST_TEXT, 
    SET_TASK_DESC, SET_TASK_REWARD, ADMIN_USER_MSG_ID, ADMIN_USER_MSG_TEXT, 
    ADMIN_BALANCE_ID, ADMIN_BALANCE_AMOUNT, ADMIN_CHANGE_BTN_NAME, 
    ADMIN_SET_BTN_DATA, ADMIN_BAN_USER, ADMIN_UNBAN_USER, 
    ADMIN_SET_MIN_WD, ADMIN_SET_REF_REWARD, ADMIN_ADD_SUBBTN_LABEL, ADMIN_ADD_SUBBTN_VAL
) = range(17)

def init_db():
    conn = sqlite3.connect("earning_bot.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, name TEXT, balance REAL DEFAULT 0.0,
        completed_tasks INTEGER DEFAULT 0, today_tasks INTEGER DEFAULT 0,
        referred_by INTEGER DEFAULT 0, ref_rewarded INTEGER DEFAULT 0, is_banned INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, task_id TEXT, status TEXT, UNIQUE(user_id, task_id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS sub_buttons (
        id INTEGER PRIMARY KEY AUTOINCREMENT, parent_btn INTEGER, label TEXT, type TEXT, value TEXT
    )''')
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('current_task_id', 'task_1')")
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('current_task_desc', ?)", (f"গ্রুপে জয়েন করে স্ক্রিনশট দিন:\n🔗 লিঙ্ক: {DEFAULT_GROUP}",))
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('task_reward', '5.0')")
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('min_withdraw', '50.0')")
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('ref_reward', '5.0')")
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('ref_task_req', '5')")
    
    defs = {
        'btn_1_name': '💼 টাস্ক লিস্ট', 'btn_1_act': 'default', 'btn_1_data': '',
        'btn_2_name': '📤 টাস্ক সাবমিট', 'btn_2_act': 'default', 'btn_2_data': '',
        'btn_3_name': '💰 ব্যালেন্স ও রেফার', 'btn_3_act': 'default', 'btn_3_data': '',
        'btn_4_name': '💳 উত্তোলন', 'btn_4_act': 'default', 'btn_4_data': '',
        'btn_5_name': '📊 আজকের টাস্ক', 'btn_5_act': 'default', 'btn_5_data': '',
        'btn_6_name': '⚡ অতিরিক্ত অপশন', 'btn_6_act': 'submenu', 'btn_6_data': 'নিচের অপশনগুলো বেছে নিন:'
    }
    for k, v in defs.items():
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
    conn.commit()
    conn.close()

init_db()

def get_user(uid, name="", ref_by=0):
    conn = sqlite3.connect("earning_bot.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (uid,))
    u = c.fetchone()
    if not u:
        c.execute("INSERT INTO users (user_id, name, balance, completed_tasks, today_tasks, referred_by, ref_rewarded, is_banned) VALUES (?, ?, 0.0, 0, 0, ?, 0, 0)", (uid, name, ref_by))
        conn.commit()
        c.execute("SELECT * FROM users WHERE user_id = ?", (uid,))
        u = c.fetchone()
    conn.close()
    return u

def update_balance(uid, amt):
    conn = sqlite3.connect("earning_bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amt, uid))
    conn.commit()
    conn.close()

def get_setting(key):
    conn = sqlite3.connect("earning_bot.db")
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = ?", (key,))
    r = c.fetchone()
    conn.close()
    return r[0] if r else ""

def set_setting(key, val):
    conn = sqlite3.connect("earning_bot.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(val)))
    conn.commit()
    conn.close()

def check_task_status(uid, tid):
    conn = sqlite3.connect("earning_bot.db")
    c = conn.cursor()
    c.execute("SELECT status FROM user_tasks WHERE user_id = ? AND task_id = ?", (uid, tid))
    r = c.fetchone()
    conn.close()
    return r[0] if r else None

def get_main_keyboard():
    b1, b2 = get_setting('btn_1_name') or "💼 টাস্ক লিস্ট", get_setting('btn_2_name') or "📤 টাস্ক সাবমিট"
    b3, b4 = get_setting('btn_3_name') or "💰 ব্যালেন্স ও রেফার", get_setting('btn_4_name') or "💳 উত্তোলন"
    b5, b6 = get_setting('btn_5_name') or "📊 আজকের টাস্ক", get_setting('btn_6_name') or "⚡ অতিরিক্ত অপশন"
    return ReplyKeyboardMarkup([[b1, b2], [b3, b4], [b5, b6]], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ref_by = 0
    if context.args and context.args[0].startswith("ref_"):
        try:
            cand = int(context.args[0].replace("ref_", ""))
            if cand != user.id: ref_by = cand
        except Exception: pass
    u = get_user(user.id, user.first_name, ref_by)
    if u[7] == 1:
        await update.message.reply_text("🚫 আপনার অ্যাকাউন্ট অ্যাডমিন দ্বারা ব্যান করা হয়েছে।")
        return
    await update.message.reply_text(f"👋 স্বাগতম *{user.first_name}*!\n🔥 *Task Cash BD* বটে আপনাকে স্বাগতম।", reply_markup=get_main_keyboard(), parse_mode="Markdown")

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text, user = update.message.text, update.effective_user
    u = get_user(user.id, user.first_name)
    if u[7] == 1: return ConversationHandler.END

    matched = None
    for i in range(1, 7):
        if text == get_setting(f'btn_{i}_name'):
            matched = i
            break
    if not matched: return ConversationHandler.END

    act = get_setting(f'btn_{matched}_act')
    data = get_setting(f'btn_{matched}_data')
    
    if act == 'text':
        await update.message.reply_text(data, parse_mode="Markdown")
        return ConversationHandler.END
    elif act == 'link':
        await update.message.reply_text("👉 লিংকে যান:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 ওপেন করুন", url=data)]]))
        return ConversationHandler.END
    elif act == 'submenu':
        conn = sqlite3.connect("earning_bot.db")
        c = conn.cursor()
        c.execute("SELECT id, label, type, value FROM sub_buttons WHERE parent_btn = ?", (matched,))
        sub_items = c.fetchall()
        conn.close()
        if not sub_items:
            await update.message.reply_text(f"{data or 'উপ-বাটন তালিকা:'}\n(বর্তমানে এই বাটনের ভেতর কোনো সাব-বাটন যুক্ত নেই)")
            return ConversationHandler.END
        ikb = []
        for s_id, s_lbl, s_tp, s_val in sub_items:
            if s_tp == 'link':
                ikb.append([InlineKeyboardButton(s_lbl, url=s_val)])
            else:
                ikb.append([InlineKeyboardButton(s_lbl, callback_data=f"subshow_{s_id}")])
        await update.message.reply_text(data or "👇 নিচের অপশনগুলো থেকে বেছে নিন:", reply_markup=InlineKeyboardMarkup(ikb), parse_mode="Markdown")
        return ConversationHandler.END

    tid = get_setting('current_task_id')
    status = check_task_status(user.id, tid)

    if matched == 1:
        desc, rew = get_setting('current_task_desc'), get_setting('task_reward')
        st = "\n\n✅ *আপনি কাজটি সম্পন্ন করেছেন!*" if status == "approved" else ("\n\n⏳ *রিভিউতে আছে।*" if status == "pending" else f"\n\n💵 *রিওয়ার্ড:* `{rew} ৳`\n👉 সাবমিট বাটনে প্রুফ দিন।")
        await update.message.reply_text(f"📋 *বর্তমান টাস্ক:*\n\n{desc}{st}", parse_mode="Markdown")
    elif matched == 2:
        if status == "approved": await update.message.reply_text("⚠️ আপনি কাজটি ইতিমধ্যে সম্পন্ন করেছেন!"); return ConversationHandler.END
        if status == "pending": await update.message.reply_text("⏳ আগের প্রুফটি পেন্ডিং রয়েছে।"); return ConversationHandler.END
        await update.message.reply_text("📸 *টাস্ক কমপ্লিটের স্ক্রিনশট বা প্রুফ পাঠান:*", parse_mode="Markdown")
        return SUBMIT_PROOF
    elif matched == 3:
        b_info = await context.bot.get_me()
        r_link = f"https://t.me/{b_info.username}?start=ref_{user.id}"
        req_t, r_rew = get_setting('ref_task_req'), get_setting('ref_reward')
        await update.message.reply_text(f"👤 *ব্যালেন্স:* `{u[2]:.2f} ৳`\n🎯 *সম্পন্ন টাস্ক:* `{u[3]} টি`\n\n🔗 *রেফার লিংক:*\n`{r_link}`\n📌 শর্ত: রেফারকৃত ব্যক্তি *{req_t}টি কাজ* সফলভাবে সম্পন্ন করলে আপনি পাবেন *{r_rew} ৳* বোনাস!", parse_mode="Markdown")
    elif matched == 4:
        min_w = float(get_setting('min_withdraw') or 50.0)
        if u[2] < min_w: await update.message.reply_text(f"❌ ন্যূনতম উত্তোলন: *{min_w:.2f} ৳*। আপনার আছে *{u[2]:.2f} ৳*।", parse_mode="Markdown"); return ConversationHandler.END
        await update.message.reply_text("পেমেন্ট মেথড নির্বাচন করুন:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("বিকাশ", callback_data="w_bkash"), InlineKeyboardButton("নগদ", callback_data="w_nagad")]]))
        return WITHDRAW_NUMBER
    elif matched == 5:
        await update.message.reply_text(f"📈 আজকে সম্পন্ন করেছেন: *{u[4]} টি*", parse_mode="Markdown")
    return ConversationHandler.END
async def receive_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user, tid, rew = update.effective_user, get_setting('current_task_id'), float(get_setting('task_reward'))
    conn = sqlite3.connect("earning_bot.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO user_tasks (user_id, task_id, status) VALUES (?, ?, 'pending')", (user.id, tid))
    conn.commit()
    conn.close()
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("অনুমোদন ✅", callback_data=f"app_{user.id}_{tid}_{rew}"), InlineKeyboardButton("বাতিল ❌", callback_data=f"rej_{user.id}_{tid}")]])
    cap = f"📥 *নতুন টাস্ক প্রুফ!*\nইউজার: {user.first_name} (`{user.id}`)\nরিওয়ার্ড: `{rew} ৳`"
    if update.message.photo:
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=update.message.photo[-1].file_id, caption=cap, reply_markup=kb, parse_mode="Markdown")
    else:
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"{cap}\n\nপ্রুফ:\n{update.message.text}", reply_markup=kb, parse_mode="Markdown")
    await update.message.reply_text("✅ আপনার সাবমিশন জমা নেওয়া হয়েছে!")
    return ConversationHandler.END

async def select_withdraw_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data['w_method'] = "bKash" if q.data == "w_bkash" else "Nagad"
    await q.edit_message_text(f"আপনি *{context.user_data['w_method']}* বেছে নিয়েছেন। নম্বরটি দিন:")
    return WITHDRAW_NUMBER

async def receive_withdraw_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['w_num'] = update.message.text
    await update.message.reply_text(f"কত টাকা তুলতে চান লিখুন (মিনিমাম {get_setting('min_withdraw')} ৳):")
    return WITHDRAW_AMOUNT

async def process_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    u = get_user(user_id)
    min_w = float(get_setting('min_withdraw') or 50.0)
    try: amt = float(update.message.text)
    except ValueError: await update.message.reply_text("❌ ভুল ইনপুট।"); return ConversationHandler.END
    if amt < min_w or amt > u[2]: await update.message.reply_text("❌ অবৈধ পরিমাণ।"); return ConversationHandler.END
    update_balance(user_id, -amt)
    btn = InlineKeyboardMarkup([[InlineKeyboardButton("পেমেন্ট কমপ্লিট ✅", callback_data=f"paid_{user_id}_{amt}")]])
    await context.bot.send_message(chat_id=ADMIN_ID, text=f"💸 *উত্তোলন রিকোয়েস্ট!*\nইউজার: `{user_id}`\nমেথড: {context.user_data['w_method']}\nনম্বর: `{context.user_data['w_num']}`\nটাকা: {amt} ৳", reply_markup=btn, parse_mode="Markdown")
    await update.message.reply_text("✅ রিকোয়েস্ট জমা হয়েছে!")
    return ConversationHandler.END

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    conn = sqlite3.connect("earning_bot.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*), SUM(balance) FROM users")
    s = c.fetchone()
    conn.close()
    kb = [
        [InlineKeyboardButton("📝 নতুন টাস্ক", callback_data="adm_new_task"), InlineKeyboardButton("💵 টাস্ক রিওয়ার্ড", callback_data="adm_set_reward")],
        [InlineKeyboardButton("👥 ইউজার লিস্ট", callback_data="adm_list_users"), InlineKeyboardButton("⚖️ ব্যালেন্স পরিবর্তন", callback_data="adm_mod_bal")],
        [InlineKeyboardButton("🚫 ব্যান", callback_data="adm_ban"), InlineKeyboardButton("✅ আনব্যান", callback_data="adm_unban")],
        [InlineKeyboardButton("🎁 রেফার বোনাস", callback_data="adm_set_ref"), InlineKeyboardButton("💳 মিনিমাম উইথড্র", callback_data="adm_set_min_wd")],
        [InlineKeyboardButton("🔘 বাটন ও সাব-মেনু কন্ট্রোল", callback_data="adm_btn_mng")],
        [InlineKeyboardButton("📢 ব্রডকাস্ট", callback_data="adm_broadcast"), InlineKeyboardButton("📩 পার্সোনাল মেসেজ", callback_data="adm_dm_user")]
    ]
    await update.message.reply_text(f"👑 *Task Cash BD - অ্যাডমিন কন্ট্রোল*\n👥 মোট ইউজার: *{s[0] or 0} জন* | 💳 বকেয়া: *{s[1] or 0.0:.2f} ৳*", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def handle_admin_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    d = q.data
    await q.answer()

    if d.startswith("app_"):
        _, uid, tid, rew = d.split("_")
        uid, rew = int(uid), float(rew)
        conn = sqlite3.connect("earning_bot.db"); c = conn.cursor()
        c.execute("UPDATE user_tasks SET status = 'approved' WHERE user_id = ? AND task_id = ?", (uid, tid))
        c.execute("UPDATE users SET balance = balance + ?, completed_tasks = completed_tasks + 1, today_tasks = today_tasks + 1 WHERE user_id = ?", (rew, uid))
        c.execute("SELECT completed_tasks, referred_by, ref_rewarded FROM users WHERE user_id = ?", (uid,))
        uinfo = c.fetchone()
        conn.commit(); conn.close()
        await q.edit_message_caption(caption=q.message.caption + "\n\n✅ *অনুমোদিত*", parse_mode="Markdown")
        await context.bot.send_message(chat_id=uid, text=f"🎉 টাস্ক অনুমোদিত! *{rew} ৳* ব্যালেন্সে যোগ হয়েছে।", parse_mode="Markdown")
        req_t = int(get_setting('ref_task_req') or 5)
        if uinfo and uinfo[1] != 0 and uinfo[2] == 0 and uinfo[0] >= req_t:
            r_bon = float(get_setting('ref_reward') or 5.0)
            update_balance(uinfo[1], r_bon)
            conn = sqlite3.connect("earning_bot.db"); c = conn.cursor()
            c.execute("UPDATE users SET ref_rewarded = 1 WHERE user_id = ?", (uid,))
            conn.commit(); conn.close()
            try: await context.bot.send_message(chat_id=uinfo[1], text=f"🎁 আপনার রেফার {req_t}টি টাস্ক শেষ করায় আপনি *{r_bon} ৳* রেফারেল বোনাস পেয়েছেন!", parse_mode="Markdown")
            except Exception: pass
    elif d.startswith("rej_"):
        _, uid, tid = d.split("_")
        conn = sqlite3.connect("earning_bot.db"); c = conn.cursor()
        c.execute("DELETE FROM user_tasks WHERE user_id = ? AND task_id = ?", (int(uid), tid))
        conn.commit(); conn.close()
        await q.edit_message_caption(caption=q.message.caption + "\n\n❌ *বাতিল*", parse_mode="Markdown")
        await context.bot.send_message(chat_id=int(uid), text="❌ আপনার সাবমিশনটি বাতিল হয়েছে।")
    elif d.startswith("paid_"):
        _, uid, amt = d.split("_")
        await q.edit_message_text(q.message.text + "\n\n✅ *পেমেন্ট সম্পন্ন।*", parse_mode="Markdown")
        await context.bot.send_message(chat_id=int(uid), text=f"✅ আপনার *{amt} ৳* উত্তোলন সফল হয়েছে।", parse_mode="Markdown")
    elif d.startswith("subshow_"):
        sid = int(d.replace("subshow_", ""))
        conn = sqlite3.connect("earning_bot.db"); c = conn.cursor()
        c.execute("SELECT label, value FROM sub_buttons WHERE id = ?", (sid,))
        srow = c.fetchone(); conn.close()
        if srow: await q.message.reply_text(f"📌 *{srow[0]}*\n\n{srow[1]}", parse_mode="Markdown")
    elif d == "adm_new_task": await q.message.reply_text("📝 নতুন টাস্কের বিবরণ ও লিঙ্ক পাঠান:"); return SET_TASK_DESC
    elif d == "adm_set_reward": await q.message.reply_text("💵 প্রতি টাস্কের রিওয়ার্ড কত?"); return SET_TASK_REWARD
    elif d == "adm_set_min_wd": await q.message.reply_text("💳 মিনিমাম উইথড্র লিমিট (৳) কত?"); return ADMIN_SET_MIN_WD
    elif d == "adm_set_ref": await q.message.reply_text("🎁 প্রতি রেফারে কত টাকা বোনাস?"); return ADMIN_SET_REF_REWARD
    elif d == "adm_ban": await q.message.reply_text("🚫 ব্যান করতে ইউজারের Telegram ID দিন:"); return ADMIN_BAN_USER
    elif d == "adm_unban": await q.message.reply_text("✅ আনব্যান করতে ইউজারের Telegram ID দিন:"); return ADMIN_UNBAN_USER
    elif d == "adm_mod_bal": await q.message.reply_text("⚖️ ইউজারের ID দিন:"); return ADMIN_BALANCE_ID
    elif d == "adm_broadcast": await q.message.reply_text("📢 ব্রডকাস্ট নোটিশ লিখুন:"); return BROADCAST_TEXT
    elif d == "adm_dm_user": await q.message.reply_text("📩 ইউজারের ID দিন:"); return ADMIN_USER_MSG_ID
    elif d == "adm_list_users":
        conn = sqlite3.connect("earning_bot.db"); c = conn.cursor()
        c.execute("SELECT user_id, name, balance, is_banned FROM users LIMIT 30"); rows = c.fetchall(); conn.close()
        txt = "👥 *ইউজার তালিকা:*\n"
        for r in rows: txt += f"• `{r[0]}` | {r[1]} | *{r[2]:.2f}৳*{' [🚫 Banned]' if r[3]==1 else ''}\n"
        await q.message.reply_text(txt, parse_mode="Markdown")
    elif d == "adm_btn_mng":
        kb = [[InlineKeyboardButton("বাটন ১", callback_data="mbtn_1"), InlineKeyboardButton("বাটন ২", callback_data="mbtn_2")], [InlineKeyboardButton("বাটন ৩", callback_data="mbtn_3"), InlineKeyboardButton("বাটন ৪", callback_data="mbtn_4")], [InlineKeyboardButton("বাটন ৫", callback_data="mbtn_5"), InlineKeyboardButton("বাটন ৬", callback_data="mbtn_6")]]
        await q.message.reply_text("🔘 কোন বাটনটি কাস্টমাইজ করবেন?", reply_markup=InlineKeyboardMarkup(kb))
    elif d.startswith("mbtn_"):
        idx = d.replace("mbtn_", "")
        context.user_data['b_idx'] = idx
        opt = [
            [InlineKeyboardButton("✏️ নাম পরিবর্তন", callback_data="bopt_n")],
            [InlineKeyboardButton("💬 টেক্সট মেসেজ", callback_data="bopt_t")],
            [InlineKeyboardButton("🔗 সরাসরি লিংক", callback_data="bopt_l")],
            [InlineKeyboardButton("📂 বাটনের ভেতর সাব-বাটন তৈরি", callback_data="bopt_sub")],
            [InlineKeyboardButton("🔄 ডিফল্ট রিসেট", callback_data="bopt_r")]
        ]
        await q.message.reply_text(f"বাটন {idx} ব্যবস্থাপনা:\nবর্তমান নাম: *{get_setting(f'btn_{idx}_name')}*\nবর্তমান অ্যাকশন: `{get_setting(f'btn_{idx}_act')}`", reply_markup=InlineKeyboardMarkup(opt), parse_mode="Markdown")
    elif d == "bopt_n": await q.message.reply_text("বাটনটির নতুন নাম লিখুন:"); return ADMIN_CHANGE_BTN_NAME
    elif d == "bopt_t": context.user_data['b_act'] = 'text'; await q.message.reply_text("বাটন চাপলে কী টেক্সট দেখাবে?"); return ADMIN_SET_BTN_DATA
    elif d == "bopt_l": context.user_data['b_act'] = 'link'; await q.message.reply_text("বাটন চাপলে কোন লিঙ্ক ওপেন হবে? (যেমন: https://...):"); return ADMIN_SET_BTN_DATA
    elif d == "bopt_sub":
        idx = context.user_data['b_idx']
        set_setting(f'btn_{idx}_act', 'submenu')
        kb = [[InlineKeyboardButton("➕ নতুন সাব-বাটন যোগ", callback_data="sub_add_new")], [InlineKeyboardButton("🗑 সব সাব-বাটন মুছে ফেলুন", callback_data="sub_clear_all")]]
        await q.message.reply_text(f"📂 বাটন {idx}-কে সাব-মেনু করা হয়েছে। নিচে অপশন বাছুন:", reply_markup=InlineKeyboardMarkup(kb))
    elif d == "sub_add_new":
        await q.message.reply_text("ভেতরের নতুন বাটনের নাম (Label) কী হবে লিখুন:")
        return ADMIN_ADD_SUBBTN_LABEL
    elif d == "sub_clear_all":
        idx = context.user_data['b_idx']
        conn = sqlite3.connect("earning_bot.db"); c = conn.cursor()
        c.execute("DELETE FROM sub_buttons WHERE parent_btn = ?", (idx,)); conn.commit(); conn.close()
        await q.message.reply_text(f"✅ বাটন {idx}-এর ভেতরের সব বাটন মুছে ফেলা হয়েছে।")
    elif d == "bopt_r":
        idx = context.user_data['b_idx']
        set_setting(f'btn_{idx}_act', 'default'); set_setting(f'btn_{idx}_data', '')
        await q.message.reply_text(f"✅ বাটন {idx} ডিফল্ট করা হয়েছে।", reply_markup=get_main_keyboard())

async def save_new_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    set_setting('current_task_id', f"task_{int(time.time())}"); set_setting('current_task_desc', update.message.text)
    await update.message.reply_text("✅ নতুন টাস্ক চালু হয়েছে!"); return ConversationHandler.END

async def save_task_reward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: set_setting('task_reward', float(update.message.text)); await update.message.reply_text("✅ টাস্ক রিওয়ার্ড আপডেট হয়েছে!")
    except: await update.message.reply_text("❌ ভুল ইনপুট।")
    return ConversationHandler.END

async def save_min_wd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: set_setting('min_withdraw', float(update.message.text)); await update.message.reply_text(f"✅ মিনিমাম উইথড্র *{update.message.text} ৳* সেট হয়েছে।")
    except: await update.message.reply_text("❌ ভুল ইনপুট।")
    return ConversationHandler.END

async def save_ref_reward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: set_setting('ref_reward', float(update.message.text)); await update.message.reply_text(f"✅ রেফার রিওয়ার্ড *{update.message.text} ৳* সেট হয়েছে।")
    except: await update.message.reply_text("❌ ভুল ইনপুট।")
    return ConversationHandler.END

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        conn = sqlite3.connect("earning_bot.db"); c = conn.cursor()
        c.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (int(update.message.text),)); conn.commit(); conn.close()
        await update.message.reply_text("🚫 ব্যান করা হয়েছে!")
    except: await update.message.reply_text("❌ ভুল ID।")
    return ConversationHandler.END

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        conn = sqlite3.connect("earning_bot.db"); c = conn.cursor()
        c.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (int(update.message.text),)); conn.commit(); conn.close()
        await update.message.reply_text("✅ আনব্যান করা হয়েছে!")
    except: await update.message.reply_text("❌ ভুল ID।")
    return ConversationHandler.END

async def save_btn_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    set_setting(f"btn_{context.user_data['b_idx']}_name", update.message.text)
    await update.message.reply_text(f"✅ নাম পরিবর্তন হয়েছে: *{update.message.text}*", reply_markup=get_main_keyboard(), parse_mode="Markdown")
    return ConversationHandler.END

async def save_btn_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx, act = context.user_data['b_idx'], context.user_data['b_act']
    set_setting(f'btn_{idx}_act', act); set_setting(f'btn_{idx}_data', update.message.text)
    await update.message.reply_text("✅ বাটনের কাজ সেট করা হয়েছে!", reply_markup=get_main_keyboard())
    return ConversationHandler.END

async def save_subbtn_label(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['sub_label'] = update.message.text
    await update.message.reply_text("এই ভেতরের বাটন চাপলে কী হবে?\n• কোনো লিঙ্ক হলে লিঙ্ক দিন (যেমন: https://...)\n• কোনো মেসেজ দেখাতে চাইলে টেক্সট লিখে পাঠান:")
    return ADMIN_ADD_SUBBTN_VAL

async def save_subbtn_val(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = update.message.text
    tp = 'link' if val.startswith("http://") or val.startswith("https://") else 'text'
    p_idx = int(context.user_data['b_idx'])
    lbl = context.user_data['sub_label']
    conn = sqlite3.connect("earning_bot.db"); c = conn.cursor()
    c.execute("INSERT INTO sub_buttons (parent_btn, label, type, value) VALUES (?, ?, ?, ?)", (p_idx, lbl, tp, val))
    conn.commit(); conn.close()
    await update.message.reply_text(f"✅ সাব-বাটন '*{lbl}*' সফলভাবে যুক্ত হয়েছে!", parse_mode="Markdown")
    return ConversationHandler.END

async def get_bal_uid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['t_uid'] = update.message.text
    await update.message.reply_text("কত টাকা যোগ বা বিয়োগ করবেন (যেমন: 20 বা -20):")
    return ADMIN_BALANCE_AMOUNT

async def save_user_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amt, uid = float(update.message.text), int(context.user_data['t_uid'])
        update_balance(uid, amt)
        await update.message.reply_text("✅ ব্যালেন্স আপডেট হয়েছে!")
        try: await context.bot.send_message(chat_id=uid, text=f"🔔 আপনার অ্যাকাউন্টে *{amt} ৳* অ্যাডমিন দ্বারা আপডেট করা হয়েছে।", parse_mode="Markdown")
        except: pass
    except: await update.message.reply_text("❌ ভুল ইনপুট।")
    return ConversationHandler.END

async def get_msg_uid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['dm_uid'] = update.message.text
    await update.message.reply_text("মেসেজটি লিখুন:")
    return ADMIN_USER_MSG_TEXT

async def send_msg_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.send_message(chat_id=int(context.user_data['dm_uid']), text=f"💬 *অ্যাডমিন বার্তা:*\n\n{update.message.text}", parse_mode="Markdown")
        await update.message.reply_text("✅ মেসেজ পাঠানো হয়েছে!")
    except: await update.message.reply_text("❌ মেসেজ পাঠানো যায়নি।")
    return ConversationHandler.END

async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect("earning_bot.db"); c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE is_banned = 0"); users = c.fetchall(); conn.close()
    for u in users:
        try: await context.bot.send_message(chat_id=u[0], text=f"📢 *Task Cash BD নোটিশ:*\n\n{update.message.text}", parse_mode="Markdown")
        except: pass
    await update.message.reply_text("✅ ব্রডকাস্ট সম্পন্ন হয়েছে!")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("বাতিল হয়েছে।")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu),
            CallbackQueryHandler(select_withdraw_method, pattern="^w_"),
            CallbackQueryHandler(handle_admin_callbacks, pattern="^adm_"),
            CallbackQueryHandler(handle_admin_callbacks, pattern="^mbtn_"),
            CallbackQueryHandler(handle_admin_callbacks, pattern="^bopt_"),
            CallbackQueryHandler(handle_admin_callbacks, pattern="^sub_")
        ],
        states={
            SUBMIT_PROOF: [MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, receive_proof)],
            WITHDRAW_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_withdraw_number)],
            WITHDRAW_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_withdraw)],
            BROADCAST_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_broadcast)],
            SET_TASK_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_new_task)],
            SET_TASK_REWARD: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_task_reward)],
            ADMIN_SET_MIN_WD: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_min_wd)],
            ADMIN_SET_REF_REWARD: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_ref_reward)],
            ADMIN_BAN_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, ban_user)],
            ADMIN_UNBAN_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, unban_user)],
            ADMIN_USER_MSG_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_msg_uid)],
            ADMIN_USER_MSG_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_msg_user)],
            ADMIN_BALANCE_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_bal_uid)],
            ADMIN_BALANCE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_user_balance)],
            ADMIN_CHANGE_BTN_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_btn_name)],
            ADMIN_SET_BTN_DATA: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_btn_data)],
            ADMIN_ADD_SUBBTN_LABEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_subbtn_label)],
            ADMIN_ADD_SUBBTN_VAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_subbtn_val)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(handle_admin_callbacks))
    print("Task Cash BD Bot চালু হয়েছে...")
    app.run_polling()

if __name__ == '__main__':
    main()
