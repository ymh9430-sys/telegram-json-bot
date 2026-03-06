import telebot
import requests
from ytmusicapi import YTMusic
import urllib.parse as urlparse

BOT_TOKEN = "8509336206:AAHnNtM7e9CUeJYeUEZLJT8ZJMlJIeF8hYk"

bot = telebot.TeleBot(BOT_TOKEN)
yt = YTMusic()

def extract_video_id(url):
    parsed = urlparse.urlparse(url)

    if parsed.query:
        params = urlparse.parse_qs(parsed.query)
        if "v" in params:
            return params["v"][0]

    if "youtu.be" in parsed.netloc:
        return parsed.path[1:]

    return None


def get_lyrics(title, artist, duration=0):
    url = "https://lyrics-api.boidu.dev/getLyrics"

    params = {
        "s": title,
        "a": artist,
        "d": duration
    }

    try:
        r = requests.get(url, params=params, timeout=15)

        if r.status_code == 200:
            data = r.json()
            return data.get("ttml")

    except:
        pass

    return None


@bot.message_handler(commands=['yt'])
def handle(message):

    try:

        link = message.text.split(" ",1)[1]

        video_id = extract_video_id(link)

        if not video_id:
            bot.reply_to(message,"❌ رابط غير صحيح")
            return

        info = yt.get_song(video_id)

        title = info["videoDetails"]["title"]
        artist = info["videoDetails"]["author"]
        duration = int(info["videoDetails"]["lengthSeconds"])

        bot.reply_to(message,f"🎵 {title}\n👤 {artist}\n\n🔎 جاري البحث عن الكلمات...")

        lyrics = get_lyrics(title,artist,duration)

        if lyrics:

            if len(lyrics) > 4000:
                lyrics = lyrics[:4000]

            bot.send_message(message.chat.id,lyrics)

        else:
            bot.send_message(message.chat.id,"❌ لم يتم العثور على كلمات")

    except Exception as e:

        bot.send_message(message.chat.id,f"خطأ:\n{e}")


print("Bot started...")

bot.infinity_polling()
