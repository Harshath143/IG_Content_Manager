# Media download & transcription
import yt_dlp
import os
import re
import sys
import urllib.request
import instaloader
import asyncio
import ssl
import subprocess
import imageio_ffmpeg

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def get_cookies_opts():
    """Detects available cookie sources for yt-dlp."""
    cookie_file = os.getenv("COOKIES_FILE", "cookies.txt")
    if os.path.exists(cookie_file):
        return {'cookiefile': cookie_file}
    if os.path.exists("data/cookies.txt"):
        return {'cookiefile': "data/cookies.txt"}
    
    browser = os.getenv("COOKIES_FROM_BROWSER")
    if browser:
        return {'cookiesfrombrowser': (browser,)}
    
    return {}

def extract_via_playwright(url, shortcode):
    """Fallback extraction using Playwright browser to capture captions, video & audio, merging with FFmpeg."""
    print("   🌐 Attempting Playwright Browser fallback (Audio + Video)...")
    caption = ""
    downloaded_path = None
    image_paths = []

    ctx_ssl = ssl.create_default_context()
    ctx_ssl.check_hostname = False
    ctx_ssl.verify_mode = ssl.CERT_NONE

    def inspect_streams(file_path):
        try:
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            cmd = [ffmpeg_exe, "-i", file_path]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            err = res.stderr.decode('utf-8', errors='ignore')
            return ("Video:" in err), ("Audio:" in err)
        except Exception:
            return False, False

    async def _pw_run():
        nonlocal caption, downloaded_path, image_paths
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 800}
                )
                page = await context.new_page()
                captured_cdn_urls = set()

                async def handle_request(req):
                    try:
                        r_url = req.url
                        if ("fbcdn.net" in r_url or "cdninstagram.com" in r_url) and ("/o1/v/" in r_url or "/t50." in r_url or "mime=" in r_url):
                            clean_cdn = re.sub(r'&bytestart=\d+&byteend=\d+', '', r_url)
                            clean_cdn = re.sub(r'\?bytestart=\d+&byteend=\d+&', '?', clean_cdn)
                            captured_cdn_urls.add(clean_cdn)
                    except Exception:
                        pass

                page.on("request", handle_request)

                clean_url = url.split("?")[0].rstrip("/")
                await page.goto(clean_url, wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(6000)

                # Caption Extraction
                meta_elem = await page.query_selector("meta[property='og:description']")
                if meta_elem:
                    caption = await meta_elem.get_attribute("content") or ""
                if not caption:
                    meta_elem = await page.query_selector("meta[name='description']")
                    if meta_elem:
                        caption = await meta_elem.get_attribute("content") or ""

                if caption:
                    caption = re.sub(r'^[\d,]+\s+likes,\s+[\d,]+\s+comments\s+-\s+[^\s]+\s+on\s+[^:]+:\s*', '', caption, flags=re.IGNORECASE).strip('"\' ')

                # Process CDN URLs for Video & Audio
                v_temp = f"downloads/temp_v_{shortcode}.mp4"
                a_temp = f"downloads/temp_a_{shortcode}.m4a"
                v_saved = False
                a_saved = False

                for idx, cdn_url in enumerate(list(captured_cdn_urls)):
                    temp_chk = f"downloads/chk_{idx}_{shortcode}.mp4"
                    try:
                        req = urllib.request.Request(cdn_url, headers={
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                            'Referer': 'https://www.instagram.com/'
                        })
                        with urllib.request.urlopen(req, context=ctx_ssl) as resp:
                            data = resp.read()
                            if len(data) > 10000:
                                with open(temp_chk, "wb") as f:
                                    f.write(data)
                                has_v, has_a = inspect_streams(temp_chk)

                                if has_v and has_a and not v_saved:
                                    # Combined stream found
                                    final_out = f"downloads/{shortcode}.mp4"
                                    os.replace(temp_chk, final_out)
                                    downloaded_path = final_out
                                    v_saved = True
                                    a_saved = True
                                    print(f"   ✅ Captured combined Video+Audio stream: {final_out}")
                                    break
                                elif has_v and not v_saved:
                                    os.replace(temp_chk, v_temp)
                                    v_saved = True
                                elif has_a and not a_saved:
                                    os.replace(temp_chk, a_temp)
                                    a_saved = True

                                if v_saved and a_saved:
                                    break
                    except Exception:
                        pass
                    finally:
                        if os.path.exists(temp_chk):
                            try: os.remove(temp_chk)
                            except Exception: pass

                # Merge separate Video & Audio streams if needed
                final_target = f"downloads/{shortcode}.mp4"
                if v_saved and a_saved and not downloaded_path:
                    try:
                        import imageio_ffmpeg
                        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
                        cmd = [ffmpeg_exe, "-y", "-i", v_temp, "-i", a_temp, "-c", "copy", final_target]
                        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        if res.returncode == 0 and os.path.exists(final_target):
                            downloaded_path = final_target
                            print(f"   🚀 Merged Video + Audio streams successfully: {final_target} ({os.path.getsize(final_target)} bytes)")
                    except Exception as me:
                        print(f"   ⚠️ FFmpeg merge warning: {me}")
                elif v_saved and not downloaded_path:
                    os.replace(v_temp, final_target)
                    downloaded_path = final_target
                    print(f"   ✅ Saved Video stream: {final_target}")

                # Clean temporary stream files
                for tf in [v_temp, a_temp]:
                    if os.path.exists(tf):
                        try: os.remove(tf)
                        except Exception: pass

                # Image Download
                post_folder = f"downloads/{shortcode}"
                os.makedirs(post_folder, exist_ok=True)
                og_img = await page.query_selector("meta[property='og:image']")
                if og_img:
                    img_url = await og_img.get_attribute("content")
                    if img_url:
                        i_path = f"{post_folder}/img_01.jpg"
                        try:
                            req = urllib.request.Request(img_url, headers={'User-Agent': 'Mozilla/5.0'})
                            with urllib.request.urlopen(req, context=ctx_ssl) as response, open(i_path, 'wb') as f:
                                f.write(response.read())
                            if os.path.exists(i_path) and os.path.getsize(i_path) > 2000:
                                image_paths.append(i_path)
                                print(f"   ✅ Downloaded image: {i_path}")
                        except Exception:
                            pass

                await page.close()
                await browser.close()
        except Exception as e:
            print(f"   ⚠️ Playwright browser error: {e}")

    try:
        asyncio.run(_pw_run())
    except Exception as e:
        print(f"   ⚠️ Playwright async error: {e}")

    return caption, downloaded_path, image_paths



def get_video_intel(url, rotator):
    # Clean URL to extract shortcode correctly
    clean_url = url.split("?")[0].rstrip("/")
    shortcode = clean_url.split("/")[-1]
    
    print(f"   ⬇️ Processing: {clean_url}")
    
    caption = ""
    downloaded_path = None
    image_paths = []
    is_video = False
    
    cookie_opts = get_cookies_opts()

    # 1. Primary Strategy: yt-dlp
    try:
        ydl_opts_meta = {
            'quiet': True,
            'no_warnings': True,
            'logger': None,
            **cookie_opts
        }
        with yt_dlp.YoutubeDL(ydl_opts_meta) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                caption = info.get('description') or info.get('title') or ""
                if info.get('_type') == 'video' or 'formats' in info or info.get('vcodec') != 'none':
                    is_video = True
                else:
                    is_video = False
            except Exception as e:
                err_str = str(e).lower()
                if "no video in this post" in err_str:
                    is_video = False
                else:
                    raise e
                    
    except Exception:
        pass

    # 2. Download Content via yt-dlp
    if caption or is_video:
        try:
            post_folder = f"downloads/{shortcode}"
            os.makedirs(post_folder, exist_ok=True)

            if is_video:
                path = f"downloads/{shortcode}.mp4"
                ydl_opts_download = {
                    'outtmpl': path,
                    'quiet': True,
                    'no_warnings': True,
                    'logger': None,
                    **cookie_opts
                }
                print(f"   ⬇️ Downloading Video to {path}...")
                with yt_dlp.YoutubeDL(ydl_opts_download) as ydl:
                    ydl.download([url])
                if os.path.exists(path):
                    downloaded_path = path
            else:
                print("   📸 Static Post detected. Downloading images...")
                image_template = f"{post_folder}/img_%(autonumber)02d"
                ydl_opts_img = {
                    'outtmpl': f"{image_template}",
                    'quiet': True,
                    'no_warnings': True,
                    'ignoreerrors': True,
                    'writethumbnail': True,
                    'logger': None,
                    **cookie_opts
                }
                try:
                    with yt_dlp.YoutubeDL(ydl_opts_img) as ydl:
                        ydl.download([url])
                except Exception:
                    pass


                for file in os.listdir(post_folder):
                    if file.startswith("img_") and file.endswith(('.jpg', '.png', '.webp')):
                        image_paths.append(os.path.join(post_folder, file))
        except Exception as e:
            print(f"   ⚠️ Download error: {e}")

    # 3. Fallback Strategy: Instaloader if yt-dlp didn't get media/caption
    if not caption and not downloaded_path and not image_paths:
        try:
            post_folder = f"downloads/{shortcode}"
            os.makedirs(post_folder, exist_ok=True)

            L = instaloader.Instaloader(
                download_pictures=True,
                download_videos=True,
                download_video_thumbnails=False,
                download_geotags=False,
                download_comments=False,
                save_metadata=False
            )
            L.context.max_attempts = 1

            cookie_file = cookie_opts.get('cookiefile')
            if cookie_file and os.path.exists(cookie_file):
                try:
                    import http.cookiejar
                    cj = http.cookiejar.MozillaCookieJar(cookie_file)
                    cj.load(ignore_discard=True, ignore_expires=True)
                    L.context._session.cookies = cj
                except Exception:
                    pass

            post = instaloader.Post.from_shortcode(L.context, shortcode)
            caption = post.caption or ""

            if post.is_video:
                v_path = f"downloads/{shortcode}.mp4"
                L.download_post(post, target=post_folder)
                for f in os.listdir(post_folder):
                    if f.endswith('.mp4'):
                        full_f = os.path.join(post_folder, f)
                        os.replace(full_f, v_path)
                        downloaded_path = v_path
                        break
            else:
                L.download_post(post, target=post_folder)
                for f in os.listdir(post_folder):
                    if f.endswith(('.jpg', '.png', '.webp')):
                        image_paths.append(os.path.join(post_folder, f))

        except Exception:
            pass


    # 4. Fallback Strategy: Playwright Browser if previous tiers failed
    if not caption and not downloaded_path and not image_paths:
        caption, downloaded_path, image_paths = extract_via_playwright(url, shortcode)

    # Clean up empty post folder if created but no media files saved inside
    post_folder = f"downloads/{shortcode}"
    if os.path.exists(post_folder) and not os.listdir(post_folder):
        try:
            os.rmdir(post_folder)
        except Exception:
            pass

    # Validation: If after all attempts we have no caption, no video, and no images, return failure indicator
    if not caption and not downloaded_path and not image_paths:
        print(f"   ❌ Extraction failed completely for {clean_url}")
        return None, "", []

    # 5. Transcribe (Only if we have a valid video/audio file)
    transcript = ""
    if downloaded_path and os.path.exists(downloaded_path):
        print("   🎙️ Transcribing audio...")
        client = rotator.get_client()
        try:
            with open(downloaded_path, "rb") as f:
                transcript = client.audio.transcriptions.create(
                    file=(downloaded_path, f.read()),
                    model="whisper-large-v3-turbo"
                ).text
            print("   ✅ Transcription complete.")
        except Exception as e:
            print(f"   ⚠️ Transcription skipped/failed (likely silent or static): {e}")
            transcript = ""
    else:
        print("   ⏭️ Skipping transcription (No video file downloaded).")

    return caption, transcript, image_paths
