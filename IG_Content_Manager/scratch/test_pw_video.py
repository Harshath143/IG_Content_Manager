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

async def capture_full_media():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )

        for url in urls:
            clean_url = url.split("?")[0].rstrip("/")
            shortcode = clean_url.split("/")[-1]
            post_folder = f"downloads/{shortcode}"
            os.makedirs(post_folder, exist_ok=True)

            print(f"\n==========================================")
            print(f"Fetching: {clean_url}")

            video_buffers = []
            page = await context.new_page()

            # Listen to responses and capture real video buffers
            async def handle_response(resp):
                try:
                    c_type = resp.headers.get("content-type", "")
                    r_url = resp.url
                    if "video/mp4" in c_type or ("cdninstagram.com" in r_url and ".mp4" in r_url and "bytestart" not in r_url):
                        body = await resp.body()
                        if len(body) > 50000: # larger than 50KB to get real video segments
                            video_buffers.append(body)
                except Exception:
                    pass

            page.on("response", handle_response)

            try:
                await page.goto(clean_url, wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(5000)

                # Extract Caption
                caption = ""
                meta_elem = await page.query_selector("meta[property='og:description']")
                if meta_elem:
                    caption = await meta_elem.get_attribute("content") or ""
                if not caption:
                    meta_elem = await page.query_selector("meta[name='description']")
                    if meta_elem:
                        caption = await meta_elem.get_attribute("content") or ""

                if caption:
                    caption = re.sub(r'^[\d,]+\s+likes,\s+[\d,]+\s+comments\s+-\s+[^\s]+\s+on\s+[^:]+:\s*', '', caption, flags=re.IGNORECASE).strip('"\' ')

                print(f"Caption ({len(caption)} chars): {caption[:120]}...")

                # Save video buffer if captured
                v_path = f"downloads/{shortcode}.mp4"
                if video_buffers:
                    # pick largest buffer
                    largest_buf = max(video_buffers, key=len)
                    with open(v_path, "wb") as f:
                        f.write(largest_buf)
                    print(f"✅ Video Saved: {v_path} ({len(largest_buf)} bytes)")
                
                # Save Images (og:image + page images)
                image_paths = []
                og_img = await page.query_selector("meta[property='og:image']")
                if og_img:
                    img_url = await og_img.get_attribute("content")
                    if img_url:
                        i_path = f"{post_folder}/img_01.jpg"
                        req = urllib.request.Request(img_url, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req) as response, open(i_path, 'wb') as f:
                            f.write(response.read())
                        if os.path.exists(i_path) and os.path.getsize(i_path) > 2000:
                            image_paths.append(i_path)
                            print(f"✅ Image Saved: {i_path} ({os.path.getsize(i_path)} bytes)")

            except Exception as e:
                print(f"Error for {shortcode}: {e}")
            finally:
                await page.close()

        await browser.close()

if __name__ == "__main__":
    asyncio.run(capture_full_media())
