import re
import requests
import xml.etree.ElementTree as ET
from yt_dlp import YoutubeDL


def parse_time(t):
    parts = t.split(":")
    if len(parts) == 2:
        m, s = parts
        return float(m) * 60 + float(s)
    if len(parts) == 3:
        h, m, s = parts
        return float(h) * 3600 + float(m) * 60 + float(s)
    return float(t)


def format_time(sec):
    m = int(sec // 60)
    s = sec % 60
    return f"{m:02}:{s:06.3f}"


def get_video_id(url):

    ydl_opts = {"quiet": True}

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    return info["id"]


def get_lyrics(video_id):

    url = f"https://music.youtube.com/youtubei/v1/get_lyrics"

    payload = {
        "context": {
            "client": {
                "clientName": "WEB_REMIX",
                "clientVersion": "1.20240201.01.00"
            }
        },
        "videoId": video_id
    }

    r = requests.post(url, json=payload)

    data = r.json()

    try:
        return data["lyrics"]["lyrics"]["timedLyrics"]["lines"]
    except:
        return None


def convert_lines(lines):

    result = []

    last_time = None

    for line in lines:

        start = float(line["startTimeMs"]) / 1000

        if last_time and abs(start - last_time) < 0.001:
            start += 0.001

        last_time = start

        line_time = format_time(start)

        words = line["words"].split()

        text = f"[{line_time}] "

        t = start

        for w in words:

            dur = 0.25

            start_w = format_time(t)
            end_w = format_time(t + dur)

            if w.startswith("(") and w.endswith(")"):
                result.append(f"[{start_w}]<{start_w}>{w}<{end_w}>")
            else:
                text += f"<{start_w}>{w}<{end_w}> "

            t += dur

        result.append(text.strip())

    return "\n".join(result)


def main():

    url = input("YouTube URL: ")

    try:

        video_id = get_video_id(url)

        lines = get_lyrics(video_id)

        if not lines:
            print("❌ لم استطع جلب الكلمات")
            return

        lrc = convert_lines(lines)

        with open("lyrics.lrc", "w", encoding="utf8") as f:
            f.write(lrc)

        print("✅ تم حفظ الملف: lyrics.lrc")

    except Exception as e:
        print("❌ خطأ:")
        print(e)


if __name__ == "__main__":
    main()
