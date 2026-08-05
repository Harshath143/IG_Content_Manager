import asyncio
import sys
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

async def inspect_requests():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print("Navigating to Reel: https://www.instagram.com/reel/DbJ-wX6AWQ4/ ...")
        
        all_reqs = []
        def on_req(req):
            r_url = req.url
            if "fbcdn.net" in r_url or "cdninstagram.com" in r_url:
                all_reqs.append(r_url)

        page.on("request", on_req)

        await page.goto("https://www.instagram.com/reel/DbJ-wX6AWQ4/", wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(6000)

        print(f"Total CDN Requests captured: {len(all_reqs)}")
        for idx, r in enumerate(all_reqs):
            print(f"[{idx+1}] {r[:150]}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_requests())
