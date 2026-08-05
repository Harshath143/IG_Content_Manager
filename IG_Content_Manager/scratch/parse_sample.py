import re
import html as html_lib

with open("scratch/embed_sample.html", "r", encoding="utf-8") as f:
    content = f.read()

print("--- Searching for Caption ---")
# Check CaptionComments / Caption element
caption_comments = re.findall(r'class="CaptionComments"[^>]*>(.*?)</div>', content, re.DOTALL)
print("CaptionComments:", caption_comments)

caption_divs = re.findall(r'class="Caption"[^>]*>(.*?)</div>', content, re.DOTALL)
print("Caption divs:", caption_divs)

# Search for any text inside script tags containing 'text' or 'caption'
json_captions = re.findall(r'"text"\s*:\s*("([^"\\]|\\.)*")', content)
for jc in json_captions[:10]:
    txt = jc[0]
    if len(txt) > 20 and not txt.startswith('"http'):
        print("JSON text snippet:", txt[:150])

print("\n--- Searching for MP4 Video URLs ---")
video_urls = set(re.findall(r'https:\\?/\\?/[^"\']+\.mp4[^"\']*', content))
print(f"Found {len(video_urls)} MP4 URLs")
for v in list(video_urls)[:5]:
    clean_v = v.replace("\\/", "/")
    print("  Video:", clean_v[:120])

print("\n--- Searching for Image URLs ---")
image_urls = set(re.findall(r'https:\\?/\\?/[^"\']+\.(?:jpg|webp)[^"\']*', content))
print(f"Found {len(image_urls)} Image URLs")
for img in list(image_urls)[:5]:
    clean_img = img.replace("\\/", "/")
    print("  Image:", clean_img[:120])
