import telebot
import requests
from ytmusicapi import YTMusic

BOT_TOKEN = "PUT_YOUR_TOKEN_HERE"

bot = telebot.TeleBot(BOT_TOKEN)
yt = YTMusic()

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
        link = message.text.split(" ",1)[1]

        search = yt.get_song(link.split("v=")[1])

        title = search["videoDetails"]["title"]
        artist = search["videoDetails"]["author"]
        duration = int(search["videoDetails"]["lengthSeconds"])

        bot.reply_to(message,f"🎵 {title}\n👤 {artist}\n\nجاري البحث عن الكلمات...")

        lyrics = get_lyrics(title,artist,duration)

        if lyrics:
            bot.send_message(message.chat.id,lyrics[:4000])
        else:
            bot.send_message(message.chat.id,"❌ لم يتم العثور على كلمات")

    except Exception as e:
        bot.send_message(message.chat.id,f"Error\n{e}")

bot.infinity_polling()
