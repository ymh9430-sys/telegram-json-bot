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

        page.goto(url, timeout=60000)

        page.wait_for_timeout(8000)

        html = page.content()

        browser.close()

        return html


@bot.message_handler(commands=['start'])
def start(message):

    bot.reply_to(message,
"""
اهلا 👋

الاوامر:

/yt رابط الاغنية من YouTube Music
""")



@bot.message_handler(commands=['yt'])
def yt(message):

    try:

        url = message.text.split(" ",1)[1]

        bot.reply_to(message,"جاري فتح الصفحة...")

        html = get_lyrics_from_ytmusic(url)

        text = re.sub("<.*?>","",html)

        result = text[:3500]

        bot.send_message(message.chat.id,result)

    except Exception as e:

        bot.send_message(message.chat.id,f"Error:\n{e}")


bot.infinity_polling()
