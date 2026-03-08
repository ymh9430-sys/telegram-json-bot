import telebot
import requests
from ytmusicapi import YTMusic
import re
import xml.etree.ElementTree as ET

BOT_TOKEN = "PUT_YOUR_BOT_TOKEN"

bot = telebot.TeleBot(BOT_TOKEN)
yt = YTMusic()


def extract_video_id(url):

    patterns = [
        r"v=([a-zA-Z0-9_-]{11})",
        r"youtu\.be/([a-zA-Z0-9_-]{11})",
        r"youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})"
    ]

    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)

    return None


def clean_title(title):

    title = re.sub(r"\(.*?\)", "", title)
    title = re.sub(r"\[.*?\]", "", title)
    title = re.sub(r"-.*", "", title)

    return title.strip()


def parse_time(t):

    if not t:
        return 0

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

        spans = p.findall(".//tt:span", ns)

        if not spans:
            continue

        line = ""
        first_time = None

        for span in spans:

            b = span.attrib.get("begin")
            e = span.attrib.get("end")
            w = span.text

            if not w:
                continue

            b = format_time(parse_time(b))
            e = format_time(parse_time(e))

            if not first_time:
                first_time = b

            line += f"<{b}>{w}<{e}>"

            tail = span.tail

            if tail and tail.strip() == "":
                line += " "

        if line and first_time:
            result.append(f"[{first_time}]" + line)

    return "\n".join(result)


def get_song_info(video_id):

    watch = yt.get_watch_playlist(video_id)

    track = watch["tracks"][0]

    title = track.get("title")
    artist = track.get("artists", [{}])[0].get("name")

    duration = track.get("duration_seconds", 0)

    album = None
    if "album" in track:
        album = track["album"]["name"]

    return title, artist, album, duration


def request_lyrics(params):

    url = "https://lyrics-api.boidu.dev/getLyrics"

    r = requests.get(url, params=params)

    print("REQUEST:", r.url)

    if r.status_code == 200:

        data = r.json()

        if data and data.get("ttml"):
            return data["ttml"]

    return None


def get_lyrics(title, artist, duration, album):

    attempts = [

        {"s": title, "a": artist, "d": duration, "al": album},
        {"s": title, "a": artist, "d": duration},
        {"s": title, "a": artist},
        {"s": title}

    ]

    for params in attempts:

        params = {k: v for k, v in params.items() if v}

        lyrics = request_lyrics(params)

        if lyrics:
            return lyrics

    return None


@bot.message_handler(func=lambda m: True)
def handle(message):

    text = message.text.strip()

    try:

        if "youtu" not in text:

            bot.reply_to(message, "❌ أرسل رابط يوتيوب")
            return

        video_id = extract_video_id(text)

        if not video_id:

            bot.reply_to(message, "❌ لم أستطع استخراج ID")
            return

        title, artist, album, duration = get_song_info(video_id)

        title = clean_title(title)

        bot.reply_to(
            message,
            f"🎵 {title}\n👤 {artist}\n\nجاري جلب الكلمات..."
        )

        ttml = get_lyrics(title, artist, duration, album)

        if not ttml:

            bot.send_message(message.chat.id, "❌ لم يتم العثور على كلمات")
            return

        lyrics = convert_ttml(ttml)

        with open("lyrics.txt", "w", encoding="utf-8") as f:
            f.write(lyrics)

        with open("lyrics.txt", "rb") as f:
            bot.send_document(message.chat.id, f)

    except Exception as e:

        bot.send_message(message.chat.id, f"❌ خطأ:\n{str(e)}")


bot.infinity_polling()
