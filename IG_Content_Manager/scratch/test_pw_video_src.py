import asyncio
import os
import sys
import re
import urllib.request
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

async def test_video_src():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )

        for url in urls:
            shortcode = url.split("?")[0].rstrip("/").split("/")[-1]
            page = await context.new_page()
            print(f"\n==========================================")
            print(f"Checking DOM video src for {shortcode}...")

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(4000)

                # Get src from <video> tag in DOM
                v_srcs = await page.eval_on_selector_all("video", "nodes => nodes.map(n => n.src || n.currentSrc)")
                print(f"Video tag srcs: {v_srcs}")

                # Also check <source> tags inside <video>
                s_srcs = await page.eval_on_selector_all("video source", "nodes => nodes.map(n => n.src)")
                print(f"Source tag srcs: {s_srcs}")

                # Also check og:video meta tag
                og_vid = await page.query_selector("meta[property='og:video']")
                og_src = await og_vid.get_attribute("content") if og_vid else None
                print(f"og:video src: {og_src}")

                target_url = None
                for candidate in v_srcs + s_srcs + ([og_src] if og_src else []):
                    if candidate and candidate.startswith("http") and not candidate.startswith("blob:"):
                        target_url = candidate
                        break

                if target_url:
                    out_path = f"downloads/test_{shortcode}.mp4"
                    print(f"Downloading direct URL: {target_url[:120]}...")
                    req = urllib.request.Request(target_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
                    with urllib.request.urlopen(req, context=ctx_ssl) as resp, open(out_path, "wb") as f:
                        f.write(resp.read())
                    
                    size = os.path.getsize(out_path)
                    with open(out_path, "rb") as f:
                        hdr = f.read(16)
                    print(f"Downloaded File: {out_path} | Size: {size} bytes | Header: {hdr}")
                else:
                    print("No direct HTTP video URL found (only blob or empty).")

            except Exception as e:
                print(f"Error: {e}")
            finally:
                await page.close()

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_video_src())
