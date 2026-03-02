import telebot
import os
import re

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

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message,
        "اختار طريقة الإرسال:\n"
        "1️⃣ اكتب text لإرسال الناتج كنص\n"
        "2️⃣ اكتب file لإرسال الناتج كملف"
    )

@bot.message_handler(func=lambda m: m.text in ["text", "file"])
def set_mode(message):
    user_mode[message.chat.id] = message.text
    bot.reply_to(message, "تمام 👌 ابعت النص دلوقتي")

@bot.message_handler(content_types=['text'])
def process_text(message):
    if message.text in ["text", "file"]:
        return

    mode = user_mode.get(message.chat.id, "text")
    content = message.text

    blocks = re.findall(r'\[(.*?)\].*?\n<(.*?)>', content, re.DOTALL)

    output_lines = []
    used_times = set()

    for line_time, words_block in blocks:
        base_seconds = to_seconds(line_time)
        
        # منع التكرار
        while round(base_seconds, 3) in used_times:
            base_seconds += 0.001

        used_times.add(round(base_seconds, 3))
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
        bot.reply_to(message, "مش عرفت أحلل النص ❌")
        return

    if mode == "file" or len(result) > 4000:
        with open("output.txt", "w", encoding="utf-8") as f:
            f.write(result)
        bot.send_document(message.chat.id, open("output.txt", "rb"))
        os.remove("output.txt")
    else:
        bot.reply_to(message, result)

bot.infinity_polling()
