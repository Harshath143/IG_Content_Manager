import urllib.request
import ssl
import subprocess
import os
import imageio_ffmpeg

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

ctx_ssl = ssl.create_default_context()
ctx_ssl.check_hostname = False
ctx_ssl.verify_mode = ssl.CERT_NONE

url_m367 = "https://instagram.fcjb6-1.fna.fbcdn.net/o1/v/t2/f2/m367/AQMZvBjcbKVLKhYI0H6cRjSzBPWBq0kUKBtxF0gqFtC-_8blVPyfzk7Kvkise8cj9yR4GaVJqhRyzi71nTcmI-_5fFeXve"
url_m78  = "https://instagram.fcjb6-1.fna.fbcdn.net/o1/v/t2/f2/m78/AQMqOAtc-iTaBa2aMWkaVqTZKibvFN2DAP8icLDvT4dgu3mV12il3iCm9CFpmSUGJxeQYuWYEYj8kunZ7RRvdh1Bga_k3O5"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Referer': 'https://www.instagram.com/'
}

print("Downloading stream m367...")
req1 = urllib.request.Request(url_m367, headers=headers)
with urllib.request.urlopen(req1, context=ctx_ssl) as resp, open("downloads/stream_m367.mp4", "wb") as f:
    f.write(resp.read())
print("m367 saved, size:", os.path.getsize("downloads/stream_m367.mp4"))

print("Downloading stream m78...")
req2 = urllib.request.Request(url_m78, headers=headers)
with urllib.request.urlopen(req2, context=ctx_ssl) as resp, open("downloads/stream_m78.mp4", "wb") as f:
    f.write(resp.read())
print("m78 saved, size:", os.path.getsize("downloads/stream_m78.mp4"))

# Check streams with ffmpeg
def check_info(file_path):
    cmd = [FFMPEG_EXE, "-i", file_path]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    err = res.stderr.decode('utf-8', errors='ignore')
    for line in err.splitlines():
        if "Stream #" in line:
            print(f"  {file_path} -> {line}")

check_info("downloads/stream_m367.mp4")
check_info("downloads/stream_m78.mp4")

# Merge them with FFmpeg
out_merged = "downloads/merged_with_audio.mp4"
merge_cmd = [FFMPEG_EXE, "-y", "-i", "downloads/stream_m367.mp4", "-i", "downloads/stream_m78.mp4", "-c", "copy", out_merged]
res = subprocess.run(merge_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
if res.returncode == 0 and os.path.exists(out_merged):
    print(f"\n🎉 SUCCESS! Merged file saved to {out_merged} (Size: {os.path.getsize(out_merged)} bytes)")
    check_info(out_merged)
