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


def convert_ttml(ttml):

    root = ET.fromstring(ttml)
    ns = {'tt': 'http://www.w3.org/ns/ttml'}

    result = []
    used_times = []

    for p in root.findall(".//tt:p", ns):

        line_begin = p.attrib.get("begin")
        if not line_begin:
            continue

        line_time_sec = parse_time(line_begin)

        while any(abs(line_time_sec - t) < 0.001 for t in used_times):
            line_time_sec += 0.001

        used_times.append(line_time_sec)

        line_time = format_time(line_time_sec)
        line = f"[{line_time}]"

        spans = p.findall("tt:span", ns)

        parts = []

        for span in spans:

            begin = span.attrib.get("begin")
            end = span.attrib.get("end")
            word = span.text

            if not begin or not end or not word:
                continue

            b = format_time(parse_time(begin))
            e = format_time(parse_time(end))

            parts.append((b, e, word))

        merged = []

        for i, (b, e, word) in enumerate(parts):

            segment = f"<{b}>{word}<{e}>"

            if merged:
                prev_b, prev_e, prev_word = merged[-1]

                if abs(parse_time(b) - parse_time(prev_e)) < 0.15:
                    merged[-1] = (
                        prev_b,
                        e,
                        prev_word + segment
                    )
                    continue

            merged.append((b, e, segment))

        words = [m[2] for m in merged]

        line += " ".join(words)

        result.append(line)

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


@bot.message_handler(commands=['yt'])
def handle(message):

    try:

        link = message.text.split(" ", 1)[1]

        video_id = extract_video_id(link)

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

        if not title:
            bot.reply_to(message, "❌ لم استطع جلب معلومات الفيديو")
            return

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
