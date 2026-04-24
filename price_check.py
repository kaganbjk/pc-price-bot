import os
import re
import json
import hashlib
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

STATE_FILE = "state.json"

OUT_OF_STOCK_WORDS = [
    "stokta yok",
    "stok yok",
    "tükendi",
    "tukendi",
    "satışta değil",
    "satista degil",
    "geçici olarak temin edilemiyor",
    "gecici olarak temin edilemiyor",
    "gelince haber ver",
    "stoklara gelince haber ver",
    "şu anda mevcut değil",
    "su anda mevcut degil",
    "currently unavailable",
    "out of stock",
    "sold out"
]

PRODUCTS = [
    {
        "name": "Colorful RTX 5070 Ti",
        "query": "Colorful RTX 5070 Ti",
        "target_price": 50000,
        "min_price": 35000,
        "include": ["colorful", "5070", "ti"],
        "exclude": [
            "hazır sistem", "hazir sistem", "oyuncu bilgisayarı", "oyuncu bilgisayari",
            "gaming pc", "laptop", "notebook", "ikinci el", "2.el", "2 el",
            "5080", "5070 super", "rtx 5070 12gb"
        ]
    },
    {
        "name": "Ryzen 7 9800X3D",
        "query": "Ryzen 7 9800X3D",
        "target_price": 20000,
        "min_price": 10000,
        "include": ["9800x3d"],
        "exclude": [
            "hazır sistem", "hazir sistem", "oyuncu bilgisayarı", "oyuncu bilgisayari",
            "gaming pc", "laptop", "notebook", "ikinci el", "2.el", "2 el",
            "tray", "fan", "soğutucu", "sogutucu", "7600x3d", "7800x3d", "7950x3d"
        ]
    },
    {
        "name": "Lian Li HydroShift II LCD-S 360CL",
        "query": "Lian Li HydroShift II LCD-S 360CL White",
        "target_price": 8500,
        "min_price": 4000,
        "include": ["lian", "li", "hydroshift", "lcd", "360"],
        "exclude": [
            "hazır sistem", "hazir sistem", "ikinci el", "2.el", "2 el",
            "black", "siyah", "240", "280", "tl", "fan paketi",
            "controller", "kontrolcü", "fansız", "fansiz"
        ]
    },
    {
        "name": "Kioxia Exceria Plus G4 2TB PCIe 5.0 M.2 SSD",
        "query": "Kioxia Exceria Plus G4 LVD10Z002TG8 PCI Express 5.0 2TB M.2 SSD",
        "target_price": 10500,
        "min_price": 5000,
        "include": ["kioxia", "exceria", "plus", "g4", "2tb"],
        "exclude": [
            "hazır sistem", "hazir sistem", "ikinci el", "2.el", "2 el",
            "1tb", "500gb", "sata", "harici", "external", "portable"
        ]
    },
    {
        "name": "MSI MPG B850 Edge TI Wi-Fi AM5 DDR5 ATX",
        "query": "MSI MPG B850 Edge TI WiFi AM5 DDR5 ATX",
        "target_price": 12500,
        "min_price": 5000,
        "include": ["msi", "b850", "edge", "wifi"],
        "exclude": [
            "hazır sistem", "hazir sistem", "ikinci el", "2.el", "2 el",
            "b650", "x870", "x670", "matx", "m-atx", "mini", "itx"
        ]
    },
    {
        "name": "Corsair RM850e Gen5.1 850W White PSU",
        "query": "Corsair RM850e Gen5.1 850W Beyaz Power Supply",
        "target_price": 6500,
        "min_price": 3000,
        "include": ["corsair", "rm850e", "850"],
        "exclude": [
            "hazır sistem", "hazir sistem", "ikinci el", "2.el", "2 el",
            "rm750e", "750w", "rm1000e", "1000w", "siyah", "black",
            "kablo", "cable", "modüler kablo"
        ]
    },
    {
        "name": "ASUS ROG Strix B850-A Gaming Wi-Fi AM5 DDR5 ATX",
        "query": "ASUS ROG Strix B850-A Gaming WiFi AM5 DDR5 ATX",
        "target_price": 12500,
        "min_price": 5000,
        "include": ["asus", "rog", "strix", "b850", "wifi"],
        "exclude": [
            "hazır sistem", "hazir sistem", "ikinci el", "2.el", "2 el",
            "b650", "x870", "x670", "matx", "m-atx", "mini", "itx",
            "b850-f", "b850-e"
        ]
    },
    {
        "name": "MSI MAG A850GL White Gen5 850W PSU",
        "query": "MSI MAG A850GL White Gen5 850W Power Supply",
        "target_price": 6500,
        "min_price": 3000,
        "include": ["msi", "a850gl", "850"],
        "exclude": [
            "hazır sistem", "hazir sistem", "ikinci el", "2.el", "2 el",
            "a750gl", "750w", "a1000gl", "1000w", "siyah", "black",
            "kablo", "cable", "modüler kablo"
        ]
    },
    {
        "name": "Colorful RTX 5080 iGame Ultra W OC",
        "query": "Colorful RTX 5080 iGame Ultra W OC",
        "target_price": 65000,
        "min_price": 55000,
        "include": ["colorful", "5080", "igame", "ultra"],
        "exclude": [
            "hazır sistem", "hazir sistem", "oyuncu bilgisayarı", "oyuncu bilgisayari",
            "gaming pc", "laptop", "notebook", "ikinci el", "2.el", "2 el",
            "5070", "5070 ti", "5090"
        ]
    },
    {
        "name": "Gigabyte RTX 5070 Ti Aero OC 16G",
        "query": "Gigabyte RTX 5070 Ti Aero OC 16G",
        "target_price": 50000,
        "min_price": 35000,
        "include": ["gigabyte", "5070", "ti", "aero"],
        "exclude": [
            "hazır sistem", "hazir sistem", "oyuncu bilgisayarı", "oyuncu bilgisayari",
            "gaming pc", "laptop", "notebook", "ikinci el", "2.el", "2 el",
            "5080", "5070 super", "rtx 5070 12gb", "windforce", "gaming oc", "eagle"
        ]
    }
]

STORES = [
    {"name": "Gaming.gen.tr", "search_url": "https://www.gaming.gen.tr/?s={query}&post_type=product"},
    {"name": "İncehesap", "search_url": "https://www.incehesap.com/arama/?q={query}"},
    {"name": "Sinerji", "search_url": "https://www.sinerji.gen.tr/arama?kelime={query}"},
    {"name": "İtopya", "search_url": "https://www.itopya.com/arama/{query}/"},
    {"name": "Teknobiyotik", "search_url": "https://www.teknobiyotik.com/catalogsearch/result/?q={query}"},
    {"name": "Vatan Bilgisayar", "search_url": "https://www.vatanbilgisayar.com/arama/{query}"},
    {"name": "Inventus", "search_url": "https://inventus.com.tr/mi_products/ProductList.aspx?text={query}"},
    {"name": "GameGaraj", "search_url": "https://www.gamegaraj.com/?s={query}&post_type=product"},
    {"name": "Ebrar Bilgisayar", "search_url": "https://www.ebrarbilgisayar.com/arama?search={query}"},
    {"name": "PcKolik", "search_url": "https://pckolik.com.tr/arama?search={query}"},
    {"name": "Amazon Türkiye", "search_url": "https://www.amazon.com.tr/s?k={query}"},
    {"name": "Hepsiburada", "search_url": "https://www.hepsiburada.com/ara?q={query}"},
    {"name": "N11", "search_url": "https://www.n11.com/arama?q={query}"},
    {"name": "Trendyol", "search_url": "https://www.trendyol.com/sr?q={query}"},
    {"name": "Pazarama", "search_url": "https://www.pazarama.com/arama?q={query}"}
]


def normalize(text):
    text = str(text).lower()
    text = text.replace("ı", "i").replace("İ", "i")
    text = text.replace("\n", " ")
    text = text.replace("\t", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def load_state():
    if not os.path.exists(STATE_FILE):
        return {}

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def parse_price(product, price_text):
    raw = str(price_text)
    raw = raw.replace("₺", "")
    raw = raw.replace("TL", "")
    raw = raw.replace("tl", "")
    raw = raw.replace("TRY", "")
    raw = raw.strip()
    raw = raw.replace(".", "").replace(",", ".")

    nums = re.findall(r"\d+(?:\.\d+)?", raw)

    if not nums:
        return None

    try:
        price = float(nums[0])
    except Exception:
        return None

    min_price = product.get("min_price", 1000)

    if price < min_price:
        return None

    if price > 500000:
        return None

    return price


def extract_prices(product, text):
    patterns = [
        r"\d{1,3}(?:\.\d{3})+(?:,\d{2})?\s*TL",
        r"\d{4,6}(?:,\d{2})?\s*TL",
        r"₺\s*\d{1,3}(?:\.\d{3})+(?:,\d{2})?",
        r"₺\s*\d{4,6}(?:,\d{2})?",
        r"\d{1,3}(?:\.\d{3})+(?:,\d{2})?\s*₺",
        r"\d{4,6}(?:,\d{2})?\s*₺"
    ]

    found = []

    for pattern in patterns:
        for match in re.findall(pattern, text, flags=re.IGNORECASE):
            price = parse_price(product, match)
            if price:
                found.append({
                    "price": price,
                    "price_text": match.strip()
                })

    return found


def has_excluded_word(product, text):
    t = normalize(text)

    for word in product["exclude"]:
        if normalize(word) in t:
            return True

    return False


def has_out_of_stock_word(text):
    t = normalize(text)

    for word in OUT_OF_STOCK_WORDS:
        if normalize(word) in t:
            return True

    return False


def product_soft_matches(product, text):
    t = normalize(text)

    include_hits = 0

    for word in product["include"]:
        if normalize(word) in t:
            include_hits += 1

    if len(product["include"]) <= 2:
        return include_hits == len(product["include"])

    return include_hits >= max(2, len(product["include"]) - 1)


def find_candidate_blocks(product, soup):
    blocks = []
    possible_tags = soup.find_all(["a", "div", "li", "article", "section", "span", "h2", "h3"])

    for tag in possible_tags:
        text = tag.get_text(" ", strip=True)

        if not text:
            continue

        if len(text) < 10:
            continue

        if not product_soft_matches(product, text):
            continue

        current = tag

        for _ in range(4):
            if current is None:
                break

            block_text = current.get_text(" ", strip=True)

            if not block_text:
                current = current.parent
                continue

            if len(block_text) > 1500:
                current = current.parent
                continue

            if not product_soft_matches(product, block_text):
                current = current.parent
                continue

            if has_excluded_word(product, block_text):
                current = current.parent
                continue

            if has_out_of_stock_word(block_text):
                current = current.parent
                continue

            prices = extract_prices(product, block_text)

            if prices:
                blocks.append(block_text)

            current = current.parent

    unique_blocks = []
    seen = set()

    for block in blocks:
        clean = normalize(block)

        if clean in seen:
            continue

        seen.add(clean)
        unique_blocks.append(block)

    return unique_blocks[:20]


def get_best_result_from_blocks(product, store, url, soup):
    blocks = find_candidate_blocks(product, soup)
    candidates = []

    for block in blocks:
        prices = extract_prices(product, block)

        if not prices:
            continue

        cheapest = min(prices, key=lambda item: item["price"])

        candidates.append({
            "product": product["name"],
            "store": store["name"],
            "url": url,
            "price": cheapest["price"],
            "price_text": cheapest["price_text"],
            "source": "block"
        })

    if not candidates:
        return None

    return min(candidates, key=lambda item: item["price"])


def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "disable_web_page_preview": False
    }

    response = requests.post(url, data=data, timeout=20)

    if response.status_code != 200:
        print("Telegram mesaj hatası:", response.text)


def fetch_store(product, store):
    query = quote_plus(product["query"])
    url = store["search_url"].format(query=query)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    }

    try:
        response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
        response.raise_for_status()
    except Exception as e:
        print(f"{product['name']} | {store['name']} hata: {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    for bad in soup(["script", "style", "noscript", "svg"]):
        bad.decompose()

    result = get_best_result_from_blocks(product, store, url, soup)

    if result:
        print(f"{product['name']} | {store['name']}: fiyat yakalandı -> {result['price_text']}")
        return result

    print(f"{product['name']} | {store['name']}: ürün/fiyat yakalanamadı")
    return None


def build_alert_key(product, result):
    raw = f"{product['name']}|{result['store']}|{result['price']}|{result['url']}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def check_product(product, state):
    results = []

    print("\n==============================")
    print(f"Kontrol ediliyor: {product['name']}")
    print(f"Hedef fiyat: {product['target_price']} TL")
    print(f"Minimum gerçekçi fiyat: {product.get('min_price')} TL")

    for store in STORES:
        result = fetch_store(product, store)

        if result:
            results.append(result)

    if not results:
        print(f"{product['name']}: ürün/fiyat bulunamadı. Telegram mesajı gönderilmiyor.")
        return state

    cheapest = min(results, key=lambda item: item["price"])

    print(f"{product['name']} en düşük bulunan sonuç:")
    print(cheapest)

    if cheapest["price"] > product["target_price"]:
        print(f"{product['name']}: fiyat hedefin üstünde. Telegram mesajı gönderilmiyor.")
        return state

    alert_key = build_alert_key(product, cheapest)
    last_alert_key = state.get(product["name"], {}).get("last_alert_key")

    if alert_key == last_alert_key:
        print(f"{product['name']}: bu fiyat daha önce bildirildi. Tekrar mesaj gönderilmiyor.")
        return state

    sorted_results = sorted(results, key=lambda item: item["price"])

    other_results = "\n".join(
        f"- {item['store']}: {item['price_text']} ({item['source']})"
        for item in sorted_results[:5]
    )

    message = (
        "🔥 Hedef fiyat yakalandı!\n\n"
        f"Ürün: {product['name']}\n"
        f"Hedef fiyat: {product['target_price']:,.0f} TL\n"
        f"Bulunan fiyat: {cheapest['price_text']}\n"
        f"Mağaza: {cheapest['store']}\n\n"
        f"Link:\n{cheapest['url']}\n\n"
        f"Bulunan diğer sonuçlar:\n{other_results}"
    )

    send_telegram(message)

    state[product["name"]] = {
        "last_alert_key": alert_key,
        "last_price": cheapest["price"],
        "last_store": cheapest["store"],
        "last_url": cheapest["url"]
    }

    return state


def main():
    state = load_state()

    for product in PRODUCTS:
        state = check_product(product, state)

    save_state(state)


if __name__ == "__main__":
    main()
