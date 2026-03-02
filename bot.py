import telebot
import os
from bs4 import BeautifulSoup

TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "ابعتلي ملف أو نص وأنا هستخرج كل كلمة مع توقيتها في TXT 👌")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    process_content(message, message.text)

@bot.message_handler(content_types=['document'])
def handle_file(message):
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    file_name = message.document.file_name

    with open(file_name, 'wb') as f:
        f.write(downloaded_file)

    with open(file_name, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    process_content(message, content)

    os.remove(file_name)

def process_content(message, content):
    soup = BeautifulSoup(content, "lxml")

    words = soup.find_all(class_="blyrics--word")

    if not words:
        bot.reply_to(message, "مش لاقي كلمات واضحة في الملف ❌")
        return

    output_lines = []

    for word in words:
        text = word.get("data-content", "").strip()
        start_time = word.get("data-time")
        duration = word.get("data-duration")

        if text and start_time and duration:
            try:
                start = float(start_time)
                end = start + float(duration)
                output_lines.append(f"{text} | {start:.3f} --> {end:.3f}")
            except:
                continue

    if not output_lines:
        bot.reply_to(message, "ملقتش توقيت صالح ❌")
        return

    output_text = "\n".join(output_lines)

    with open("output.txt", "w", encoding="utf-8") as f:
        f.write(output_text)

    bot.send_document(message.chat.id, open("output.txt", "rb"))

    os.remove("output.txt")

bot.infinity_polling()
