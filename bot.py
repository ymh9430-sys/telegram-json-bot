import telebot
import os
import re
from playwright.sync_api import sync_playwright

TOKEN = os.getenv("TOKEN")

bot = telebot.TeleBot(TOKEN)


def format_time(seconds):
    seconds = float(seconds)
    minutes = int(seconds // 60)
    remaining = seconds % 60
    return f"{minutes:02d}:{remaining:06.3f}"


def parse_lyrics(html):

    words = re.findall(r'data-time="([\d.]+)".*?data-content="(.*?)"', html)

    result = []
    line = ""

    for i in range(len(words)):
        start = float(words[i][0])
        word = words[i][1]

        if i < len(words) - 1:
            end = float(words[i + 1][0])
        else:
            end = start + 0.3

        start_f = format_time(start)
        end_f = format_time(end)

        if line == "":
            line = f"[{start_f}]"

        line += f"<{start_f}>{word}<{end_f}> "

        if word.endswith(".") or word.endswith("!") or word.endswith("?"):
            result.append(line.strip())
            line = ""

    if line:
        result.append(line.strip())

    return "\n".join(result)


def get_lyrics(url):

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)

        page = browser.new_page()

        page.goto(url)

        page.wait_for_timeout(8000)

        html = page.content()

        browser.close()

    return parse_lyrics(html)


@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message,
        "ابعت الأمر كده:\n\n"
        "/yt لينك الأغنية من YouTube Music"
    )


@bot.message_handler(commands=['yt'])
def yt(message):

    try:

        url = message.text.split(" ",1)[1]

        bot.reply_to(message,"جاري استخراج الكلمات ⏳")

        lyrics = get_lyrics(url)

        if not lyrics:
            bot.reply_to(message,"ملقتش كلمات ❌")
            return

        if len(lyrics) > 4000:

            with open("lyrics.txt","w",encoding="utf-8") as f:
                f.write(lyrics)

            bot.send_document(message.chat.id,open("lyrics.txt","rb"))

            os.remove("lyrics.txt")

        else:
            bot.reply_to(message,lyrics)

    except:
        bot.reply_to(message,"استخدم الشكل ده:\n/yt LINK")


bot.infinity_polling()
