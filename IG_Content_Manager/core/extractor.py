# Media download & transcription
import yt_dlp
import os
import re
import urllib.request

def get_video_intel(url, rotator):
    # Clean URL to extract shortcode correctly
    clean_url = url.split("?")[0].rstrip("/")
    shortcode = clean_url.split("/")[-1]
    path = f"downloads/{shortcode}.mp4"
    
    # Download Strategy: Try Video -> Convert Fallback -> Metadata Only
    print(f"   ⬇️ Processing: {clean_url}")
    
    caption = ""
    downloaded_path = None
    image_paths = []
    is_video = False
    
    # 1. Determine Content Type (Video vs Image)
    try:
        ydl_opts_meta = {'quiet': True, 'no_warnings': True}
        with yt_dlp.YoutubeDL(ydl_opts_meta) as ydl:
            # We catch errors here to detect 'no video' scenarios early
            try:
                info = ydl.extract_info(url, download=False)
                caption = info.get('description', '')
                if info.get('_type') == 'video' or 'formats' in info:
                     is_video = True
                else:
                     is_video = False
            except Exception as e:
                # If extract_info crashes, check if it's the "no video" error
                if "no video in this post" in str(e).lower():
                    print("   ℹ️ 'No video' detected. Treating as valid static post.")
                    is_video = False
                else:
                    raise e # Re-raise if it's something else
                 
    except Exception as e:
        print(f"   ⚠️ metadata/download error: {e}")
        return "[Error extracting content]", "", []

    # 2. Download Content
    try:
        if is_video:
             # Video Download
             path = f"downloads/{shortcode}.mp4"
             ydl_opts_download = {'outtmpl': path, 'quiet': True, 'no_warnings': True}
             print(f"   ⬇️ Downloading Video to {path}...")
             with yt_dlp.YoutubeDL(ydl_opts_download) as ydl:
                 ydl.download([url])
             downloaded_path = path 
        else:
            # Static/Image Download
            print("   📸 Static Post detected. Downloading images...")
            
            # Create a subfolder for this post
            post_folder = f"downloads/{shortcode}"
            os.makedirs(post_folder, exist_ok=True)
            
            # Template for images: downloads/shortcode/img_01.jpg
            image_template = f"{post_folder}/img_%(autonumber)02d"
            
            # ATTEMPT 1: Try to download as a regular "video" (which works for carousels/images often)
            ydl_opts_img = {
                'outtmpl': f"{image_template}", 
                'quiet': True, 
                'no_warnings': True,
                'ignoreerrors': True,
            }
            try:
                with yt_dlp.YoutubeDL(ydl_opts_img) as ydl:
                    ydl.download([url])
            except:
                pass
            
            # Find downloaded images in the subfolder
            for file in os.listdir(post_folder):
                if file.startswith("img_") and file.endswith(('.jpg', '.png', '.webp')):
                        image_paths.append(os.path.join(post_folder, file))

            # ATTEMPT 2: Fallback to Thumbnail extraction if main download failed (Common for single images)
            if not image_paths:
                print("   ⚠️ Main download failed. Trying thumbnail extraction...")
                ydl_opts_thumb = {
                    'outtmpl': f"{post_folder}/img_01", # Force single filename for thumb
                    'quiet': True, 
                    'no_warnings': True,
                    'writethumbnail': True,
                    'skip_download': True,
                    'ignoreerrors': True
                }
                try:
                    with yt_dlp.YoutubeDL(ydl_opts_thumb) as ydl:
                        ydl.download([url])
                except:
                    pass
                
                # Check again
                for file in os.listdir(post_folder):
                    if (file.startswith("img_") or "webp" in file or "jpg" in file) and file.endswith(('.jpg', '.png', '.webp')):
                         full_path = os.path.join(post_folder, file)
                         if full_path not in image_paths:
                             image_paths.append(full_path)
            
            # ATTEMPT 3: Manual Redirect Check (Last Resort for "No Video" errors)
            if not image_paths:
                print("   ⚠️ Thumbnail extraction failed. Attempting /media/?size=l fallback...")
                try:
                    # Construct media URL
                    media_url = f"{url.rstrip('/')}/media/?size=l"
                    
                    # Basic request with User-Agent
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                    req = urllib.request.Request(media_url, headers=headers)
                    
                    with urllib.request.urlopen(req) as response:
                        final_url = response.geturl()
                        if ".jpg" in final_url or ".webp" in final_url:
                             fallback_path = f"{post_folder}/img_fallback.jpg"
                             with open(fallback_path, 'wb') as f:
                                 f.write(response.read())
                             
                             image_paths.append(fallback_path)
                             print(f"   ✅ Fetched fallback image via redirect: {fallback_path}")
                        else:
                             print(f"   ❌ Fallback redirect failed (non-image): {final_url}")

                except Exception as e:
                    print(f"   ❌ Fallback failed: {e}")

            if not image_paths:
                print("   ⚠️ No images found after all attempts.")
            else:
                print(f"   ✅ Found {len(image_paths)} images in {post_folder}")
            
            # 3. Try Downloading Audio (if present in static post)
            print("   🎵 Checking for audio in static post...")
            # We save audio as 'shortcode.m4a' inside the same folder
            audio_path_template = f"{post_folder}/{shortcode}" 
            ydl_opts_audio = {
                'outtmpl': audio_path_template,
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'm4a',
                }],
                'quiet': True,
                'no_warnings': True,
                'ignoreerrors': True,
            }
            try:
                with yt_dlp.YoutubeDL(ydl_opts_audio) as ydl:
                    ydl.download([url])
                
                potential_audio = f"{post_folder}/{shortcode}.m4a"
                if os.path.exists(potential_audio):
                        downloaded_path = potential_audio # Use this for transcription!
                        print(f"   ✅ Audio downloaded: {potential_audio}")
            except Exception as e:
                pass

    except Exception as e:
        print(f"   ⚠️ Download error: {e}")
        return "[Error downloading]", "", []

    # 2. Transcribe (Only if we have a file)
    transcript = ""
    if downloaded_path and os.path.exists(downloaded_path):
        print("   🎙️ Transcribing audio...")
        client = rotator.get_client()
        try:
            with open(downloaded_path, "rb") as f:
                transcript = client.audio.transcriptions.create(
                    file=(downloaded_path, f.read()), 
                    model="whisper-large-v3-turbo"
                ).text
            print("   ✅ Transcription complete.")
        except Exception as e:
            # Catch "no audio track" (400) or other API errors
            print(f"   ⚠️ Transcription skipped/failed (likely silent or static): {e}")
            transcript = ""
    else:
        print("   ⏭️ Skipping transcription (No video file).")

    return caption, transcript, image_paths