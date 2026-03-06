import telebot
import requests
from ytmusicapi import YTMusic
import urllib.parse as urlparse

BOT_TOKEN = "8509336206:AAHnNtM7e9CUeJYeUEZLJT8ZJMlJIeF8hYk"

bot = telebot.TeleBot(BOT_TOKEN)

yt = YTMusic()  # بدون auth


def extract_video_id(url):
    parsed = urlparse.urlparse(url)

    if "v=" in url:
        return url.split("v=")[1].split("&")[0]

    if "youtu.be" in parsed.netloc:
        return parsed.path.replace("/","")

    return None


def get_song_info(video_id):

    url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"

    r = requests.get(url)

    if r.status_code == 200:
        data = r.json()
        title = data["title"]
        author = data["author_name"]
        return title, author

    return None, None


def get_lyrics(title, artist):

    url = "https://lyrics-api.boidu.dev/getLyrics"

    params = {
        "s": title,
        "a": artist
    }

    r = requests.get(url, params=params)

    if r.status_code == 200:
        data = r.json()
        return data.get("ttml")

    return None


@bot.message_handler(commands=['yt'])
def handle(message):

    try:

        link = message.text.split(" ",1)[1]

        video_id = extract_video_id(link)

        if not video_id:
            bot.reply_to(message,"❌ رابط غير صحيح")
            return

        title, artist = get_song_info(video_id)

        if not title:
            bot.reply_to(message,"❌ لم استطع جلب معلومات الفيديو")
            return

        bot.reply_to(message,f"🎵 {title}\n👤 {artist}\n\n🔎 جاري البحث عن الكلمات...")

        lyrics = get_lyrics(title,artist)

        if lyrics:
            bot.send_message(message.chat.id,lyrics[:4000])
        else:
            bot.send_message(message.chat.id,"❌ لم يتم العثور على كلمات")

    except Exception as e:
        bot.send_message(message.chat.id,f"خطأ:\n{e}")


print("Bot started...")

bot.infinity_polling()
