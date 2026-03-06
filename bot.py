import telebot
import requests
from ytmusicapi import YTMusic
import re
import xml.etree.ElementTree as ET

BOT_TOKEN = "8509336206:AAHnNtM7e9CUeJYeUEZLJT8ZJMlJIeF8hYk"

bot = telebot.TeleBot(BOT_TOKEN)
yt = YTMusic()


def extract_video_id(url):

    patterns = [
        r"v=([a-zA-Z0-9_-]{11})",
        r"youtu\.be/([a-zA-Z0-9_-]{11})",
        r"music\.youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})",
        r"youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})",
        r"shorts/([a-zA-Z0-9_-]{11})"
    ]

    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)

    return None


def parse_time(t):

    if ":" in t:
        parts = t.split(":")
        if len(parts) == 2:
            m, s = parts
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

        while round(sec,3) in used_times:
            sec += 0.001

        used_times.add(round(sec,3))

        line_time = format_time(sec)

        line = f"[{line_time}]"

        spans = p.findall("tt:span", ns)

        prev_word = ""
        prev_end = ""

        for span in spans:

            word = span.text

            if not word:
                continue

            b = span.attrib.get("begin")
            e = span.attrib.get("end")

            if not b or not e:
                continue

            b = format_time(parse_time(b))
            e = format_time(parse_time(e))

            segment = f"<{b}>{word}<{e}>"

            # دمج الكلمات المجزأة فقط
            if prev_word and prev_word.isalpha() and word.isalpha() and len(word) <= 3:
                line += segment
            else:
                line += " " + segment

            prev_word = word
            prev_end = e

        result.append(line.strip())

    return "\n".join(result)


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

            if data and data.get("ttml"):
                return data["ttml"]

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
            artist = video.get("author")
            duration = int(video.get("lengthSeconds",0))

        except:
            pass

        # fallback
        if not title:

            try:

                r = requests.get(
                    f"https://noembed.com/embed?url=https://www.youtube.com/watch?v={video_id}"
                )

                data = r.json()

                title = data.get("title")
                artist = data.get("author_name")

            except:
                pass

        if not title:
            bot.send_message(message.chat.id,"❌ لم استطع جلب معلومات الفيديو")
            return

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
