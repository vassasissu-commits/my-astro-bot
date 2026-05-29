import os
import requests
from datetime import datetime

# Get free token from: https://huggingface.co/settings/tokens
HF_API_TOKEN = os.getenv("HF_API_TOKEN", "YOUR_TOKEN_HERE")
# Correct model paths for Hugging Face Inference API
MODEL_ID = "stabilityai/stable-diffusion-3.5-medium"  # SD3.5 Medium (better availability)

def test_image_generation():
    """Test Hugging Face SD3.5 image generation (free tier)"""
    sign = "aries"
    output_dir = f"images/{sign}"
    os.makedirs(output_dir, exist_ok=True)
    
    prompt = "fiery background, ram symbol, dynamic, red and orange colors, no watermarks, astrology theme, 512x512"
    
    print("Testing Hugging Face SD3.5 image generation...")
    print(f"Prompt: {prompt}")
    
    try:
        headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
        payload = {"inputs": prompt}
        
        print("Sending request to Hugging Face API...")
        response = requests.post(
            f"https://api-inference.huggingface.co/models/{MODEL_ID}",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            output_path = f"{output_dir}/test_aries.png"
            with open(output_path, "wb") as f:
                f.write(response.content)
            print(f"[OK] Image saved: {output_path}")
            print("Check the image - if it's good, we can generate 10/day for free!")
            return True
        elif response.status_code == 503:
            print("[INFO] Model is loading, wait 20 seconds and try again...")
            print("This is normal for free tier - model needs to wake up")
            return False
        else:
            print(f"[ERROR] Status {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

if __name__ == "__main__":
    if HF_API_TOKEN == "YOUR_TOKEN_HERE":
        print("ERROR: Set HF_API_TOKEN environment variable first!")
        print("Get free token: https://huggingface.co/settings/tokens")
    else:
        test_image_generation()