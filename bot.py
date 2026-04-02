import telebot
import requests
import re
import xml.etree.ElementTree as ET

import os
BOT_TOKEN = os.getenv("8509336206:AAHnNtM7e9CUeJYeUEZLJT8ZJMlJIeF8hYk")

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
# تنظيف البيانات
# =========================
def clean_title(title):

    title = re.sub(
        r"\s*\((?i:(feat\.?|ft\.?|with|from)[^)]*)\)",
        "",
        title
    )

    return title.strip()


def clean_album(album):

    if not album:
        return album

    album = re.sub(r"\s*\([^)]*\)", "", album)

    return album.strip()

# =========================
# Apple ID
# =========================

def extract_track_id(url):

    m = re.search(r"[?&]i=(\d+)", url)
    if m:
        return m.group(1)

    m = re.search(r"/(\d{6,})", url)
    if m:
        return m.group(1)

    return None


# =========================
# Apple lookup
# =========================

def get_song_data(track_id):

    url = f"https://itunes.apple.com/lookup?id={track_id}"

    r = requests.get(url)
    data = r.json()

    if data["resultCount"] == 0:
        return None

    track = None

    for item in data["results"]:
        if item.get("kind") == "song":
            track = item
            break

    if not track:
        return None

    title = clean_title(track["trackName"])
    artist = track["artistName"]
    album = clean_album(track["collectionName"])

    if album and "single" in album.lower():
        album = title

    duration = round(track["trackTimeMillis"] / 1000)

    return title, artist, album, duration


# =========================
# Apple search
# =========================

def search_song(title, artist):

    url = "https://itunes.apple.com/search"

    params = {
        "term": f"{title} {artist}",
        "entity": "song",
        "limit": 1
    }

    r = requests.get(url, params=params)
    data = r.json()

    if data["resultCount"] == 0:
        return None

    track = data["results"][0]

    title = clean_title(track["trackName"])
    artist = track["artistName"]
    album = clean_album(track["collectionName"])

    # لو الألبوم سينجل نخليه اسم الأغنية
    if album and "single" in album.lower():
        album = title

    duration = round(track["trackTimeMillis"] / 1000)

    return title, artist, album, duration

# =========================
# استخراج عنوان من صفحات
# =========================

def extract_title_artist_from_page(url):

    r = requests.get(url)

    m = re.search(r"<title>(.*?)</title>", r.text)

    if not m:
        return None

    title = m.group(1)

    title = title.replace(" - YouTube Music", "")
    title = title.replace(" - YouTube", "")
    title = title.replace(" | Spotify", "")

    parts = title.split(" - ")

    if len(parts) >= 2:
        artist = parts[0].strip()
        song = parts[1].strip()
    else:
        song = title.strip()
        artist = ""

    return song, artist


# =========================
# طلب الكلمات
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
# قراءة إدخال يدوي (المعدل فقط)
# =========================

def parse_manual(text):

    # دعم الشكل الجديد
    # 🎵
    # 👤
    # 💿
    # ⏱

    if "🎵" in text and "👤" in text:

        title = None
        artist = None
        album = None
        duration = None

        lines = text.splitlines()

        for line in lines:

            line = line.strip()

            if line.startswith("🎵"):
                title = line.replace("🎵", "").strip()

            elif line.startswith("👤"):
                artist = line.replace("👤", "").strip()

            elif line.startswith("💿"):
                album = line.replace("💿", "").strip()

            elif line.startswith("⏱"):
                d = line.replace("⏱", "").replace("s", "").strip()
                try:
                    duration = int(d)
                except:
                    duration = None

        if title and artist and album and duration:
            return title, artist, album, duration


    # الصيغة القديمة الكاملة
    # song | artist | album | duration
    if "|" in text:

        parts = [x.strip() for x in text.split("|")]

        if len(parts) == 4:

            title = parts[0]
            artist = parts[1]
            album = parts[2]

            try:
                duration = int(parts[3])
            except:
                return None

            return title, artist, album, duration


    # الصيغة القديمة
    # song - artist
    m = re.match(r"(.+?)\s*-\s*(.+)", text)

    if m:

        title = m.group(1).strip()
        artist = m.group(2).strip()

        return search_song(title, artist)

    return None


# =========================
# handler
# =========================

@bot.message_handler(func=lambda m: True)
def handle(message):

    try:

        text = message.text.strip()

        if text.startswith("http"):

            track_id = extract_track_id(text)

            if track_id:
                song = get_song_data(track_id)
            else:
                info = extract_title_artist_from_page(text)

                if not info:
                    bot.send_message(message.chat.id, "❌ لم أستطع قراءة الرابط")
                    return

                title, artist = info
                song = search_song(title, artist)

        else:

            song = parse_manual(text)

        if not song:
            bot.send_message(message.chat.id, "❌ لم أستطع استخراج بيانات الأغنية")
            return

        title, artist, album, duration = song

        bot.send_message(
            message.chat.id,
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


from flask import Flask
import threading

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running"

def run_web():
    app.run(host="0.0.0.0", port=3000)

threading.Thread(target=run_web).start()
