import os
import requests
from playwright.sync_api import sync_playwright

ACCOUNT_ID = os.environ.get("CF_ACCOUNT_ID")
NAMESPACE_ID = os.environ.get("CF_NAMESPACE_ID")
API_TOKEN = os.environ.get("CF_API_TOKEN")

CHANNELS = {
    "siaraTV": "https://mana2.my/channel/siara-tv",
    "fmTV": "https://mana2.my/channel/free-movies",
    "msTV": "https://mana2.my/channel/mysport",
    "ahTV": "https://mana2.my/channel/tv-alhijrah",
    "slTV": "https://mana2.my/channel/selangor-tv",
    "twTV": "https://mana2.my/channel/taiwanplus",
    "ikTV": "https://mana2.my/channel/tv-ikim",
    "5TV": "https://mana2.my/channel/tv5",
    "bTV": "https://mana2.my/channel/borneo-tv"
}

def update_kv(key_name, m3u8_url):
    url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/storage/kv/namespaces/{NAMESPACE_ID}/values/{key_name}"
    headers = {"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "text/plain"}
    response = requests.put(url, data=m3u8_url, headers=headers)
    return response.status_code == 200

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-gpu",
                "--dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--window-size=1920,1080"
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            locale="ms-MY",
            timezone_id="Asia/Kuala_Lumpur"
        )
        
        for key_name, target_url in CHANNELS.items():
            print(f"\nSedang proses: {key_name}")
            page = context.new_page()
            found_links = []

            def handle_request(request):
                if ".m3u8" in request.url:
                    if request.url not in found_links:
                        found_links.append(request.url)

            page.on("request", handle_request)

            try:
                page.goto(target_url, timeout=60000)
                page.wait_for_timeout(3000)
                page.mouse.click(500, 500)
                # Beri masa lebih panjang di GitHub Actions untuk lulus cabaran Cloudflare & load player
                page.wait_for_timeout(20000)

                chunks_links = [l for l in found_links if "chunks.m3u8" in l]

                if chunks_links:
                    best_link = max(chunks_links, key=len)
                    print(f"Jumpa Link CHUNKS Tepat: {best_link}")
                    
                    if ACCOUNT_ID and NAMESPACE_ID and API_TOKEN:
                        success = update_kv(key_name, best_link)
                        if success:
                            print(f"Berjaya simpan {key_name} ke Cloudflare KV!")
                        else:
                            print(f"Gagal simpan ke KV untuk {key_name}")
                    else:
                        print("Simulasi sahaja (Tiada KV credentials).")
                else:
                    print(f"Amaran: Tiada pautan chunks.m3u8 dikesan untuk {key_name}")

            except Exception as e:
                print(f"Error pada {key_name}: {e}")
            finally:
                page.close()
                
        browser.close()

if __name__ == "__main__":
    main()
