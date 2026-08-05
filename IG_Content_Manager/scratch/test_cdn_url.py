import asyncio
import os
import sys
import re
import urllib.request
import urllib.parse
import ssl
from playwright.async_api import async_playwright

urls = [
    "https://www.instagram.com/p/Da5xwapDGIC/",
    "https://www.instagram.com/reel/Dak9akADi4e/",
    "https://www.instagram.com/reel/DbFZWADTgwf/",
    "https://www.instagram.com/reel/DbJ-wX6AWQ4/"
]

ctx_ssl = ssl.create_default_context()
ctx_ssl.check_hostname = False
ctx_ssl.verify_mode = ssl.CERT_NONE

async def test_full_cdn_download():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )

        for url in urls:
            shortcode = url.split("?")[0].rstrip("/").split("/")[-1]
            page = await context.new_page()
            print(f"\n==========================================")
            print(f"Intercepting CDN requests for {shortcode}...")

            captured_cdn_urls = set()

            async def handle_request(req):
                r_url = req.url
                if ("cdninstagram.com" in r_url or "fbcdn.net" in r_url) and (".mp4" in r_url or "mime=video" in r_url or "efg=" in r_url):
                    # Clean range params from URL
                    clean_cdn = re.sub(r'&bytestart=\d+&byteend=\d+', '', r_url)
                    clean_cdn = re.sub(r'\?bytestart=\d+&byteend=\d+&', '?', clean_cdn)
                    captured_cdn_urls.add(clean_cdn)

            page.on("request", handle_request)

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(5000)

                print(f"Captured clean CDN video URLs count: {len(captured_cdn_urls)}")
                
                success = False
                for idx, cdn_url in enumerate(list(captured_cdn_urls)[:5]):
                    print(f"Testing CDN URL #{idx+1}: {cdn_url[:120]}...")
                    out_path = f"downloads/test_clean_{shortcode}.mp4"
                    try:
                        req = urllib.request.Request(cdn_url, headers={
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                            'Accept': '*/*',
                            'Referer': 'https://www.instagram.com/'
                        })
                        with urllib.request.urlopen(req, context=ctx_ssl) as resp:
                            data = resp.read()
                            if len(data) > 100000: # larger than 100KB
                                with open(out_path, "wb") as f:
                                    f.write(data)
                                
                                size = os.path.getsize(out_path)
                                with open(out_path, "rb") as f:
                                    hdr = f.read(16)
                                print(f"👉 SUCCESS! Saved {out_path} | Size: {size} bytes | Header: {hdr}")
                                success = True
                                break
                            else:
                                print(f"   Skip small segment size ({len(data)} bytes)")
                    except Exception as e:
                        print(f"   CDN download error: {e}")

                if not success:
                    print("❌ Could not download full video from captured CDN URLs.")

            except Exception as e:
                print(f"Error: {e}")
            finally:
                await page.close()

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_full_cdn_download())
