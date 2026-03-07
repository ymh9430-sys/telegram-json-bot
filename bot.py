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


def get_song_info(video_id):

    watch = yt.get_watch_playlist(video_id)

    track = watch["tracks"][0]

    title = track.get("title")
    artist = track.get("artists", [{}])[0].get("name")

    duration = 0
    if "duration_seconds" in track:
        duration = track["duration_seconds"]

    album = None
    if "album" in track:
        album = track["album"]["name"]

    return title, artist, album, duration


def get_lyrics(title, artist, duration, album=None):

    url = "https://lyrics-api.boidu.dev/getLyrics"

    params = {
        "s": title,
        "a": artist,
        "d": duration
    }

    if album:
        params["al"] = album

    r = requests.get(url, params=params)

    if r.status_code == 200:
        data = r.json()
        return data.get("ttml")

    return None


@bot.message_handler(func=lambda m: True)
def handle(message):

    text = message.text.strip()

    try:

        if "youtube" in text:

            video_id = extract_video_id(text)

            if not video_id:
                bot.reply_to(message, "❌ لم أستطع استخراج الفيديو")
                return

            title, artist, album, duration = get_song_info(video_id)

            bot.reply_to(
                message,
                f"🎵 {title}\n👤 {artist}\n💿 {album if album else 'Unknown'}\n\nجاري البحث عن الكلمات..."
            )

            lyrics_ttml = get_lyrics(title, artist, duration, album)

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
