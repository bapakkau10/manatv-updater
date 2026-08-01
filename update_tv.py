import os
import requests

ACCOUNT_ID = os.environ.get("CF_ACCOUNT_ID")
NAMESPACE_ID = os.environ.get("CF_NAMESPACE_ID")
API_TOKEN = os.environ.get("CF_API_TOKEN")

# Senarai channel beserta endpoint/slug asal mereka dalam sistem mana2.my
CHANNELS = {
    "siaraTV": "siara-tv",
    "fmTV": "free-movies",
    "msTV": "mysport",
    "ahTV": "tv-alhijrah",
    "slTV": "selangor-tv",
    "twTV": "taiwanplus",
    "ikTV": "tv-ikim",
    "5TV": "tv5",
    "bTV": "borneo-tv"
}

def update_kv(key_name, m3u8_url):
    url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/storage/kv/namespaces/{NAMESPACE_ID}/values/{key_name}"
    headers = {"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "text/plain"}
    response = requests.put(url, data=m3u8_url, headers=headers)
    return response.status_code == 200

def main():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://mana2.my/"
    }

    for key_name, slug in CHANNELS.items():
        print(f"\nSedang proses: {key_name}")
        try:
            # Cuba tembak terus ke page channel untuk ekstrak data atau API dalaman
            target_url = f"https://mana2.my/channel/{slug}"
            res = requests.get(target_url, headers=headers, timeout=30)
            
            if res.status_code == 200:
                html_content = res.text
                
                # Cari pautan m3u8 secara terus dalam source code HTML/JS halaman tersebut
                import re
                m3u8_matches = re.findall(r'https?://[^\s<>"]+?\.m3u8[^\s<>"]*', html_content)
                
                if m3u8_matches:
                    # Ambil pautan chunks yang sah jika ada, atau mana-mana m3u8 terbaik
                    chunks_links = [l for l in m3u8_matches if "chunks.m3u8" in l]
                    best_link = max(chunks_links, key=len) if chunks_links else max(m3u8_matches, key=len)
                    
                    print(f"Jumpa Link M3U8 Direct: {best_link}")
                    
                    if ACCOUNT_ID and NAMESPACE_ID and API_TOKEN:
                        success = update_kv(key_name, best_link)
                        if success:
                            print(f"Berjaya simpan {key_name} ke Cloudflare KV!")
                        else:
                            print(f"Gagal simpan ke KV untuk {key_name}")
                    else:
                        print("Simulasi sahaja (Tiada KV credentials).")
                else:
                    print(f"Amaran: Tiada pautan m3u8 dijumpai dalam sumber HTML untuk {key_name}")
            else:
                print(f"Gagal akses laman web untuk {key_name} (Status: {res.status_code})")

        except Exception as e:
            print(f"Error pada {key_name}: {e}")

if __name__ == "__main__":
    main()
