import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

TOKEN = "8509336206:AAHnNtM7e9CUeJYeUEZLJT8ZJMlJIeF8hYk"


def extract_video_id(url):
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]

    if "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]

    return None


def get_lyrics(video_id):

    url = "https://lyrics.api.dacubeking.com/lyrics"

    params = {
        "videoId": video_id
    }

    r = requests.get(url, params=params)

    if r.status_code != 200:
        return None

    data = r.json()

    if "lyrics" in data:
        return data["lyrics"]

    return None


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    video_id = extract_video_id(text)

    if not video_id:
        await update.message.reply_text("ابعت رابط يوتيوب صحيح")
        return

    await update.message.reply_text("بجيب الكلمات...")

    lyrics = get_lyrics(video_id)

    if not lyrics:
        await update.message.reply_text("ملقتش كلمات للأغنية دي")
        return

    with open("lyrics.lrc", "w", encoding="utf-8") as f:
        f.write(lyrics)

    await update.message.reply_document(open("lyrics.lrc", "rb"))


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(MessageHandler(filters.TEXT, handle_message))

app.run_polling()
