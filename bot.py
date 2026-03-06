import asyncio
import aiohttp
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

        await asyncio.sleep(20)

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

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as r:
            return await r.text()


def extract_video_id(url):

    if "v=" in url:
        return url.split("v=")[1].split("&")[0]

    if "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]

    return None


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    video_id = extract_video_id(text)

    if not video_id:
        await update.message.reply_text("ابعت لينك YouTube أو YouTube Music صحيح")
        return

    try:
        lyrics = await get_lyrics(video_id)

        if not lyrics:
            await update.message.reply_text("ملقتش lyrics للأغنية")
            return

        await update.message.reply_text(lyrics[:4000])

    except Exception as e:
        await update.message.reply_text("حصل خطأ أثناء جلب الكلمات")


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("Bot Started")

app.run_polling()
