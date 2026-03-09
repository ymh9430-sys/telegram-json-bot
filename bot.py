import telebot
import requests
import re
import xml.etree.ElementTree as ET
import json

BOT_TOKEN = "8509336206:AAHnNtM7e9CUeJYeUEZLJT8ZJMlJIeF8hYk"

bot = telebot.TeleBot(BOT_TOKEN)


# ---------------------------
# تنظيف العنوان
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
# منع تكرار التوقيت
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
# convert_ttml (بدون تعديل)
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

            else:

                text = span.text
                if not text:
                    continue

                b = format_time(parse_time(span.attrib.get("begin")))
                e = format_time(parse_time(span.attrib.get("end")))

                if not main_time:
                    main_time = b

                main_line += f"<{b}>{text}<{e}>"

        if main_line:
            result.append(f"[{main_time}]{main_line}")

        if bg_line:
            result.append(f"[{bg_time}]{bg_line}")

    result = avoid_duplicate_time(result)

    return "\n".join(result)


# ---------------------------
# استخراج بيانات الأغنية
# ---------------------------

def extract_song_data(url):

    r = requests.get(url)
    html = r.text

    data = {}

    match = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)

    if match:

        try:

            j = json.loads(match.group(1))

            if isinstance(j, list):
                j = j[0]

            data["title"] = j.get("name")

            artist = j.get("byArtist")

            if isinstance(artist, dict):
                data["artist"] = artist.get("name")

            album = j.get("inAlbum")

            if isinstance(album, dict):
                data["album"] = album.get("name")

            duration = j.get("duration")

            if duration:

                duration = duration.replace("PT", "")

                m = re.match(r"(\d+)M(\d+)S", duration)

                if m:
                    minutes = int(m.group(1))
                    seconds = int(m.group(2))
                    data["duration"] = minutes * 60 + seconds

        except:
            pass

    return data


# ---------------------------
# طلب الكلمات
# ---------------------------

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


# ---------------------------
# telegram handler
# ---------------------------

@bot.message_handler(func=lambda m: True)
def handle(message):

    text = message.text.strip()

    try:

        if "http" not in text:

            bot.reply_to(message, "❌ أرسل رابط الأغنية")
            return

        info = extract_song_data(text)

        title = clean_title(info.get("title"))
        artist = info.get("artist")
        album = info.get("album")
        duration = info.get("duration")

        bot.reply_to(
            message,
            f"🎵 {title}\n👤 {artist}\n💿 {album}\n⏱ {duration}s\n\nجاري جلب الكلمات..."
        )

        result = request_lyrics(title, artist, album, duration)

        if not result:

            bot.send_message(message.chat.id, "❌ لم يتم العثور على كلمات")
            return

        typ, data = result

        if typ == "ttml":

            lyrics = convert_ttml(data)

        else:

            lyrics = data

        with open("lyrics.txt", "w", encoding="utf-8") as f:
            f.write(lyrics)

        with open("lyrics.txt", "rb") as f:
            bot.send_document(message.chat.id, f)

    except Exception as e:

        bot.send_message(message.chat.id, f"❌ خطأ:\n{str(e)}")


bot.infinity_polling()
