import requests
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TOKEN = "8509336206:AAHnNtM7e9CUeJYeUEZLJT8ZJMlJIeF8hYk"

API_URL = "https://lyrics.api.dacubeking.com/lyrics"


def extract_video_id(url):
    match = re.search(r"v=([a-zA-Z0-9_-]{11})", url)
    if match:
        return match.group(1)
    return None


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    video_id = extract_video_id(text)

    if not video_id:
        await update.message.reply_text("ابعت رابط يوتيوب")
        return

    await update.message.reply_text("بدور على الكلمات...")

    try:
        r = requests.get(API_URL, params={"videoId": video_id})
        data = r.json()

        if "syncedLyrics" in data and data["syncedLyrics"]:
            lyrics = data["syncedLyrics"]
        elif "lyrics" in data and data["lyrics"]:
            lyrics = data["lyrics"]
        else:
            await update.message.reply_text("مش لاقي كلمات للأغنية")
            return

        if len(lyrics) > 4000:
            lyrics = lyrics[:4000]

        await update.message.reply_text(lyrics)

    except Exception as e:
        await update.message.reply_text("خطأ: " + str(e))


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(MessageHandler(filters.TEXT, handle_message))

app.run_polling()
