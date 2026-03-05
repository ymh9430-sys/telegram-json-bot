import telebot
import os
import re
import requests

TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

user_mode = {}

def format_time(seconds):
    seconds = float(seconds)
    minutes = int(seconds // 60)
    remaining = seconds % 60
    return f"{minutes:02d}:{remaining:06.3f}"

def to_seconds(time_str):
    if ":" in time_str:
        parts = time_str.split(":")
        return float(parts[0]) * 60 + float(parts[1])
    return float(time_str)

def fix_duplicate_times(seconds, used):
    while round(seconds,3) in used:
        seconds += 0.001
    used.add(round(seconds,3))
    return seconds

# =========================
# جلب كلمات الأغنية
# =========================

def get_lyrics(artist, song):
    url = f"https://lrclib.net/api/get?artist_name={artist}&track_name={song}"
    r = requests.get(url)

    if r.status_code != 200:
        return None

    data = r.json()

    if "syncedLyrics" not in data:
        return None

    return data["syncedLyrics"]

# =========================
# تحويل LRC لصيغة الكلمة
# =========================

def convert_lrc(text):

    lines = text.split("\n")
    used_times = set()
    output = []

    for line in lines:

        m = re.match(r"\[(.*?)\](.*)", line)

        if not m:
            continue

        time = m.group(1)
        words = m.group(2).strip().split()

        base = fix_duplicate_times(to_seconds(time), used_times)
        line_time = format_time(base)

        new_line = f"[{line_time}]"

        current = base

        for w in words:
            start = format_time(current)
            end = format_time(current + 0.3)
            new_line += f"<{start}>{w}<{end}> "
            current += 0.3

        output.append(new_line.strip())

    return "\n".join(output)

# =========================
# start
# =========================

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message,
    """اهلا 👋

ارسل:

artist - song

مثال:
Billie Eilish - Bad Guy

او ارسل النص القديم للتحويل
""")

# =========================
# معالجة الرسائل
# =========================

@bot.message_handler(content_types=['text'])
def handle(message):

    text = message.text.strip()

    # لو صيغة اغنية
    if " - " in text:

        artist, song = text.split(" - ",1)

        bot.reply_to(message,"🔎 جاري البحث عن الكلمات...")

        lyrics = get_lyrics(artist, song)

        if not lyrics:
            bot.reply_to(message,"❌ لم يتم العثور على كلمات")
            return

        result = convert_lrc(lyrics)

        if len(result) > 4000:
            with open("lyrics.txt","w",encoding="utf-8") as f:
                f.write(result)

            bot.send_document(message.chat.id,open("lyrics.txt","rb"))
            os.remove("lyrics.txt")

        else:
            bot.reply_to(message,result)

        return

    # =========================
    # النظام القديم
    # =========================

    blocks = re.findall(r'\[(.*?)\].*?\n<(.*?)>', text, re.DOTALL)

    output_lines = []
    used_times = set()

    for line_time, words_block in blocks:

        base_seconds = fix_duplicate_times(to_seconds(line_time), used_times)

        line_time_formatted = format_time(base_seconds)

        words = words_block.split("|")

        new_line = f"[{line_time_formatted}]"

        for w in words:
            parts = w.split(":")

            if len(parts) == 3:
                word = parts[0]
                start = format_time(parts[1])
                end = format_time(parts[2])
                new_line += f"<{start}>{word}<{end}> "

        output_lines.append(new_line.strip())

    result = "\n".join(output_lines)

    if result:
        bot.reply_to(message,result)
    else:
        bot.reply_to(message,"❌ لم يتم فهم النص")

bot.infinity_polling()
