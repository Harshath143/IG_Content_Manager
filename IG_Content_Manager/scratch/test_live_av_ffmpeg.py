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
    "https://www.instagram.com/reel/DbJ-wX6AWQ4/",
    "https://www.instagram.com/reel/DbFZWADTgwf/",
    "https://www.instagram.com/reel/Dak9akADi4e/",
    "https://www.instagram.com/p/Da5xwapDGIC/"
]

ctx_ssl = ssl.create_default_context()
ctx_ssl.check_hostname = False
ctx_ssl.verify_mode = ssl.CERT_NONE

def inspect_media_streams(file_path):
    """Uses ffmpeg to detect if a file contains video and/or audio tracks."""
    cmd = [FFMPEG_EXE, "-i", file_path]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    err = res.stderr.decode('utf-8', errors='ignore')
    has_video = "Video:" in err
    has_audio = "Audio:" in err
    return has_video, has_audio, err

async def test_live_capture():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )

        for url in urls:
            shortcode = url.split("?")[0].rstrip("/").split("/")[-1]
            page = await context.new_page()
            print(f"\n==========================================")
            print(f"Live Playwright AV Stream Interception for {shortcode}...")

            captured_cdn_urls = set()

            async def handle_request(req):
                r_url = req.url
                if ("fbcdn.net" in r_url or "cdninstagram.com" in r_url) and ("/o1/v/" in r_url or "/t50." in r_url or "mime=" in r_url):
                    clean_cdn = re.sub(r'&bytestart=\d+&byteend=\d+', '', r_url)
                    clean_cdn = re.sub(r'\?bytestart=\d+&byteend=\d+&', '?', clean_cdn)
                    captured_cdn_urls.add(clean_cdn)

            page.on("request", handle_request)

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(6000)

                print(f"Captured {len(captured_cdn_urls)} candidate CDN URLs.")

                video_file = None
                audio_file = None

                # Test candidate URLs
                for idx, cdn_url in enumerate(list(captured_cdn_urls)):
                    temp_test = f"downloads/temp_test_{idx}.mp4"
                    try:
                        req = urllib.request.Request(cdn_url, headers={
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                            'Referer': 'https://www.instagram.com/'
                        })
                        with urllib.request.urlopen(req, context=ctx_ssl) as resp:
                            data = resp.read()
                            if len(data) > 10000:
                                with open(temp_test, "wb") as f:
                                    f.write(data)
                                
                                has_v, has_a, info = inspect_media_streams(temp_test)
                                print(f"  Candidate #{idx+1} ({len(data)} bytes) -> Has Video: {has_v}, Has Audio: {has_a}")

                                if has_v and has_a:
                                    # Both already present in single stream
                                    final_out = f"downloads/final_av_{shortcode}.mp4"
                                    os.replace(temp_test, final_out)
                                    video_file = final_out
                                    audio_file = None
                                    print(f"  🎉 Found combined AV stream: {final_out}")
                                    break
                                elif has_v and not video_file:
                                    v_target = f"downloads/video_only_{shortcode}.mp4"
                                    os.replace(temp_test, v_target)
                                    video_file = v_target
                                    print(f"  📹 Saved Video stream: {v_target}")
                                elif has_a and not audio_file:
                                    a_target = f"downloads/audio_only_{shortcode}.m4a"
                                    os.replace(temp_test, a_target)
                                    audio_file = a_target
                                    print(f"  🎵 Saved Audio stream: {a_target}")

                                if video_file and audio_file:
                                    break
                    except Exception:
                        pass
                    finally:
                        if os.path.exists(temp_test):
                            try: os.remove(temp_test)
                            except Exception: pass

                # If separate video and audio were found, merge them with FFmpeg
                final_merged = f"downloads/{shortcode}.mp4"
                if video_file and audio_file:
                    print(f"Merging Video ({video_file}) and Audio ({audio_file}) with FFmpeg...")
                    merge_cmd = [FFMPEG_EXE, "-y", "-i", video_file, "-i", audio_file, "-c", "copy", final_merged]
                    res = subprocess.run(merge_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    if res.returncode == 0 and os.path.exists(final_merged):
                        print(f"🚀 SUCCESS! Merged complete video+audio file: {final_merged} ({os.path.getsize(final_merged)} bytes)")
                        has_v, has_a, err_info = inspect_media_streams(final_merged)
                        print(f"   Final Verification -> Has Video: {has_v}, Has Audio: {has_a}")
                elif video_file:
                    os.replace(video_file, final_merged)
                    has_v, has_a, err_info = inspect_media_streams(final_merged)
                    print(f"Saved video file: {final_merged} -> Has Video: {has_v}, Has Audio: {has_a}")

                # Clean up intermediate files
                for tf in [f"downloads/video_only_{shortcode}.mp4", f"downloads/audio_only_{shortcode}.m4a"]:
                    if os.path.exists(tf):
                        try: os.remove(tf)
                        except Exception: pass

            except Exception as e:
                print(f"Error processing {shortcode}: {e}")
            finally:
                await page.close()

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_live_capture())
