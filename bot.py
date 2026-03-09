import telebot
import requests
from ytmusicapi import YTMusic
import re
import xml.etree.ElementTree as ET

BOT_TOKEN = "8509336206:AAHnNtM7e9CUeJYeUEZLJT8ZJMlJIeF8hYk"

bot = telebot.TeleBot(BOT_TOKEN)
yt = YTMusic()


# ---------------------------
# extract youtube video id
# ---------------------------

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


# ---------------------------
# clean title
# ---------------------------

def clean_title(title):

    title = re.sub(r"\(.*?\)", "", title)
    title = re.sub(r"\[.*?\]", "", title)
    title = re.sub(r"-.*", "", title)

    return title.strip()


# ---------------------------
# time helpers
# ---------------------------

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


# ---------------------------
# avoid duplicate timestamps
# ---------------------------

def avoid_duplicate_time(lines):

    used = set()
    fixed = []

    for line in lines:

        m = re.match(r"\[(.*?)\]", line)

        if not m:
            fixed.append(line)
            continue

        t = m.group(1)

        while t in used:
            sec = parse_time(t) + 0.001
            t = format_time(sec)

        used.add(t)

        line = re.sub(r"\[.*?\]", f"[{t}]", line, 1)

        fixed.append(line)

    return fixed


# ---------------------------
# convert ttml (لم يتم تعديله)
# ---------------------------

def convert_ttml(ttml):

    root = ET.fromstring(ttml)

    ns = {
        'tt': 'http://www.w3.org/ns/ttml',
        'ttm': 'http://www.w3.org/ns/ttml#metadata'
    }

    result = []

    for p in root.findall(".//tt:p", ns):

        main_line = ""
        bg_line = ""

        main_time = None
        bg_time = None

        for span in p:

            tag = span.tag.split("}")[-1]
            if tag != "span":
                continue

            role = span.attrib.get('{http://www.w3.org/ns/ttml#metadata}role')

            if role == "x-bg":

                for sub in span.findall("tt:span", ns):

                    text = sub.text
                    if not text:
                        continue

                    b = format_time(parse_time(sub.attrib.get("begin")))
                    e = format_time(parse_time(sub.attrib.get("end")))

                    if not bg_time:
                        bg_time = b

                    bg_line += f"<{b}>{text}<{e}>"

                    tail = sub.tail
                    if tail and tail.strip() == "":
                        bg_line += " "

            else:

                text = span.text
                if not text:
                    continue

                b = format_time(parse_time(span.attrib.get("begin")))
                e = format_time(parse_time(span.attrib.get("end")))

                if not main_time:
                    main_time = b

                main_line += f"<{b}>{text}<{e}>"

                tail = span.tail
                if tail and tail.strip() == "":
                    main_line += " "

        if main_line:
            result.append(f"[{main_time}]{main_line}")

        if bg_line:
            result.append(f"[{bg_time}]{bg_line}")

    result = avoid_duplicate_time(result)

    return "\n".join(result)


# ---------------------------
# get song info youtube
# ---------------------------

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


# ---------------------------
# spotify parser
# ---------------------------

def get_spotify_info(url):

    r = requests.get(url)
    html = r.text

    title = re.search(r'<meta property="og:title" content="(.*?)"', html)
    artist = re.search(r'<meta name="music:musician_description" content="(.*?)"', html)

    if title:
        title = title.group(1)

    if artist:
        artist = artist.group(1)

    return title, artist, None, None


# ---------------------------
# apple music parser
# ---------------------------

def get_apple_info(url):

    r = requests.get(url)
    html = r.text

    title = re.search(r'<meta property="og:title" content="(.*?)"', html)
    artist = re.search(r'<meta name="apple:title" content="(.*?)"', html)

    if title:
        title = title.group(1)

    if artist:
        artist = artist.group(1)

    return title, artist, None, None


# ---------------------------
# lyrics api
# ---------------------------

def request_lyrics(params):

    url = "https://lyrics-api.boidu.dev/getLyrics"

    r = requests.get(url, params=params)

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


# ---------------------------
# telegram handler
# ---------------------------

@bot.message_handler(func=lambda m: True)
def handle(message):

    text = message.text.strip()

    try:

        # youtube
        if "youtu" in text:

            video_id = extract_video_id(text)

            if not video_id:
                bot.reply_to(message, "❌ لم أستطع استخراج ID")
                return

            title, artist, album, duration = get_song_info(video_id)

        # spotify
        elif "spotify.com" in text:

            title, artist, album, duration = get_spotify_info(text)

        # apple music
        elif "music.apple.com" in text:

            title, artist, album, duration = get_apple_info(text)

        else:

            bot.reply_to(message, "❌ أرسل رابط من YouTube أو Spotify أو Apple Music")
            return


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
