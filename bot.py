import telebot
import requests
from ytmusicapi import YTMusic
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, parse_qs

BOT_TOKEN = "8509336206:AAHnNtM7e9CUeJYeUEZLJT8ZJMlJIeF8hYk"

bot = telebot.TeleBot(BOT_TOKEN)
yt = YTMusic()


# استخراج video id من أي لينك
def extract_video_id(url):

    try:

        parsed = urlparse(url)

        if "youtu.be" in parsed.netloc:
            return parsed.path.replace("/", "")

        if "youtube.com" in parsed.netloc or "music.youtube.com" in parsed.netloc:
            qs = parse_qs(parsed.query)
            return qs.get("v", [None])[0]

    except:
        pass

    return None


def clean_artist(name):

    if not name:
        return ""

    name = name.replace("- Topic", "")
    name = name.replace("VEVO", "")
    return name.strip()


def parse_time(t):

    if ":" in t:
        m, s = t.split(":")
        return int(m) * 60 + float(s)

    return float(t)


def format_time(sec):

    m = int(sec // 60)
    s = sec % 60

    return f"{m:02d}:{s:06.3f}"


def convert_ttml(ttml):

    root = ET.fromstring(ttml)

    ns = {'tt': 'http://www.w3.org/ns/ttml'}

    result = []
    used_times = set()

    for p in root.findall(".//tt:p", ns):

        begin = p.attrib.get("begin")

        if not begin:
            continue

        sec = parse_time(begin)

        # منع اختفاء السطور المتشابهة
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

            if data.get("ttml"):
                return data.get("ttml")

    except:
        pass

    # محاولة ثانية بدون الفنان
    try:

        params = {"s": title}

        r = requests.get(url, params=params, timeout=10)

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
            bot.reply_to(message,"❌ لم أستطع استخراج video id")
            return

        title = None
        artist = None
        duration = 0

        try:

            info = yt.get_song(video_id)
            video = info.get("videoDetails",{})

            title = video.get("title")
            artist = clean_artist(video.get("author"))
            duration = int(video.get("lengthSeconds",0))

        except:
            pass

        # fallback لو ytmusicapi فشل
        if not title:

            r = requests.get(
                f"https://noembed.com/embed?url=https://www.youtube.com/watch?v={video_id}"
            )

            data = r.json()

            title = data.get("title","Unknown")
            artist = clean_artist(data.get("author_name","Unknown"))

        bot.reply_to(
            message,
            f"🎵 {title}\n👤 {artist}\n\nجاري البحث عن الكلمات..."
        )

        lyrics_ttml = get_lyrics(title,artist,duration)

        if not lyrics_ttml:
            bot.send_message(message.chat.id,"❌ لم يتم العثور على كلمات")
            return

        lyrics = convert_ttml(lyrics_ttml)

        with open("lyrics.txt","w",encoding="utf-8") as f:
            f.write(lyrics)

        with open("lyrics.txt","rb") as f:
            bot.send_document(message.chat.id,f)

    except Exception as e:

        bot.send_message(message.chat.id,f"❌ خطأ:\n{str(e)}")


bot.infinity_polling()
