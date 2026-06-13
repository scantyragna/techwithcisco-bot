import os
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, ConversationHandler, filters
)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
BOT_TOKEN      = os.environ.get("BOT_TOKEN", "8535568864:AAFWDifPgQate3OtTH6xasZcrklWvemzsDk")
WEBHOOK_URL    = os.environ.get("WEBHOOK_URL", "https://techwithcisco-bot.onrender.com")
ADMIN_ID       = 8625461305
MOMO_NUMBER    = "0243 812 365"
COURSE_PRICE   = 200
DATA_FILE      = "students.json"
PORT           = int(os.environ.get("PORT", 10000))

DAY_LINKS = {
    "Sunday":    "https://t.me/c/3950943192/2",
    "Monday":    "https://t.me/c/3950943192/4",
    "Tuesday":   "https://t.me/c/3950943192/6",
    "Wednesday": "https://t.me/c/3950943192/8",
    "Thursday":  "https://t.me/c/3950943192/10",
    "Friday":    "https://t.me/c/3950943192/12",
    "Saturday":  "https://t.me/c/3950943192/14",
}
ANNOUNCEMENTS_LINK  = "https://t.me/c/3950943192/1"
COMMUNITY_JOIN_LINK = "https://t.me/+BypZjsERlWw2NGU8"

DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
ASK_NAME, ASK_DAY, ASK_PAYMENT, ASK_CONFIRM = range(4)

# ── Data helpers ──────────────────────────────────────────────────────────────
def load_students():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_students(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def add_student(user_id, name, day, proof_type, proof_value):
    data = load_students()
    data[str(user_id)] = {
        "name": name, "day": day,
        "proof_type": proof_type,
        "proof_value": proof_value,
        "amount": COURSE_PRICE, "status": "approved",
        "enrolled_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "telegram_id": user_id
    }
    save_students(data)

# ── Auto-approve and send links ───────────────────────────────────────────────
async def approve_and_send(context, user_id, name, day):
    day_link = DAY_LINKS.get(day, ANNOUNCEMENTS_LINK)
    await context.bot.send_message(
        chat_id=user_id,
        text=(
            f"🎉 Welcome to PC Basics Academy, {name}!\n\n"
            f"You're now enrolled for {day} sessions.\n\n"
            f"Step 1 — Join the community first 👇\n"
            f"{COMMUNITY_JOIN_LINK}\n\n"
            f"Step 2 — Then open your {day} class 👇\n"
            f"{day_link}\n\n"
            f"📢 General announcements 👇\n"
            f"{ANNOUNCEMENTS_LINK}\n\n"
            f"Welcome aboard! See you in class 📚💻"
        )
    )

# ── Notify admin (info only, no approve/reject needed) ────────────────────────
async def notify_admin(context, user_id, name, day, proof_type, proof_value, username):
    msg = (
        f"✅ New Auto-Enrollment!\n\n"
        f"👤 Name: {name}\n"
        f"📅 Day: {day}\n"
        f"💰 Amount: GHS {COURSE_PRICE}\n"
        f"📱 Telegram: @{username}\n"
        f"🆔 User ID: {user_id}\n"
        f"📎 Proof: {proof_type.upper()}\n"
        f"⏰ Time: {datetime.now().strftime('%d %b %Y, %I:%M %p')}"
    )
    try:
        if proof_type == "screenshot":
            await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=proof_value,
                caption=msg
            )
        else:
            msg += f"\n🧾 TX ID: {proof_value}"
            await context.bot.send_message(chat_id=ADMIN_ID, text=msg)
    except Exception as e:
        logger.error(f"Could not notify admin: {e}")

# ── Conversation handlers ─────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Welcome to TechWithCisco — PC Basics Academy!*\n\n"
        "I'm here to get you enrolled in our IT Fundamentals course.\n\n"
        "You'll get:\n"
        "📹 Pre-recorded video lessons\n"
        "👥 Weekly 2-hour live session with your group\n"
        "💬 Private Telegram community for your day\n\n"
        f"💰 *Course fee: GHS {COURSE_PRICE} (one-time)*\n\n"
        "Let's get started! What is your *full name*?",
        parse_mode="Markdown"
    )
    return ASK_NAME

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if len(name) < 2:
        await update.message.reply_text("Please enter your full name.")
        return ASK_NAME
    context.user_data["name"] = name
    keyboard = [[InlineKeyboardButton(day, callback_data=f"day_{day}")] for day in DAYS]
    await update.message.reply_text(
        f"Nice to meet you, *{name}*! 🎉\n\n"
        "Which day works best for your *live sessions*? 👇",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ASK_DAY

async def ask_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    day = query.data.replace("day_", "")
    context.user_data["day"] = day
    await query.edit_message_text(
        f"✅ *{day}* selected!\n\n"
        f"Please send *GHS {COURSE_PRICE}* via MoMo to:\n\n"
        f"📱 *{MOMO_NUMBER}*\n"
        f"_(TechWithCisco — PC Basics Academy)_\n\n"
        "Once sent, you can either:\n"
        "📸 *Send a screenshot* of your MoMo confirmation\n"
        "or\n"
        "🔢 *Type your transaction ID*\n\n"
        "When done, type *sent* or send your screenshot 👇",
        parse_mode="Markdown"
    )
    return ASK_PAYMENT

async def ask_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = context.user_data["name"]
    day  = context.user_data["day"]

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        add_student(user.id, name, day, "screenshot", file_id)
        await update.message.reply_text(
            f"📸 Screenshot received! Enrolling you now...",
        )
        await approve_and_send(context, user.id, name, day)
        await notify_admin(context, user.id, name, day, "screenshot", file_id, user.username or "No username")
        return ConversationHandler.END

    if update.message.document:
        file_id = update.message.document.file_id
        add_student(user.id, name, day, "document", file_id)
        await update.message.reply_text("📎 File received! Enrolling you now...")
        await approve_and_send(context, user.id, name, day)
        await notify_admin(context, user.id, name, day, "document", file_id, user.username or "No username")
        return ConversationHandler.END

    if update.message.text:
        text = update.message.text.strip()
        if text.lower() == "sent":
            await update.message.reply_text(
                "Got it! Please now send a screenshot of your MoMo confirmation or type your transaction ID.",
            )
            return ASK_CONFIRM
        else:
            add_student(user.id, name, day, "tx_id", text)
            await update.message.reply_text("✅ Transaction ID received! Enrolling you now...")
            await approve_and_send(context, user.id, name, day)
            await notify_admin(context, user.id, name, day, "tx_id", text, user.username or "No username")
            return ConversationHandler.END

    await update.message.reply_text(
        "Please send a screenshot, your transaction ID, or type *sent*.",
        parse_mode="Markdown"
    )
    return ASK_PAYMENT

async def ask_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = context.user_data["name"]
    day  = context.user_data["day"]

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        add_student(user.id, name, day, "screenshot", file_id)
        await update.message.reply_text("📸 Screenshot received! Enrolling you now...")
        await approve_and_send(context, user.id, name, day)
        await notify_admin(context, user.id, name, day, "screenshot", file_id, user.username or "No username")

    elif update.message.text:
        tx_id = update.message.text.strip()
        add_student(user.id, name, day, "tx_id", tx_id)
        await update.message.reply_text("✅ Transaction ID received! Enrolling you now...")
        await approve_and_send(context, user.id, name, day)
        await notify_admin(context, user.id, name, day, "tx_id", tx_id, user.username or "No username")

    return ConversationHandler.END

# ── Admin commands ────────────────────────────────────────────────────────────
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    data     = load_students()
    approved = [s for s in data.values() if s["status"] == "approved"]
    lines = [
        f"📊 Enrollment Report — {datetime.now().strftime('%d %b %Y')}\n",
        f"👥 Total enrolled: {len(approved)}\n"
        f"💰 Revenue: GHS {sum(s['amount'] for s in approved)}\n"
        f"─────────────────────"
    ]
    for s in approved:
        lines.append(f"✅ {s['name']} · {s['day']} · GHS {s['amount']} · {s['enrolled_at']}")
    await update.message.reply_text("\n".join(lines))

async def list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    data = load_students()
    if not data:
        await update.message.reply_text("No students yet.")
        return
    args = context.args
    if args:
        day_filter = args[0].capitalize()
        filtered = [v for v in data.values() if v["day"] == day_filter]
        lines = [f"📅 {day_filter} students ({len(filtered)}):\n"] + [f"• {s['name']}" for s in filtered]
    else:
        lines = [f"👥 All students ({len(data)}):\n"]
        for s in data.values():
            lines.append(f"✅ {s['name']} — {s['day']} — {s['enrolled_at']}")
    await update.message.reply_text("\n".join(lines))

async def revenue_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    data  = load_students()
    total = sum(s["amount"] for s in data.values())
    await update.message.reply_text(
        f"💰 Revenue Summary\n\n"
        f"✅ Total students enrolled: {len(data)}\n"
        f"💵 Total collected: GHS {total}"
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Enrollment cancelled. Type /start to begin again anytime.")
    return ConversationHandler.END

# ── Build Telegram application ────────────────────────────────────────────────
ptb_app = Application.builder().token(BOT_TOKEN).updater(None).build()

conv = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
        ASK_DAY:  [CallbackQueryHandler(ask_day, pattern="^day_")],
        ASK_PAYMENT: [
            MessageHandler(filters.PHOTO, ask_payment),
            MessageHandler(filters.Document.ALL, ask_payment),
            MessageHandler(filters.TEXT & ~filters.COMMAND, ask_payment),
        ],
        ASK_CONFIRM: [
            MessageHandler(filters.PHOTO, ask_confirm),
            MessageHandler(filters.TEXT & ~filters.COMMAND, ask_confirm),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
ptb_app.add_handler(conv)
ptb_app.add_handler(CommandHandler("report",  report))
ptb_app.add_handler(CommandHandler("list",    list_cmd))
ptb_app.add_handler(CommandHandler("revenue", revenue_cmd))

# ── FastAPI ───────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await ptb_app.initialize()
    await ptb_app.bot.set_webhook(f"{WEBHOOK_URL}/webhook")
    logger.info(f"Webhook set to {WEBHOOK_URL}/webhook")
    yield
    await ptb_app.shutdown()

api = FastAPI(lifespan=lifespan)

@api.get("/")
async def index():
    return PlainTextResponse("TechWithCisco Bot is running! ✅")

@api.post("/webhook")
async def webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, ptb_app.bot)
    await ptb_app.process_update(update)
    return PlainTextResponse("ok")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(api, host="0.0.0.0", port=PORT)
