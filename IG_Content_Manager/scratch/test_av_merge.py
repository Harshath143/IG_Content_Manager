import asyncio
import os
import sys
import re
import subprocess
import urllib.request
import ssl
import imageio_ffmpeg
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

urls = [
    "https://www.instagram.com/p/Da5xwapDGIC/",
    "https://www.instagram.com/reel/Dak9akADi4e/",
    "https://www.instagram.com/reel/DbFZWADTgwf/",
    "https://www.instagram.com/reel/DbJ-wX6AWQ4/"
]

ctx_ssl = ssl.create_default_context()
ctx_ssl.check_hostname = False
ctx_ssl.verify_mode = ssl.CERT_NONE

async def test_av_merge():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )

        for url in urls:
            shortcode = url.split("?")[0].rstrip("/").split("/")[-1]
            page = await context.new_page()
            print(f"\n==========================================")
            print(f"Capturing Audio & Video streams for {shortcode}...")

            video_urls = set()
            audio_urls = set()

            async def handle_request(req):
                r_url = req.url
                if ("fbcdn.net" in r_url or "cdninstagram.com" in r_url):
                    clean_cdn = re.sub(r'&bytestart=\d+&byteend=\d+', '', r_url)
                    clean_cdn = re.sub(r'\?bytestart=\d+&byteend=\d+&', '?', clean_cdn)
                    if "mime=audio" in r_url or "/m4a" in r_url or "audio" in r_url:
                        audio_urls.add(clean_cdn)
                    elif "/o1/v/" in r_url or "/t50." in r_url or "mime=video" in r_url:
                        video_urls.add(clean_cdn)

            page.on("request", handle_request)

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(5000)

                print(f"Captured {len(video_urls)} Video URLs, {len(audio_urls)} Audio URLs.")

                v_temp = f"downloads/temp_v_{shortcode}.mp4"
                a_temp = f"downloads/temp_a_{shortcode}.m4a"
                final_mp4 = f"downloads/final_av_{shortcode}.mp4"

                # 1. Download Video
                got_video = False
                for cdn_v in list(video_urls):
                    try:
                        req = urllib.request.Request(cdn_v, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req, context=ctx_ssl) as resp:
                            data = resp.read()
                            if len(data) > 100000 and (b'ftyp' in data[:64] or b'moov' in data[:64]):
                                with open(v_temp, "wb") as f:
                                    f.write(data)
                                got_video = True
                                print(f"  Saved Video temp: {len(data)} bytes")
                                break
                    except Exception:
                        pass

                # 2. Download Audio
                got_audio = False
                for cdn_a in list(audio_urls):
                    try:
                        req = urllib.request.Request(cdn_a, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req, context=ctx_ssl) as resp:
                            data = resp.read()
                            if len(data) > 20000:
                                with open(a_temp, "wb") as f:
                                    f.write(data)
                                got_audio = True
                                print(f"  Saved Audio temp: {len(data)} bytes")
                                break
                    except Exception:
                        pass

                # 3. Merge Video & Audio using FFmpeg
                if got_video and got_audio:
                    cmd = [FFMPEG_EXE, "-y", "-i", v_temp, "-i", a_temp, "-c", "copy", final_mp4]
                    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    if res.returncode == 0 and os.path.exists(final_mp4):
                        print(f"🎉 SUCCESS! Merged AV file: {final_mp4} ({os.path.getsize(final_mp4)} bytes)")
                    else:
                        print(f"FFmpeg error: {res.stderr.decode('utf-8', errors='ignore')[:200]}")
                elif got_video:
                    os.replace(v_temp, final_mp4)
                    print(f"⚠️ Saved Video only (No separate audio stream found): {final_mp4}")

                # Clean temps
                for temp_f in [v_temp, a_temp]:
                    if os.path.exists(temp_f):
                        try: os.remove(temp_f)
                        except Exception: pass

            except Exception as e:
                print(f"Error: {e}")
            finally:
                await page.close()

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_av_merge())
