import telebot
import os
import re
import asyncio
from playwright.async_api import async_playwright

TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)


async def get_lyrics(url):
    async with async_playwright() as p:

        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto(url)

        # نستنى تحميل الصفحة
        await page.wait_for_timeout(8000)

        # نحاول نقرأ كلمات Better Lyrics
        lyrics = await page.evaluate("""
        () => {
            let lines = document.querySelectorAll('[data-line-number]');
            let result = [];

            lines.forEach(line => {
                let lineTime = line.getAttribute("data-time");
                let words = line.querySelectorAll('[data-content]');
                let text = "";

                words.forEach(word=>{
                    let start = word.getAttribute("data-time");
                    let dur = word.getAttribute("data-duration");
                    let content = word.getAttribute("data-content");

                    let end = (parseFloat(start) + parseFloat(dur)).toFixed(3);

                    function format(t){
                        let m = Math.floor(t/60);
                        let s = (t%60).toFixed(3);
                        if(s < 10) s = "0"+s;
                        if(m < 10) m = "0"+m;
                        return m+":"+s;
                    }

                    text += "<"+format(start)+">"+content+"<"+format(end)+"> ";
                });

                function format(t){
                    t = parseFloat(t);
                    let m = Math.floor(t/60);
                    let s = (t%60).toFixed(3);
                    if(s < 10) s = "0"+s;
                    if(m < 10) m = "0"+m;
                    return m+":"+s;
                }

                result.push("["+format(lineTime)+"]"+text.trim());
            });

            return result.join("\\n");
        }
        """)

        await browser.close()
        return lyrics


@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "ابعت لينك YouTube Music 🎵")


@bot.message_handler(func=lambda m: "music.youtube.com" in m.text)
def handle_link(message):

    bot.reply_to(message, "⏳ جاري استخراج الكلمات...")

    try:
        lyrics = asyncio.run(get_lyrics(message.text))

        if lyrics:
            bot.send_message(message.chat.id, lyrics)
        else:
            bot.send_message(message.chat.id, "❌ مقدرتش أجيب الكلمات")

    except Exception as e:
        bot.send_message(message.chat.id, str(e))


bot.infinity_polling()
