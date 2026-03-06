import telebot
import requests
from ytmusicapi import YTMusic

BOT_TOKEN = "8509336206:AAHnNtM7e9CUeJYeUEZLJT8ZJMlJIeF8hYk"

bot = telebot.TeleBot(BOT_TOKEN)
yt = YTMusic()

def get_lyrics(title, artist, duration=0):
    url = "https://lyrics-api.boidu.dev/getLyrics"

    params = {
        "s": title,
        "a": artist,
        "d": duration
    }

    try:
        r = requests.get(url, params=params, timeout=10)

        if r.status_code == 200:
            data = r.json()
            return data.get("ttml")

    except:
        return None

    return None


@bot.message_handler(commands=['yt'])
def handle(message):
    try:
        if " " not in message.text:
            bot.reply_to(message,"ارسل الامر هكذا:\n/yt رابط الاغنية")
            return

        link = message.text.split(" ",1)[1]

        if "v=" not in link:
            bot.reply_to(message,"الرابط غير صحيح")
            return

        video_id = link.split("v=")[1].split("&")[0]

        info = yt.get_song(video_id)

        title = info["videoDetails"]["title"]
        artist = info["videoDetails"]["author"]
        duration = int(info["videoDetails"]["lengthSeconds"])

        bot.reply_to(message,f"🎵 {title}\n👤 {artist}\n\nجاري البحث عن الكلمات...")

        lyrics = get_lyrics(title,artist,duration)

        if lyrics:
            bot.send_message(message.chat.id, lyrics[:4000])
        else:
            bot.send_message(message.chat.id,"❌ لم يتم العثور على كلمات")

    except Exception as e:
        bot.send_message(message.chat.id,f"خطأ:\n{str(e)}")


print("Bot Started...")
bot.infinity_polling()
