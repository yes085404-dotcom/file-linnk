import os
import asyncio
import threading
from flask import Flask
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================= CONFIGURATION (Render Environment se load hoga) =================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "0"))

ADMIN_USERNAME = "surajraj01231"
ADMIN_PASSWORD = "Boss@2011123"
AUTO_DELETE_SECONDS = 120 * 60  # 120 Minutes
# ==================================================================================

admin_states = {}

# 24/7 Render Keep-Alive Web Server
web_app = Flask(__name__)

@web_app.route("/")
def home():
    return "Sanskari Vault Bot is Running 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port)


async def delete_messages_later(bot, chat_id, message_ids, delay=1.5):
    await asyncio.sleep(delay)
    for mid in message_ids:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=mid)
        except Exception:
            pass


async def auto_delete_user_file(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data
    try:
        await context.bot.delete_message(
            chat_id=job_data["chat_id"],
            message_id=job_data["message_id"]
        )
    except Exception:
        pass


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.effective_chat.type != "private":
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    try:
        await update.message.delete()
    except Exception:
        pass

    msg = await context.bot.send_message(chat_id=chat_id, text="Username")
    admin_states[user_id] = {"step": "WAIT_USER", "prompt_id": msg.message_id}


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.effective_chat.type != "private":
        return

    if not context.args:
        return

    payload = context.args[0]
    if not payload.startswith("SV"):
        return

    try:
        encoded_num = int(payload[2:])
        if encoded_num % 7919 != 0:
            return
        storage_msg_id = encoded_num // 7919
    except ValueError:
        return

    chat_id = update.effective_chat.id
    caption_text = (
        "⚠️ Yeh file 120 minutes me automatically delete ho jayegi.\n\n"
        "Contact Admin @isurajsethh"
    )

    try:
        sent_msg = await context.bot.copy_message(
            chat_id=chat_id,
            from_chat_id=CHANNEL_ID,
            message_id=storage_msg_id,
            caption=caption_text,
            protect_content=True,
        )

        context.job_queue.run_once(
            auto_delete_user_file,
            when=AUTO_DELETE_SECONDS,
            data={"chat_id": chat_id, "message_id": sent_msg.message_id},
        )
    except Exception:
        pass


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.effective_chat.type != "private":
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    text = update.message.text.strip()

    if user_id not in admin_states:
        return

    state = admin_states[user_id]

    if state["step"] == "WAIT_USER":
        if text == ADMIN_USERNAME:
            verify_msg = await update.message.reply_text("Username verify")
            to_delete = [state["prompt_id"], update.message.message_id, verify_msg.message_id]
            await delete_messages_later(context.bot, chat_id, to_delete, delay=1.5)

            pass_prompt = await context.bot.send_message(chat_id=chat_id, text="Password")
            admin_states[user_id] = {"step": "WAIT_PASS", "prompt_id": pass_prompt.message_id}
        else:
            to_delete = [state["prompt_id"], update.message.message_id]
            admin_states.pop(user_id, None)
            await delete_messages_later(context.bot, chat_id, to_delete, delay=0.5)

    elif state["step"] == "WAIT_PASS":
        if text == ADMIN_PASSWORD:
            verify_msg = await update.message.reply_text("Password verify successfully")
            to_delete = [state["prompt_id"], update.message.message_id, verify_msg.message_id]
            await delete_messages_later(context.bot, chat_id, to_delete, delay=1.5)

            await context.bot.send_message(chat_id=chat_id, text="नमस्ते सर अपना फाइल डालिए")
            admin_states[user_id] = {"step": "AUTHENTICATED"}
        else:
            to_delete = [state["prompt_id"], update.message.message_id]
            admin_states.pop(user_id, None)
            await delete_messages_later(context.bot, chat_id, to_delete, delay=0.5)


async def handle_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.effective_chat.type != "private":
        return

    user_id = update.effective_user.id

    if user_id not in admin_states or admin_states[user_id].get("step") != "AUTHENTICATED":
        return

    stored_msg = await update.message.copy(chat_id=CHANNEL_ID)

    bot_info = await context.bot.get_me()
    code = f"SV{stored_msg.message_id * 7919}"
    share_link = f"https://t.me/{bot_info.username}?start={code}"

    await update.message.reply_text(
        f"Ye raha link\n<code>{share_link}</code>",
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


def main():
    if not BOT_TOKEN or CHANNEL_ID == 0:
        raise ValueError("Error: Render Environment Variables me BOT_TOKEN aur CHANNEL_ID set karein!")

    threading.Thread(target=run_web, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(
        MessageHandler(
            filters.VIDEO | filters.Document.ALL | filters.PHOTO | filters.AUDIO | filters.VOICE,
            handle_files,
        )
    )

    print("Sanskari Vault Bot Started!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
