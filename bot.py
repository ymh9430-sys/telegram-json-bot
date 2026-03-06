import telebot
import requests
from ytmusicapi import YTMusic
import re

BOT_TOKEN = "8509336206:AAHnNtM7e9CUeJYeUEZLJT8ZJMlJIeF8hYk"

bot = telebot.TeleBot(BOT_TOKEN)
yt = YTMusic()

def extract_video_id(url):
    match = re.search(r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})", url)
    if match:
        return match.group(1)
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

        if len(message.text.split()) < 2:
            bot.reply_to(message, "ابعت رابط يوتيوب بعد الأمر\n/yt link")
            return

        link = message.text.split(" ",1)[1]

        video_id = extract_video_id(link)

        if not video_id:
            bot.reply_to(message,"❌ رابط غير صحيح")
            return

        info = yt.get_song(video_id)

        if not info or "videoDetails" not in info:
            bot.reply_to(message,"❌ لم استطع جلب معلومات الفيديو")
            return

        details = info["videoDetails"]

        title = details["title"]
        artist = details["author"]
        duration = int(details["lengthSeconds"])

        bot.reply_to(message,f"🎵 {title}\n👤 {artist}\n\nجاري البحث عن الكلمات...")

        lyrics = get_lyrics(title,artist,duration)

        if lyrics:
            bot.send_message(message.chat.id,lyrics[:4000])
        else:
            bot.send_message(message.chat.id,"❌ لم يتم العثور على كلمات")

    except Exception as e:
        bot.send_message(message.chat.id,"خطأ:\n"+str(e))


bot.infinity_polling()
