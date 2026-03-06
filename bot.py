import telebot
import yt_dlp
import requests
import re
import html

TOKEN = "8509336206:AAHnNtM7e9CUeJYeUEZLJT8ZJMlJIeF8hYk"

bot = telebot.TeleBot(TOKEN)


def time_to_seconds(t):
    parts = t.split(":")
    if len(parts) == 2:
        m, s = parts
        return float(m) * 60 + float(s)
    if len(parts) == 3:
        h, m, s = parts
        return float(h) * 3600 + float(m) * 60 + float(s)
    return float(t)


def seconds_to_time(sec):
    m = int(sec // 60)
    s = sec % 60
    return f"{m:02d}:{s:06.3f}"


def fix_duplicate_times(lines):
    seen = {}
    new_lines = []

    for line in lines:
        start = re.search(r"\[(.*?)\]", line)
        if not start:
            new_lines.append(line)
            continue

        t = start.group(1)
        sec = time_to_seconds(t)

        if sec in seen:
            sec += 0.001

        seen[sec] = True
        new_time = seconds_to_time(sec)

        line = line.replace(f"[{t}]", f"[{new_time}]", 1)
        new_lines.append(line)

    return new_lines


def parse_lyrics(xml):

    spans = re.findall(
        r'<span begin="(.*?)" end="(.*?)">(.*?)</span>', xml)

    lines = []
    current_line = ""
    last_end = None

    for begin, end, word in spans:

        word = html.unescape(word)
        word = word.strip()

        begin = seconds_to_time(time_to_seconds(begin))
        end = seconds_to_time(time_to_seconds(end))

        # كلمات بين اقواس
        if word.startswith("(") or word.startswith("["):
            if current_line:
                lines.append(current_line)
                current_line = ""

            lines.append(f"[{begin}]<{begin}>{word}<{end}>")
            last_end = end
            continue

        part = f"<{begin}>{word}<{end}>"

        if last_end == begin:
            current_line += part
        else:
            if current_line:
                lines.append(current_line)
            current_line = f"[{begin}]" + part

        last_end = end

    if current_line:
        lines.append(current_line)

    return lines


def get_lyrics(video_id):

    url = f"https://music.apple.com/api/v1/catalog/us/songs/{video_id}"

    r = requests.get(url)

    if r.status_code != 200:
        return None

    data = r.text

    return data


@bot.message_handler(commands=['start'])
def start(message):

    bot.send_message(
        message.chat.id,
        "ابعت لينك يوتيوب وانا هطلعلك الكلمات بالتوقيت 🎵"
    )


@bot.message_handler(func=lambda m: True)
def handle(message):

    url = message.text.strip()

    try:

        ydl_opts = {
            'quiet': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        video_id = info.get("id")

        if not video_id:
            bot.send_message(message.chat.id, "❌ لم استطع جلب معلومات الفيديو")
            return

        lyrics_xml = get_lyrics(video_id)

        if not lyrics_xml:
            bot.send_message(message.chat.id, "❌ لم يتم العثور على كلمات")
            return

        lines = parse_lyrics(lyrics_xml)

        lines = fix_duplicate_times(lines)

        text = "\n".join(lines)

        file = open("lyrics.txt", "w", encoding="utf-8")
        file.write(text)
        file.close()

        bot.send_document(message.chat.id, open("lyrics.txt", "rb"))

    except Exception as e:

        bot.send_message(message.chat.id, f"❌ خطأ:\n{e}")


bot.infinity_polling()
