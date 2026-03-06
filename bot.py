import telebot
import requests
from ytmusicapi import YTMusic
import xml.etree.ElementTree as ET
import tempfile

BOT_TOKEN = "8509336206:AAHnNtM7e9CUeJYeUEZLJT8ZJMlJIeF8hYk"

bot = telebot.TeleBot(BOT_TOKEN)
yt = YTMusic()

# ---------- time helpers ----------

def parse_time(t):
    if ":" in t:
        parts = t.split(":")
        if len(parts) == 2:
            m = int(parts[0])
            s = float(parts[1])
            return m * 60 + s
        elif len(parts) == 3:
            h = int(parts[0])
            m = int(parts[1])
            s = float(parts[2])
            return h * 3600 + m * 60 + s
    return float(t)

def to_lrc_time(sec):
    m = int(sec // 60)
    s = sec % 60
    return f"{m:02}:{s:06.3f}"

# ---------- lyrics parser ----------

def ttml_to_word_lrc(ttml):

    root = ET.fromstring(ttml)
    ns = {"tt": "http://www.w3.org/ns/ttml"}

    lines = []

    for p in root.findall(".//tt:p", ns):

        line_begin = parse_time(p.attrib.get("begin", "0"))
        line = f"[{to_lrc_time(line_begin)}]"

        for span in p.findall("tt:span", ns):

            word = (span.text or "").strip()

            begin = to_lrc_time(parse_time(span.attrib["begin"]))
            end = to_lrc_time(parse_time(span.attrib["end"]))

            line += f"<{begin}>{word}<{end}> "

        lines.append(line.strip())

    return "\n".join(lines)

# ---------- fetch lyrics ----------

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

# ---------- telegram command ----------

@bot.message_handler(commands=['yt'])
def handle(message):

    try:

        link = message.text.split(" ",1)[1]

        if "v=" in link:
            video_id = link.split("v=")[1].split("&")[0]
        else:
            video_id = link.split("/")[-1]

        info = yt.get_song(video_id)

        video = info.get("videoDetails")

        if not video:
            bot.reply_to(message,"❌ لم استطع جلب معلومات الفيديو")
            return

        title = video["title"]
        artist = video["author"]
        duration = int(video["lengthSeconds"])

        bot.reply_to(message,f"🎵 {title}\n👤 {artist}\n\nجاري جلب الكلمات...")

        ttml = get_lyrics(title,artist,duration)

        if not ttml:
            bot.send_message(message.chat.id,"❌ لم يتم العثور على كلمات")
            return

        lyrics = ttml_to_word_lrc(ttml)

        with tempfile.NamedTemporaryFile(delete=False,suffix=".txt") as f:
            f.write(lyrics.encode("utf-8"))
            path = f.name

        with open(path,"rb") as file:
            bot.send_document(message.chat.id,file)

    except Exception as e:
        bot.send_message(message.chat.id,f"❌ خطأ:\n{e}")

bot.infinity_polling()
