import os
import json
import logging
from datetime import datetime

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, ConversationHandler, filters
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
BOT_TOKEN      = os.environ.get("BOT_TOKEN", "8535568864:AAFWDifPgQate3OtTH6xasZcrklWvemzsDk")
WEBHOOK_URL    = os.environ.get("WEBHOOK_URL", "")   # e.g. https://techwithcisco-bot.onrender.com
ADMIN_USERNAME = "Othniel"
MOMO_NUMBER    = "0243 812 365"
COURSE_PRICE   = 200
DATA_FILE      = "students.json"
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
PORT = int(os.environ.get("PORT", 8080))

DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
ASK_NAME, ASK_DAY, ASK_TXID = range(3)

# ── Data helpers ──────────────────────────────────────────────────────────────
def load_students():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_students(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def add_student(user_id, name, day, tx_id):
    data = load_students()
    data[str(user_id)] = {
        "name": name, "day": day, "tx_id": tx_id,
        "amount": COURSE_PRICE, "status": "pending",
        "enrolled_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "telegram_id": user_id,
    }
    save_students(data)

def update_status(user_id, status):
    data = load_students()
    if str(user_id) in data:
        data[str(user_id)]["status"] = status
        save_students(data)

def get_student(user_id):
    return load_students().get(str(user_id))

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
        parse_mode="Markdown",
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
        reply_markup=InlineKeyboardMarkup(keyboard),
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
        "Once sent, reply here with your *MoMo transaction ID*.",
        parse_mode="Markdown",
    )
    return ASK_TXID

async def ask_txid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tx_id  = update.message.text.strip()
    user   = update.effective_user
    name   = context.user_data["name"]
    day    = context.user_data["day"]
    add_student(user.id, name, day, tx_id)
    await update.message.reply_text(
        f"Thank you, *{name}*! 🙏\n\n"
        f"Transaction ID *{tx_id}* received.\n\n"
        "⏳ Verifying your payment — you'll get your community link within a few minutes!",
        parse_mode="Markdown",
    )
    await notify_admin(context, user.id, name, day, tx_id, user.username or "No username")
    return ConversationHandler.END

async def notify_admin(context, user_id, name, day, tx_id, username):
    keyboard = [[
        InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}"),
        InlineKeyboardButton("❌ Reject",  callback_data=f"reject_{user_id}"),
    ]]
    msg = (
        f"🔔 *New Enrollment Request!*\n\n"
        f"👤 Name: *{name}*\n"
        f"📅 Day: *{day}*\n"
        f"💰 Amount: GHS {COURSE_PRICE}\n"
        f"🧾 Transaction ID: `{tx_id}`\n"
        f"📱 Telegram: @{username}\n"
        f"🆔 User ID: `{user_id}`\n"
        f"⏰ Time: {datetime.now().strftime('%d %b %Y, %I:%M %p')}"
    )
    try:
        admin = await context.bot.get_chat(f"@{ADMIN_USERNAME}")
        await context.bot.send_message(
            chat_id=admin.id, text=msg,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    except Exception as e:
        logger.error(f"Could not notify admin: {e}")

async def handle_approval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, user_id = query.data.split("_", 1)
    user_id = int(user_id)
    student = get_student(user_id)
    if not student:
        await query.edit_message_text("Student not found.")
        return
    name, day = student["name"], student["day"]
    if action == "approve":
        update_status(user_id, "approved")
        day_link = DAY_LINKS.get(day, ANNOUNCEMENTS_LINK)
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                f"🎉 *Welcome to PC Basics Academy, {name}!*\n\n"
                f"Your payment has been confirmed! You're enrolled for *{day}* sessions.\n\n"
                f"Please follow these two steps to get in:\n\n"
                f"*Step 1 — Join the community first* 👇\n"
                f"{COMMUNITY_JOIN_LINK}\n\n"
                f"*Step 2 — Then open your {day} class* 👇\n"
                f"{day_link}\n\n"
                f"*📢 General announcements* 👇\n"
                f"{ANNOUNCEMENTS_LINK}\n\n"
                f"Welcome aboard! See you in class 📚💻"
            ),
            parse_mode="Markdown",
        )
        await query.edit_message_text(
            query.message.text + f"\n\n✅ *Approved* — link sent to {name}.",
            parse_mode="Markdown",
        )
    else:
        update_status(user_id, "rejected")
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                f"Hi {name}, we couldn't verify your transaction ID.\n\n"
                "Please check and send the correct MoMo transaction ID, or contact us for help."
            ),
        )
        await query.edit_message_text(
            query.message.text + f"\n\n❌ *Rejected* — {name} has been notified.",
            parse_mode="Markdown",
        )

# ── Admin commands ────────────────────────────────────────────────────────────
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.username != ADMIN_USERNAME:
        return
    data     = load_students()
    approved = [s for s in data.values() if s["status"] == "approved"]
    pending  = [s for s in data.values() if s["status"] == "pending"]
    revenue  = sum(s["amount"] for s in approved)
    lines = [
        f"📊 *Enrollment Report — {datetime.now().strftime('%d %b %Y')}*\n",
        f"👥 Total: *{len(data)}* | ✅ Approved: *{len(approved)}* | ⏳ Pending: *{len(pending)}*",
        f"💰 Revenue: *GHS {revenue}*\n─────────────────────",
    ]
    for s in data.values():
        icon = "✅" if s["status"] == "approved" else ("⏳" if s["status"] == "pending" else "❌")
        lines.append(f"{icon} {s['name']} · {s['day']} · GHS {s['amount']} · {s['enrolled_at']}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

async def list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.username != ADMIN_USERNAME:
        return
    data = load_students()
    if not data:
        await update.message.reply_text("No students yet.")
        return
    args = context.args
    if args:
        day_filter = args[0].capitalize()
        filtered = {k: v for k, v in data.items() if v["day"] == day_filter}
        lines = [f"📅 *{day_filter} students:*\n"] + [
            f"• {s['name']} — {s['status']}" for s in filtered.values()
        ]
    else:
        lines = ["👥 *All students:*\n"]
        for s in data.values():
            icon = "✅" if s["status"] == "approved" else "⏳"
            lines.append(f"{icon} {s['name']} — {s['day']} — {s['status']}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

async def pending_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.username != ADMIN_USERNAME:
        return
    data  = load_students()
    plist = [(uid, s) for uid, s in data.items() if s["status"] == "pending"]
    if not plist:
        await update.message.reply_text("No pending approvals. All caught up! ✅")
        return
    await update.message.reply_text(f"⏳ *{len(plist)} pending approvals:*", parse_mode="Markdown")
    for uid, s in plist:
        keyboard = [[
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{uid}"),
            InlineKeyboardButton("❌ Reject",  callback_data=f"reject_{uid}"),
        ]]
        await update.message.reply_text(
            f"👤 *{s['name']}* — {s['day']}\nTX: `{s['tx_id']}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

async def revenue_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.username != ADMIN_USERNAME:
        return
    data     = load_students()
    approved = [s for s in data.values() if s["status"] == "approved"]
    pending  = [s for s in data.values() if s["status"] == "pending"]
    total    = sum(s["amount"] for s in approved)
    await update.message.reply_text(
        f"💰 *Revenue Summary*\n\n"
        f"✅ Approved students: *{len(approved)}*\n"
        f"⏳ Pending students: *{len(pending)}*\n"
        f"💵 Total collected: *GHS {total}*\n"
        f"📈 Potential if all pending approved: *GHS {total + len(pending) * COURSE_PRICE}*",
        parse_mode="Markdown",
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Enrollment cancelled. Type /start to begin again anytime.")
    return ConversationHandler.END

# ── Build PTB Application ─────────────────────────────────────────────────────
def build_application() -> Application:
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .updater(None)   # webhook mode — no polling updater needed
        .build()
    )

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_DAY:  [CallbackQueryHandler(ask_day, pattern="^day_")],
            ASK_TXID: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_txid)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
    )

    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(handle_approval, pattern="^(approve|reject)_"))
    app.add_handler(CommandHandler("report",  report))
    app.add_handler(CommandHandler("list",    list_cmd))
    app.add_handler(CommandHandler("pending", pending_cmd))
    app.add_handler(CommandHandler("revenue", revenue_cmd))
    return app

# ── Starlette ASGI app ────────────────────────────────────────────────────────
ptb_app = build_application()

async def health(request: Request) -> PlainTextResponse:
    return PlainTextResponse("TechWithCisco Bot is running! ✅")

async def webhook_handler(request: Request) -> PlainTextResponse:
    data   = await request.json()
    update = Update.de_json(data, ptb_app.bot)
    await ptb_app.process_update(update)
    return PlainTextResponse("ok")

async def on_startup():
    await ptb_app.initialize()
    await ptb_app.bot.set_webhook(f"{WEBHOOK_URL}/webhook")
    logger.info(f"Webhook set to {WEBHOOK_URL}/webhook")

async def on_shutdown():
    await ptb_app.shutdown()

starlette_app = Starlette(
    routes=[
        Route("/",        health),
        Route("/webhook", webhook_handler, methods=["POST"]),
    ],
    on_startup=[on_startup],
    on_shutdown=[on_shutdown],
)

# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(starlette_app, host="0.0.0.0", port=PORT)
