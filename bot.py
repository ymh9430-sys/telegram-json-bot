import telebot
import os
import re

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    print("TOKEN NOT FOUND")
    exit()

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

# start command
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message,
        "👋 اهلا بيك\n\n"
        "الاوامر:\n"
        "/json ← ابعت بعده النص لتحويله\n"
        "/yt ← ابعت لينك اغنية YT Music\n"
    )

# JSON convert
@bot.message_handler(commands=['json'])
def json_command(message):

    content = message.text.replace("/json", "").strip()

    if not content:
        bot.reply_to(message,"ابعت النص بعد /json")
        return

    blocks = re.findall(r'\[(.*?)\].*?\n<(.*?)>', content, re.DOTALL)

    output_lines = []
    used_times = set()

    for line_time, words_block in blocks:

        base_seconds = to_seconds(line_time)

        while round(base_seconds,3) in used_times:
            base_seconds += 0.001

        used_times.add(round(base_seconds,3))

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

    if not result:
        bot.reply_to(message,"❌ مش عرفت احلل النص")
        return

    if len(result) > 3500:

        with open("output.txt","w",encoding="utf-8") as f:
            f.write(result)

        bot.send_document(message.chat.id,open("output.txt","rb"))
        os.remove("output.txt")

    else:
        bot.reply_to(message,result)

# YT command
@bot.message_handler(commands=['yt'])
def yt_command(message):

    text = message.text.split(" ",1)

    if len(text) < 2:
        bot.reply_to(message,"ابعت لينك بعد /yt")
        return

    url = text[1]

    bot.reply_to(message,
        "📥 استلمت اللينك\n"
        f"{url}\n\n"
        "الميزة دي لسه بنجهزها..."
    )

print("BOT STARTED")

bot.infinity_polling()
