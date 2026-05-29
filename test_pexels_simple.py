import requests
import os

PEXELS_API_KEY = "Cw11dvrPt7hX0XZVOohVAxh082iq357pXN5HXNyiYwwBxrcaEm9bxzxN"

print("Testing Pexels API in Python...")
print("="*60)

headers = {"Authorization": PEXELS_API_KEY}
url = "https://api.pexels.com/v1/search?query=aries+zodiac&per_page=3"

try:
    response = requests.get(url, headers=headers, timeout=30)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        photos = data.get("photos", [])
        print(f"Found {len(photos)} photos!")
        
        if photos:
            # Download first photo
            img_url = photos[0]["src"]["large"]
            img_data = requests.get(img_url, timeout=30).content
            
            os.makedirs("images/aries", exist_ok=True)
            output_path = "images/aries/test_pexels.jpg"
            
            with open(output_path, "wb") as f:
                f.write(img_data)
            
            print(f"[OK] Downloaded test image: {output_path}")
            print(f"     Size: {len(img_data)} bytes")
            print(f"     Photographer: {photos[0]['photographer']}")
            print("\nPEXELS API WORKS! No watermarks!")
        else:
            print("No photos found in response")
    else:
        print(f"Error response: {response.text}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("="*60)