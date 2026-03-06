import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "PUT_YOUR_BOT_TOKEN_HERE"

API_URL = "https://lyrics.api.dacubeking.com/lyrics"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ابعت اسم الأغنية بالشكل ده:\nsong - artist")


async def get_lyrics(song, artist):
    params = {
        "videoId": "test",
        "song": song,
        "artist": artist
    }

    try:
        r = requests.get(API_URL, params=params)
        data = r.json()

        if "lyrics" not in data:
            return None

        lines = []
        for line in data["lyrics"]:
            lines.append(line["text"])

        return "\n".join(lines)

    except:
        return None


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    if "-" not in text:
        await update.message.reply_text("اكتبها كده:\nsong - artist")
        return

    song, artist = text.split("-", 1)
    song = song.strip()
    artist = artist.strip()

    await update.message.reply_text("بدور على الكلمات...")

    lyrics = await get_lyrics(song, artist)

    if lyrics:
        if len(lyrics) > 4000:
            lyrics = lyrics[:4000]

        await update.message.reply_text(lyrics)

    else:
        await update.message.reply_text("مش لاقي كلمات الأغنية 😢")


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, handle_message))

app.run_polling()
