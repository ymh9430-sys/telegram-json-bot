import telebot
import os
import re
from playwright.sync_api import sync_playwright

TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

def get_lyrics_from_ytmusic(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(url)

        # نستنى الصفحة تحمل
        page.wait_for_timeout(8000)

        # نحاول نجيب النص من الصفحة
        content = page.content()

        browser.close()

        return content

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message,"ابعت:\n/yt رابط الأغنية من YouTube Music")

@bot.message_handler(commands=['yt'])
def yt(message):
    try:
        url = message.text.split(" ",1)[1]

        bot.reply_to(message,"جاري جلب الكلمات...")

        html = get_lyrics_from_ytmusic(url)

        # استخراج نص بسيط كبداية
        text = re.sub("<.*?>","",html)

        result = text[:3500]

        bot.send_message(message.chat.id,result)

    except:
        bot.reply_to(message,"حصل خطأ")

bot.infinity_polling()
