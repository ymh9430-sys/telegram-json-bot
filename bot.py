import telebot
import json
import os
from bs4 import BeautifulSoup

# بياخد التوكن من Railway Variables
TOKEN = os.getenv("TOKEN")

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "ابعتلي ملف HTML أو نص فيه بيانات وأنا هستخرجه لك 👌")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    content = message.text
    process_content(message, content)

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

    lines_data = []
    lines = soup.find_all(class_="blyrics--line")

    for line in lines:
        time = line.get("data-time")
        duration = line.get("data-duration")
        line_number = line.get("data-line-number")

        words = line.find_all(class_="blyrics--word")
        text = "".join(word.get("data-content", "") for word in words)

        if text.strip():
            lines_data.append({
                "line_number": line_number,
                "time": time,
                "duration": duration,
                "text": text.strip()
            })

    if lines_data:
        with open("output.json", "w", encoding="utf-8") as f:
            json.dump(lines_data, f, ensure_ascii=False, indent=2)

        bot.send_document(message.chat.id, open("output.json", "rb"))
        os.remove("output.json")
    else:
        bot.reply_to(message, "مش لاقي بيانات lyrics واضحة في الملف ❌")

bot.infinity_polling()
