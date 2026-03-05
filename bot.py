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
        m, s = time_str.split(":")
        return float(m) * 60 + float(s)
    return float(time_str)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message,
        "اختار طريقة الإرسال:\n"
        "text = إرسال كنص\n"
        "file = إرسال كملف"
    )

@bot.message_handler(func=lambda m: m.text in ["text","file"])
def set_mode(message):
    user_mode[message.chat.id] = message.text
    bot.reply_to(message,"تمام 👌 ابعت النص")

@bot.message_handler(content_types=['text'])
def process_text(message):

    if message.text in ["text","file"]:
        return

    mode = user_mode.get(message.chat.id,"text")
    text = message.text

    blocks = re.findall(r'\[(.*?)\](.*)', text)

    used_times = set()
    result_lines = []

    for line_time, words in blocks:

        base = to_seconds(line_time)

        while round(base,3) in used_times:
            base += 0.001

        used_times.add(round(base,3))
        line_time = format_time(base)

        word_parts = re.findall(r'<(.*?)>(.*?)<(.*?)>', words)

        line = f"[{line_time}]"

        for start, word, end in word_parts:

            start = format_time(to_seconds(start))
            end = format_time(to_seconds(end))

            line += f"<{start}>{word}<{end}> "

        result_lines.append(line.strip())

    result = "\n".join(result_lines)

    if not result:
        bot.reply_to(message,"❌ حصل خطأ في تحليل النص")
        return

    if mode == "file" or len(result) > 4000:

        with open("lyrics.txt","w",encoding="utf-8") as f:
            f.write(result)

        bot.send_document(message.chat.id,open("lyrics.txt","rb"))
        os.remove("lyrics.txt")

    else:
        bot.reply_to(message,result)

bot.infinity_polling()
