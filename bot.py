import asyncio
import requests
from playwright.async_api import async_playwright
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

TOKEN = "8509336206:AAHnNtM7e9CUeJYeUEZLJT8ZJMlJIeF8hYk"

jwt_token = None


async def get_jwt():
    global jwt_token

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        page = await context.new_page()

        async def handle_request(request):
            global jwt_token
            if "lyrics.api.dacubeking.com" in request.url:
                headers = request.headers
                if "authorization" in headers:
                    jwt_token = headers["authorization"]

        page.on("request", handle_request)

        await page.goto("https://music.youtube.com")

        await asyncio.sleep(10)

        await browser.close()

    return jwt_token


async def get_lyrics(video_id):

    global jwt_token

    if not jwt_token:
        jwt_token = await get_jwt()

    url = "https://lyrics.api.dacubeking.com/lyrics"

    headers = {
        "Authorization": jwt_token
    }

    params = {
        "videoId": video_id
    }

    r = requests.get(url, headers=headers, params=params)

    return r.text


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    if "youtube.com" not in text:
        await update.message.reply_text("ابعت لينك YouTube Music")
        return

    video_id = text.split("v=")[1]

    lyrics = await get_lyrics(video_id)

    await update.message.reply_text(lyrics[:4000])


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(MessageHandler(filters.TEXT, handle))

app.run_polling()
