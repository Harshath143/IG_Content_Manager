import asyncio
import os
import sys
import yt_dlp
from playwright.async_api import async_playwright

urls = [
    "https://www.instagram.com/p/Da5xwapDGIC/",
    "https://www.instagram.com/p/Da03ym3jSaJ/",
    "https://www.instagram.com/reel/Dak9akADi4e/",
    "https://www.instagram.com/reel/DbFZWADTgwf/",
    "https://www.instagram.com/reel/DbJ-wX6AWQ4/"
]

def save_playwright_cookies_to_netscape(cookies, filepath="cookies.txt"):
    """Converts Playwright cookies list to Netscape cookies.txt format."""
    lines = ["# Netscape HTTP Cookie File\n"]
    for c in cookies:
        domain = c.get("domain", "")
        flag = "TRUE" if domain.startswith(".") else "FALSE"
        path = c.get("path", "/")
        secure = "TRUE" if c.get("secure", False) else "FALSE"
        expiration = int(c.get("expires", 2147483647))
        if expiration < 0:
            expiration = 2147483647
        name = c.get("name", "")
        value = c.get("value", "")
        lines.append(f"{domain}\t{flag}\t{path}\t{secure}\t{expiration}\t{name}\t{value}\n")
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"Saved {len(cookies)} cookies to {filepath}")

async def test_cookie_export():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # Navigate to instagram home or reel to get session cookies
        print("Navigating to Instagram via Playwright...")
        await page.goto("https://www.instagram.com/reel/DbJ-wX6AWQ4/", wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(3000)
        
        cookies = await context.cookies()
        save_playwright_cookies_to_netscape(cookies, "cookies.txt")
        await browser.close()

    # Now test yt-dlp with the generated cookies.txt
    print("\n--- Testing yt-dlp with Playwright cookies.txt ---")
    ydl_opts = {
        'quiet': False,
        'cookiefile': 'cookies.txt',
        'outtmpl': 'downloads/test_valid.mp4'
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([urls[0]])
        
        if os.path.exists("downloads/test_valid.mp4"):
            size = os.path.getsize("downloads/test_valid.mp4")
            with open("downloads/test_valid.mp4", "rb") as f:
                hdr = f.read(16)
            print(f"yt-dlp SUCCESS! Size: {size} bytes, Header: {hdr}")
    except Exception as e:
        print(f"yt-dlp error: {e}")

if __name__ == "__main__":
    asyncio.run(test_cookie_export())
