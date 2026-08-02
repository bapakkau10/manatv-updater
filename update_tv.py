import os
import time
import requests
from playwright.sync_api import sync_playwright

def update_cloudflare_kv(key_name, m3u8_link):
    ACCOUNT_ID = os.environ.get("CF_ACCOUNT_ID")
    NAMESPACE_ID = os.environ.get("CF_NAMESPACE_ID")
    API_TOKEN = os.environ.get("CF_API_TOKEN")

    kv_url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/storage/kv/namespaces/{NAMESPACE_ID}/values/{key_name}"
    kv_headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "text/plain"
    }
    
    resp = requests.put(kv_url, data=m3u8_link, headers=kv_headers)
    if resp.status_code == 200:
        print(f"[{key_name}] Berjaya dikemaskini ke Cloudflare KV!")
    else:
        print(f"[{key_name}] Gagal simpan ke KV: {resp.text}")

def main():
    channels = {
        "tv3": "https://watch.tonton.com.my/live/tv3",
        "tv9": "https://watch.tonton.com.my/live/tv9",
        "8tv": "https://watch.tonton.com.my/live/8tv"
    }

    with sync_playwright() as p:
        # Guna resolusi skrin standard supaya elemen video nampak
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()

        for key_name, url in channels.items():
            captured_links = []

            def handle_request(intercepted_request):
                req_url = intercepted_request.url
                # Tangkap apa sahaja pautan yang mengandungi .m3u8
                if ".m3u8" in req_url:
                    if req_url not in captured_links:
                        captured_links.append(req_url)

            page.on("request", handle_request)

            print(f"Sedang buka: {url}...")
            try:
                page.goto(url, timeout=60000, wait_until="domcontentloaded")
                
                # Tunggu beberapa saat dan cuba klik pada bahagian tengah skrin/video untuk cetuskan pemain
                time.sleep(5)
                try:
                    page.mouse.click(640, 400)
                except Exception:
                    pass
                
                # Tunggu stream dimuatkan dan permintaan rangkaian berlaku
                time.sleep(10)
            except Exception as e:
                print(f"[{key_name}] Error loading page: {e}")

            # Pilih pautan m3u8 terbaik (biasanya master m3u8 tiada perkataan 'chunks' atau paling panjang)
            valid_links = [l for l in captured_links if "chunks" not in l]
            if not valid_links:
                valid_links = captured_links # Kalau tak jumpa, ambil apa sahaja yang ada

            if valid_links:
                # Ambil pautan master m3u8 (biasanya yang paling pendek atau unik untuk manifest induk)
                best_link = min(valid_links, key=len)
                print(f"[{key_name}] Jumpai M3u8: {best_link}")
                update_cloudflare_kv(key_name, best_link)
            else:
                print(f"[{key_name}] M3u8 tidak dijumpai.")

            page.remove_listener("request", handle_request)

        browser.close()

if __name__ == "__main__":
    main()
