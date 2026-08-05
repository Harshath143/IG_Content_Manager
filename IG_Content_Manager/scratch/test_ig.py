import urllib.request
import re
import json

url = "https://www.instagram.com/p/Da5xwapDGIC/embed/captioned/"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}
req = urllib.request.Request(url, headers=headers)
try:
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode('utf-8')
        with open("scratch/embed_sample.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("Saved embed_sample.html, length:", len(html))
        
        # Check window.__additionalDataLoaded or similar script data
        scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
        print("Found scripts:", len(scripts))
        for i, s in enumerate(scripts):
            if "caption" in s.lower() or "video" in s.lower() or "display_url" in s.lower() or "additionalData" in s:
                print(f"Script {i} snippet:", s[:300])
except Exception as e:
    print("Error:", e)
