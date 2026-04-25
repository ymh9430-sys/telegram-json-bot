import telebot
import requests
import re
import xml.etree.ElementTree as ET

import os
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(BOT_TOKEN)


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


# =========================
# convert_ttml (بدون تعديل)
# =========================

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


# =========================
# LyricsPlus request
# =========================

def request_lyricsplus(title, artist, album, duration):

    url = "https://lyricsplus.prjktla.my.id/v2/lyrics/get"

    params = {
        "title": title,
        "artist": artist,
        "album": album,
        "duration": duration
    }

    r = requests.get(url, params=params)

    if r.status_code != 200:
        return None

    data = r.json()

    if not data or not data.get("lyrics"):
        return None

    return data


# =========================
# LyricsPlus converter (مطابق لناتج TTML)
# =========================

def convert_lyricsplus_to_lrc(data):

    lines = data.get("lyrics", [])
    if not lines:
        return None

    result = []

    for line in lines:

        words = line.get("syllabus") or []
        if not words:
            continue

        main_line = ""
        main_time = None

        for w in words:

            text = w.get("text", "")
            if not text.strip():
                continue

            b = format_time(w.get("time", 0) / 1000)
            e = format_time((w.get("time", 0) + w.get("duration", 0)) / 1000)

            if not main_time:
                main_time = b

            main_line += f"<{b}>{text}<{e}>"

        if main_line and main_time:
            result.append(f"[{main_time}]{main_line}")

    result = avoid_duplicate_time(result)

    return "\n".join(result)


# =========================
# المصدر الأساسي (Boidu)
# =========================

def request_lyrics(title, artist, album, duration):

    url = "https://lyrics-api.boidu.dev/getLyrics"

    params = {
        "s": title,
        "a": artist,
        "al": album,
        "d": duration
    }

    r = requests.get(url, params=params)

    if r.status_code != 200:
        return None

    data = r.json()

    if not data:
        return None

    if data.get("ttml"):
        return ("ttml", data["ttml"])

    if data.get("lyrics"):
        return ("txt", data["lyrics"])

    return None


# =========================
# handler
# =========================

@bot.message_handler(func=lambda m: True)
def handle(message):

    try:

        text = message.text.strip()

        parts = text.split(" - ")

        if len(parts) != 2:
            bot.send_message(message.chat.id, "❌ اكتب بالشكل: song - artist")
            return

        title = parts[0].strip()
        artist = parts[1].strip()
        album = ""
        duration = 0

        bot.send_message(
            message.chat.id,
            f"🎵 {title}\n👤 {artist}\n\nجاري جلب الكلمات..."
        )

        source = "Boidu"

        result = request_lyrics(title, artist, album, duration)

        if result:
            typ, data = result

            if typ == "ttml":
                lyrics = convert_ttml(data)
            else:
                lyrics = data

        else:
            lp = request_lyricsplus(title, artist, album, duration)

            if not lp:
                bot.send_message(message.chat.id, "❌ لم يتم العثور على كلمات")
                return

            lyrics = convert_lyricsplus_to_lrc(lp)

            if not lyrics:
                bot.send_message(message.chat.id, "❌ فشل تحويل الكلمات")
                return

            source = "LyricsPlus"

        with open("lyrics.txt", "w", encoding="utf-8") as f:
            f.write(lyrics)

        bot.send_message(
            message.chat.id,
            f"📄 المصدر: {source}"
        )

        with open("lyrics.txt", "rb") as f:
            bot.send_document(message.chat.id, f)

    except Exception as e:

        bot.send_message(message.chat.id, f"❌ خطأ:\n{str(e)}")


bot.infinity_polling()
