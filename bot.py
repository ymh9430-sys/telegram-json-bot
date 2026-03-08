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
        r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
        r"music\.youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})",
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

        words = []

        for span in spans:

            b = span.attrib.get("begin")
            e = span.attrib.get("end")
            w = span.text

            if not b or not e or not w:
                continue

            words.append({
                "begin": format_time(parse_time(b)),
                "end": format_time(parse_time(e)),
                "text": w.strip()
            })

        if not words:
            continue

        normal = []
        background = []

        for w in words:
            if "(" in w["text"] or ")" in w["text"]:
                background.append(w)
            else:
                normal.append(w)

        def build_line(words):

            if not words:
                return None

            line = f"[{words[0]['begin']}]"

            for i, w in enumerate(words):

                line += f"<{w['begin']}>{w['text']}<{w['end']}>"

                if i < len(words) - 1:

                    next_word = words[i+1]

                    # لو الكلمة مجزأة لا نضع مسافة
                    if w["end"] != next_word["begin"]:
                        line += " "

            return line

        main_line = build_line(normal)
        bg_line = build_line(background)

        if main_line:
            result.append(main_line)

        if bg_line:
            result.append(bg_line)

    return "\n".join(result)


def convert_manual(text):

    lines = text.splitlines()
    result = []

    for line in lines:

        if line.startswith("<"):

            parts = line.strip("<>").split("|")

            line_out = ""

            for i, p in enumerate(parts):

                try:
                    word, start, end = p.split(":")
                except:
                    continue

                start = format_time(float(start))
                end = format_time(float(end))

                line_out += f"<{start}>{word}<{end}>"

                if i < len(parts) - 1:
                    line_out += " "

            result.append(line_out)

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

        # تحويل النص اليدوي
        if text.startswith("[") and "<" in text:

            lyrics = convert_manual(text)

            with open("lyrics.lrc", "w", encoding="utf-8") as f:
                f.write(lyrics)

            with open("lyrics.lrc", "rb") as f:
                bot.send_document(message.chat.id, f)

            return

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
            f"🎵 {title}\n👤 {artist}\n💿 {album if album else 'Unknown'}\n\nجاري البحث عن الكلمات..."
        )

        ttml = get_lyrics(title, artist, duration, album)

        if not ttml:

            bot.send_message(message.chat.id, "❌ لم يتم العثور على كلمات")
            return

        lyrics = convert_ttml(ttml)

        with open("lyrics.lrc", "w", encoding="utf-8") as f:
            f.write(lyrics)

        with open("lyrics.lrc", "rb") as f:
            bot.send_document(message.chat.id, f)

    except Exception as e:

        bot.send_message(message.chat.id, f"❌ خطأ:\n{str(e)}")


bot.infinity_polling()
