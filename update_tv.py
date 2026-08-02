import os
import time
import requests
from playwright.sync_api import sync_playwright

def update_cloudflare_kv(key_name, m3u8_link):
    # Membaca maklumat rahsia daripada GitHub Secrets
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
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for key_name, url in channels.items():
            found_master_m3u8 = None

            def handle_request(intercepted_request):
                nonlocal found_master_m3u8
                req_url = intercepted_request.url
                # Menapis pautan m3u8 utama (master playlist) yang membenarkan pilihan resolusi manual
                if ".m3u8" in req_url and "chunks" not in req_url:
                    found_master_m3u8 = req_url

            page.on("request", handle_request)

            print(f"Sedang buka: {url}...")
            try:
                page.goto(url, timeout=60000, wait_until="networkidle")
                time.sleep(10)
            except Exception as e:
                print(f"[{key_name}] Error loading page: {e}")

            if found_master_m3u8:
                print(f"[{key_name}] Jumpai Master M3u8: {found_master_m3u8}")
                update_cloudflare_kv(key_name, found_master_m3u8)
            else:
                print(f"[{key_name}] Master M3u8 tidak dijumpai.")

            page.remove_listener("request", handle_request)

        browser.close()

if __name__ == "__main__":
    main()
