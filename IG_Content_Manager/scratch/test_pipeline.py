import os
import sys
import yt_dlp
import instaloader
import urllib.request
import re

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def get_cookies_option():
    """Finds cookies file or browser cookies setting."""
    cookie_file = os.getenv("COOKIES_FILE", "cookies.txt")
    if os.path.exists(cookie_file):
        return {'cookiefile': cookie_file}
    if os.path.exists("data/cookies.txt"):
        return {'cookiefile': "data/cookies.txt"}
    
    browser = os.getenv("COOKIES_FROM_BROWSER")
    if browser:
        return {'cookiesfrombrowser': (browser,)}
    
    return {}

def extract_instagram_intel(url):
    clean_url = url.split("?")[0].rstrip("/")
    shortcode = clean_url.split("/")[-1]
    post_folder = f"downloads/{shortcode}"
    os.makedirs(post_folder, exist_ok=True)
    
    caption = ""
    downloaded_video = None
    image_paths = []
    
    cookie_opts = get_cookies_option()
    if cookie_opts:
        print(f"   [Cookies] Using cookies option: {cookie_opts}")
    else:
        print("   [Warning] No cookies file found (cookies.txt). Standard unauthenticated requests may fail.")

    # TIER 1: yt-dlp
    print("   [Tier 1] Trying yt-dlp...")
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'outtmpl': f"{post_folder}/%(title)s.%(ext)s",
            **cookie_opts
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            caption = info.get('description') or info.get('title') or ""
            is_video = info.get('_type') == 'video' or 'formats' in info or info.get('vcodec') != 'none'
            
            if is_video:
                video_path = f"downloads/{shortcode}.mp4"
                ydl_download_opts = {
                    'outtmpl': video_path,
                    'quiet': True,
                    'no_warnings': True,
                    **cookie_opts
                }
                with yt_dlp.YoutubeDL(ydl_download_opts) as ydl_dl:
                    ydl_dl.download([url])
                if os.path.exists(video_path):
                    downloaded_video = video_path
                    print(f"   [OK] Video downloaded via yt-dlp: {video_path}")
            else:
                image_template = f"{post_folder}/img_%(autonumber)02d"
                ydl_img_opts = {
                    'outtmpl': f"{image_template}",
                    'quiet': True,
                    'no_warnings': True,
                    'ignoreerrors': True,
                    'writethumbnail': True,
                    **cookie_opts
                }
                with yt_dlp.YoutubeDL(ydl_img_opts) as ydl_dl:
                    ydl_dl.download([url])
                
                for file in os.listdir(post_folder):
                    if file.endswith(('.jpg', '.png', '.webp')):
                        image_paths.append(os.path.join(post_folder, file))
                print(f"   [OK] Extracted {len(image_paths)} images via yt-dlp")
                
    except Exception as e:
        print(f"   [Fail] yt-dlp Tier failed: {e}")

    # TIER 2: Instaloader Fallback
    if not caption and not downloaded_video and not image_paths:
        print("   [Tier 2] Trying Instaloader...")
        try:
            L = instaloader.Instaloader(
                download_pictures=True,
                download_videos=True,
                download_video_thumbnails=False,
                download_geotags=False,
                download_comments=False,
                save_metadata=False,
                dirname_pattern=post_folder
            )
            cookie_file = cookie_opts.get('cookiefile')
            if cookie_file and os.path.exists(cookie_file):
                try:
                    import http.cookiejar
                    cj = http.cookiejar.MozillaCookieJar(cookie_file)
                    cj.load(ignore_discard=True, ignore_expires=True)
                    L.context._session.cookies = cj
                    print("   [Cookies] Loaded cookies into Instaloader session.")
                except Exception as ce:
                    print(f"   [Warning] Could not load cookies into Instaloader: {ce}")
            
            post = instaloader.Post.from_shortcode(L.context, shortcode)
            caption = post.caption or ""
            print(f"   [OK] Instaloader caption fetched ({len(caption)} chars)")
            
            if post.is_video:
                v_path = f"downloads/{shortcode}.mp4"
                L.download_post(post, target=post_folder)
                for f in os.listdir(post_folder):
                    if f.endswith('.mp4'):
                        os.rename(os.path.join(post_folder, f), v_path)
                        downloaded_video = v_path
                        break
            else:
                L.download_post(post, target=post_folder)
                for f in os.listdir(post_folder):
                    if f.endswith(('.jpg', '.png', '.webp')):
                        image_paths.append(os.path.join(post_folder, f))
        except Exception as e:
            print(f"   [Fail] Instaloader Tier failed: {e}")

    # Return results or None if completely failed
    if not caption and not downloaded_video and not image_paths:
        return None, None, []
    
    return caption, downloaded_video, image_paths

print("Testing pipeline logic...")
c, v, i = extract_instagram_intel("https://www.instagram.com/p/Da5xwapDGIC/")
print("Result -> Caption:", bool(c), "Video:", v, "Images:", len(i))
