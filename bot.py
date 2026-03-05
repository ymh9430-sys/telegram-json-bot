import telebot
import os
import re

TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

used_times = set()

def format_time(seconds):
    seconds = float(seconds)
    minutes = int(seconds // 60)
    remaining = seconds % 60
    return f"{minutes:02d}:{remaining:06.3f}"

def adjust_duplicate_time(seconds):

    while round(seconds,3) in used_times:
        seconds += 0.001

    used_times.add(round(seconds,3))
    return seconds

def to_seconds(t):
    if ":" in t:
        m, s = t.split(":")
        return float(m)*60 + float(s)
    return float(t)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message,"ابعت النص وأنا هحوله")

@bot.message_handler(content_types=['text'])
def convert(message):

    global used_times
    used_times = set()

    text = message.text
    lines = text.split("\n")
    result = []

    i = 0
    while i < len(lines):

        line = lines[i]

        if line.startswith("["):

            time_match = re.search(r'\[(.*?)\]', line)

            if time_match and i+1 < len(lines):

                base_seconds = to_seconds(time_match.group(1))

                base_seconds = adjust_duplicate_time(base_seconds)

                line_time = format_time(base_seconds)

                words_line = lines[i+1]

                if words_line.startswith("<"):

                    words_line = words_line.strip("<>")
                    words = words_line.split("|")

                    new_line = f"[{line_time}]"

                    for w in words:

                        parts = w.split(":")

                        if len(parts) == 3:

                            word = parts[0]
                            start = format_time(to_seconds(parts[1]))
                            end = format_time(to_seconds(parts[2]))

                            new_line += f"<{start}>{word}<{end}> "

                    result.append(new_line.strip())

                i += 1

        i += 1

    final = "\n".join(result)

    if len(final) > 4000:

        with open("lyrics.txt","w",encoding="utf-8") as f:
            f.write(final)

        bot.send_document(message.chat.id,open("lyrics.txt","rb"))
        os.remove("lyrics.txt")

    else:
        bot.reply_to(message,final)

bot.infinity_polling()
