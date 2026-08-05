import asyncio
import os
import re
import urllib.request
from playwright.async_api import async_playwright

urls = [
    "https://www.instagram.com/p/Da5xwapDGIC/",
    "https://www.instagram.com/p/Da03ym3jSaJ/",
    "https://www.instagram.com/reel/Dak9akADi4e/",
    "https://www.instagram.com/reel/DbFZWADTgwf/",
    "https://www.instagram.com/reel/DbJ-wX6AWQ4/"
]

async def scrape_ig_playwright():
    async with async_playwright() as p:
        # Launch browser (chromium or edge)
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        for url in urls:
            shortcode = url.split("?")[0].rstrip("/").split("/")[-1]
            print(f"\n--- Playwright Fetching: {shortcode} ---")
            try:
                # Go to page
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                await page.wait_for_timeout(3000)
                
                # Title & Description
                page_title = await page.title()
                print(f"Page Title: {page_title}")

                # Extract video src or img src
                videos = await page.eval_on_selector_all("video", "nodes => nodes.map(n => n.src)")
                images = await page.eval_on_selector_all("img", "nodes => nodes.map(n => n.src)")
                
                # Extract meta og:description or caption element
                meta_desc = await page.locator("meta[property='og:description']").get_attribute("content")
                print(f"Meta Description: {meta_desc}")

                print(f"Videos found: {len(videos)} -> {videos[:2]}")
                print(f"Images found: {len(images)} -> {images[:2]}")

            except Exception as e:
                print(f"Playwright error for {shortcode}: {e}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_ig_playwright())
