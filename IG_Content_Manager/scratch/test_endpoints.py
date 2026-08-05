import urllib.request
import urllib.parse
import json
import ssl

urls = [
    "https://www.instagram.com/p/Da5xwapDGIC/",
    "https://www.instagram.com/p/Da03ym3jSaJ/",
    "https://www.instagram.com/reel/Dak9akADi4e/",
    "https://www.instagram.com/reel/DbFZWADTgwf/",
    "https://www.instagram.com/reel/DbJ-wX6AWQ4/"
]

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*'
}

print("--- Testing Instagram oEmbed ---")
for url in urls[:2]:
    oembed_url = f"https://api.instagram.com/oembed/?url={urllib.parse.quote(url)}"
    req = urllib.request.Request(oembed_url, headers=headers)
    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print(f"[oEmbed SUCCESS] Title: {data.get('title')}, Author: {data.get('author_name')}, Thumb: {data.get('thumbnail_url')}")
    except Exception as e:
        print(f"[oEmbed Failed] {e}")

print("\n--- Testing DDInstagram / VXInstagram ---")
for url in urls[:2]:
    # Replace instagram.com with ddinstagram.com or vxinstagram.com
    dd_url = url.replace("instagram.com", "ddinstagram.com")
    req = urllib.request.Request(dd_url, headers={'User-Agent': 'TelegramBot (like TwitterBot)'})
    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            html = resp.read().decode('utf-8')
            print(f"[DDInstagram] Len: {len(html)}")
            # look for og:description or og:video
            import re
            desc = re.findall(r'<meta property="og:description" content="([^"]+)"', html)
            video = re.findall(r'<meta property="og:video" content="([^"]+)"', html)
            image = re.findall(r'<meta property="og:image" content="([^"]+)"', html)
            print(f"  Desc: {desc}")
            print(f"  Video: {video}")
            print(f"  Image: {image}")
    except Exception as e:
        print(f"[DDInstagram Failed] {e}")

print("\n--- Testing Cobalt API ---")
cobalt_url = "https://api.cobalt.tools/"
cobalt_req_data = json.dumps({"url": urls[0]}).encode('utf-8')
cobalt_req = urllib.request.Request(cobalt_url, data=cobalt_req_data, headers={
    'User-Agent': 'Mozilla/5.0',
    'Content-Type': 'application/json',
    'Accept': 'application/json'
})
try:
    with urllib.request.urlopen(cobalt_req, context=ctx) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        print("[Cobalt SUCCESS]:", res)
except Exception as e:
    print("[Cobalt Failed]:", e)
