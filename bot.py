import telebot
import requests
from ytmusicapi import YTMusic
import re
import xml.etree.ElementTree as ET

BOT_TOKEN = "8509336206:AAHnNtM7e9CUeJYeUEZLJT8ZJMlJIeF8hYk"

bot = telebot.TeleBot(BOT_TOKEN)
yt = YTMusic()

# استخراج video id من أي رابط
def extract_video_id(url):

    patterns = [
        r"v=([a-zA-Z0-9_-]{11})",
        r"youtu\.be/([a-zA-Z0-9_-]{11})",
        r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
        r"music\.youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})"
    ]

    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)

    return None


# تحويل الوقت لثواني
def parse_time(t):

    try:
        if ":" in t:
            m, s = t.split(":")
            return int(m) * 60 + float(s)
        return float(t)
    except:
        return 0


# تنسيق الوقت
def format_time(sec):

    m = int(sec // 60)
    s = sec % 60

    return f"{m:02d}:{s:06.3f}"


# تحويل TTML إلى الصيغة المطلوبة
def convert_ttml(ttml):

    root = ET.fromstring(ttml)

    result = []
    used_times = set()

    for p in root.iter():

        if not p.tag.endswith("p"):
            continue

        begin = p.attrib.get("begin")

        if not begin:
            continue

        sec = parse_time(begin)

        while round(sec,3) in used_times:
            sec += 0.001

        used_times.add(round(sec,3))

        line_time = format_time(sec)

        line = f"[{line_time}]"

        words = []

        for span in p.iter():

            if not span.tag.endswith("span"):
                continue

            b = span.attrib.get("begin")
            e = span.attrib.get("end")
            word = span.text

            if not b or not e or not word:
                continue

            b = format_time(parse_time(b))
            e = format_time(parse_time(e))

            words.append(f"<{b}>{word}<{e}>")

        if words:
            line += " " + " ".join(words)
            result.append(line)

    return "\n".join(result)


# جلب الكلمات
def get_lyrics(title, artist, duration):

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

        link = message.text.split(" ",1)[1]

    except:
        bot.reply_to(message,"اكتب الأمر هكذا:\n/yt LINK")
        return

    video_id = extract_video_id(link)

    if not video_id:
        bot.reply_to(message,"❌ رابط غير صالح")
        return


    # جلب معلومات الفيديو
    try:

        info = yt.get_song(video_id)

        video = info.get("videoDetails",{})

        title = video.get("title")
        artist = video.get("author")
        duration = int(video.get("lengthSeconds",0))

    except:

        title = None


    # fallback
    if not title:

        try:

            r = requests.get(f"https://noembed.com/embed?url=https://www.youtube.com/watch?v={video_id}")

            data = r.json()

            title = data.get("title","Unknown")
            artist = data.get("author_name","Unknown")
            duration = 0

        except:

            bot.reply_to(message,"❌ لم استطع جلب معلومات الفيديو")
            return


    bot.reply_to(message,f"🎵 {title}\n👤 {artist}\n\nجاري البحث عن الكلمات...")


    lyrics_ttml = get_lyrics(title,artist,duration)

    if not lyrics_ttml:
        bot.send_message(message.chat.id,"❌ لم يتم العثور على كلمات")
        return


    try:

        lyrics = convert_ttml(lyrics_ttml)

    except:

        bot.send_message(message.chat.id,"❌ خطأ في معالجة الكلمات")
        return


    with open("lyrics.txt","w",encoding="utf-8") as f:
        f.write(lyrics)


    with open("lyrics.txt","rb") as f:
        bot.send_document(message.chat.id,f)


bot.infinity_polling()
