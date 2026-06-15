import os
import pandas as pd
import yt_dlp
from core.rotator import APIKeyRotator
from tqdm import tqdm

from core.extractor import get_video_intel
from core.processor import generate_metadata

# --- CONFIGURATION ---
KEYS = ["GROQ_KEY_1", "GROQ_KEY_2", "GROQ_KEY_3", "GROQ_KEY_4", "GROQ_KEY_5"]
rotator = APIKeyRotator(KEYS)
DOWNLOAD_PATH = "downloads"
os.makedirs(DOWNLOAD_PATH, exist_ok=True)

import re

def parse_ai_output(url, raw_output):
    """Parses the raw AI text response into a structured dict using regex."""
    # Default structure
    result = {
        "Link": url,
        "Title": "",
        "Description": "",
        "Keywords": "",
        "Categories": "",
        "RawOutput": raw_output
    }
    
    try:
        if not raw_output:
            print(f"⚠️ Empty AI output for {url}")
            return result

        # Define flexible patterns (case-insensitive, optional bolding)
        patterns = {
            "Title": r"(?i)\**TITLE\**:?\s*(.*)",
            "Description": r"(?i)\**DESCRIPTION\**:?\s*(.*)",
            "Keywords": r"(?i)\**KEYWORDS\**:?\s*(.*)",
            "Categories": r"(?i)\**CATEGORIES\**:?\s*(.*)"
        }

        def clean_val(text):
            """Removes markdown bolding, quotes, and extra whitespace."""
            if not text: return ""
            # Remove **bold** markers
            text = text.replace("**", "")
            # Remove leading/trailing quotes
            text = text.strip("'\"")
            # Collapse multiple spaces
            text = re.sub(r'\s+', ' ', text)
            return text.strip()

        # Cleaning regex input
        clean_text = raw_output.strip()
        
        # 1. Title
        title_match = re.search(patterns["Title"], clean_text)
        if title_match:
            result["Title"] = clean_val(title_match.group(1))

        # 2. Keywords
        kw_match = re.search(patterns["Keywords"], clean_text)
        if kw_match:
            result["Keywords"] = clean_val(kw_match.group(1))

        # 3. Categories
        cat_match = re.search(patterns["Categories"], clean_text)
        if cat_match:
            result["Categories"] = clean_val(cat_match.group(1))

        # 4. Description (Multiline handling is trickier)
        desc_match = re.search(patterns["Description"], clean_text)
        if desc_match:
            start_idx = desc_match.end()
            next_indices = []
            for key in ["Keywords", "Categories"]:
                m = re.search(patterns[key], clean_text)
                if m and m.start() > start_idx:
                    next_indices.append(m.start())
            
            end_idx = min(next_indices) if next_indices else len(clean_text)
            desc_content = clean_text[start_idx:end_idx].strip()
            
            # Prepend inline description if present
            inline_desc = desc_match.group(1).strip()
            if inline_desc and inline_desc not in desc_content:
                 desc_content = inline_desc + "\n" + desc_content
            
            # Clean description lines individually
            clean_lines = [clean_val(line) for line in desc_content.splitlines() if line.strip()]
            result["Description"] = "\n".join(clean_lines[:4])

        if not result["Title"] and not result["Description"]:
             print(f"⚠️ Regex parsing failed. Raw output start: {clean_text[:50]}...")

        return result
        
    except Exception as e:
        print(f"❌ Error parsing AI output: {e}")
        return result

def main():
    # Load Input Data
    try:
        # Check for Excel first, then CSV
        if os.path.exists("data/links.xlsx"):
            links_df = pd.read_excel("data/links.xlsx")
            print("✅ Loaded links from data/links.xlsx")
        elif os.path.exists("data/links.csv"):
            links_df = pd.read_csv("data/links.csv")
            print("✅ Loaded links from data/links.csv")
        else:
            raise FileNotFoundError("Could not find 'data/links.xlsx' or 'data/links.csv'")

        cats_df = pd.read_excel("data/categories.xlsx")
    except Exception as e:
        print(f"❌ File Error: {e}")
        return

    cat_list = cats_df['category'].tolist()

    # Load Existing Results (Resumability)
    output_file = "output/Final_Report.xlsx"
    processed_urls = set()
    final_results = []

    if os.path.exists(output_file):
        try:
            existing_df = pd.read_excel(output_file)
            processed_urls = set(existing_df['Link'].astype(str).str.strip())
            final_results = existing_df.to_dict('records')
            print(f"🔄 Resuming... Found {len(final_results)} items already processed.")
        except Exception as e:
            print(f"⚠️ Could not load existing report: {e}")

    for url in tqdm(links_df['link'], desc="🚀 Processing Instagram Data"):
        url_str = str(url).strip()
        
        # Skip if already processed
        if url_str in processed_urls:
            continue

        try:
            # 1. Extract (Download & Transcribe & Images)
            caption, transcript, image_paths = get_video_intel(url_str, rotator)
            
            # 2. Process (AI Synthesis)
            raw_ai_output = generate_metadata(caption, transcript, cat_list, rotator, image_paths)
            
            # 3. Parse & Store
            row = parse_ai_output(url_str, raw_ai_output)
            final_results.append(row)
            
            # INCREMENTAL SAVE (Safety) - Critical Step
            import time
            while True:
                try:
                    pd.DataFrame(final_results).to_excel(output_file, index=False)
                    processed_urls.add(url_str) # Only mark as processed if save succeeded
                    print(f"   💾 Saved data for {url_str}")
                    break
                except PermissionError:
                    print(f"   ❌ CRITICAL ERROR: Could not save to {output_file}. Please close it in Excel! Retrying in 5 seconds...")
                    time.sleep(5)
                except Exception as e:
                    print(f"   ❌ Error saving data: {e}")
                    break

        except Exception as e:
            print(f"Error processing {url}: {e}")

    print("\n✅ All Content Processed and Exported.")

if __name__ == "__main__":
    main()