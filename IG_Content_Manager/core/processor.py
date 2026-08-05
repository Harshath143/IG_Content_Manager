from groq import Groq

import base64

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def generate_metadata(caption, transcript, categories, rotator, image_paths=[]):
    client = rotator.get_client()
    
    # Base Prompt
    text_prompt = f"""
    Act as a Senior Content Manager. Synthesize this content perfectly.
    CAPTION: {caption}
    TRANSCRIPT: {transcript if transcript else "(No transcript/Static Post)"}
    ALLOWED CATEGORIES: {categories}

    RULES:
    1. TITLE: Engaging, between 30 and 60 words. DO NOT include the words "Unlock" or "Unlocking".
    2. DESCRIPTION: More than 8 lines. Insightful, not repetitive.
    3. KEYWORDS: More than 6 relevant SEO keywords (comma-separated).
    4. CATEGORIES: Select MORE THAN 6 from the ALLOWED list.

    OUTPUT FORMAT:
    TITLE: [text]
    DESCRIPTION: [text]
    KEYWORDS: [text]
    CATEGORIES: [text]
    """

    messages = [{"role": "user", "content": text_prompt}]
    model = "llama-3.3-70b-versatile"

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.2 
    )

    return response.choices[0].message.content