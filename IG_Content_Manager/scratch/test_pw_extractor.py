import asyncio
import os
import sys
import re
import urllib.request
import ssl
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

urls = [
    "https://www.instagram.com/p/Da5xwapDGIC/?igsh=MWFoNTFqNHlyaHdyYQ==",
    "https://www.instagram.com/p/Da03ym3jSaJ/?igsh=d3FpN2ZybnowM2Yx",
    "https://www.instagram.com/reel/Dak9akADi4e/?igsh=MWVjbTBndjc3ZjYx",
    "https://www.instagram.com/reel/DbFZWADTgwf/?igsh=eXEzdzJvZDVpbHJr",
    "https://www.instagram.com/reel/DbJ-wX6AWQ4/?igsh=MW44NWQyMjNwaW5rbw=="
]

ctx_ssl = ssl.create_default_context()
ctx_ssl.check_hostname = False
ctx_ssl.verify_mode = ssl.CERT_NONE

async def extract_all():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )

        for url in urls:
            clean_url = url.split("?")[0].rstrip("/")
            shortcode = clean_url.split("/")[-1]
            print(f"\n==========================================")
            print(f"Processing: {clean_url} (Shortcode: {shortcode})")

            media_urls = set()
            video_urls = set()

            page = await context.new_page()

            # Intercept response URLs to find direct video/image CDN links
            def handle_response(response):
                r_url = response.url
                if ("cdninstagram.com" in r_url or "fbcdn.net" in r_url):
                    if ".mp4" in r_url or "bytestart" in r_url:
                        video_urls.add(r_url)
                    elif ".jpg" in r_url or ".webp" in r_url:
                        media_urls.add(r_url)

            page.on("response", handle_response)

            try:
                await page.goto(clean_url, wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(4000)

                # Extract Caption
                caption = ""
                # Try og:description first
                try:
                    meta_elem = await page.query_selector("meta[property='og:description']")
                    if meta_elem:
                        caption = await meta_elem.get_attribute("content") or ""
                except Exception:
                    pass

                if not caption:
                    try:
                        meta_elem = await page.query_selector("meta[name='description']")
                        if meta_elem:
                            caption = await meta_elem.get_attribute("content") or ""
                    except Exception:
                        pass

                # Clean caption string
                if caption:
                    # Remove "likes, comments - username on date:" prefix if present
                    caption_clean = re.sub(r'^[\d,]+\s+likes,\s+[\d,]+\s+comments\s+-\s+[^\s]+\s+on\s+[^:]+:\s*', '', caption, flags=re.IGNORECASE)
                    caption_clean = caption_clean.strip('"\' ')
                else:
                    caption_clean = ""

                print(f"Extracted Caption ({len(caption_clean)} chars):\n{caption_clean[:200]}...")

                # Extract og:video or og:image
                try:
                    og_vid = await page.query_selector("meta[property='og:video']")
                    if og_vid:
                        v_src = await og_vid.get_attribute("content")
                        if v_src: video_urls.add(v_src)
                except Exception:
                    pass

                try:
                    og_img = await page.query_selector("meta[property='og:image']")
                    if og_img:
                        i_src = await og_img.get_attribute("content")
                        if i_src: media_urls.add(i_src)
                except Exception:
                    pass

                print(f"Captured Video CDN Links: {len(video_urls)}")
                print(f"Captured Image CDN Links: {len(media_urls)}")

                # Save media
                post_folder = f"downloads/{shortcode}"
                os.makedirs(post_folder, exist_ok=True)
                downloaded_file = None
                image_paths = []

                if video_urls:
                    v_url = list(video_urls)[0]
                    v_path = f"downloads/{shortcode}.mp4"
                    print(f"Downloading Video from CDN to {v_path}...")
                    req = urllib.request.Request(v_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, context=ctx_ssl) as resp, open(v_path, 'wb') as f:
                        f.write(resp.read())
                    downloaded_file = v_path
                    print(f"SUCCESS: Saved {v_path} (Size: {os.path.getsize(v_path)} bytes)")
                elif media_urls:
                    print("Downloading Images from CDN...")
                    for idx, img_url in enumerate(list(media_urls)[:3]):
                        img_path = f"{post_folder}/img_{idx+1:02d}.jpg"
                        try:
                            req = urllib.request.Request(img_url, headers={'User-Agent': 'Mozilla/5.0'})
                            with urllib.request.urlopen(req, context=ctx_ssl) as resp, open(img_path, 'wb') as f:
                                f.write(resp.read())
                            if os.path.getsize(img_path) > 2000: # filter icons
                                image_paths.append(img_path)
                                print(f"SUCCESS: Saved image {img_path}")
                        except Exception as ie:
                            print(f"Error downloading image: {ie}")

            except Exception as e:
                print(f"Error processing {shortcode}: {e}")
            finally:
                await page.close()

        await browser.close()

if __name__ == "__main__":
    asyncio.run(extract_all())
