import telebot
import requests
import xml.etree.ElementTree as ET
import tempfile
import re
from ytmusicapi import YTMusic

BOT_TOKEN = "8509336206:AAHnNtM7e9CUeJYeUEZLJT8ZJMlJIeF8hYk"

bot = telebot.TeleBot(BOT_TOKEN)
yt = YTMusic()

# -------- extract video id --------

def extract_video_id(url):

    patterns = [
        r"v=([a-zA-Z0-9_-]{11})",
        r"youtu\.be/([a-zA-Z0-9_-]{11})",
        r"music\.youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})"
    ]

    for p in patterns:
        m = re.search(p,url)
        if m:
            return m.group(1)

    return None


# -------- time helpers --------

def parse_time(t):

    if ":" in t:

        parts = t.split(":")

        if len(parts) == 2:
            m = int(parts[0])
            s = float(parts[1])
            return m*60 + s

        if len(parts) == 3:
            h = int(parts[0])
            m = int(parts[1])
            s = float(parts[2])
            return h*3600 + m*60 + s

    return float(t)


def to_lrc(sec):

    m = int(sec//60)
    s = sec%60

    return f"{m:02}:{s:06.3f}"


# -------- TTML parser --------

def ttml_to_word_lrc(ttml):

    root = ET.fromstring(ttml)

    ns = {"tt":"http://www.w3.org/ns/ttml"}

    lines = []

    for p in root.findall(".//tt:p",ns):

        begin = parse_time(p.attrib.get("begin","0"))

        line = f"[{to_lrc(begin)}]"

        for span in p.findall("tt:span",ns):

            word = (span.text or "").strip()

            b = to_lrc(parse_time(span.attrib["begin"]))
            e = to_lrc(parse_time(span.attrib["end"]))

            line += f"<{b}>{word}<{e}> "

        lines.append(line.strip())

    return "\n".join(lines)


# -------- lyrics api --------

def get_lyrics(title,artist,duration):

    url = "https://lyrics-api.boidu.dev/getLyrics"

    params = {
        "s": title,
        "a": artist,
        "d": duration
    }

    r = requests.get(url,params=params)

    if r.status_code == 200:
        return r.json().get("ttml")

    return None


# -------- telegram command --------

@bot.message_handler(commands=["yt"])
def handle(message):

    try:

        url = message.text.split(" ",1)[1]

        video_id = extract_video_id(url)

        if not video_id:
            bot.reply_to(message,"❌ رابط غير صحيح")
            return

        info = yt.get_song(video_id)

        video = info.get("videoDetails")

        if not video:
            bot.reply_to(message,"❌ لم استطع جلب معلومات الفيديو")
            return

        title = video["title"]
        artist = video["author"]
        duration = int(video["lengthSeconds"])

        bot.reply_to(message,f"🎵 {title}\n👤 {artist}\n\nجاري جلب الكلمات...")

        ttml = get_lyrics(title,artist,duration)

        if not ttml:
            bot.send_message(message.chat.id,"❌ لم يتم العثور على كلمات")
            return

        lyrics = ttml_to_word_lrc(ttml)

        with tempfile.NamedTemporaryFile(delete=False,suffix=".txt") as f:
            f.write(lyrics.encode("utf-8"))
            path = f.name

        with open(path,"rb") as file:
            bot.send_document(message.chat.id,file)

    except Exception as e:

        bot.send_message(message.chat.id,f"❌ خطأ:\n{e}")


bot.infinity_polling()
