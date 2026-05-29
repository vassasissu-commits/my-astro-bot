import os
import requests
import shutil
from pathlib import Path

# ========== CONFIGURATION ==========
PEXELS_API_KEY = "Cw11dvrPt7hX0XZVOohVAxh082iq357pXN5HXNyiYwwBxrcaEm9bxzxN"
PIXABAY_API_KEY = "55480657-d26f6d3deeb911fb71ae92716"

def get_output_dir(sign: str) -> str:
    return f"images/{sign}"

def get_local_dir(sign: str) -> str:
    return f"local_images/{sign}"

# ========== FREE IMAGE SOURCES ==========
# 1. Pexels API: https://www.pexels.com/api/ (works! tested)
# 2. Pixabay API: https://pixabay.com/api/docs/ (free, no watermarks)
# 3. Local images: Place your own images in local_images/{sign}/
# 4. Hugging Face: 1000 req/month (model access issues, skip for now)

def fetch_from_pexels(sign: str, count: int = 10) -> bool:
    """Fetch high-quality stock photos from Pexels (NO watermarks, free)"""
    output_dir = get_output_dir(sign)
    os.makedirs(output_dir, exist_ok=True)
    
    # Search queries for each zodiac sign
    queries = {
        "aries": "ram zodiac fire dynamic red orange",
        "taurus": "bull zodiac nature green calm earth",
        "gemini": "twins zodiac air blue silver sky",
        "cancer": "crab zodiac water blue silver ocean",
        "leo": "lion zodiac gold yellow majestic sun",
        "virgo": "maiden zodiac earth green nature harvest",
        "libra": "scales zodiac pink balance elegant",
        "scorpio": "scorpion zodiac dark red intense night",
        "sagittarius": "archer zodiac purple bow arrow dynamic",
        "capricorn": "goat zodiac mountain grey stable snow",
        "aquarius": "water bearer zodiac blue electric flow",
        "pisces": "fish zodiac teal ocean flowing water"
    }
    
    query = queries.get(sign, f"{sign} zodiac")
    url = f"https://api.pexels.com/v1/search?query={query}&per_page={count}&orientation=vertical"
    
    headers = {"Authorization": PEXELS_API_KEY}
    
    try:
        print(f"Fetching from Pexels: {query}...")
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            photos = response.json().get("photos", [])
            print(f"  Found {len(photos)} photos")
            
            for i, photo in enumerate(photos[:count]):
                img_url = photo["src"]["large"]
                img_data = requests.get(img_url, timeout=30).content
                output_path = f"{output_dir}/{sign}_pexels_{i}.jpg"
                
                with open(output_path, "wb") as f:
                    f.write(img_data)
                print(f"  Saved: {output_path}")
            
            return True
        else:
            print(f"  Pexels error: {response.status_code}")
            return False
    except Exception as e:
        print(f"  Pexels error: {e}")
        return False

def fetch_from_pixabay(sign: str, count: int = 10) -> bool:
    """Fetch images from Pixabay API (free, no watermarks)"""
    output_dir = get_output_dir(sign)
    os.makedirs(output_dir, exist_ok=True)
    
    query = f"{sign} zodiac"
    url = f"https://pixabay.com/api/?key={PIXABAY_API_KEY}&q={query}&per_page={count}&image_type=photo"
    
    try:
        print(f"Fetching from Pixabay: {query}...")
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            hits = response.json().get("hits", [])
            print(f"  Found {len(hits)} images")
            
            for i, img in enumerate(hits[:count]):
                img_url = img["largeImageURL"]
                img_data = requests.get(img_url, timeout=30).content
                output_path = f"{output_dir}/{sign}_pixabay_{i}.jpg"
                
                with open(output_path, "wb") as f:
                    f.write(img_data)
                print(f"  Saved: {output_path}")
            
            return True
        else:
            print(f"  Pixabay error: {response.status_code}")
            return False
    except Exception as e:
        print(f"  Pixabay error: {e}")
        return False

def copy_local_images(sign: str) -> bool:
    """Copy images from local folder (your own images)"""
    local_dir = get_local_dir(sign)
    output_dir = get_output_dir(sign)
    
    if not os.path.exists(local_dir):
        return False
    
    os.makedirs(output_dir, exist_ok=True)
    images = list(Path(local_dir).glob("*.png")) + list(Path(local_dir).glob("*.jpg")) + list(Path(local_dir).glob("*.jpeg"))
    
    if not images:
        return False
    
    print(f"Copying local images from {local_dir}...")
    for i, img_path in enumerate(images[:10]):
        output_path = f"{output_dir}/{sign}_local_{i}{img_path.suffix}"
        shutil.copy(img_path, output_path)
        print(f"  Copied: {img_path.name}")
    
    return True

def save_images(sign: str, use_local_first: bool = False):
    """
    Get images for a zodiac sign.
    Priority: 1. Local images (if use_local_first=True)
              2. Pexels API (best quality, no watermarks)
              3. Pixabay API (backup)
    """
    print(f"\n{'='*60}")
    print(f"Getting images for {sign.upper()}...")
    print(f"{'='*60}")
    
    # Try local images first if requested
    if use_local_first:
        if copy_local_images(sign):
            print(f"[OK] Using local images for {sign}")
            return
    
    # Try Pexels (best option - tested, works)
    if fetch_from_pexels(sign, count=10):
        print(f"[OK] Images from Pexels saved for {sign}")
        return
    
    # Try Pixabay as backup
    print("Pexels failed, trying Pixabay...")
    if fetch_from_pixabay(sign, count=10):
        print(f"[OK] Images from Pixabay saved for {sign}")
        return
    
    print("[ERROR] All image sources failed!")

if __name__ == "__main__":
    import sys
    sign = sys.argv[1] if len(sys.argv) > 1 else "aries"
    use_local = "--local" in sys.argv
    
    save_images(sign, use_local_first=use_local)
    
    print(f"\nImages ready in: images/{sign}/")
    print("These are high-quality photos with NO watermarks!")
