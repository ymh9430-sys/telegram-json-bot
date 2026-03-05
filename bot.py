import telebot
import os
import asyncio
from playwright.async_api import async_playwright

TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

async def get_lyrics_from_ytmusic(url):

    async with async_playwright() as p:

        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto(url)

        await page.wait_for_timeout(8000)

        try:
            lyrics = await page.inner_text("ytmusic-description-shelf-renderer")
        except:
            lyrics = "❌ لم أستطع استخراج الكلمات"

        await browser.close()

        return lyrics


@bot.message_handler(commands=['start'])
def start(message):

    bot.reply_to(
        message,
        "ابعت لينك الأغنية من YouTube Music بهذا الشكل:\n\n"
        "/yt link"
    )


@bot.message_handler(commands=['yt'])
def get_lyrics(message):

    try:

        url = message.text.split(" ",1)[1]

        bot.reply_to(message,"⏳ جاري استخراج الكلمات...")

        lyrics = asyncio.run(get_lyrics_from_ytmusic(url))

        if len(lyrics) > 3500:

            with open("lyrics.txt","w",encoding="utf-8") as f:
                f.write(lyrics)

            bot.send_document(message.chat.id,open("lyrics.txt","rb"))

        else:

            bot.reply_to(message,lyrics)

    except:

        bot.reply_to(message,"❌ ارسل الأمر بهذا الشكل:\n/yt link")


bot.infinity_polling()
