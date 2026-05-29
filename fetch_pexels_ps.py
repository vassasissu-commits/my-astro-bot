import subprocess
import os
import json
import requests

PEXELS_API_KEY = "Cw11dvrPt7hX0XZVOohVAxh082iq357pXN5HXNyiYwwBxrcaEm9bxzxN"

def fetch_pexels_powershell(sign: str, count: int = 10):
    """Use PowerShell to fetch from Pexels (since it works there)"""
    output_dir = f"images/{sign}"
    os.makedirs(output_dir, exist_ok=True)
    
    queries = {
        "aries": "ram zodiac fire",
        "taurus": "bull zodiac nature",
        "gemini": "twins zodiac air",
        "cancer": "crab zodiac water",
        "leo": "lion zodiac gold",
        "virgo": "maiden zodiac earth",
        "libra": "scales zodiac pink",
        "scorpio": "scorpion zodiac dark",
        "sagittarius": "archer zodiac purple",
        "capricorn": "goat zodiac mountain",
        "aquarius": "water bearer zodiac blue",
        "pisces": "fish zodiac ocean"
    }
    
    query = queries.get(sign, sign)
    url = f"https://api.pexels.com/v1/search?query={query}&per_page={count}&orientation=vertical"
    
    print(f"Fetching from Pexels via PowerShell: {query}...")
    
    # Use PowerShell to make the request (bypassing Python requests issue)
    ps_script = f"""
$headers = @{{Authorization = "{PEXELS_API_KEY}"}}
$response = Invoke-RestMethod -Uri "{url}" -Headers $headers -Method Get
$response | ConvertTo-Json -Depth 10 | Out-File -FilePath "pexels_temp.json" -Encoding UTF8
"""
    
    try:
        # Save PowerShell script
        with open("temp_pexels.ps1", "w", encoding="utf-8") as f:
            f.write(ps_script)
        
        # Execute PowerShell script
        result = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", "temp_pexels.ps1"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Read response
        if os.path.exists("pexels_temp.json"):
            with open("pexels_temp.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            
            photos = data.get("photos", [])
            print(f"  Found {len(photos)} photos")
            
            for i, photo in enumerate(photos[:count]):
                img_url = photo["src"]["large"]
                img_data = requests.get(img_url, timeout=30).content
                output_path = f"{output_dir}/{sign}_pexels_{i}.jpg"
                
                with open(output_path, "wb") as f:
                    f.write(img_data)
                print(f"  Saved: {output_path}")
            
            # Cleanup
            os.remove("pexels_temp.json")
            os.remove("temp_pexels.ps1")
            return True
        else:
            print(f"  PowerShell error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"  Error: {e}")
        return False

if __name__ == "__main__":
    import sys
    sign = sys.argv[1] if len(sys.argv) > 1 else "aries"
    fetch_pexels_powershell(sign, count=5)
    print(f"\nImages ready in: images/{sign}/")