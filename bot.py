import telebot
import os
import re
from ytmusicapi import YTMusic

TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

yt = YTMusic()

def format_time(seconds):
    seconds = float(seconds)
    minutes = int(seconds // 60)
    remaining = seconds % 60
    return f"{minutes:02d}:{remaining:06.3f}"

def extract_video_id(url):
    match = re.search(r"v=([a-zA-Z0-9_-]+)", url)
    if match:
        return match.group(1)
    return None

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message,"ابعت لينك YouTube Music بعد /yt")

@bot.message_handler(commands=['yt'])
def get_song(message):
    try:
        url = message.text.split(" ")[1]
    except:
        bot.reply_to(message,"ابعت اللينك بعد الأمر")
        return

    video_id = extract_video_id(url)

    if not video_id:
        bot.reply_to(message,"لينك غير صحيح")
        return

    info = yt.get_song(video_id)

    title = info["videoDetails"]["title"]
    artist = info["videoDetails"]["author"]

    bot.reply_to(message,f"لقيت الأغنية 🎵\n{artist} - {title}")

    # هنا هنضيف جلب lyrics بعد كده
    bot.send_message(message.chat.id,"جاري البحث عن الكلمات...")

bot.infinity_polling()
