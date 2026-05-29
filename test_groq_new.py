from groq import Groq
import os

# New API key from user
api_key = "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"

print("Testing new Groq API key...")
print("="*60)

try:
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": "Привет! Напиши 1 предложение про Овнов на русском"}],
        model="llama3-70b-8192",
        max_tokens=50
    )
    print("[OK] Groq API работает!")
    print(f"Response: {response.choices[0].message.content}")
    print("="*60)
    print("\nSuccess! Now we can generate scripts automatically.")
except Exception as e:
    print(f"[ERROR] {e}")
    print("="*60)