import telebot
import requests
import re
from ytmusicapi import YTMusic
import os

TOKEN = os.getenv("BOT_TOKEN")
APPLE_TOKEN = os.getenv("APPLE_TOKEN")

bot = telebot.TeleBot(TOKEN)

yt = YTMusic()

def extract_video_id(url):
    match = re.search(r"v=([a-zA-Z0-9_-]+)", url)
    if match:
        return match.group(1)
    return None


def search_song(title, artist):

    url = "https://api.music.apple.com/v1/catalog/us/search"

    params = {
        "term": f"{artist} {title}",
        "types": "songs",
        "limit": 1
    }

    headers = {
        "Authorization": f"Bearer {APPLE_TOKEN}"
    }

    r = requests.get(url, headers=headers, params=params)

    data = r.json()

    try:
        song = data["results"]["songs"]["data"][0]
        return song["id"]
    except:
        return None


def get_lyrics(song_id):

    url = f"https://api.music.apple.com/v1/catalog/us/songs/{song_id}"

    headers = {
        "Authorization": f"Bearer {APPLE_TOKEN}"
    }

    r = requests.get(url, headers=headers)

    return r.text


@bot.message_handler(commands=['start'])
def start(message):

    bot.reply_to(
        message,
        "ابعت:\n\n/yt رابط يوتيوب ميوزك"
    )


@bot.message_handler(commands=['yt'])
def yt(message):

    try:

        url = message.text.split(" ",1)[1]

        video_id = extract_video_id(url)

        song = yt.get_song(video_id)

        title = song["videoDetails"]["title"]
        artist = song["videoDetails"]["author"]

        bot.reply_to(message,f"🎵 {title} - {artist}")

        song_id = search_song(title,artist)

        if not song_id:

            bot.reply_to(message,"❌ لم يتم العثور على الأغنية")
            return

        lyrics = get_lyrics(song_id)

        bot.send_message(message.chat.id,lyrics[:4000])

    except Exception as e:

        bot.reply_to(message,f"خطأ:\n{e}")


print("Bot Running...")

bot.infinity_polling()
