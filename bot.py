import telebot
import requests
from ytmusicapi import YTMusic
import xml.etree.ElementTree as ET
import tempfile

BOT_TOKEN = "8509336206:AAHnNtM7e9CUeJYeUEZLJT8ZJMlJIeF8hYk"

bot = telebot.TeleBot(BOT_TOKEN)
yt = YTMusic()


def get_lyrics(title, artist, duration=0):

    url = "https://lyrics-api.boidu.dev/getLyrics"

    params = {
        "s": title,
        "a": artist,
        "d": duration
    }

    r = requests.get(url, params=params)

    if r.status_code == 200:
        data = r.json()
        return data.get("ttml")

    return None


def format_time(t):

    if not t:
        return "00:00.000"

    t = float(t.replace("s", ""))
    minutes = int(t // 60)
    seconds = int(t % 60)
    millis = int((t - int(t)) * 1000)

    return f"{minutes:02}:{seconds:02}.{millis:03}"


def ttml_to_word_lrc(ttml):

    root = ET.fromstring(ttml)

    lines = []

    for p in root.iter():
        if p.tag.endswith("p"):

            line_start = format_time(p.attrib.get("begin"))
            text = f"[{line_start}]"

            for span in p:

                word = span.text.strip() if span.text else ""
                start = format_time(span.attrib.get("begin"))
                end = format_time(span.attrib.get("end"))

                text += f"<{start}>{word}<{end}> "

            lines.append(text.strip())

    return "\n".join(lines)


def extract_video_id(link):

    if "watch?v=" in link:
        return link.split("watch?v=")[1].split("&")[0]

    if "youtu.be/" in link:
        return link.split("youtu.be/")[1].split("?")[0]

    return None


def get_video_info(video_id):

    try:
        info = yt.get_song(video_id)

        details = info.get("videoDetails", {})

        title = details.get("title")
        artist = details.get("author")
        duration = int(details.get("lengthSeconds", 0))

        if title and artist:
            return title, artist, duration

    except:
        pass

    return None, None, 0


@bot.message_handler(commands=['yt'])
def handle(message):

    try:

        link = message.text.split(" ",1)[1]

        video_id = extract_video_id(link)

        if not video_id:
            bot.reply_to(message,"❌ رابط غير صالح")
            return

        title, artist, duration = get_video_info(video_id)

        if not title:
            bot.send_message(message.chat.id,"❌ لم استطع جلب معلومات الفيديو")
            return

        bot.reply_to(message,f"🎵 {title}\n👤 {artist}\n\nجاري تحميل الكلمات...")

        ttml = get_lyrics(title,artist,duration)

        if not ttml:
            bot.send_message(message.chat.id,"❌ لم يتم العثور على كلمات")
            return

        lyrics = ttml_to_word_lrc(ttml)

        file = tempfile.NamedTemporaryFile(delete=False,suffix=".txt",mode="w",encoding="utf-8")
        file.write(lyrics)
        file.close()

        bot.send_document(message.chat.id,open(file.name,"rb"))

    except Exception as e:
        bot.send_message(message.chat.id,f"❌ خطأ:\n{str(e)}")


bot.infinity_polling()
