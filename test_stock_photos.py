import os
import requests
import json

PEXELS_API_KEY = "Cw11dvrPt7hX0XZVOohVAxh082iq357pXN5HXNyiYwwBxrcaEm9bxzxN"
PIXABAY_API_KEY = "55480657-d26f6d3deeb911fb71ae92716"

def test_pexels(sign="aries"):
    """Test Pexels API for high-quality stock photos (no watermarks via API)"""
    print("="*60)
    print("Testing PEXELS API (high-quality stock photos)")
    print("="*60)
    
    headers = {"Authorization": PEXELS_API_KEY}
    query = f"{sign} zodiac astrology"
    url = f"https://api.pexels.com/v1/search?query={query}&per_page=5"
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            photos = data.get("photos", [])
            print(f"[OK] Found {len(photos)} photos for '{query}'")
            
            # Download first photo
            if photos:
                photo_url = photos[0]["src"]["large"]
                img_response = requests.get(photo_url, timeout=30)
                
                output_dir = f"images/{sign}"
                os.makedirs(output_dir, exist_ok=True)
                output_path = f"{output_dir}/pexels_test.jpg"
                
                with open(output_path, "wb") as f:
                    f.write(img_response.content)
                
                print(f"[OK] Downloaded: {output_path}")
                print(f"     Size: {len(img_response.content)} bytes")
                print(f"     Photographer: {photos[0]['photographer']}")
                print("     NOTE: NO watermarks (proper API usage)")
                return True
        else:
            print(f"[ERROR] Status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

def test_pixabay(sign="aries"):
    """Test Pixabay API for free images (no watermarks)"""
    print("\n" + "="*60)
    print("Testing PIXABAY API (free stock photos)")
    print("="*60)
    
    query = f"{sign} zodiac"
    url = f"https://pixabay.com/api/?key={PIXABAY_API_KEY}&q={query}&per_page=5&image_type=photo"
    
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            hits = data.get("hits", [])
            print(f"[OK] Found {len(hits)} images for '{query}'")
            
            if hits:
                img_url = hits[0]["largeImageURL"]
                img_response = requests.get(img_url, timeout=30)
                
                output_dir = f"images/{sign}"
                os.makedirs(output_dir, exist_ok=True)
                output_path = f"{output_dir}/pixabay_test.jpg"
                
                with open(output_path, "wb") as f:
                    f.write(img_response.content)
                
                print(f"[OK] Downloaded: {output_path}")
                print(f"     Size: {len(img_response.content)} bytes")
                print(f"     User: {hits[0]['user']}")
                print("     NOTE: NO watermarks (free API)")
                return True
        else:
            print(f"[ERROR] Status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

if __name__ == "__main__":
    print("\nTesting FREE image APIs (NO watermarks)...\n")
    test_pexels("aries")
    test_pixabay("aries")
    print("\n" + "="*60)
    print("CHECK THE IMAGES IN: images/aries/")
    print("These are REAL photos - perfect for YouTube/TikTok!")
    print("="*60)