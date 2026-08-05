import urllib.request
import urllib.parse
import json
import re
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
    'Referer': 'https://saveig.app/',
    'Origin': 'https://saveig.app'
}

print("--- Testing saveig / snapinsta ajax API ---")
try:
    api_url = "https://saveig.app/api/ajaxSearch"
    data = urllib.parse.urlencode({'q': urls[0], 't': 'media', 'lang': 'en'}).encode('utf-8')
    req = urllib.request.Request(api_url, data=data, headers=headers)
    with urllib.request.urlopen(req, context=ctx) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        print("SaveIG response status:", res.get("status"))
        if "data" in res:
            html_content = res["data"]
            # search for links
            v_links = re.findall(r'href=["\'](https://[^"\']+\.mp4[^"\']*)["\']', html_content)
            img_links = re.findall(r'href=["\'](https://[^"\']+\.(?:jpg|webp)[^"\']*)["\']', html_content)
            print("Video links from saveig:", len(v_links))
            print("Img links from saveig:", len(img_links))
except Exception as e:
    print("SaveIG Error:", e)

print("\n--- Testing FastDL / SnapInsta ---")
try:
    api_url = "https://snapinsta.app/api/ajaxSearch"
    data = urllib.parse.urlencode({'q': urls[0], 't': 'media', 'lang': 'en'}).encode('utf-8')
    req = urllib.request.Request(api_url, data=data, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Referer': 'https://snapinsta.app/',
        'Origin': 'https://snapinsta.app'
    })
    with urllib.request.urlopen(req, context=ctx) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        print("SnapInsta response status:", res.get("status"))
        if "data" in res:
            html_content = res["data"]
            v_links = re.findall(r'href=["\'](https://[^"\']+\.mp4[^"\']*)["\']', html_content)
            print("Video links from snapinsta:", len(v_links))
except Exception as e:
    print("SnapInsta Error:", e)
