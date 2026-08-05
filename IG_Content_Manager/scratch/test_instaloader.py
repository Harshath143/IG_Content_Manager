import instaloader
import os

L = instaloader.Instaloader(
    download_pictures=True,
    download_videos=True,
    download_video_thumbnails=False,
    download_geotags=False,
    download_comments=False,
    save_metadata=False
)

urls = [
    "https://www.instagram.com/p/Da5xwapDGIC/?igsh=MWFoNTFqNHlyaHdyYQ==",
    "https://www.instagram.com/p/Da03ym3jSaJ/?igsh=d3FpN2ZybnowM2Yx",
    "https://www.instagram.com/reel/Dak9akADi4e/?igsh=MWVjbTBndjc3ZjYx",
    "https://www.instagram.com/reel/DbFZWADTgwf/?igsh=eXEzdzJvZDVpbHJr",
    "https://www.instagram.com/reel/DbJ-wX6AWQ4/?igsh=MW44NWQyMjNwaW5rbw=="
]

for url in urls:
    shortcode = url.split("?")[0].rstrip("/").split("/")[-1]
    print(f"\n--- Testing Shortcode: {shortcode} ---")
    try:
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        print(f"Caption: {post.caption[:150] if post.caption else 'None'}...")
        print(f"Is Video: {post.is_video}")
        print(f"Video URL: {post.video_url if post.is_video else 'None'}")
        print(f"Image URL: {post.url}")
        print(f"TypeName: {post.typename}")
    except Exception as e:
        print(f"Instaloader error for {shortcode}: {e}")
