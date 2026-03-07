import telebot
import requests
from ytmusicapi import YTMusic
import re
import xml.etree.ElementTree as ET

BOT_TOKEN = "8509336206:AAHnNtM7e9CUeJYeUEZLJT8ZJMlJIeF8hYk"

bot = telebot.TeleBot(BOT_TOKEN)
yt = YTMusic()

# استخراج video id من كل روابط يوتيوب
def extract_video_id(url):

    patterns = [
        r"v=([a-zA-Z0-9_-]{11})",
        r"youtu\.be/([a-zA-Z0-9_-]{11})",
        r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
        r"youtube\.com/embed/([a-zA-Z0-9_-]{11})",
        r"music\.youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})"
    ]

    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)

    return None


def parse_time(t):

    if ":" in t:
        m, s = t.split(":")
        return int(m) * 60 + float(s)

    return float(t)


def format_time(sec):

    m = int(sec // 60)
    s = sec % 60

    return f"{m:02d}:{s:06.3f}"


# تحويل TTML إلى تنسيق الكلمات
def convert_ttml(ttml):

    root = ET.fromstring(ttml)
    ns = {'tt': 'http://www.w3.org/ns/ttml'}

    result = []

    for p in root.findall(".//tt:p", ns):

        line_begin = p.attrib.get("begin")

        if not line_begin:
            continue

        line_time = format_time(parse_time(line_begin))
        line = f"[{line_time}]"

        words = []

        for span in p.findall("tt:span", ns):

            begin = span.attrib.get("begin")
            end = span.attrib.get("end")
            word = span.text

            if not begin or not end or not word:
                continue

            b = format_time(parse_time(begin))
            e = format_time(parse_time(end))

            words.append(f"<{b}>{word}<{e}>")

        line += " " + " ".join(words)
        result.append(line)

    return "\n".join(result)


# تحويل صيغة agent إلى الصيغة القديمة
def convert_agent(text):

    lines = text.split("\n")

    result = []
    base_time = None

    for line in lines:

        if line.startswith("["):
            base_time = re.findall(r"\[(.*?)\]", line)[0]

        if line.startswith("<"):

            words = line.strip("<>").split("|")

            line_result = f"[{base_time}] "
            parts = []

            for w in words:

                word, start, end = w.split(":")

                b = format_time(float(start))
                e = format_time(float(end))

                parts.append(f"<{b}>{word}<{e}>")

            line_result += " ".join(parts)
            result.append(line_result)

    return "\n".join(result)


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


@bot.message_handler(func=lambda m: True)
def handle(message):

    text = message.text.strip()

    try:

        # لو أرسل كلمات agent
        if "{agent:" in text:

            lyrics = convert_agent(text)

            with open("lyrics.txt", "w", encoding="utf-8") as f:
                f.write(lyrics)

            with open("lyrics.txt", "rb") as f:
                bot.send_document(message.chat.id, f)

            return


        # لو أرسل رابط يوتيوب
        if "youtube" in text or "youtu.be" in text:

            video_id = extract_video_id(text)

            if not video_id:
                bot.reply_to(message, "❌ لم أستطع استخراج video id")
                return

            info = yt.get_song(video_id)

            if not info:
                bot.reply_to(message, "❌ لم استطع جلب معلومات الفيديو")
                return

            video = info.get("videoDetails", {})

            title = video.get("title")
            artist = video.get("author")
            duration = int(video.get("lengthSeconds", 0))

            bot.reply_to(
                message,
                f"🎵 {title}\n👤 {artist}\n\nجاري البحث عن الكلمات..."
            )

            lyrics_ttml = get_lyrics(title, artist, duration)

            if not lyrics_ttml:
                bot.send_message(message.chat.id, "❌ لم يتم العثور على كلمات")
                return

            lyrics = convert_ttml(lyrics_ttml)

            with open("lyrics.txt", "w", encoding="utf-8") as f:
                f.write(lyrics)

            with open("lyrics.txt", "rb") as f:
                bot.send_document(message.chat.id, f)

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ:\n{str(e)}")


bot.infinity_polling()
