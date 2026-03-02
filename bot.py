import telebot
import json
import re
import os
from bs4 import BeautifulSoup

TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "ابعتلي ملف أو نص فيه JSON وأنا هستخرجه لك 👌")

def extract_json(text):
    try:
        json_objects = re.findall(r'\{.*?\}', text, re.DOTALL)
        results = []
        for obj in json_objects:
            try:
                parsed = json.loads(obj)
                results.append(parsed)
            except:
                continue
        return results
    except:
        return []

@bot.message_handler(content_types=['text'])
def handle_text(message):
    results = extract_json(message.text)
    if results:
        with open("output.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        bot.send_document(message.chat.id, open("output.json", "rb"))
        os.remove("output.json")
    else:
        bot.reply_to(message, "مفيش JSON واضح في النص ❌")

@bot.message_handler(content_types=['document'])
def handle_file(message):
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    file_name = message.document.file_name
    with open(file_name, 'wb') as f:
        f.write(downloaded_file)

    try:
        with open(file_name, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except:
        bot.reply_to(message, "مش عرفت أقرأ الملف ❌")
        return

    results = extract_json(content)

    if results:
        with open("output.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        bot.send_document(message.chat.id, open("output.json", "rb"))
        os.remove("output.json")
    else:
        bot.reply_to(message, "مفيش JSON واضح في الملف ❌")

    os.remove(file_name)

bot.infinity_polling()
