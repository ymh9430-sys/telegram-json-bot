import telebot
import requests
from ytmusicapi import YTMusic
import re

BOT_TOKEN = "8509336206:AAHnNtM7e9CUeJYeUEZLJT8ZJMlJIeF8hYk"

bot = telebot.TeleBot(BOT_TOKEN)
yt = YTMusic()


def extract_video_id(url):
    patterns = [
        r"v=([a-zA-Z0-9_-]{11})",
        r"youtu\.be/([a-zA-Z0-9_-]{11})",
        r"music\.youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})"
    ]

    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)

    return None


def get_lyrics(title, artist, duration=0):
    url = "https://lyrics-api.boidu.dev/getLyrics"

    params = {
        "s": title,
        "a": artist,
        "d": duration
    }

    r = requests.get(url, params=params)

    if r.status_code == 200:
        data = r.json()
        return data.get("ttml")

    return None


@bot.message_handler(commands=['yt'])
def handle(message):
    try:

        link = message.text.split(" ", 1)[1]

        video_id = extract_video_id(link)

        if not video_id:
            bot.reply_to(message, "❌ لم أستطع استخراج video id")
            return

        info = yt.get_song(video_id)

        if not info:
            bot.reply_to(message, "❌ لم استطع جلب معلومات الفيديو")
            return

        video = info.get("videoDetails", {})

        title = video.get("title")
        artist = video.get("author")
        duration = int(video.get("lengthSeconds", 0))

        if not title:
            bot.reply_to(message, "❌ لم استطع جلب معلومات الفيديو")
            return

        bot.reply_to(
            message,
            f"🎵 {title}\n👤 {artist}\n\nجاري البحث عن الكلمات..."
        )

        lyrics = get_lyrics(title, artist, duration)

        if not lyrics:
            bot.send_message(message.chat.id, "❌ لم يتم العثور على كلمات")
            return

        with open("lyrics.txt", "w", encoding="utf-8") as f:
            f.write(lyrics)

        with open("lyrics.txt", "rb") as f:
            bot.send_document(message.chat.id, f)

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ:\n{str(e)}")


bot.infinity_polling()
