import telebot
import requests
import urllib.parse as urlparse
from yt_dlp import YoutubeDL

BOT_TOKEN = "8509336206:AAHnNtM7e9CUeJYeUEZLJT8ZJMlJIeF8hYk"

bot = telebot.TeleBot(BOT_TOKEN)


def extract_video_id(url):
    parsed = urlparse.urlparse(url)

    if "v=" in url:
        return url.split("v=")[1].split("&")[0]

    if "youtu.be" in parsed.netloc:
        return parsed.path.replace("/","")

    return None


def get_video_info(url):

    ydl_opts = {
        'quiet': True,
        'skip_download': True
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    title = info.get("title")
    artist = info.get("uploader")
    duration = int(info.get("duration",0))

    return title, artist, duration


def get_lyrics(title, artist, duration):

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

        link = message.text.split(" ",1)[1]

        video_id = extract_video_id(link)

        if not video_id:
            bot.reply_to(message,"❌ رابط غير صحيح")
            return

        title, artist, duration = get_video_info(link)

        bot.reply_to(
            message,
            f"🎵 {title}\n👤 {artist}\n⏱ {duration}s\n\n🔎 جاري البحث عن الكلمات..."
        )

        lyrics = get_lyrics(title, artist, duration)

        for i in range(0, len(lyrics), 4000):
    bot.send_message(message.chat.id, lyrics[i:i+4000])
        else:
            bot.send_message(message.chat.id,"❌ لم يتم العثور على كلمات")

    except Exception as e:
        bot.send_message(message.chat.id,str(e))


print("Bot running...")

bot.infinity_polling()
