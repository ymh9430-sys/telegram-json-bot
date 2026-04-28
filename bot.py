import telebot
import requests
import re
import xml.etree.ElementTree as ET
import os
from flask import Flask
import threading

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

def parse_time(t):
    if not t:
        return 0
    if ":" in str(t):
        m, s = str(t).split(":")
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
# ✅ NEW: فصل الكورال (bg)
# =========================
def split_bg_lines(lines):
    result = []

    for line in lines:
        if "(" not in line or ")" not in line:
            result.append(line)
            continue

        main_time_match = re.match(r"\[(.*?)\]", line)
        if not main_time_match:
            result.append(line)
            continue

        main_time = main_time_match.group(1)

        parts = re.split(r"(\(.*?\))", line)

        main_part = ""
        bg_part = ""

        for part in parts:
            if part.startswith("(") and part.endswith(")"):
                bg_part += part
            else:
                main_part += part

        main_part = re.sub(r"^\[.*?\]", "", main_part).strip()
        bg_part = bg_part.strip()

        bg_time_match = re.search(r"<(.*?)>", bg_part)
        bg_time = bg_time_match.group(1) if bg_time_match else main_time

        if main_part:
            result.append(f"[{main_time}]{main_part}")

        if bg_part:
            result.append(f"[{bg_time}]{bg_part}")

    return result

# =========================
# convert_ttml
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
# convert_json_lyrics
# =========================
# =========================
# convert_json_lyrics
# =========================
def convert_json_lyrics(data):
    lyrics_list = data.get("lyrics", [])
    result = []

    for line in lyrics_list:
        syllabus = line.get("syllabus", [])

        if not syllabus:
            continue

        main_line = ""
        bg_line = ""

        main_start = None
        bg_start = None

        inside_bg = False

        for i, syl in enumerate(syllabus):
            text = syl.get("text", "")

            start_ms = syl.get("time", 0)
            dur_ms = syl.get("duration", 0)

            start = format_time(start_ms / 1000)
            end = format_time((start_ms + dur_ms) / 1000)

            word = text.strip()

            next_syl = syllabus[i + 1] if i + 1 < len(syllabus) else None

            if "(" in text:
                inside_bg = True

            # =========================
            # MAIN
            # =========================
            if not inside_bg:
                if main_start is None:
                    main_start = start

                main_line += f"<{start}>{word}<{end}>"

                # ✅ مسافة بتوقيت (زي المثال بالظبط)
                if next_syl:
                    next_start = format_time(next_syl.get("time", 0) / 1000)
                    main_line += f"<{end}> <{next_start}>"

            # =========================
            # BG
            # =========================
            else:
                if bg_start is None:
                    bg_start = start

                bg_line += f"<{start}>{word}<{end}>"

                if next_syl:
                    next_start = format_time(next_syl.get("time", 0) / 1000)
                    bg_line += f"<{end}> <{next_start}>"

            if ")" in text:
                inside_bg = False

        if main_line.strip():
            result.append(f"[{main_start}]{main_line}")

        if bg_line.strip():
            result.append(f"[{bg_start}]{bg_line}")

    result = avoid_duplicate_time(result)

    return "\n".join(result)

# =========================
# باقي الكود
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

def extract_track_id(url):
    m = re.search(r"[?&]i=(\d+)", url)
    if m:
        return m.group(1)

    m = re.search(r"/(\d{6,})", url)
    if m:
        return m.group(1)

    return None

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

    if album and "single" in album.lower():
        album = title

    duration = round(track["trackTimeMillis"] / 1000)

    return title, artist, album, duration

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
        return ("ttml", data["ttml"], "Apple Music")

    if data.get("lyrics"):
        return ("txt", data["lyrics"], "Apple Music")

    return None

def request_lyrics_lyricsplus(title, artist, album, duration):
    base_urls = [
        "https://lyricsplus.binimum.org",
        "https://lyricsplus.atomix.one",
        "https://lyricsplus.prjktla.my.id",
        "https://lyricsplus-seven.vercel.app"
    ]

    for base in base_urls:
        try:
            url = f"{base}/v2/lyrics/get"
            params = {
                "title": title,
                "artist": artist,
                "duration": duration
            }

            r = requests.get(url, params=params, timeout=10)

            if r.status_code != 200:
                continue

            data = r.json()

            if not data:
                continue

            lyrics = data.get("lyrics")

            if lyrics and len(lyrics) > 0:
                return ("json", data, "LyricsPlus")

        except Exception:
            continue

    return None

def parse_manual(text):
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

    m = re.match(r"(.+?)\s*-\s*(.+)", text)

    if m:
        title = m.group(1).strip()
        artist = m.group(2).strip()

        return search_song(title, artist)

    return None

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

        result_apple = request_lyrics(title, artist, album, duration)
        result_plus = request_lyrics_lyricsplus(title, artist, album, duration)

        if not result_apple and not result_plus:
            bot.send_message(message.chat.id, "❌ لم يتم العثور على كلمات")
            return

        if result_apple:
            typ, data, source = result_apple

            if typ == "ttml":
                lyrics = convert_ttml(data)
            else:
                lyrics = data

            file_content = f"[Source: {source}]\n\n{lyrics}"

            with open("lyrics_apple.txt", "w", encoding="utf-8") as f:
                f.write(file_content)

            with open("lyrics_apple.txt", "rb") as f:
                bot.send_document(
                    message.chat.id,
                    f,
                    caption=f"📄 المصدر: {source}"
                )

        if result_plus:
            typ, data, source = result_plus

            lyrics = convert_json_lyrics(data)

            file_content = f"[Source: {source}]\n\n{lyrics}"

            with open("lyrics_plus.txt", "w", encoding="utf-8") as f:
                f.write(file_content)

            with open("lyrics_plus.txt", "rb") as f:
                bot.send_document(
                    message.chat.id,
                    f,
                    caption=f"📄 المصدر: {source}"
                )

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ:\n{str(e)}")

bot.infinity_polling()

# =========================
# Flask
# =========================

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running"

def run_web():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 3000)))

threading.Thread(target=run_web).start()
