import os
import time
import requests
from playwright.sync_api import sync_playwright

CLOUDFLARE_CONFIG = {
    "ACCOUNT_ID": "810e7bd19b4f27a6bccc0337dfe74289",
    "NAMESPACE_ID": "174e94b1a1ad4b098a2f719f7614d8ec",
    "API_TOKEN": "6tpyeHpdanMot48YKEyP1OBM5h_VveVNjH1OxJlU"
}

def update_cloudflare_kv(key_name, m3u8_link):
    ACCOUNT_ID = CLOUDFLARE_CONFIG["ACCOUNT_ID"]
    NAMESPACE_ID = CLOUDFLARE_CONFIG["NAMESPACE_ID"]
    API_TOKEN = CLOUDFLARE_CONFIG["API_TOKEN"]

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
        browser = p.chromium.launch_persistent_context(
            user_data_dir="./tonton_session",
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage"
            ],
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = browser.new_page()

        for key_name, url in channels.items():
            found_links = {}

            def handle_response(response):
                resp_url = response.url
                if ".m3u8" in resp_url and "bpkio_serviceid" in resp_url:
                    # Semak kod resolusi yang dikesan
                    for res_code in ["04", "03", "02", "01"]:
                        if f"/{res_code}.m3u8" in resp_url:
                            found_links[res_code] = resp_url
                            break

            page.on("response", handle_response)

            print(f"Sedang akses {key_name}: {url}...")
            try:
                page.goto(url, timeout=60000, wait_until="networkidle")
                
                start_time = time.time()
                # Tunggu sehingga sekurang-kurangnya satu resolusi dijumpai atau masa tamat
                while len(found_links) == 0 and (time.time() - start_time) < 25:
                    time.sleep(1)
                    try:
                        page.mouse.click(640, 400)
                    except Exception:
                        pass
            except Exception as e:
                print(f"[{key_name}] Error: {e}")

            # Auto-select: Utamakan resolusi tertinggi yang tersedia (04 > 03 > 02 > 01)
            selected_link = None
            chosen_res = None
            for res_code in ["04", "03", "02", "01"]:
                if res_code in found_links:
                    selected_link = found_links[res_code]
                    chosen_res = res_code
                    break

            if selected_link:
                print(f"[{key_name}] Auto-pilih resolusi [{chosen_res}]: {selected_link}")
                update_cloudflare_kv(key_name, selected_link)
            else:
                print(f"[{key_name}] Gagal dapatkan sebarang pautan m3u8.")

            page.remove_listener("response", handle_response)
            time.sleep(2)

        print("\nSemua saluran selesai diproses.")
        browser.close()

if __name__ == "__main__":
    main()
