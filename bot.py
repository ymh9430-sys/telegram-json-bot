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
        r"youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})",
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
    used_times = set()

    for p in root.findall(".//tt:p", ns):

        line_begin = p.attrib.get("begin")
        line_end = p.attrib.get("end")

        if not line_begin or not line_end:
            continue

        line_time = parse_time(line_begin)

        while line_time in used_times:
            line_time += 0.001

        used_times.add(line_time)

        line_time_str = format_time(line_time)

        spans = p.findall("tt:span", ns)

        line = f"[{line_time_str}]"

        prev_end = None

        for span in spans:

            word = span.text
            begin = span.attrib.get("begin")
            end = span.attrib.get("end")

            if not word or not begin or not end:
                continue

            b = format_time(parse_time(begin))
            e = format_time(parse_time(end))

            segment = f"<{b}>{word}<{e}>"

            if prev_end and b == prev_end:
                line += segment
            else:
                line += " " + segment

            prev_end = e

        result.append(line.strip())

        # معالجة الكلمات بين الأقواس
        full_text = "".join([s.text or "" for s in spans])

        if "(" in full_text and ")" in full_text:

            begin = format_time(parse_time(line_begin))
            end = format_time(parse_time(line_end))

            bracket_line = f"[{begin}]<{begin}>{full_text}<{end}>"
            result.append(bracket_line)

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
