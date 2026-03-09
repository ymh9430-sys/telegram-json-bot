import telebot
import requests
import re
import xml.etree.ElementTree as ET

BOT_TOKEN = "8509336206:AAHnNtM7e9CUeJYeUEZLJT8ZJMlJIeF8hYk"

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
# convert_ttml (بدون أي تعديل)
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
# استخراج track id من رابط Apple Music
# =========================

def extract_track_id(url):

    m = re.search(r"i=(\d+)", url)

    if m:
        return m.group(1)

    return None


# =========================
# جلب بيانات الأغنية من Apple
# =========================

def get_song_data(track_id):

    url = f"https://itunes.apple.com/lookup?id={track_id}"

    r = requests.get(url)

    data = r.json()

    if data["resultCount"] == 0:
        return None

    track = data["results"][0]

    title = track["trackName"]
    artist = track["artistName"]
    album = track["collectionName"]

    duration = round(track["trackTimeMillis"] / 1000)

    return title, artist, album, duration


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
# telegram handler
# =========================

@bot.message_handler(func=lambda m: True)
def handle(message):

    try:

        url = message.text.strip()

        track_id = extract_track_id(url)

        if not track_id:

            bot.reply_to(message, "❌ أرسل رابط Apple Music صحيح")
            return

        title, artist, album, duration = get_song_data(track_id)

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
