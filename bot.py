import asyncio
from datetime import datetime, timedelta
from telegram import Update, ChatPermissions
from telegram.ext import Application, MessageHandler, filters, ContextTypes

BOT_TOKEN = "9207416361:AAEegDiQJjdqivN-aYAWCoykq417bK9HvCE"

user_warnings = {}
pending_verifications = {}

WAIT_SECONDS = 120
WARN_LIMIT = 3

async def check_voice_timeout(chat_id: int, user_id: int, video_message_id: int, context: ContextTypes.DEFAULT_TYPE):
    await asyncio.sleep(WAIT_SECONDS)
    chat_pending = pending_verifications.get(chat_id, {})
    user_state = chat_pending.get(user_id)
    
    if user_state and not user_state.get("has_voice"):
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=video_message_id)
        except Exception:
            pass

        current_warns = user_warnings.get(user_id, 0) + 1
        user_warnings[user_id] = current_warns

        if current_warns >= WARN_LIMIT:
            try:
                until_date = datetime.now() + timedelta(days=1)
                await context.bot.restrict_chat_member(
                    chat_id=chat_id,
                    user_id=user_id,
                    permissions=ChatPermissions(can_send_messages=False),
                    until_date=until_date
                )
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"⚠️ உறுப்பினர் [ID: {user_id}] தொடர்ந்து 3 முறை குரல் விளக்கம் இல்லாமல் வீடியோ பதிவிட்டதால் 24 மணிநேரத்திற்கு மியூட் செய்யப்பட்டுள்ளார்."
                )
            except Exception as e:
                print(f"Mute error: {e}")
            user_warnings[user_id] = 0
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"⚠️ எச்சரிக்கை ({current_warns}/{WARN_LIMIT}): வீடியோ பகிர்ந்தால் 2 நிமிடத்திற்குள் அதற்கான குரல் விளக்கம் கட்டாயம் அளிக்கப்பட வேண்டும்! பதிவு நீக்கப்பட்டது."
            )
            
        if user_id in chat_pending:
            del chat_pending[user_id]

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    chat_id = chat.id
    user_id = user.id

    if chat_id not in pending_verifications:
        pending_verifications[chat_id] = {}

    if user_id in pending_verifications[chat_id]:
        pending_verifications[chat_id][user_id]["task"].cancel()

    task = asyncio.create_task(check_voice_timeout(chat_id, user_id, message.message_id, context))
    pending_verifications[chat_id][user_id] = {
        "message_id": message.message_id,
        "has_voice": False,
        "task": task
    }

    await message.reply_text("⏳ இந்த வீடியோவிற்கான குரல் பதிவு விளக்கத்தை அடுத்த 2 நிமிடங்களுக்குள் அனுப்பவும்.")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    chat_pending = pending_verifications.get(chat_id, {})
    if user_id in chat_pending:
        chat_pending[user_id]["task"].cancel()
        del chat_pending[user_id]
        await update.effective_message.reply_text("✅ குரல் பதிவு விளக்கம் பெறப்பட்டது. நன்றி!")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.VIDEO | filters.VIDEO_NOTE, handle_video))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    print("பாட் இயங்கத் தொடங்கியது...")
    app.run_polling()

if __name__ == "__main__":
    main()
