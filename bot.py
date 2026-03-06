import telebot
import requests
from ytmusicapi import YTMusic

BOT_TOKEN = "8509336206:AAHnNtM7e9CUeJYeUEZLJT8ZJMlJIeF8hYk"

bot = telebot.TeleBot(BOT_TOKEN)
yt = YTMusic()

def get_video_id(link):
    if "v=" in link:
        return link.split("v=")[1].split("&")[0]
    if "youtu.be/" in link:
        return link.split("youtu.be/")[1].split("?")[0]
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
    except:
        bot.reply_to(message,"❌ ابعت الامر كده:\n/yt link")
        return

    video_id = get_video_id(link)

    if not video_id:
        bot.reply_to(message,"❌ الرابط غير صحيح")
        return

    bot.reply_to(message,"🔎 جاري جلب معلومات الاغنية...")

    try:
        info = yt.get_song(video_id)
        details = info.get("videoDetails",{})

        title = details.get("title")
        artist = details.get("author")
        duration = int(details.get("lengthSeconds",0))

    except:
        bot.send_message(message.chat.id,"❌ لم استطع جلب معلومات الفيديو")
        return

    if not title:
        bot.send_message(message.chat.id,"❌ لم استطع جلب معلومات الفيديو")
        return

    bot.send_message(message.chat.id,f"🎵 {title}\n👤 {artist}\n\n🔎 جاري البحث عن الكلمات...")

    lyrics = get_lyrics(title,artist,duration)

    if not lyrics:
        bot.send_message(message.chat.id,"❌ لم يتم العثور على كلمات")
        return

    try:
        filename = "lyrics.txt"

        with open(filename,"w",encoding="utf-8") as f:
            f.write(lyrics)

        with open(filename,"rb") as f:
            bot.send_document(message.chat.id,f)

    except Exception as e:
        bot.send_message(message.chat.id,f"❌ خطأ:\n{e}")


bot.infinity_polling()
