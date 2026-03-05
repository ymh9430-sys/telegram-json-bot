import telebot
import os
import re
import requests
from ytmusicapi import YTMusic

TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

yt = YTMusic()

# =========================
# time helpers
# =========================

def format_time(seconds):
    seconds = float(seconds)
    minutes = int(seconds // 60)
    remaining = seconds % 60
    return f"{minutes:02d}:{remaining:06.3f}"

def to_seconds(time_str):
    if ":" in time_str:
        m, s = time_str.split(":")
        return float(m)*60 + float(s)
    return float(time_str)

def fix_duplicate(t, used):
    while round(t,3) in used:
        t += 0.001
    used.add(round(t,3))
    return t

# =========================
# search song
# =========================

def search_song(query):

    results = yt.search(query, filter="songs")

    if not results:
        return None

    return results[0]["videoId"]

# =========================
# get synced lyrics
# =========================

def get_synced_lyrics(artist, title):

    url = f"https://lrclib.net/api/get?artist_name={artist}&track_name={title}"

    r = requests.get(url)

    if r.status_code != 200:
        return None

    data = r.json()

    if "syncedLyrics" not in data:
        return None

    return data["syncedLyrics"]

# =========================
# convert LRC
# =========================

def convert_lrc(text):

    lines = text.split("\n")
    used = set()
    output = []

    for line in lines:

        m = re.match(r"\[(.*?)\](.*)", line)

        if not m:
            continue

        t = m.group(1)
        words = m.group(2).strip().split()

        base = fix_duplicate(to_seconds(t), used)

        line = f"[{format_time(base)}]"

        current = base

        for w in words:

            start = format_time(current)
            end = format_time(current + 0.3)

            line += f"<{start}>{w}<{end}> "

            current += 0.3

        output.append(line.strip())

    return "\n".join(output)

# =========================
# start
# =========================

@bot.message_handler(commands=['start'])
def start(m):

    bot.reply_to(m,
"""
الاوامر:

/song artist - title
/yt link
/json text
""")

# =========================
# song command
# =========================

@bot.message_handler(commands=['song'])
def song_cmd(m):

    try:
        query = m.text.replace("/song","").strip()

        artist,title = query.split("-",1)

        bot.reply_to(m,"🔎 جاري البحث...")

        lyrics = get_synced_lyrics(artist.strip(),title.strip())

        if not lyrics:
            bot.reply_to(m,"❌ لم يتم العثور على كلمات")
            return

        result = convert_lrc(lyrics)

        if len(result) > 4000:

            with open("lyrics.txt","w",encoding="utf8") as f:
                f.write(result)

            bot.send_document(m.chat.id,open("lyrics.txt","rb"))

            os.remove("lyrics.txt")

        else:
            bot.reply_to(m,result)

    except:
        bot.reply_to(m,"الصيغة:\n/song artist - title")

# =========================
# json convert
# =========================

@bot.message_handler(commands=['json'])
def json_convert(m):

    text = m.text.replace("/json","").strip()

    blocks = re.findall(r'\[(.*?)\].*?\n<(.*?)>', text, re.DOTALL)

    used = set()
    output = []

    for line_time, words_block in blocks:

        base = fix_duplicate(to_seconds(line_time), used)

        new_line = f"[{format_time(base)}]"

        words = words_block.split("|")

        for w in words:

            parts = w.split(":")

            if len(parts) == 3:

                word = parts[0]
                start = format_time(parts[1])
                end = format_time(parts[2])

                new_line += f"<{start}>{word}<{end}> "

        output.append(new_line.strip())

    bot.reply_to(m,"\n".join(output))

bot.infinity_polling()
